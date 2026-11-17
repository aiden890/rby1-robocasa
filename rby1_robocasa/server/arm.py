"""Arm part: robo-synapse Arm contract (ee_pose, move_to_pose, send_joint_trajectory, wrench)."""
import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

from rby1_robocasa.server.core import ARMS, CONTROL_HZ, POS_SCALE, ROT_SCALE


class ArmPart:
    def __init__(self, core):
        self.core = core
        self._tare = {a: np.zeros(6) for a in ARMS}
        core.reset_hooks.append(lambda: self._tare.update({a: np.zeros(6) for a in ARMS}))

    def joint_names(self, arm):
        return [j for j in self.core.robot.robot_model.joints if f"{arm}_arm_" in j]

    def joint_positions(self, arm):
        names = self.joint_names(arm)
        return dict(zip(names, self.core.qpos(names).tolist()))

    def _tip(self, arm):
        return self.core.to_t5(*self.core.site(f"gripper0_{arm}_grip_site"))

    def ee_pose(self, arm):
        p, R = self._tip(arm)
        return {"position": p.tolist(), "orientation": Rotation.from_matrix(R).as_quat().tolist()}

    def move_to_pose(self, arm, position, orientation=None, cartesian=False, max_step_m=0.01,
                     max_step_rad=0.05, tol_m=0.004, tol_rad=0.03, timeout_s=15.0):
        """Servo the fingertip frame to a link_torso_5 pose along a straight line."""
        goal = np.asarray(position, float)
        R_goal = None if orientation is None else Rotation.from_quat(orientation).as_matrix()
        best, stall, err = np.inf, 0, np.inf
        for _ in range(int(timeout_s * CONTROL_HZ)):
            p, R = self._tip(arm)
            dp = goal - p
            dr = Rotation.from_matrix(R_goal @ R.T).as_rotvec() if R_goal is not None else np.zeros(3)
            err = float(np.linalg.norm(dp))
            if err < tol_m and np.linalg.norm(dr) < tol_rad:
                return {"ok": True, "error_m": err}
            stall = stall + 1 if err > best - 2e-4 else 0
            best = min(best, err)
            if stall > 30:
                return {"ok": False, "error_m": err,
                        "reason": f"stalled {err * 100:.1f} cm from the goal (reach limit or contact)"}
            dp *= min(1.0, max_step_m / max(err, 1e-9))
            ang = np.linalg.norm(dr)
            dr *= min(1.0, max_step_rad / max(ang, 1e-9))
            self.core.step(arm_cmd={arm: np.concatenate([dp / POS_SCALE, dr / ROT_SCALE])})
        return {"ok": False, "error_m": err, "reason": "timeout"}

    def send_joint_trajectory(self, arm, targets, duration_s=None):
        """The goal's fingertip pose (FK on a scratch MjData) reached with the Cartesian
        controller: joint-exact tracking would need a second arm controller."""
        sim = self.core.sim
        m = sim.model._model
        d = mujoco.MjData(m)
        d.qpos[:] = sim.data.qpos
        for j, q in targets.items():
            d.qpos[sim.model.get_joint_qpos_addr(j)] = q
        mujoco.mj_kinematics(m, d)
        sid, tid = m.site(f"gripper0_{arm}_grip_site").id, m.site("robot0_right_center").id
        TR = d.site_xmat[tid].reshape(3, 3)
        p = TR.T @ (d.site_xpos[sid] - d.site_xpos[tid])
        R = TR.T @ d.site_xmat[sid].reshape(3, 3)
        return self.move_to_pose(arm, p.tolist(), Rotation.from_matrix(R).as_quat().tolist())

    def _raw_wrench(self, arm):
        r = self.core.robot
        return np.concatenate([r.get_sensor_measurement(f"gripper0_{arm}_force_ee"),
                               r.get_sensor_measurement(f"gripper0_{arm}_torque_ee")])

    def external_wrench(self, arm):
        return (self._raw_wrench(arm) - self._tare[arm]).tolist()

    def tare_wrench(self, arm):
        self._tare[arm] = self._raw_wrench(arm)
        return True
