"""A launch-process-lifetime lock prevents two UAMC simulators sharing topics."""
import fcntl
import os

_lock = None


def acquire_session_lock(path=None):
    """Acquire once per launch process; keep the file open until process exit."""
    global _lock
    if _lock is not None:
        raise RuntimeError('This process already owns a UAMC simulation session')
    path = path or os.path.join('/tmp', f'uamc-sim-{os.getuid()}.lock')
    handle = open(path, 'a+', encoding='utf-8')
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        handle.close()
        raise RuntimeError('Another UAMC simulation session is already running') from exc
    except Exception:
        handle.close()
        raise
    _lock = handle
