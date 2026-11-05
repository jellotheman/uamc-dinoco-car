"""Lifecycle tests use tiny fake processes; they never start Gazebo."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

PACKAGE_DIR = Path(__file__).resolve().parents[1]
SUPERVISOR = PACKAGE_DIR / 'uamc_sim' / 'gazebo_supervisor.py'


def wait_for(predicate, timeout=8):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(0.05)
    pytest.fail('timed out waiting for fake process')


def test_supervisor_stops_server_gui_and_their_descendants(tmp_path):
    fake = tmp_path / 'gz'
    fake.write_text('''#!/usr/bin/python3
import os, signal, sys, time
role = 'gui' if '-g' in sys.argv else 'server'
path = os.environ['FAKE_GZ_LOG']
pid = os.fork()
role += '-child' if pid == 0 else '-parent'
def log(s):
    with open(path, 'a', encoding='utf8') as f:
        f.write(role + ':' + s + '\\n')
def stop(sig, frame):
    log('stop')
    sys.exit(0)
signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)
log('start')
while True:
    time.sleep(.1)
''')
    fake.chmod(0o755)
    log = tmp_path / 'events'
    env = dict(os.environ, PATH=str(tmp_path) + os.pathsep + os.environ['PATH'],
               FAKE_GZ_LOG=str(log))
    proc = subprocess.Popen([sys.executable, str(SUPERVISOR), '--world', 'fake',
                             '--gui', '--extra-args=--fake-flag'], env=env)
    try:
        wait_for(lambda: log.exists() and len(log.read_text().splitlines()) >= 4)
        proc.send_signal(signal.SIGTERM)
        assert proc.wait(timeout=10) == 0
        events = set(log.read_text().splitlines())
        for role in ('server-parent', 'server-child', 'gui-parent', 'gui-child'):
            assert role + ':start' in events
            assert role + ':stop' in events
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()


@pytest.mark.parametrize('exit_code', [0, 3])
def test_gui_exit_ends_supervisor_and_stops_server(tmp_path, exit_code):
    fake = tmp_path / 'gz'
    fake.write_text('''#!/usr/bin/python3
import os, signal, sys, time
if '-g' in sys.argv:
    time.sleep(.4)
    sys.exit(int(os.environ['FAKE_GUI_EXIT']))
def stop(sig, frame):
    with open(os.environ['FAKE_GZ_LOG'], 'a') as f:
        f.write('server stopped')
    sys.exit(0)
signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)
while True:
    time.sleep(.1)
''')
    fake.chmod(0o755)
    log = tmp_path / 'events'
    env = dict(os.environ, PATH=str(tmp_path) + os.pathsep + os.environ['PATH'],
               FAKE_GZ_LOG=str(log), FAKE_GUI_EXIT=str(exit_code))
    proc = subprocess.run([sys.executable, str(SUPERVISOR), '--world', 'fake', '--gui'],
                          env=env, timeout=10, capture_output=True, text=True)
    assert proc.returncode == (0 if exit_code == 0 else 1)
    assert 'GUI exited' in proc.stdout
    assert log.read_text() == 'server stopped'


def test_duplicate_session_lock_is_rejected_and_released(tmp_path):
    env = dict(os.environ, FAKE_LOCK=str(tmp_path / 'lock'),
               PYTHONPATH=str(PACKAGE_DIR) + os.pathsep + os.environ.get('PYTHONPATH', ''))
    code = ('import os; from uamc_sim.session_lock import acquire_session_lock; '
            'acquire_session_lock(os.environ["FAKE_LOCK"]); print("locked", flush=True); '
            'import time; time.sleep(30)')
    first = subprocess.Popen([sys.executable, '-c', code], env=env, stdout=subprocess.PIPE, text=True)
    try:
        assert first.stdout.readline().strip() == 'locked'
        check = subprocess.run([sys.executable, '-c',
                                'import os; from uamc_sim.session_lock import acquire_session_lock; acquire_session_lock(os.environ["FAKE_LOCK"])'],
                               env=env, capture_output=True, text=True, timeout=5)
        assert check.returncode != 0
        assert 'already running' in check.stderr
    finally:
        first.terminate()
        first.wait(timeout=5)
    check = subprocess.run([sys.executable, '-c',
                            'import os; from uamc_sim.session_lock import acquire_session_lock; acquire_session_lock(os.environ["FAKE_LOCK"])'],
                           env=env, capture_output=True, text=True, timeout=5)
    assert check.returncode == 0
