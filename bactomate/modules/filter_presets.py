"""Portable, versioned cell and per-channel foci filter settings."""
import json
import math
import re
from pathlib import Path

FORMAT = 'bactomate-filter-settings'


def validate_settings(settings, defaults):
    if not isinstance(settings, dict):
        raise ValueError('Filter settings must be an object.')
    result = dict(defaults)
    for key, value in settings.items():
        if key == 'foci_channels':
            from bactomate.gui.filter_preview_utils import default_foci_channel_settings
            if not isinstance(value, dict):
                raise ValueError('foci_channels must be an object.')
            result[key] = {str(channel): validate_settings(block, default_foci_channel_settings())
                           for channel, block in value.items()}
            continue
        if key not in defaults:
            raise ValueError(f'Unknown filter setting: {key}')
        expected = defaults[key]
        if isinstance(expected, bool):
            valid = isinstance(value, bool)
        elif isinstance(expected, str):
            valid = isinstance(value, str) and value in ('phase', 'brightfield')
        else:
            valid = (value is None and expected is None) or (
                isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(value) and (not isinstance(expected, int) or isinstance(value, int)))
        if not valid:
            raise ValueError(f'Invalid value for {key}: {value!r}')
        result[key] = value
    return result


def save_filter_preset(path, settings):
    payload = {'format': FORMAT, 'version': 1, 'filter_settings': settings}
    Path(path).write_text(json.dumps(payload, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def load_filter_preset(path, defaults):
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, dict) or payload.get('format') != FORMAT or payload.get('version') != 1:
        raise ValueError('This is not a supported BactoMate filter settings file (version 1).')
    scope = payload.get('scope', 'all')
    if scope == 'cells':
        return validate_settings(payload.get('filter_settings'),
                                 {k: v for k, v in defaults.items() if not k.startswith('foci_')})
    if scope == 'foci':
        from bactomate.gui.filter_preview_utils import default_foci_channel_settings
        channel = payload.get('channel')
        if not isinstance(channel, str) or not channel.strip() or channel == '_default':
            raise ValueError('A foci settings file must identify its channel.')
        block = validate_settings(payload.get('filter_settings'), default_foci_channel_settings())
        return {'foci_channels': {channel: block}}
    if scope != 'all':
        raise ValueError('Unknown filter settings scope.')
    return validate_settings(payload.get('filter_settings'), defaults)


def save_separate_filter_presets(path, settings):
    """Export cells and one independent file for each known fluorescence channel."""
    from bactomate.gui.filter_preview_utils import ensure_foci_channels_map
    path = Path(path)
    stem = path.stem
    channels = ensure_foci_channels_map(dict(settings))
    blocks = [('cells', None, {k: v for k, v in settings.items() if not k.startswith('foci_')})]
    blocks += [('foci', channel, block) for channel, block in channels.items() if channel != '_default']
    written = []
    for index, (scope, channel, block) in enumerate(blocks):
        safe_channel = re.sub(r'[^\w.-]+', '_', channel or '')
        suffix = 'cells' if channel is None else f'foci_{index:02d}_{safe_channel}'
        target = path.with_name(f'{stem}.{suffix}.json')
        payload = {'format': FORMAT, 'version': 1, 'scope': scope, 'filter_settings': block}
        if channel is not None:
            payload['channel'] = channel
        target.write_text(json.dumps(payload, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        written.append(target)
    return written
