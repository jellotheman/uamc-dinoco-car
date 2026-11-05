from pathlib import Path
import yaml


def test_ekf_uses_wheel_and_yaw_rate_in_local_frame():
    config = Path(__file__).parents[1] / 'config' / 'ekf.yaml'
    params = yaml.safe_load(config.read_text())['ekf_filter_node']['ros__parameters']
    assert params['two_d_mode'] and params['publish_tf']
    assert params['world_frame'] == 'odom' and params['base_link_frame'] == 'base_link'
    assert params['odom0_config'][6] and params['imu0_config'][11]
    assert sum(params['odom0_config']) == 1 and sum(params['imu0_config']) == 1
