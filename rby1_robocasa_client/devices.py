"""robo-synapse device contracts (common/interfaces.py: Arm, Gripper, MobileBase) over the sim.

Duck-typed: nothing here imports robo-synapse. Frames follow robo-synapse's RB-Y1 arm facade:
link_torso_5, quaternion (x, y, z, w), metres.
"""
from rby1_robocasa_client.client import SimCallError


class SimArm:
    """Arm: joint_names, joint_positions, send_joint_trajectory, ee_pose, move_to_pose,
    external_wrench, tare_wrench. `last_refusal` explains the last failed move."""

    def __init__(self, sim, side):
        self.sim, self.side = sim, side
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

    def ee_pose(self):
        p = self.sim.arm.ee_pose(self.side)
        return {"position": tuple(p["position"]), "orientation": tuple(p["orientation"])}

    def move_to_pose(self, position, *, orientation=None, cartesian=False, pose_floor=False):
        return self._ok(self.sim.arm.move_to_pose(self.side, list(position),
                                                  None if orientation is None else list(orientation), cartesian))

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
