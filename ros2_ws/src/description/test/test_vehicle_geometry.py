"""Check expanded geometry, drivetrain consistency and the safety envelope."""
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
import xacro


MODEL = Path(__file__).resolve().parents[1] / 'urdf' / 'vehicle.urdf.xacro'


@pytest.fixture(scope='module')
def robot():
    return ET.fromstring(xacro.process_file(str(MODEL)).toxml())


def values(element, attribute):
    return tuple(map(float, element.get(attribute).split()))


def test_reported_dimensions_and_body_envelope(robot):
    body = robot.find("./link[@name='base_link']")
    for kind in ('visual', 'collision'):
        shape = body.find(kind)
        length, width, height = values(shape.find('./geometry/box'), 'size')
        x, _, z = values(shape.find('origin'), 'xyz')
        assert length == pytest.approx(.345)
        assert width == pytest.approx(.120)  # Chassis width remains an assumption.
        assert x == pytest.approx(.232 / 2)
        assert z + height / 2 + .045 == pytest.approx(.160)
        assert z - height / 2 > 0


def test_wheels_and_ackermann_plugin_agree(robot):
    wheel_centers = {}
    for name in ('front_left', 'front_right', 'rear_left', 'rear_right'):
        joint_name = name + ('_steer_joint' if name.startswith('front') else '_wheel_joint')
        wheel_centers[name] = values(robot.find(f"./joint[@name='{joint_name}']/origin"), 'xyz')
        wheel = robot.find(f"./link[@name='{name}_wheel']")
        for kind in ('visual', 'collision'):
            cylinder = wheel.find(f'./{kind}/geometry/cylinder')
            assert float(cylinder.get('radius')) == pytest.approx(.090 / 2)
            assert float(cylinder.get('length')) == pytest.approx(.038)
    assert wheel_centers == {
        'front_left': (.232, .0825, 0), 'front_right': (.232, -.0825, 0),
        'rear_left': (0, .0825, 0), 'rear_right': (0, -.0825, 0)}
    plugin = robot.find("./gazebo/plugin[@name='gz::sim::systems::AckermannSteering']")
    for key, expected in (('wheel_base', .232), ('wheel_separation', .165),
                          ('kingpin_width', .165), ('wheel_radius', .045)):
        assert float(plugin.findtext(key)) == pytest.approx(expected)
    # Published overall width and center track + tire width differ by 2 mm.
    # Preserve both reports instead of silently widening the wheel-center track.
    straight_tire_width = wheel_centers['rear_left'][1] - wheel_centers['rear_right'][1] + .038
    assert .205 - straight_tire_width == pytest.approx(.002)


def test_existing_conservative_obstacle_envelope_contains_steered_tires(robot):
    # The perception footprint stays at front=.30, rear=.10, half_width=.13.
    # Stock overall width alone would miss the outside of a steered front tire.
    for name in ('front_left', 'front_right', 'rear_left', 'rear_right'):
        front = name.startswith('front')
        joint_name = name + ('_steer_joint' if front else '_wheel_joint')
        joint = robot.find(f"./joint[@name='{joint_name}']")
        x, y, _ = values(joint.find('origin'), 'xyz')
        if front:
            limit = joint.find('limit')
            angles = (float(limit.get('lower')), 0., float(limit.get('upper')))
        else:
            angles = (0.,)
        wheel = robot.find(f"./link[@name='{name}_wheel']/collision/geometry/cylinder")
        radius, half_width = float(wheel.get('radius')), float(wheel.get('length')) / 2
        for angle in angles:
            for dx in (-radius, radius):
                for dy in (-half_width, half_width):
                    px = x + dx * math.cos(angle) - dy * math.sin(angle)
                    py = y + dx * math.sin(angle) + dy * math.cos(angle)
                    assert -.10 <= px <= .30
                    assert abs(py) <= .13
    shape = robot.find("./link[@name='base_link']/collision")
    length, width, _ = values(shape.find('./geometry/box'), 'size')
    x, y, _ = values(shape.find('origin'), 'xyz')
    assert x - length / 2 >= -.10 and x + length / 2 <= .30
    assert abs(y) + width / 2 <= .13


def test_sensor_mounts_stay_above_simplified_chassis(robot):
    # Stock height does not locate the added sensors on the modified car.
    body = robot.find("./link[@name='base_link']/collision")
    top = values(body.find('origin'), 'xyz')[2] + values(body.find('./geometry/box'), 'size')[2] / 2
    for name, expected in (('camera_mount', (.20, 0, .17)), ('laser_mount', (.23, 0, .13))):
        xyz = values(robot.find(f"./joint[@name='{name}']/origin"), 'xyz')
        assert xyz == pytest.approx(expected)
        assert xyz[2] > top
