"""The real RB-Y1 observation/action contract (robo-synapse CONTROL_API.md section 3, checked 261117).

observation.state (15, float32): active arm joints 7 (rad) + ee position 3 (m) + ee quaternion
    xyzw 4 + gripper 1 (closed = 1), all in link_torso_5.
action ee_delta (7, float32): dxyz 3 (m, link_torso_5) + rotation vector 3 (rad, applied on the
    left of the current orientation: R_next = exp(rv) R_cur) + gripper 1.
Real execution limits per step: 10 mm, 5 deg; cumulative path 0.3 m (eval panel defaults).
Images: observation.images.top (head camera), observation.images.wrist (right wrist).
"""
import numpy as np

from scipy.spatial.transform import Rotation

STATE_DIM = 15
ACTION_DIM = 7
MAX_STEP_M = 0.010
MAX_STEP_RAD = np.deg2rad(5.0)
GRIPPER_OPEN_WIDTH = 0.10  # sim finger separation when fully open


def ee_in_torso(eef_pos, eef_R, torso_pos, torso_R):
    p = torso_R.T @ (eef_pos - torso_pos)
    R = torso_R.T @ eef_R
    return p, R


def state15(arm_q, p, R, gripper_width):
    closed = 1.0 - np.clip(gripper_width / GRIPPER_OPEN_WIDTH, 0.0, 1.0)
    return np.concatenate([arm_q, p, Rotation.from_matrix(R).as_quat(), [closed]]).astype(np.float32)


def ee_delta(p0, R0, p1, R1, gripper_cmd):
    """Action that takes pose (p0, R0) to (p1, R1), both in link_torso_5."""
    return np.concatenate([p1 - p0, Rotation.from_matrix(R1 @ R0.T).as_rotvec(), [gripper_cmd]]).astype(np.float32)


def apply_ee_delta(p, R, action):
    """Target pose after one ee_delta action (inverse of ee_delta)."""
    return p + action[:3], Rotation.from_rotvec(action[3:6]).as_matrix() @ R


def within_real_limits(action):
    return np.linalg.norm(action[:3]) <= MAX_STEP_M + 1e-6 and np.linalg.norm(action[3:6]) <= MAX_STEP_RAD + 1e-6
