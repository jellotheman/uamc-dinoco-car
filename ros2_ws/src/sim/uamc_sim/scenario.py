"""Resolve packaged simulation scenarios before starting any process."""
from dataclasses import dataclass
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import yaml


@dataclass(frozen=True)
class Scenario:
    name: str
    world: str
    world_name: str
    rviz_config: str
    spawn: tuple
    node_parameters: str | None


def _packaged_asset(root, value, kind):
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError(f'{kind} must be a relative packaged path')
    relative = Path(value)
    if '..' in relative.parts:
        raise ValueError(f'{kind} must stay inside the simulation package')
    path = root / relative
    if not path.is_file():
        raise ValueError(f'{kind} not found: {path}')
    return str(path)


def _yaml_file(path, kind):
    try:
        with open(path, encoding='utf-8') as stream:
            value = yaml.safe_load(stream)
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f'invalid {kind} {path}: {exc}') from exc
    if not isinstance(value, dict):
        raise ValueError(f'{kind} must be a YAML mapping: {path}')
    return value


def validate_parameters(path):
    """Validate ROS parameter-file structure before spawning nodes."""
    parameters = _yaml_file(path, 'node parameters')
    if not parameters:
        raise ValueError(f'node parameters must not be empty: {path}')
    for node, configuration in parameters.items():
        if not isinstance(node, str) or not node or '*' in node or not isinstance(configuration, dict):
            raise ValueError(f'invalid node parameters entry in {path}')
        # Exact node selectors keep a tuning override scoped to named nodes.
        if not isinstance(configuration.get('ros__parameters'), dict):
            raise ValueError(f'node {node!r} lacks a ros__parameters mapping in {path}')
    # Use the same native ROS argument parser used during node initialization:
    # generic YAML parsing alone accepts mixed arrays and unsupported scalar types.
    from rclpy.utilities import remove_ros_args
    try:
        remove_ros_args(['uamc-validation', '--ros-args', '--params-file', str(path)])
    except Exception as exc:
        raise ValueError(f'invalid ROS node parameters {path}: {exc}') from exc
    return str(path)


def resolve_scenario(package_share, name, parameter_override=''):
    if not isinstance(name, str) or not re.fullmatch(r'[a-z][a-z0-9_-]*', name):
        raise ValueError(f'invalid scenario name: {name!r}')
    root = Path(package_share)
    manifest = root / 'scenarios' / (name + '.yaml')
    if not manifest.is_file():
        raise ValueError(f'unknown scenario {name!r}: {manifest} not found')
    profile = _yaml_file(manifest, 'scenario profile')
    allowed = {'world', 'rviz_config', 'spawn', 'node_parameters'}
    extra = set(profile) - allowed
    if extra:
        raise ValueError(f'unknown scenario fields: {sorted(extra)}')
    world = _packaged_asset(root, profile.get('world'), 'world')
    rviz = _packaged_asset(root, profile.get('rviz_config'), 'RViz configuration')
    _yaml_file(rviz, 'RViz configuration')
    try:
        tree = ET.parse(world)
    except (ET.ParseError, OSError) as exc:
        raise ValueError(f'invalid world SDF {world}: {exc}') from exc
    worlds = tree.getroot().findall('world')
    if tree.getroot().tag != 'sdf' or len(worlds) != 1:
        raise ValueError(f'world SDF must contain exactly one world: {world}')
    world_name = worlds[0].get('name', '')
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', world_name):
        raise ValueError(f'invalid SDF world name: {world_name!r}')
    spawn = profile.get('spawn')
    if not isinstance(spawn, dict) or set(spawn) != {'x', 'y', 'z', 'yaw'}:
        raise ValueError('spawn must specify exactly x, y, z and yaw')
    coordinates = []
    for key in ('x', 'y', 'z', 'yaw'):
        val = spawn[key]
        if isinstance(val, bool) or not isinstance(val, (float, int)) or not math.isfinite(val):
            raise ValueError(f'spawn {key} must be a finite number')
        coordinates.append(float(val))
    params = None
    if parameter_override:
        override = Path(parameter_override).expanduser()
        if not override.is_file():
            raise ValueError(f'node parameters not found: {override}')
        params = validate_parameters(override)
    elif profile.get('node_parameters') is not None:
        params = validate_parameters(_packaged_asset(root, profile['node_parameters'], 'node parameters'))
    return Scenario(name, world, world_name, rviz, tuple(coordinates), params)
