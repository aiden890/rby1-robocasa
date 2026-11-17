"""robosuite model classes. Importing this module registers RBY1 and RBY1Gripper."""
import numpy as np

from robosuite.models.grippers import GRIPPER_MAPPING
from robosuite.models.grippers.gripper_model import GripperModel
from robosuite.models.robots.manipulators.manipulator_model import ManipulatorModel

from rby1_sim.robot import (
    HEAD_READY,
    LEFT_ARM_READY,
    RIGHT_ARM_READY,
    TORSO_READY,
    ensure_generated,
)

_GEN = ensure_generated()


class RBY1GripperBase(GripperModel):
    """RB-Y1 parallel gripper: two slide fingers, 0 = closed, 0.05 m each side = open."""

    def __init__(self, idn=0):
        super().__init__(str(_GEN / "gripper.xml"), idn=idn)

    def format_action(self, action):
        return action

    @property
    def init_qpos(self):
        return np.array([-0.04, 0.04])

    @property
    def _important_geoms(self):
        f1 = [n for n in self._names("finger1")]
        f2 = [n for n in self._names("finger2")]
        return {
            "left_finger": f1,
            "right_finger": f2,
            "left_fingerpad": ["finger1_pad"],
            "right_fingerpad": ["finger2_pad"],
        }

    def _names(self, body):
        root = self.worldbody
        out = []
        for b in root.iter("body"):
            if b.get("name", "").endswith(body):
                for g in b.findall("geom"):
                    n = g.get("name", "")
                    if "collision" in n or n.endswith("_pad"):
                        out.append(n[len(self.naming_prefix):] if n.startswith(self.naming_prefix) else n)
        return out


class RBY1Gripper(RBY1GripperBase):
    """One continuous action in [-1, 1]: -1 open, +1 close (robosuite convention)."""

    def format_action(self, action):
        assert len(action) == self.dof
        self.current_action = np.clip(
            self.current_action + np.array([1.0, -1.0]) * self.speed * np.sign(action), -1.0, 1.0
        )
        return self.current_action

    @property
    def speed(self):
        return 0.2

    @property
    def dof(self):
        return 1


GRIPPER_MAPPING["RBY1Gripper"] = RBY1Gripper


class RBY1(ManipulatorModel):
    """Rainbow Robotics RB-Y1 Model M v1.2 (mecanum base modelled as holonomic x/y/yaw)."""

    arms = ["right", "left"]

    def __init__(self, idn=0):
        super().__init__(str(_GEN / "robot.xml"), idn=idn)

    @property
    def default_base(self):
        return "NullMobileBase"

    @property
    def default_gripper(self):
        return {"right": "RBY1Gripper", "left": "RBY1Gripper"}

    @property
    def default_controller_config(self):
        return {"right": "default_rby1", "left": "default_rby1"}

    @property
    def init_qpos(self):
        return np.concatenate([TORSO_READY, RIGHT_ARM_READY, LEFT_ARM_READY, HEAD_READY])

    @property
    def init_torso_qpos(self):
        return TORSO_READY.copy()

    @property
    def base_xpos_offset(self):
        return {
            "bins": (-0.6, -0.1, 0),
            "empty": (-0.6, 0, 0),
            "table": lambda table_length: (-0.45 - table_length / 2, 0, 0),
        }

    @property
    def top_offset(self):
        return np.array((0, 0, 1.0))

    @property
    def _horizontal_radius(self):
        return 0.4

    @property
    def arm_type(self):
        return "bimanual"

    @property
    def _eef_name(self):
        return {"right": "right_hand", "left": "left_hand"}
