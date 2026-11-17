"""Base part: robo-synapse MobileBase contract. The mecanum base is modelled by robosuite's
holonomic x/y/yaw joints; a velocity command is a lease of `duration_s` sim seconds."""
import numpy as np

from rby1_robocasa.server.core import CONTROL_HZ


class BasePart:
    def __init__(self, core):
        self.core = core
        self._odom0 = None
        self._ref = None           # moving reference pose of the current velocity command
        self._ref_step = -1        # core.steps when the last lease ended
        core.reset_hooks.append(self._on_reset)

    def _on_reset(self):
        self._odom0 = self.world_pose_array()
        self._ref = None

    def world_pose_array(self):
        sim = self.core.sim
        bid = sim.model.body_name2id("mobilebase0_support")
        R = sim.data.xmat[bid].reshape(3, 3)
        return np.array([sim.data.xpos[bid][0], sim.data.xpos[bid][1], np.arctan2(R[1, 0], R[0, 0])])

    def world_pose(self):
        return self.world_pose_array().tolist()

    # The base joints are velocity actuators with heavy friction (robosuite NullMobileBase), so an
    # action is not a speed: the commanded twist is integrated into a moving reference pose and
    # tracked with a P term (measured 261117: action 0.5 gave 0.16 m/s open loop).
    KP_XY, KP_YAW, FF = 8.0, 6.0, 1.6

    def set_velocity(self, vx, vy, wz, duration_s=0.1):
        """Body-frame twist (m/s, m/s, rad/s) for `duration_s` of sim time. Back-to-back calls
        continue one motion; any other command that advances the sim sends zero base velocity,
        so the base stops unless the lease is renewed (sim time is frozen between calls)."""
        sim = self.core.sim
        root = sim.model.body_name2id(self.core.robot.robot_model.root_body)
        R0 = sim.data.xmat[root].reshape(3, 3)[:2, :2]   # the slide joints are fixed in the root frame
        continuing = self._ref is not None and self._ref_step == self.core.steps
        ref = self._ref if continuing else self.world_pose_array()
        dt = 1.0 / CONTROL_HZ
        for _ in range(max(1, int(round(duration_s * CONTROL_HZ)))):
            c, s = np.cos(ref[2]), np.sin(ref[2])
            v_world = np.array([c * vx - s * vy, s * vx + c * vy])
            ref = ref + np.array([v_world[0], v_world[1], wz]) * dt
            cur = self.world_pose_array()
            cmd_xy = self.FF * v_world + self.KP_XY * (ref[:2] - cur[:2])
            cmd_w = self.FF * wz + self.KP_YAW * float((ref[2] - cur[2] + np.pi) % (2 * np.pi) - np.pi)
            v_joint = R0.T @ cmd_xy
            self.core.step(base=np.array([v_joint[0], v_joint[1], cmd_w]))
        self._ref, self._ref_step = ref, self.core.steps
        return True

    def odom_pose(self):
        """(x, y, yaw) relative to the episode start pose."""
        w, (x0, y0, a0) = self.world_pose_array(), self._odom0
        c, s = np.cos(-a0), np.sin(-a0)
        dx, dy = w[0] - x0, w[1] - y0
        return [c * dx - s * dy, s * dx + c * dy, float((w[2] - a0 + np.pi) % (2 * np.pi) - np.pi)]

    def stop(self):
        self._ref = None
        self.core.step(base=np.zeros(3))
        return True
