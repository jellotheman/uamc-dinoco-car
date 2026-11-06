import os
from pathlib import Path
import shutil
import subprocess


SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "real.sh"


def test_helper_setup_error_and_quoted_forwarding(tmp_path):
    project = tmp_path / "workspace with spaces"
    (project / "scripts").mkdir(parents=True)
    helper = project / "scripts" / "real.sh"
    shutil.copy2(SCRIPT, helper)
    failed = subprocess.run([str(helper)], cwd="/", capture_output=True, text=True)
    assert failed.returncode != 0 and "Build first" in failed.stderr
    install = project / "ros2_ws" / "install"
    install.mkdir(parents=True)
    (install / "setup.bash").write_text("# test workspace\n")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    capture = tmp_path / "args"
    stub = bin_dir / "ros2"
    stub.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$CAPTURE"\nexit 23\n')
    stub.chmod(0o755)
    env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ["PATH"], CAPTURE=str(capture))
    result = subprocess.run([str(helper), "rviz:=false", "hardware_config:=/tmp/a b.yaml", "visualization_debug:=true"], cwd="/", env=env)
    assert result.returncode == 23
    assert capture.read_text().splitlines() == ["launch", "uamc_bringup", "real.launch.py", "rviz:=true", "rviz:=false", "hardware_config:=/tmp/a b.yaml", "visualization_debug:=true"]
