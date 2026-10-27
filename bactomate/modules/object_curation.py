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
        rows = {self.peak_key(row): dict(row) for row in [*failed, *passed]}
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
