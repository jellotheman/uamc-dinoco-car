"""Parent-loss cleanup using fake processes only; no Gazebo is started."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

SUPERVISOR = Path(__file__).resolve().parents[1] / 'uamc_sim' / 'gazebo_supervisor.py'


def wait_for(predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.05)
    pytest.fail('fake processes did not stop in time')


def fake_environment(tmp_path):
    fake = tmp_path / 'gz'
    fake.write_text('''#!/usr/bin/python3
import os, signal, time
path = os.environ['FAKE_LOG']
pid = os.fork()
role = 'child' if pid == 0 else 'parent'
def log(event):
    with open(path, 'a') as f:
        f.write(role + ':' + event + '\\n')
def stop(signum, frame):
    log('stopped')
    os._exit(0)
signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGHUP, stop)
log('started')
while True: time.sleep(.1)
''')
    fake.chmod(0o755)
    log = tmp_path / 'events'
    env = dict(os.environ, PATH=str(tmp_path) + os.pathsep + os.environ['PATH'],
               FAKE_LOG=str(log))
    return env, log


def all_started(log):
    return log.exists() and {'parent:started', 'child:started'} <= set(log.read_text().splitlines())


def all_stopped(log):
    return log.exists() and {'parent:stopped', 'child:stopped'} <= set(log.read_text().splitlines())


@pytest.mark.parametrize('terminate_signal', [signal.SIGHUP, signal.SIGKILL])
def test_supervisor_death_stops_whole_child_group(tmp_path, terminate_signal):
    env, log = fake_environment(tmp_path)
    proc = subprocess.Popen([sys.executable, str(SUPERVISOR), '--world', 'fake'], env=env)
    try:
        wait_for(lambda: all_started(log))
        proc.send_signal(terminate_signal)
        proc.wait(timeout=8)
        wait_for(lambda: all_stopped(log))
        if terminate_signal == signal.SIGHUP:
            assert proc.returncode == 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()


def test_launch_parent_hard_exit_stops_supervisor_and_children(tmp_path):
    env, log = fake_environment(tmp_path)
    parent = '''import os, subprocess, sys, time
p=subprocess.Popen([sys.executable, sys.argv[1], '--world', 'fake',
                    '--expected-parent', str(os.getpid())])
print(p.pid, flush=True)
time.sleep(30)
'''
    proc = subprocess.Popen([sys.executable, '-c', parent, str(SUPERVISOR)], env=env,
                            stdout=subprocess.PIPE, text=True)
    try:
        supervisor_pid = int(proc.stdout.readline())
        wait_for(lambda: all_started(log))
        proc.kill()
        proc.wait(timeout=5)
        wait_for(lambda: all_stopped(log))
        def supervisor_gone():
            try:
                state = Path(f'/proc/{supervisor_pid}/stat').read_text().rsplit(')', 1)[1].split()[0]
                return state == 'Z'
            except FileNotFoundError:
                return True
        wait_for(supervisor_gone)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()


def test_parent_loss_escalates_for_unresponsive_group(tmp_path):
    fake = tmp_path / 'gz'
    fake.write_text('''#!/usr/bin/python3
import os, signal, time
signal.signal(signal.SIGINT, signal.SIG_IGN)
signal.signal(signal.SIGTERM, signal.SIG_IGN)
with open(os.environ['FAKE_LOG'], 'w') as f:
    f.write(str(os.getpid()))
while True: time.sleep(.1)
''')
    fake.chmod(0o755)
    log = tmp_path / 'pid'
    env = dict(os.environ, PATH=str(tmp_path) + os.pathsep + os.environ['PATH'],
               FAKE_LOG=str(log))
    proc = subprocess.Popen([sys.executable, str(SUPERVISOR), '--world', 'fake'], env=env)
    try:
        wait_for(lambda: log.exists() and bool(log.read_text()))
        child_pid = int(log.read_text())
        proc.kill()
        proc.wait(timeout=5)
        def child_gone():
            try:
                state = Path(f'/proc/{child_pid}/stat').read_text().rsplit(')', 1)[1].split()[0]
                return state == 'Z'
            except FileNotFoundError:
                return True
        wait_for(child_gone)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
