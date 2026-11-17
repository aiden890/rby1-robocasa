"""RB-Y1 Model M as a robosuite robot (bimanual, 6-DoF torso, 2-DoF head, holonomic base)."""
from pathlib import Path

import numpy as np

from rby1_robocasa.robot import build_model

GEN_DIR = build_model.OUT_DIR
CONFIG_DIR = Path(__file__).resolve().parent / "configs"

# joint order in robot.xml: torso_0..5, right_arm_0..6, left_arm_0..6, head_0..1
TORSO_READY = np.array([0.0, 0.35, -0.7, 0.35, 0.0, 0.0])  # slight crouch, chest level
# hands in front of the chest (fingertip ~0.52 m ahead, 0.13 m below link_torso_5, found by FK
# search 261117); a hanging hand sits at counter height and catches the counter edge
RIGHT_ARM_READY = np.array([0.0, -0.2, 0.0, -1.9, 0.0, 0.3, 0.0])
LEFT_ARM_READY = np.array([0.0, 0.2, 0.0, -1.9, 0.0, 0.3, 0.0])
HEAD_READY = np.array([0.0, 0.5])


def ensure_generated():
    if not (GEN_DIR / "robot.xml").is_file() or not (GEN_DIR / "gripper.xml").is_file():
        build_model.build()
    return GEN_DIR


def controller_config_path(name="default"):
    return str(CONFIG_DIR / f"controller_{name}.json")
