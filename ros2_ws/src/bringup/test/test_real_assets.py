from pathlib import Path
import yaml


def test_real_assets_use_wall_clock_and_do_not_include_simulator():
    src = Path(__file__).resolve().parents[2]
    config = yaml.safe_load((src / "dashboard" / "config" / "real.rviz").read_text())
    panels = config["Panels"]
    dashboard = next(panel for panel in panels if "Dashboard" in panel.get("Class", ""))
    assert dashboard["Simulation"] is False
    for name in ("real.launch.py", "real_view.launch.py"):
        content = (src / "bringup" / "launch" / name).read_text().lower()
        assert "uamc_sim" not in content and "gazebo" not in content.replace("no gazebo", "").replace("gazebo-free", "")
