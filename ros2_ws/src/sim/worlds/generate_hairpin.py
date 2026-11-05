#!/usr/bin/env python3
"""Generate the deterministic hairpin course with 0.45 m clear lane width.

The geometry is authored here so both sides of the markings and the final box
come from one sequence of straight/constant-curvature centerline segments.
Regenerate with: python3 generate_hairpin.py
"""
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

# Clear width is measured between inner paint edges, not line centers.
CLEAR_LANE_WIDTH = 0.45
LINE_WIDTH = 0.035
LANE_WIDTH = CLEAR_LANE_WIDTH + LINE_WIDTH
ARC_STEP = 0.15
# Signed turn angle and radius must have the same sign; all motion is forward.
SEGMENTS = (
    ('straight', 5.0),
    ('arc', 3.5, math.pi),
    ('straight', 5.0),
    ('arc', -3.5, -math.pi),
    ('arc', 5.0, 0.18),
    ('arc', -5.0, -0.18),
    ('straight', 6.0),
)
BOX_DISTANCE_ON_FINAL = 4.0


def pose_text(values):
    return ' '.join(f'{value:.9f}' for value in values)


def add_text(parent, name, value):
    element = ET.SubElement(parent, name)
    element.text = str(value)
    return element


def add_visual(link, name, x, y, yaw, length):
    visual = ET.SubElement(link, 'visual', name=name)
    add_text(visual, 'pose', pose_text((x, y, .002, 0, 0, yaw)))
    box = ET.SubElement(ET.SubElement(visual, 'geometry'), 'box')
    add_text(box, 'size', pose_text((length, LINE_WIDTH, .002)))
    material = ET.SubElement(visual, 'material')
    add_text(material, 'ambient', '1 1 1 1')
    add_text(material, 'diffuse', '1 1 1 1')


def arc_position(x, y, heading, radius, angle):
    return (x + radius * (math.sin(heading + angle) - math.sin(heading)),
            y - radius * (math.cos(heading + angle) - math.cos(heading)))


def centerline_metadata():
    x = y = heading = total = 0.0
    records = []
    for segment in SEGMENTS:
        start = [x, y, heading]
        if segment[0] == 'straight':
            distance = segment[1]
            x += distance * math.cos(heading)
            y += distance * math.sin(heading)
            record = {'kind': 'straight', 'length_m': distance}
        else:
            _, radius, angle = segment
            distance = radius * angle
            x, y = arc_position(x, y, heading, radius, angle)
            heading += angle
            record = {'kind': 'arc', 'length_m': distance,
                      'radius_m': abs(radius), 'turn_rad': angle}
        total += distance
        record.update(start=start, end=[x, y, heading])
        records.append(record)
    fx, fy, fh = records[-1]['start']
    return {'clear_lane_width_m': CLEAR_LANE_WIDTH,
            'lane_width_m': LANE_WIDTH, 'line_width_m': LINE_WIDTH,
            'centerline_length_m': total, 'segments': records,
            'obstacle': {'pose': [fx + BOX_DISTANCE_ON_FINAL * math.cos(fh),
                                  fy + BOX_DISTANCE_ON_FINAL * math.sin(fh), fh],
                         'size_m': [0.25, 0.35, 0.30]}}


def generate():
    root = ET.Element('sdf', version='1.9')
    world = ET.SubElement(root, 'world', name='hairpin')
    physics = ET.SubElement(world, 'physics', name='physics', type='ignored')
    add_text(physics, 'max_step_size', '.002')
    add_text(physics, 'real_time_factor', '1')
    for filename, name in (
        ('gz-sim-physics-system', 'Physics'),
        ('gz-sim-user-commands-system', 'UserCommands'),
        ('gz-sim-scene-broadcaster-system', 'SceneBroadcaster'),
        ('gz-sim-sensors-system', 'Sensors'),
        ('gz-sim-imu-system', 'Imu'),
    ):
        plugin = ET.SubElement(world, 'plugin', filename=filename,
                               name='gz::sim::systems::' + name)
        if name == 'Sensors':
            add_text(plugin, 'render_engine', 'ogre2')
    light = ET.SubElement(world, 'light', name='sun', type='directional')
    for tag, value in (('pose', '0 0 10 0 0 0'), ('diffuse', '.9 .9 .9 1'),
                       ('specular', '.1 .1 .1 1'), ('direction', '-.4 .1 -.9')):
        add_text(light, tag, value)
    ground = ET.SubElement(world, 'model', name='ground')
    add_text(ground, 'static', 'true')
    add_text(ground, 'pose', '2.5 7 0 0 0 0')
    ground_link = ET.SubElement(ground, 'link', name='ground_link')
    for kind in ('collision', 'visual'):
        item = ET.SubElement(ground_link, kind, name='surface' if kind == 'visual' else 'collision')
        plane = ET.SubElement(ET.SubElement(item, 'geometry'), 'plane')
        add_text(plane, 'normal', '0 0 1')
        add_text(plane, 'size', '30 30')
        if kind == 'visual':
            material = ET.SubElement(item, 'material')
            add_text(material, 'ambient', '.12 .12 .12 1')
            add_text(material, 'diffuse', '.12 .12 .12 1')
    lane = ET.SubElement(world, 'model', name='lane')
    add_text(lane, 'static', 'true')
    markings = ET.SubElement(lane, 'link', name='markings')
    x = y = heading = 0.0
    index = 0
    final_origin = None
    for segment in SEGMENTS:
        if segment[0] == 'straight':
            length = segment[1]
            if segment is SEGMENTS[-1]:
                final_origin = (x, y, heading)
            mx = x + length / 2 * math.cos(heading)
            my = y + length / 2 * math.sin(heading)
            for side, offset in (('left', LANE_WIDTH / 2), ('right', -LANE_WIDTH / 2)):
                add_visual(markings, f'lane_{side}_{index:04}', mx - offset * math.sin(heading),
                           my + offset * math.cos(heading), heading, length + .002)
            x += length * math.cos(heading)
            y += length * math.sin(heading)
            index += 1
            continue
        _, radius, angle = segment
        assert radius * angle > 0
        steps = math.ceil(abs(radius * angle) / ARC_STEP)
        delta = angle / steps
        for step in range(steps):
            a = (step + .5) * delta
            mx, my = arc_position(x, y, heading, radius, a)
            h = heading + a
            for side, offset in (('left', LANE_WIDTH / 2), ('right', -LANE_WIDTH / 2)):
                # Each side travels a different chord length, while corresponding
                # chord midpoints remain LANE_WIDTH apart on the centerline normal.
                boundary_radius = abs(radius - offset)
                chord = 2 * boundary_radius * math.sin(abs(delta) / 2)
                add_visual(markings, f'lane_{side}_{index:04}', mx - offset * math.sin(h),
                           my + offset * math.cos(h), h, chord + .002)
            index += 1
        x, y = arc_position(x, y, heading, radius, angle)
        heading += angle
    assert final_origin is not None
    fx, fy, fh = final_origin
    obstacle = ET.SubElement(world, 'model', name='obstacle')
    add_text(obstacle, 'static', 'true')
    add_text(obstacle, 'pose', pose_text((fx + BOX_DISTANCE_ON_FINAL * math.cos(fh),
                                          fy + BOX_DISTANCE_ON_FINAL * math.sin(fh),
                                          .15, 0, 0, fh)))
    box_link = ET.SubElement(obstacle, 'link', name='box')
    for kind in ('collision', 'visual'):
        item = ET.SubElement(box_link, kind, name=kind)
        box = ET.SubElement(ET.SubElement(item, 'geometry'), 'box')
        add_text(box, 'size', '.25 .35 .30')
        if kind == 'visual':
            material = ET.SubElement(item, 'material')
            add_text(material, 'ambient', '.8 .1 .05 1')
            add_text(material, 'diffuse', '.8 .1 .05 1')
    ET.indent(root, space='  ')
    return ET.tostring(root, encoding='unicode', xml_declaration=True) + '\n'


if __name__ == '__main__':
    Path(__file__).with_name('hairpin.sdf').write_text(generate(), encoding='utf-8')
    Path(__file__).with_name('hairpin_geometry.json').write_text(
        json.dumps(centerline_metadata(), indent=2) + '\n', encoding='utf-8')
