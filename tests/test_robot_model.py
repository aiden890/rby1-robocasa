"""RB-Y1 robosuite model: loads, has the expected joints/cameras, gripper opens/closes, arm OSC moves."""
import numpy as np
import pytest

import rby1_robocasa.register  # noqa: F401
import robosuite
from robosuite.controllers import load_composite_controller_config

from rby1_robocasa.robot import controller_config_path


@pytest.fixture(scope="module")
def env():
    cfg = load_composite_controller_config(controller=controller_config_path())
    e = robosuite.make(
        "Lift", robots="RBY1", controller_configs=cfg, has_renderer=False, has_offscreen_renderer=False,
        use_camera_obs=False, ignore_done=True, control_freq=20,
    )
    e.reset()
    yield e
    e.close()


def test_joints(env):
    names = env.robots[0].robot_model.joints
    assert sum(n.startswith("robot0_torso_") for n in names) == 6
    assert sum("right_arm_" in n for n in names) == 7
    assert sum("left_arm_" in n for n in names) == 7
    assert sum("head_" in n for n in names) == 2


def test_hold_still(env):
    env.reset()
    r = env.robots[0]
    q0 = r._joint_positions.copy()
    for _ in range(40):
        env.step(np.zeros(env.action_dim) + _hold_action(env))
    assert np.all(np.isfinite(env.sim.data.qpos))
    assert np.max(np.abs(r._joint_positions - q0)) < 0.1


def _hold_action(env):
    """every part is delta/velocity controlled, so zeros hold the pose."""
    return np.zeros(env.action_dim)


def test_gripper_close_open(env):
    env.reset()
    r = env.robots[0]
    cc = r.composite_controller
    s, e = cc._action_split_indexes["right_gripper"]
    width = lambda: float(np.sum(np.abs(env.sim.data.qpos[r._ref_gripper_joint_pos_indexes["right"]])))
    a = _hold_action(env)
    a[s:e] = 1.0
    for _ in range(30):
        env.step(a)
    closed = width()
    a[s:e] = -1.0
    for _ in range(30):
        env.step(a)
    opened = width()
    assert closed < 0.02 and opened > 0.08, (closed, opened)


def test_arm_moves_up(env):
    env.reset()
    r = env.robots[0]
    site = env.sim.model.site_name2id("gripper0_right_grip_site")
    z0 = env.sim.data.site_xpos[site][2]
    cc = r.composite_controller
    s, e = cc._action_split_indexes["right"]
    a = _hold_action(env)
    a[s + 2] = 1.0  # +z delta
    for _ in range(20):
        env.step(a)
    assert env.sim.data.site_xpos[site][2] - z0 > 0.05
