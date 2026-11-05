"""Own the Gazebo server and optional GUI, including their process groups."""
import argparse
import ctypes
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import time


# The supervisor is single-threaded. Load libc before forking; the child sets a
# parent-death signal before exec and checks for parent loss in the race window.
_LIBC = ctypes.CDLL(None, use_errno=True)
_PR_SET_PDEATHSIG = 1


def _parent_death_setup(expected_parent):
    if _LIBC.prctl(_PR_SET_PDEATHSIG, signal.SIGTERM) != 0:
        raise OSError(ctypes.get_errno(), 'prctl(PR_SET_PDEATHSIG) failed')
    if os.getppid() != expected_parent:
        os._exit(1)


class GazeboSupervisor:
    def __init__(self, world, gui=False, extra_args=(), expected_parent=None):
        self.world = world
        self.gui = gui
        self.extra_args = list(extra_args)
        self.children = []
        self.stopping = False
        self.expected_parent = expected_parent

    def stop_requested(self, _signum, _frame):
        self.stopping = True

    def start_child(self, args):
        # Gazebo may create descendants. Each owned command gets its own group
        # so cleanup reaches descendants without touching unrelated processes.
        wrapper = Path(__file__).with_name('gazebo_group.py')
        parent_pid = os.getpid()
        child = subprocess.Popen([sys.executable, str(wrapper), *args],
                                 start_new_session=True,
                                 preexec_fn=lambda: _parent_death_setup(parent_pid))
        self.children.append(child)
        return child

    def cleanup(self):
        # Always signal each owned group, even if its leader already exited:
        # a Gazebo descendant may still be alive in that group.
        for sig, timeout in ((signal.SIGINT, 3.0), (signal.SIGTERM, 2.0), (signal.SIGKILL, 0.5)):
            for child in self.children:
                try:
                    os.killpg(child.pid, sig)
                except ProcessLookupError:
                    pass
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                # Group existence, not leader status, matters for orphaned descendants.
                alive = False
                for child in self.children:
                    try:
                        os.killpg(child.pid, 0)
                        alive = True
                    except ProcessLookupError:
                        pass
                if not alive:
                    break
                # Reap exited group leaders promptly.
                for child in self.children:
                    child.poll()
                time.sleep(0.05)
        for child in self.children:
            try:
                child.wait(timeout=1)
            except subprocess.TimeoutExpired:
                print(f'Gazebo process {child.pid} did not exit after SIGKILL', file=sys.stderr)

    def run(self):
        previous = {}
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            previous[sig] = signal.signal(sig, self.stop_requested)
        try:
            if self.expected_parent is not None:
                _parent_death_setup(self.expected_parent)
            if self.stopping:
                return 0
            server = self.start_child(['gz', 'sim', self.world, '-r', '-s', *self.extra_args,
                                       '--force-version', '8'])
            gui = self.start_child(['gz', 'sim', '-g', '--force-version', '8']) if self.gui else None
            while not self.stopping:
                if server.poll() is not None:
                    print(f'Gazebo server exited with status {server.returncode}', flush=True)
                    return 0 if server.returncode == 0 else 1
                if gui is not None and gui.poll() is not None:
                    print(f'Gazebo GUI exited with status {gui.returncode}', flush=True)
                    return 0 if gui.returncode == 0 else 1
                time.sleep(0.1)
            return 0
        except OSError as exc:
            print(f'Could not launch Gazebo: {exc}', file=sys.stderr, flush=True)
            return 1
        finally:
            self.cleanup()
            for sig, handler in previous.items():
                signal.signal(sig, handler)


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--world', required=True)
    parser.add_argument('--gui', action='store_true')
    parser.add_argument('--extra-args', default='')
    parser.add_argument('--expected-parent', type=int, default=None)
    parsed = parser.parse_args(args)
    try:
        extra = shlex.split(parsed.extra_args)
    except ValueError as exc:
        parser.error(str(exc))
    return GazeboSupervisor(parsed.world, parsed.gui, extra, parsed.expected_parent).run()


if __name__ == '__main__':
    sys.exit(main())
