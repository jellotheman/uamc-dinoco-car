import math

from uamc_io.logic import FakeTransport, ManualState


def test_requires_released_neutral_and_new_press():
    joy = ManualState()
    assert joy.update(0, 0, True, 0) == (False, 0, 0)
    assert joy.update(0.5, 0, False, 0.1) == (False, 0, 0)
    assert joy.update(0, 0, True, 0.2) == (False, 0, 0)
    assert joy.update(0, 0, False, 0.3) == (False, 0, 0)
    assert joy.update(0, 0, True, 0.4) == (True, 0, 0)
    assert joy.update(0.5, -0.5, True, 0.5) == (True, 0.15, -0.2)
    assert joy.update(0, 0, False, 0.6) == (False, 0, 0)


def test_disconnect_requires_release_neutral_and_fresh_press():
    joy = ManualState(timeout=0.3)
    joy.update(0, 0, False, 0)
    joy.update(0, 0, True, 0.1)
    assert not joy.fresh(0.5)
    assert joy.update(0, 0, True, 0.6) == (False, 0, 0)
    joy.update(0, 0, False, 0.7)
    assert joy.update(0, 0, True, 0.8) == (True, 0, 0)


def test_invalid_data_and_reverse_fail_closed():
    joy = ManualState()
    joy.update(0, 0, False, 0)
    joy.update(0, 0, True, 0.1)
    assert joy.update(-1, 0, True, 0.2) == (True, 0, 0)
    assert joy.update(math.nan, 0, True, 0.3) == (False, 0, 0)
    assert joy.update(0, 0, True, 0.4) == (False, 0, 0)


def test_fake_transport_clamps_and_times_out_to_neutral():
    fake = FakeTransport(timeout=0.3)
    fake.accept(2, -2, 0)
    assert fake.read(0.1) == (0.3, -0.4)
    assert fake.read(0.4) == (0, 0)
    fake.accept(math.inf, 0, 0.5)
    assert fake.read(0.5) == (0, 0)
