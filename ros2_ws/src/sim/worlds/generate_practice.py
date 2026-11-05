#!/usr/bin/env python3
"""Regenerate practice markings with 0.45 m between their inner paint edges.

The original centerline is preserved: a 2 m straight followed by a left turn
of radius 3 m through 1.2 rad. The obstacle stays at turn angle 0.95 rad.
Run this file from any directory; it updates practice.sdf and its metadata.
"""
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from generate_hairpin import (CLEAR_LANE_WIDTH, LANE_WIDTH, LINE_WIDTH,
                              add_text, add_visual, arc_position, pose_text)

STRAIGHT_LENGTH = 2.0
TURN_RADIUS = 3.0
TURN_ANGLE = 1.2
TURN_STEPS = 48
BOX_ANGLE = 0.95


def centerline_metadata():
    end_x, end_y = arc_position(STRAIGHT_LENGTH, 0, 0, TURN_RADIUS, TURN_ANGLE)
    box_x, box_y = arc_position(STRAIGHT_LENGTH, 0, 0, TURN_RADIUS, BOX_ANGLE)
    return {'clear_lane_width_m': CLEAR_LANE_WIDTH,
            'lane_width_m': LANE_WIDTH, 'line_width_m': LINE_WIDTH,
            'centerline_length_m': STRAIGHT_LENGTH + TURN_RADIUS * TURN_ANGLE,
            'segments': [
                {'kind': 'straight', 'length_m': STRAIGHT_LENGTH,
                 'start': [0.0, 0.0, 0.0], 'end': [STRAIGHT_LENGTH, 0.0, 0.0]},
                {'kind': 'arc', 'length_m': TURN_RADIUS * TURN_ANGLE,
                 'radius_m': TURN_RADIUS, 'turn_rad': TURN_ANGLE,
                 'start': [STRAIGHT_LENGTH, 0.0, 0.0],
                 'end': [end_x, end_y, TURN_ANGLE]}],
            'obstacle': {'pose': [box_x, box_y, BOX_ANGLE],
                         'size_m': [0.25, 0.35, 0.30]}}


def generate():
    # Keep the original world environment and system plugins. Only regenerate
    # the lane markings from explicit centerline geometry.
    root = ET.fromstring(WORLD_ENVIRONMENT)
    world = root.find('world')
    lane = ET.SubElement(world, 'model', name='lane')
    add_text(lane, 'static', 'true')
    markings = ET.SubElement(lane, 'link', name='markings')
    for side, offset in (('left', LANE_WIDTH / 2), ('right', -LANE_WIDTH / 2)):
        add_visual(markings, 'lane_' + side + '_straight',
                   STRAIGHT_LENGTH / 2, offset, 0, STRAIGHT_LENGTH + .002)
    delta = TURN_ANGLE / TURN_STEPS
    for step in range(TURN_STEPS):
        heading = (step + .5) * delta
        x, y = arc_position(STRAIGHT_LENGTH, 0, 0, TURN_RADIUS, heading)
        for side, offset in (('left', LANE_WIDTH / 2), ('right', -LANE_WIDTH / 2)):
            radius = TURN_RADIUS - offset
            chord = 2 * radius * math.sin(delta / 2)
            add_visual(markings, f'lane_{side}_arc_{step:04}',
                       x - offset * math.sin(heading), y + offset * math.cos(heading),
                       heading, chord + .002)
    obstacle = ET.SubElement(world, 'model', name='obstacle')
    add_text(obstacle, 'static', 'true')
    x, y, yaw = centerline_metadata()['obstacle']['pose']
    add_text(obstacle, 'pose', pose_text((x, y, .15, 0, 0, yaw)))
    link = ET.SubElement(obstacle, 'link', name='box')
    for kind in ('collision', 'visual'):
        item = ET.SubElement(link, kind, name=kind)
        box = ET.SubElement(ET.SubElement(item, 'geometry'), 'box')
        add_text(box, 'size', '.25 .35 .30')
        if kind == 'visual':
            material = ET.SubElement(item, 'material')
            add_text(material, 'ambient', '.8 .1 .05 1')
            add_text(material, 'diffuse', '.8 .1 .05 1')
    ET.indent(root, space='  ')
    return ET.tostring(root, encoding='unicode', xml_declaration=True) + '\n'


WORLD_ENVIRONMENT = '''<sdf version="1.9"><world name="practice">
<physics name="physics" type="ignored"><max_step_size>0.002</max_step_size><real_time_factor>1</real_time_factor></physics>
<plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
<plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
<plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
<plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors"><render_engine>ogre2</render_engine></plugin>
<plugin filename="gz-sim-imu-system" name="gz::sim::systems::Imu"/>
<light name="sun" type="directional"><pose>0 0 10 0 0 0</pose><diffuse>0.9 0.9 0.9 1</diffuse><specular>0.1 0.1 0.1 1</specular><direction>-0.4 0.1 -0.9</direction></light>
<model name="ground"><static>true</static><link name="ground_link"><collision name="collision"><geometry><plane><normal>0 0 1</normal><size>20 20</size></plane></geometry></collision><visual name="surface"><geometry><plane><normal>0 0 1</normal><size>20 20</size></plane></geometry><material><ambient>0.12 0.12 0.12 1</ambient><diffuse>0.12 0.12 0.12 1</diffuse></material></visual></link></model>
</world></sdf>'''


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stdout', action='store_true', help='print SDF instead of writing files')
    args = parser.parse_args()
    if args.stdout:
        print(generate(), end='')
    else:
        Path(__file__).with_name('practice.sdf').write_text(generate(), encoding='utf-8')
        Path(__file__).with_name('practice_geometry.json').write_text(
            json.dumps(centerline_metadata(), indent=2) + '\n', encoding='utf-8')
