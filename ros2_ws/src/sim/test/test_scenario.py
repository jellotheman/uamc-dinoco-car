"""Scenario selection checks that never start the simulator."""
from pathlib import Path

import pytest
import yaml

from uamc_sim.scenario import resolve_scenario


@pytest.fixture
def assets(tmp_path):
    for d in ('worlds', 'config', 'scenarios'):
        (tmp_path / d).mkdir()
    (tmp_path / 'worlds' / 'track.sdf').write_text('<sdf version="1.9"><world name="inner_name"/></sdf>')
    (tmp_path / 'config' / 'track.rviz').write_text('Visualization Manager: {}\n')
    profile = {'world': 'worlds/track.sdf', 'rviz_config': 'config/track.rviz',
               'spawn': {'x': 1, 'y': -2, 'z': 0.05, 'yaw': 0.5}}
    (tmp_path / 'scenarios' / 'test.yaml').write_text(yaml.safe_dump(profile))
    return tmp_path, profile


def save(root, profile):
    (root / 'scenarios' / 'test.yaml').write_text(yaml.safe_dump(profile))


def test_resolves_world_identity_and_spawn_from_one_manifest(assets):
    root, _ = assets
    selected = resolve_scenario(root, 'test')
    assert selected.world_name == 'inner_name'
    assert Path(selected.world) == root / 'worlds' / 'track.sdf'
    assert selected.spawn == (1.0, -2.0, 0.05, 0.5)
    assert selected.node_parameters is None


@pytest.mark.parametrize('name', ['', '../test', 'Test', 'unknown', '/tmp/test'])
def test_unknown_or_unsafe_profile_name_is_rejected(assets, name):
    with pytest.raises(ValueError):
        resolve_scenario(assets[0], name)


@pytest.mark.parametrize('field,value', [
    ('world', 'worlds/missing.sdf'), ('world', '../outside.sdf'),
    ('world', '/tmp/outside.sdf'), ('rviz_config', 'config/missing.rviz'),
    ('spawn', {'x': 0}), ('spawn', {'x': float('nan'), 'y': 0, 'z': 0, 'yaw': 0}),
])
def test_missing_or_invalid_assets_and_pose_are_rejected(assets, field, value):
    root, profile = assets
    profile[field] = value
    save(root, profile)
    with pytest.raises(ValueError):
        resolve_scenario(root, 'test')


@pytest.mark.parametrize('sdf', [
    '<sdf><world name="one"/><world name="two"/></sdf>',
    '<sdf><world/></sdf>', '<sdf><world name="bad name"/></sdf>',
    '<sdf><world name="broken"></sdf>', '<robot/>',
])
def test_invalid_or_ambiguous_world_is_rejected(assets, sdf):
    root, _ = assets
    (root / 'worlds' / 'track.sdf').write_text(sdf)
    with pytest.raises(ValueError):
        resolve_scenario(root, 'test')


def test_node_parameter_file_and_override_must_exist_and_be_valid(assets):
    root, profile = assets
    p = root / 'config' / 'tuning.yaml'
    p.write_text('path_controller:\n  ros__parameters:\n    max_speed: 0.2\n')
    profile['node_parameters'] = 'config/tuning.yaml'
    save(root, profile)
    assert resolve_scenario(root, 'test').node_parameters == str(p)
    override = root / 'override.yaml'
    override.write_text('safety_gate:\n  ros__parameters:\n    max_speed: 0.2\n')
    assert resolve_scenario(root, 'test', str(override)).node_parameters == str(override)
    override.write_text('safety_gate:\n  invalid: 1\n')
    with pytest.raises(ValueError):
        resolve_scenario(root, 'test', str(override))
    with pytest.raises(ValueError):
        resolve_scenario(root, 'test', str(root / 'missing.yaml'))


def test_packaged_practice_contract():
    root = Path(__file__).resolve().parents[1]
    practice = resolve_scenario(root, 'practice')
    assert practice.world_name == 'practice'
    assert practice.spawn == (0.0, 0.0, 0.05, 0.0)


@pytest.mark.parametrize('value', [
    '[0.2, bad]',
    '[true, 3]',
])
def test_ros_invalid_parameter_values_are_rejected_before_launch(assets, value):
    root, _ = assets
    override = root / 'invalid.yaml'
    override.write_text('path_controller:\n  ros__parameters:\n    max_speed: ' + value + '\n')
    with pytest.raises(ValueError):
        resolve_scenario(root, 'test', str(override))


def test_nested_named_parameters_are_accepted_but_wildcards_are_not(assets):
    root, _ = assets
    override = root / 'named.yaml'
    override.write_text('path_controller:\n  ros__parameters:\n    nested:\n      limit: 0.2\n')
    assert resolve_scenario(root, 'test', str(override)).node_parameters == str(override)
    override.write_text('/**:\n  ros__parameters:\n    max_speed: 0.2\n')
    with pytest.raises(ValueError):
        resolve_scenario(root, 'test', str(override))


def test_both_scenarios_share_dashboard_but_keep_world_identity():
    root = Path(__file__).resolve().parents[1]
    practice = resolve_scenario(root, 'practice')
    hairpin = resolve_scenario(root, 'hairpin')
    assert practice.rviz_config == hairpin.rviz_config
    assert Path(practice.rviz_config).name == 'dashboard.rviz'
    assert practice.world != hairpin.world
    assert practice.world_name != hairpin.world_name
