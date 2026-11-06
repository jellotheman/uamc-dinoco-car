import fcntl
import pytest
from uamc_bringup.real_session import acquire_session_locks, release_session_locks


def test_partial_lock_is_released(tmp_path):
    first, second = (str(tmp_path / name) for name in ("first", "second"))
    with open(second, "a+") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(RuntimeError):
            acquire_session_locks([first, second])
        with open(first, "a+") as probe:
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
    acquire_session_locks([first, second])
    release_session_locks()
