from types import SimpleNamespace
import threading
from uamc_control.safety_gate import SafetyGate


class Goal:
    is_cancel_requested = False
    is_active = True
    def __init__(self):
        self.state = None
    def publish_feedback(self, feedback):
        pass
    def succeed(self):
        self.state = 'succeeded'
    def abort(self):
        self.state = 'aborted'
    def canceled(self):
        self.state = 'cancelled'


def test_action_finishes_and_disarms_after_obstacle_standstill(monkeypatch):
    monkeypatch.setattr('uamc_control.safety_gate.rclpy.ok', lambda: True)
    gate = SimpleNamespace(fault='', armed=True, running=True, obstacle_hold=True,
                           data={}, stopped=lambda: True, lock=threading.RLock(),
                           active_generation=0, generation=0)
    goal = Goal()
    result = SafetyGate.execute(gate, goal)
    assert result.success and goal.state == 'succeeded'
    assert not gate.armed and not gate.running


def test_rapid_disarm_rearm_rejects_while_old_goal_is_finishing():
    gate = SimpleNamespace(lock=threading.RLock(), armed=True, running=True,
                           generation=7, manual_latch=True, manual_released_neutral=True,
                           fault='', obstacle_hold=False, mode='auto', health=lambda: '',
                           stopped=lambda: True)
    req = SimpleNamespace(data=False)
    res = SafetyGate.arm(gate, req, SimpleNamespace())
    assert res.success and gate.generation == 8 and not gate.armed
    req.data = True
    res = SafetyGate.arm(gate, req, SimpleNamespace())
    assert not res.success and not gate.armed
    assert res.message == 'previous run still ending'
