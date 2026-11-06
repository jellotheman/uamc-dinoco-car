"""Strict measured, open-loop actuator maps; no extrapolation."""
import math
import yaml


class _UniqueLoader(yaml.SafeLoader):
    pass


def _mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise ValueError('duplicate or invalid calibration key')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError('calibration values must be finite numbers')
    return float(value)


def _keys(obj, keys):
    if not isinstance(obj, dict) or set(obj) != set(keys):
        raise ValueError('calibration keys do not match schema')


def load_calibration(path):
    with open(path, encoding='utf-8') as stream:
        data = yaml.load(stream, Loader=_UniqueLoader)
    _keys(data, ('version', 'provenance', 'steering', 'throttle'))
    if type(data['version']) is not int or data['version'] != 1:
        raise ValueError('unsupported calibration version')
    provenance = data['provenance']
    _keys(provenance, ('board', 'firmware', 'esc', 'servo', 'measured_on', 'method', 'conditions', 'reference'))
    for value in provenance.values():
        if (not isinstance(value, str) or not value.strip() or
                value.strip().lower() in ('todo', 'unknown', 'placeholder', 'tbd', 'example', 'unmeasured', 'none')):
            raise ValueError('measured provenance is required')
    for name, deadband in (('steering', 'deadband_rad'), ('throttle', 'deadband_mps')):
        section = data[name]
        _keys(section, ('samples', deadband))
        band = _number(section[deadband])
        if band < 0:
            raise ValueError('negative deadband')
        samples = section['samples']
        if not isinstance(samples, list) or len(samples) < (3 if name == 'steering' else 2):
            raise ValueError('insufficient samples')
        values = []
        for point in samples:
            if not isinstance(point, list) or len(point) != 2:
                raise ValueError('sample must contain input and output')
            x, y = map(_number, point)
            if not -1 <= y <= 1:
                raise ValueError('output outside normalized range')
            values.append((x, y))
        if any(a[0] >= b[0] for a, b in zip(values, values[1:])):
            raise ValueError('inputs must be strictly increasing')
        diffs = [b[1] - a[1] for a, b in zip(values, values[1:])]
        if not (all(d > 0 for d in diffs) or all(d < 0 for d in diffs)):
            raise ValueError('outputs must be strictly monotonic')
        if name == 'steering':
            if not values[0][0] < 0 < values[-1][0] or sum(x == 0 for x, _ in values) != 1 or band >= min(-values[0][0], values[-1][0]):
                raise ValueError('steering needs both directions and a zero center')
        elif values[0][0] != 0 or values[1][0] <= band or values[-1][0] <= 0:
            raise ValueError('throttle needs neutral and a measured moving envelope')
    return data


def validate_caps(data, max_speed, max_steer):
    speed, steer = _number(max_speed), _number(max_steer)
    s = data['steering']['samples']
    t = data['throttle']['samples']
    if speed < t[1][0] or steer <= 0 or speed > t[-1][0] or -steer < s[0][0] or steer > s[-1][0]:
        raise ValueError('operating caps exceed measured envelope')


def _interp(samples, x):
    if x < samples[0][0] or x > samples[-1][0]:
        raise ValueError('target outside measured envelope')
    for (x0, y0), (x1, y1) in zip(samples, samples[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return samples[-1][1]


def map_command(data, speed, steer):
    speed, steer = _number(speed), _number(steer)
    s, t = data['steering'], data['throttle']
    if speed < 0:
        raise ValueError('reverse unsupported')
    if 0 < speed < t['samples'][1][0]:
        speed = 0.0
    if abs(steer) <= s['deadband_rad']:
        steer = 0.0
    return _interp(s['samples'], steer), _interp(t['samples'], speed)
