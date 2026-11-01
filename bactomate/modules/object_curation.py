"""Persistent object selection, scoped to a particular segmentation and timepoint."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


class ObjectCuration:
    def __init__(self, mask_path):
        self.mask_path = Path(mask_path).resolve()
        self.path = self.mask_path.with_name(self.mask_path.name + '.curation.json')
        with self.mask_path.open('rb') as stream:
            signature = hashlib.file_digest(stream, 'sha256').hexdigest()
        self.data = {'version': 1, 'segmentation_sha256': signature,
                     'cells': {}, 'foci': {}, 'history': []}
        if self.path.exists():
            saved = json.loads(self.path.read_text())
            if saved.get('version') != 1:
                raise ValueError('Unsupported curation file version')
            if saved.get('segmentation_sha256') == signature:
                self.data = saved
            else:
                raise ValueError('Segmentation changed: archive its curation file before curating new masks')

    def save(self):
        fd, name = tempfile.mkstemp(dir=self.path.parent, prefix=self.path.name, suffix='.tmp')
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(self.data, stream, indent=2, allow_nan=False)
            os.replace(name, self.path)
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
