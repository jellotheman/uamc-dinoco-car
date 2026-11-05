"""Forward parent-loss signals to one owned Gazebo process group."""
import os
import signal
import subprocess
import sys
import time

_stopping = False


def request_stop(_signal, _frame):
    global _stopping
    _stopping = True


def group_has_other_live_processes(group):
    """Check Linux process groups, ignoring this wrapper and zombie processes."""
    for name in os.listdir('/proc'):
        if not name.isdigit() or int(name) == os.getpid():
            continue
        try:
            # The command name can contain spaces and parentheses.
            rest = open(f'/proc/{name}/stat', encoding='utf-8').read().rsplit(')', 1)[1].split()
            state, process_group = rest[0], int(rest[2])
            if process_group == group and state != 'Z':
                return True
        except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError, IndexError):
            continue
    return False


def main():
    if len(sys.argv) < 2:
        print('No Gazebo command supplied', file=sys.stderr)
        return 2
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, request_stop)
    child = None
    try:
        if not _stopping:
            child = subprocess.Popen(sys.argv[1:])
        while not _stopping and child is not None and child.poll() is None:
            time.sleep(0.05)
        return_code = child.returncode if child is not None and child.returncode is not None else 0
    except OSError as exc:
        print(f'Could not launch Gazebo: {exc}', file=sys.stderr, flush=True)
        return_code = 1
    finally:
        # The wrapper may have received a parent-death signal itself. Forward
        # that shutdown to its group, including grandchildren, without
        # recursively invoking its own handler.
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(sig, signal.SIG_IGN)
        group = os.getpgrp()
        os.killpg(group, signal.SIGTERM)
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            if child is not None:
                child.poll()
            if not group_has_other_live_processes(group):
                break
            time.sleep(0.05)
        if group_has_other_live_processes(group):
            # This also terminates the wrapper; only the group it owns is hit.
            os.killpg(group, signal.SIGKILL)
        if child is not None:
            child.wait()
    return return_code


if __name__ == '__main__':
    sys.exit(main())
