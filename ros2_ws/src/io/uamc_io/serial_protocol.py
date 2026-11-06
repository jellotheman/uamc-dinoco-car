"""Known sender framing; receiver behavior remains unverified."""
import math


def encode_command(steer, throttle):
    if not all(isinstance(v, (float, int)) and not isinstance(v, bool) and math.isfinite(v) and -1 <= v <= 1 for v in (steer, throttle)):
        raise ValueError('invalid normalized command')
    def fmt(value):
        text = f'{value:.3f}'
        return '0.000' if text == '-0.000' else text
    return f'S,{fmt(steer)},{fmt(throttle)}\n'.encode('ascii')
