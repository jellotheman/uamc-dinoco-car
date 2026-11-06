"""Process-lifetime real and simulator exclusion locks."""
import fcntl
import os

_locks = []


def acquire_session_locks(paths=None):
    if _locks:
        raise RuntimeError("real session already acquired")
    paths = paths or [f"/tmp/uamc-sim-{os.getuid()}.lock", f"/tmp/uamc-real-{os.getuid()}.lock"]
    handles = []
    try:
        for path in paths:
            handle = open(path, "a+")
            handles.append(handle)
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, BlockingIOError) as exc:
        for handle in handles:
            handle.close()
        raise RuntimeError("another UAMC simulator or real stack owns the session lock") from exc
    _locks.extend(handles)


def release_session_locks():
    while _locks:
        _locks.pop().close()
