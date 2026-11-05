"""Check the minimum-width practice course against its preserved route."""
import json
import math
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET


WORLDS = Path(__file__).resolve().parents[1] / 'worlds'


def test_practice_artifact_is_reproducible():
    generated = subprocess.check_output(
        [sys.executable, str(WORLDS / 'generate_practice.py'), '--stdout'], text=True)
    assert generated == (WORLDS / 'practice.sdf').read_text()


def test_both_courses_use_45cm_clear_width_and_preserve_practice_route():
    for name in ('practice', 'hairpin'):
        metadata = json.loads((WORLDS / f'{name}_geometry.json').read_text())
        assert metadata['clear_lane_width_m'] == .45
        assert abs(metadata['lane_width_m'] - metadata['line_width_m'] - .45) < 1e-9
        world = ET.parse(WORLDS / f'{name}.sdf').getroot().find('world')
        link = world.find("./model[@name='lane']/link")
        left = {v.get('name').removeprefix('lane_left_'): v for v in link.findall('visual')
                if v.get('name').startswith('lane_left_')}
        right = {v.get('name').removeprefix('lane_right_'): v for v in link.findall('visual')
                 if v.get('name').startswith('lane_right_')}
        assert left.keys() == right.keys()
        for suffix, l in left.items():
            r = right[suffix]
            lp = list(map(float, l.findtext('pose').split()))
            rp = list(map(float, r.findtext('pose').split()))
            lw = float(l.findtext('./geometry/box/size').split()[1])
            rw = float(r.findtext('./geometry/box/size').split()[1])
            # Width is measured across each paired marking's normal.
            separation = abs(-(lp[0]-rp[0])*math.sin(lp[5]) +
                             (lp[1]-rp[1])*math.cos(lp[5]))
            assert abs(separation - (lw + rw)/2 - .45) < 1e-8
    metadata = json.loads((WORLDS / 'practice_geometry.json').read_text())
    straight, turn = metadata['segments']
    assert straight['end'] == turn['start'] == [2, 0, 0]
    assert turn['radius_m'] == 3 and turn['turn_rad'] == 1.2
    assert abs(metadata['centerline_length_m'] - 5.6) < 1e-9
    world = ET.parse(WORLDS / 'practice.sdf').getroot().find('world')
    box = list(map(float, world.findtext("./model[@name='obstacle']/pose").split()))
    assert math.dist(box[:2], (4.440246514368122, 1.2549507316083492)) < 1e-8
    assert box[5] == .95
    assert {p.get('name').split('::')[-1] for p in world.findall('plugin')} == {
        'Physics', 'UserCommands', 'SceneBroadcaster', 'Sensors', 'Imu'}


def test_practice_markings_join_without_gaps():
    world = ET.parse(WORLDS / 'practice.sdf').getroot().find('world')
    link = world.find("./model[@name='lane']/link")
    for side in ('left', 'right'):
        visuals = {v.get('name'): v for v in link.findall('visual')}
        ordered = [visuals[f'lane_{side}_straight']] + [
            visuals[f'lane_{side}_arc_{i:04}'] for i in range(48)]
        previous_end = None
        for visual in ordered:
            x, y, _, _, _, heading = map(float, visual.findtext('pose').split())
            length = float(visual.findtext('./geometry/box/size').split()[0])
            start = (x - length/2*math.cos(heading), y - length/2*math.sin(heading))
            if previous_end is not None:
                assert math.dist(start, previous_end) < .003
            previous_end = (x + length/2*math.cos(heading), y + length/2*math.sin(heading))
