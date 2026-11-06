import pytest
from uamc_bringup.real_config import validate_description

VALID = '<robot name="test"><link name="base_link"/><link name="sensor"/><joint name="mount" type="fixed"><parent link="base_link"/><child link="sensor"/><origin xyz="1 2 3" rpy="0 0 0"/></joint></robot>'


def test_description_rejects_invalid_values_and_extensions():
    for xyz in ("", "0 0 nan", "0 0", "0 nope 0"):
        with pytest.raises(ValueError):
            validate_description(VALID.replace('xyz="1 2 3"', f'xyz="{xyz}"'))
    for invalid in (VALID.replace("</robot>", "<gazebo/></robot>"),
                    VALID.replace("</robot>", '<link name="odom"/></robot>'),
                    VALID.replace('type="fixed"', 'type="continuous"'),
                    VALID.replace('name="sensor"', 'name=""', 1),
                    VALID.replace('link="base_link"', 'link="missing"'),
                    VALID.replace("</robot>", '<link name="other"/><joint name="duplicate" type="fixed"><parent link="base_link"/><child link="sensor"/></joint></robot>')):
        with pytest.raises(ValueError):
            validate_description(invalid)
    assert validate_description(VALID) == VALID
