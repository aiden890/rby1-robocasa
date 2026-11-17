"""robo-synapse device contracts (common/interfaces.py: Arm, Gripper, MobileBase) over the sim.

Duck-typed: nothing here imports robo-synapse. Frames follow robo-synapse's RB-Y1 arm facade:
link_torso_5, quaternion (x, y, z, w), metres.
"""
import numpy as np

from rby1_robocasa_client.client import SimCallError

# half a turn about x: the sim's fingertip frame has z along the approach, the RB-Y1 facade's
# ee frame has the fingers along -z (x, the jaw axis, is shared)
_RX180 = np.diag([1.0, -1.0, -1.0])


def _quat_to_mat(q):
    x, y, z, w = (float(v) for v in q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def _mat_to_quat(R):
    t = np.trace(R)
    if t > 0:
        s = np.sqrt(t + 1.0) * 2
        q = [(R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s, 0.25 * s]
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        q = [0.25 * s, (R[0, 1] + R[1, 0]) / s, (R[0, 2] + R[2, 0]) / s, (R[2, 1] - R[1, 2]) / s]
    elif R[1, 1] > R[2, 2]:
        s = np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        q = [(R[0, 1] + R[1, 0]) / s, 0.25 * s, (R[1, 2] + R[2, 1]) / s, (R[0, 2] - R[2, 0]) / s]
    else:
        s = np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
        q = [(R[0, 2] + R[2, 0]) / s, (R[1, 2] + R[2, 1]) / s, 0.25 * s, (R[1, 0] - R[0, 1]) / s]
    q = np.array(q)
    return tuple(float(v) for v in (q if q[3] >= 0 else -q))


class SimArm:
    """Arm: joint_names, joint_positions, send_joint_trajectory, ee_pose, move_to_pose,
    external_wrench, tare_wrench. `last_refusal` explains the last failed move.

    convention="rby1" (default) reports the pose robo-synapse's real RB-Y1 facade reports:
    the wrist point `tool_offset_m` behind the fingertip, fingers along -z (its Skills profile
    then uses cap.skills.tcp_offset_m = -tool_offset_m). convention="tip" passes the sim's
    fingertip frame (z along the approach) through unchanged."""

    def __init__(self, sim, side, *, convention="rby1", tool_offset_m=0.074):
        if convention not in ("rby1", "tip"):
            raise ValueError("convention must be 'rby1' or 'tip'")
        self.sim, self.side = sim, side
        self.convention, self.tool_offset_m = convention, float(tool_offset_m)
        self.last_refusal = ""
        self._names = None

    @property
    def joint_names(self):
        if self._names is None:
            self._names = list(self.sim.arm.joint_names(self.side))
        return self._names

    def joint_positions(self):
        return dict(self.sim.arm.joint_positions(self.side))

    def send_joint_trajectory(self, targets, *, duration_s=None):
        return self._ok(self.sim.arm.send_joint_trajectory(self.side, dict(targets), duration_s))

    def _tip_to_ee(self, p, q):
        if self.convention == "tip":
            return tuple(p), tuple(q)
        R_tip = _quat_to_mat(q)
        approach = R_tip[:, 2]
        return tuple(np.asarray(p) - self.tool_offset_m * approach), _mat_to_quat(R_tip @ _RX180)

    def _ee_to_tip(self, p, q):
        if self.convention == "tip":
            return list(p), (None if q is None else list(q))
        R_ee = _quat_to_mat(q)
        approach = -R_ee[:, 2]
        return list(np.asarray(p, float) + self.tool_offset_m * approach), list(_mat_to_quat(R_ee @ _RX180))

    def ee_pose(self):
        p = self.sim.arm.ee_pose(self.side)
        pos, quat = self._tip_to_ee(p["position"], p["orientation"])
        return {"position": pos, "orientation": quat}

    def move_to_pose(self, position, *, orientation=None, cartesian=False, pose_floor=False):
        if orientation is None:
            orientation = self.ee_pose()["orientation"]   # keep the present hand orientation
        tip, quat = self._ee_to_tip(position, orientation)
        return self._ok(self.sim.arm.move_to_pose(self.side, tip, quat, cartesian))

    def external_wrench(self):
        return tuple(self.sim.arm.external_wrench(self.side))

    def tare_wrench(self):
        return bool(self.sim.arm.tare_wrench(self.side))

    def _ok(self, res):
        ok = bool(res.get("ok"))
        self.last_refusal = "" if ok else str(res.get("reason") or "move failed")
        return ok


class SimGripper:
    """Gripper: ready, open_gripper, close_gripper, gripper_state (widthMeters, hasObject)."""

    def __init__(self, sim, side):
        self.sim, self.side = sim, side

    def ready(self):
        try:
            self.sim.ping()
            return True
        except Exception:
            return False

    def open_gripper(self):
        return bool(self.sim.gripper.open(self.side))

    def close_gripper(self, *, width_m=None, force_newtons=None, speed=None):
        return bool(self.sim.gripper.close(self.side, width_m))

    def gripper_state(self, *, refresh=True):
        return dict(self.sim.gripper.state(self.side))


class SimMobileBase:
    """MobileBase: a velocity lease is one sim time slice (`lease_s`) and then the base stops;
    the sim only advances inside calls, so a dead client never leaves it rolling."""

    def __init__(self, sim, lease_s=0.1):
        self.sim, self.lease_s = sim, lease_s

    def ready(self):
        try:
            self.sim.ping()
            return True
        except Exception:
            return False

    def set_velocity(self, vx, vy, wz):
        return bool(self.sim.base.set_velocity(float(vx), float(vy), float(wz), self.lease_s))

    def odom_pose(self):
        try:
            return tuple(self.sim.base.odom_pose())
        except SimCallError:
            return None

    def stop(self):
        return bool(self.sim.base.stop())


class SimBody:
    """Torso (6) and head (2) joint targets; robo-synapse has no device contract for these."""

    def __init__(self, sim):
        self.sim = sim

    def joint_positions(self, part="torso"):
        return dict(self.sim.body.joint_positions(part))

    def set_torso(self, targets):
        return bool(self.sim.body.set_torso(list(targets)).get("ok"))

    def look(self, yaw, pitch):
        return bool(self.sim.body.set_head([float(yaw), float(pitch)]).get("ok"))
