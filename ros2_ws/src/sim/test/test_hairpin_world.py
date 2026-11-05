"""Geometry checks against the generated SDF, without running a simulator."""
import importlib.util
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET


WORLDS = Path(__file__).resolve().parents[1] / 'worlds'


def test_hairpin_artifacts_are_reproducible_and_have_sensors():
    spec = importlib.util.spec_from_file_location('hairpin_generator', WORLDS / 'generate_hairpin.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert (WORLDS / 'hairpin.sdf').read_text() == module.generate()
    assert json.loads((WORLDS / 'hairpin_geometry.json').read_text()) == module.centerline_metadata()
    root = ET.parse(WORLDS / 'hairpin.sdf').getroot()
    worlds = root.findall('world')
    assert len(worlds) == 1 and worlds[0].get('name') == 'hairpin'
    assert {p.get('name').split('::')[-1] for p in worlds[0].findall('plugin')} == {
        'Physics', 'UserCommands', 'SceneBroadcaster', 'Sensors', 'Imu'}


def test_markings_are_paired_continuous_and_have_wide_turns():
    world = ET.parse(WORLDS / 'hairpin.sdf').getroot().find('world')
    link = world.find("./model[@name='lane']/link")
    markings = {v.get('name'): v for v in link.findall('visual')}
    left = sorted(name for name in markings if name.startswith('lane_left_'))
    right = sorted(name for name in markings if name.startswith('lane_right_'))
    assert len(left) == len(right) > 100
    previous = None
    max_curvature = 0.0
    left_rotation = right_rotation = 0.0
    for a, b in zip(left, right):
        assert a.removeprefix('lane_left_') == b.removeprefix('lane_right_')
        l = markings[a]
        r = markings[b]
        lp = list(map(float, l.findtext('pose').split()))
        rp = list(map(float, r.findtext('pose').split()))
        ll, lw, _ = map(float, l.findtext('./geometry/box/size').split())
        rl, rw, _ = map(float, r.findtext('./geometry/box/size').split())
        assert abs(math.hypot(lp[0] - rp[0], lp[1] - rp[1]) - .485) < 1e-6
        assert abs(math.hypot(lp[0] - rp[0], lp[1] - rp[1]) - (lw + rw)/2 - .45) < 1e-6
        assert abs(lw - .035) < 1e-8 and abs(rw - .035) < 1e-8
        assert abs(lp[5] - rp[5]) < 1e-8
        center = ((lp[0]+rp[0])/2, (lp[1]+rp[1])/2, lp[5], (ll+rl)/2)
        if previous is not None:
            px, py, ph, plen = previous
            x, y, h, length = center
            prev_end = (px + math.cos(ph)*plen/2, py + math.sin(ph)*plen/2)
            curr_start = (x - math.cos(h)*length/2, y - math.sin(h)*length/2)
            assert math.dist(prev_end, curr_start) < .005
            delta = h - ph
            if plen < .2 and length < .2:
                separation = math.hypot(x-px, y-py)
                curvature = abs(2 * math.sin(delta/2) / separation)
                max_curvature = max(max_curvature, curvature)
            if delta > 0:
                left_rotation += delta
            else:
                right_rotation += delta
        previous = center
    assert 1 / max_curvature >= 3.49
    assert left_rotation > math.pi and right_rotation < -math.pi


def test_course_length_tangency_and_box_clearance():
    metadata = json.loads((WORLDS / 'hairpin_geometry.json').read_text())
    assert 35 <= metadata['centerline_length_m'] <= 50
    segments = metadata['segments']
    assert len(segments) == 7
    for first, second in zip(segments, segments[1:]):
        assert math.dist(first['end'][:2], second['start'][:2]) < 1e-8
        assert abs(first['end'][2] - second['start'][2]) < 1e-8
    assert any(s['kind'] == 'arc' and s['turn_rad'] >= math.pi for s in segments)
    assert any(s['kind'] == 'arc' and s['turn_rad'] <= -math.pi for s in segments)
    assert all(s['radius_m'] >= 3.5 for s in segments if s['kind'] == 'arc')
    final = segments[-1]
    box = metadata['obstacle']['pose']
    assert final['kind'] == 'straight'
    assert abs(math.dist(final['start'][:2], box[:2]) - 4.0) < 1e-8
    assert abs(math.dist(final['end'][:2], box[:2]) - 2.0) < 1e-8
    root = ET.parse(WORLDS / 'hairpin.sdf').getroot()
    pose = list(map(float, root.findtext("./world/model[@name='obstacle']/pose").split()))
    assert math.dist(pose[:2], box[:2]) < 1e-8
    assert abs(pose[5] - box[2]) < 1e-8
    assert pose[2] == .15  # 0.30 m-high box crosses the simulated scan plane.


def test_distant_path_sections_do_not_intersect_or_crowd():
    metadata = json.loads((WORLDS / 'hairpin_geometry.json').read_text())
    points = []
    elapsed = 0.0
    for segment in metadata['segments']:
        x, y, heading = segment['start']
        count = math.ceil(segment['length_m'] / .1)
        for i in range(count):
            distance = segment['length_m'] * i / count
            if segment['kind'] == 'straight':
                px = x + distance * math.cos(heading)
                py = y + distance * math.sin(heading)
            else:
                curvature = math.copysign(1 / segment['radius_m'], segment['turn_rad'])
                px = x + (math.sin(heading + curvature * distance) - math.sin(heading)) / curvature
                py = y - (math.cos(heading + curvature * distance) - math.cos(heading)) / curvature
            points.append((elapsed + distance, px, py))
        elapsed += segment['length_m']
    separated = [math.hypot(a[1]-b[1], a[2]-b[2])
                 for i, a in enumerate(points) for b in points[i+1:]
                 if b[0]-a[0] >= 3.0]
    # The narrower lane leaves over 2 m between remote boundaries.
    assert min(separated) > 2.8
