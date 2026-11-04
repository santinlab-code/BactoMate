"""Persistent object selection, scoped to a particular segmentation and timepoint."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import tempfile
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


LOG = logging.getLogger('bactomate')


def _label_signature(path):
    """Identify label geometry, independent of TIFF metadata and integer storage."""
    import numpy as np
    import tifffile
    labels = np.asarray(tifffile.imread(path))
    if labels.ndim == 2:
        labels = labels[np.newaxis]
    if labels.ndim != 3 or not np.issubdtype(labels.dtype, np.integer) or (labels < 0).any():
        raise ValueError('Curation needs a YX or TYX integer segmentation mask.')
    digest = hashlib.sha256(str(labels.shape).encode('ascii'))
    # One plane at a time avoids an extra uint64 copy of an entire time-lapse.
    for plane in labels:
        digest.update(np.ascontiguousarray(plane, dtype='<u8').tobytes())
    return digest.hexdigest()


def _replace(source, destination):
    """Retry short Windows sharing/antivirus locks; keep other errors explicit."""
    for attempt in range(5):
        try:
            os.replace(source, destination)
            return
        except PermissionError as exc:
            if getattr(exc, 'winerror', None) not in (5, 32, 33) or attempt == 4:
                raise
            time.sleep(.05 * 2 ** attempt)


class ObjectCuration:
    def __init__(self, mask_path):
        self.mask_path = Path(mask_path).resolve()
        self.path = self.mask_path.with_name(self.mask_path.name + '.curation.json')
        self.archived_path = None
        self._source_stat = self._stat()
        with self.mask_path.open('rb') as stream:
            signature = hashlib.file_digest(stream, 'sha256').hexdigest()
        self.data = {'version': 1, 'segmentation_sha256': signature,
                     'cells': {}, 'foci': {}, 'history': []}
        if self.path.exists():
            saved_bytes = self.path.read_bytes()
            saved = json.loads(saved_bytes.decode('utf-8'))
            if saved.get('version') != 1:
                raise ValueError('Unsupported curation file version')
            if saved.get('segmentation_sha256') == signature:
                self.data = saved
            else:
                labels_signature = _label_signature(self.mask_path)
                if saved.get('segmentation_labels_sha256') == labels_signature:
                    # TIFF metadata/compression/dtype changed, but IDs and geometry did not.
                    self.data = saved
                    self.data['segmentation_sha256'] = signature
                else:
                    # Old IDs cannot be assigned to a new segmentation. Preserve the
                    # complete old record, carrying only portable filter parameters.
                    archive = self.path.parent / 'curation_archive'
                    archive.mkdir(exist_ok=True)
                    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
                    self.archived_path = archive / f'{self.path.stem}.{stamp}.{uuid4().hex[:8]}.json'
                    # Keep the active JSON intact until its replacement succeeds.
                    with self.archived_path.open('xb') as stream:
                        stream.write(saved_bytes)
                        stream.flush()
                        os.fsync(stream.fileno())
                    if isinstance(saved.get('filter_settings'), dict):
                        self.data['filter_settings'] = deepcopy(saved['filter_settings'])
                    LOG.warning(f'[Curation] New segmentation: archived old object decisions at {self.archived_path}; filter parameters retained.')
                self.data['segmentation_labels_sha256'] = labels_signature
                self.save()
        if 'segmentation_labels_sha256' not in self.data:
            self.data['segmentation_labels_sha256'] = _label_signature(self.mask_path)
        self._clean_old_temporary_files()

    def _stat(self):
        stat = self.mask_path.stat()
        return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)

    def _check_source(self):
        current = self._stat()
        if current == self._source_stat:
            return
        with self.mask_path.open('rb') as stream:
            signature = hashlib.file_digest(stream, 'sha256').hexdigest()
        if signature != self.data['segmentation_sha256']:
            if _label_signature(self.mask_path) != self.data.get('segmentation_labels_sha256'):
                raise ValueError('Segmentation changed while Filtering was open. Reopen Filtering before editing the new masks.')
            self.data['segmentation_sha256'] = signature
        self._source_stat = current

    def _clean_old_temporary_files(self):
        # Only this writer's exact scratch names, older than a day. Never load
        # unfinished writes as curation or touch another mask's temporary files.
        pattern = re.compile(re.escape(self.path.name) + r'[a-z0-9_]{8}\.tmp')
        for path in self.path.parent.glob(self.path.name + '*.tmp'):
            try:
                if pattern.fullmatch(path.name) and path.stat().st_mtime < time.time() - 86400:
                    path.unlink()
            except OSError:
                LOG.debug(f'[Curation] Could not remove old scratch file {path}')

    def save(self):
        self._check_source()
        fd, name = tempfile.mkstemp(dir=self.path.parent, prefix=self.path.name, suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(self.data, stream, indent=2, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            # Refuse a stale preview write if segmentation completed meanwhile.
            self._check_source()
            _replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def cells(self, frame, accepted, all_labels):
        result = set(accepted)
        for label, keep in self.data['cells'].get(str(int(frame)), {}).items():
            if keep:
                result.add(int(label))
            else:
                result.discard(int(label))
        return result & set(all_labels)

    @staticmethod
    def peak_key(row):
        return f"{int(float(row['y']))},{int(float(row['x']))}"

    def peaks(self, frame, channel, passed, failed):
        rules = self.data['foci'].get(str(channel), {}).get(str(int(frame)), {})
        rows={}
        for row in [*failed,*passed]:
            key=self.peak_key(row);previous=rows.get(key,{})
            rows[key]={**previous,**row}
            if previous.get('manual') or row.get('manual'):rows[key]['manual']=True
        selected = {self.peak_key(row) for row in passed}
        for key, keep in rules.items():
            if keep:
                selected.add(key)
            else:
                selected.discard(key)
        return ([row for key, row in rows.items() if key in selected],
                [row for key, row in rows.items() if key not in selected])

    def set_objects(self, kind, frame, objects, keep, *, channel=''):
        if kind not in ('cells', 'foci'):
            raise ValueError('Unknown object type')
        target = self.data[kind]
        if kind == 'foci':
            target = target.setdefault(str(channel), {})
        rules = target.setdefault(str(int(frame)), {})
        for obj in objects:
            key = str(int(obj)) if kind == 'cells' else self.peak_key(obj)
            if keep is None:
                rules.pop(key, None)
            else:
                rules[key] = bool(keep)
        self.save()

    def augment_masks(self,masks):
        import numpy as np
        from skimage.draw import polygon
        edits=self.data.get('manual_cells',{})
        if not edits:return masks
        key=(id(masks),repr(edits))
        if getattr(self,'_manual_mask_key',None)==key:return self._manual_mask_value
        out=np.asarray(masks).copy();stack=out[None] if out.ndim==2 else out
        for frame,objects in edits.items():
            if int(frame)>=len(stack):continue
            plane=stack[int(frame)]
            for item in objects:
                points=np.array(item['polygon'])
                rr,cc=polygon(points[:,1],points[:,0],shape=plane.shape)
                plane[rr,cc]=int(item['label'])
        self._manual_mask_key=key;self._manual_mask_value=out
        return out

    def add_cell(self,frame,points,masks):
        import numpy as np
        from skimage.draw import polygon
        points=np.asarray(points,dtype=float)
        if points.ndim!=2 or len(points)<3:raise ValueError('Draw at least three contour points.')
        if not np.isfinite(points).all():raise ValueError('Contour coordinates must be finite.')
        stack=np.asarray(self.augment_masks(masks));stack=stack[None] if stack.ndim==2 else stack
        rr,cc=polygon(points[:,1],points[:,0],shape=stack[int(frame)].shape)
        if len(rr)<3:raise ValueError('The contour is too small.')
        if np.any(stack[int(frame)][rr,cc]>0):raise ValueError('The new cell overlaps an existing cell. Draw in an unsegmented region.')
        label=int(stack.max())+1
        self.data.setdefault('manual_cells',{}).setdefault(str(int(frame)),[]).append(dict(label=label,polygon=points.tolist()))
        self.set_objects('cells',frame,[label],True)
        return label

    def augment_foci(self,rows,channel):
        result={(int(float(r.get('frame',0))),self.peak_key(r)):dict(r) for r in rows}
        for row in self.data.get('manual_foci',{}).get(str(channel),[]):
            result[(int(row['frame']),self.peak_key(row))]=dict(row)
        return list(result.values())

    def add_focus(self,frame,channel,x,y,intensity):
        import math
        if not all(math.isfinite(float(v)) for v in (x,y,intensity)):raise ValueError('Focus coordinates/intensity must be finite.')
        row=dict(frame=int(frame),x=int(x),y=int(y),intensity=float(intensity),manual=True)
        rows=self.data.setdefault('manual_foci',{}).setdefault(str(channel),[])
        if any(int(r['frame'])==int(frame) and self.peak_key(r)==self.peak_key(row) for r in rows):
            raise ValueError('A manual focus already exists at this position.')
        rows.append(row);self.set_objects('foci',frame,[row],True,channel=channel)
        return row

    def record(self, frame, total, selected, settings, *, action='Apply filters', foci=None):
        previous = next((h['selected'] for h in reversed(self.data['history'])
                         if h['frame'] == int(frame)), total)
        event = {'time': datetime.now(timezone.utc).isoformat(), 'frame': int(frame),
                 'action': action, 'total': int(total), 'before': int(previous),
                 'selected': int(selected), 'delta': int(selected - previous),
                 'settings': deepcopy(settings), 'foci': deepcopy(foci or {}),
                 'manual': deepcopy({'cells': self.data['cells'], 'foci': self.data['foci']})}
        self.data['history'].append(event)
        self.save()
        return event
