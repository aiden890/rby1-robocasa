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

    # OSC delta control converges slowly near the goal (the steady-state error of a P loop against
    # gravity/joint damping); the command is boosted inside NEAR_M so moves finish within TOL_M.
    # TOL_M matches the real RB-Y1 facade's arrival tolerance (Rby1SkillsRobot.HOME_TOL_M, 5 mm).
    NEAR_M, NEAR_GAIN, TOL_M, STALL_STEPS = 0.02, 2.0, 0.005, 40

    def move_to_pose(self, arm, position, orientation=None, cartesian=False, max_step_m=0.01,
                     max_step_rad=0.05, tol_m=None, tol_rad=0.03, timeout_s=15.0):
        """Servo the fingertip frame to a link_torso_5 pose along a straight line."""
        tol_m = self.TOL_M if tol_m is None else tol_m
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
            if stall > self.STALL_STEPS and err > 2 * tol_m:
                return {"ok": False, "error_m": err,
                        "reason": f"stalled {err * 100:.1f} cm from the goal ({self.blocked_by(arm)})"}
            gain = self.NEAR_GAIN if err < self.NEAR_M else 1.0
            dp = dp * min(gain, max_step_m / max(err, 1e-9))
            ang = np.linalg.norm(dr)
            dr = dr * min(gain, max_step_rad / max(ang, 1e-9))
            self.core.step(arm_cmd={arm: np.concatenate([dp / POS_SCALE, dr / ROT_SCALE])})
        ok = err < 2 * tol_m
        return {"ok": ok, "error_m": err, **({} if ok else {"reason": f"timeout ({self.blocked_by(arm)})"})}

    def blocked_by(self, arm, margin_rad=0.05):
        """Why an arm stops short: its joints at a limit and what its links touch."""
        sim = self.core.sim
        m = sim.model
        limits = []
        for j in self.joint_names(arm):
            jid = m.joint_name2id(j)
            lo, hi = m.jnt_range[jid]
            q = sim.data.qpos[m.get_joint_qpos_addr(j)]
            if q < lo + margin_rad or q > hi - margin_rad:
                limits.append(j.rsplit("_", 1)[-1])
        mine = (f"robot0_link_{arm}_arm", f"gripper0_{arm}_")
        touching = set()
        for i in range(sim.data.ncon):
            c = sim.data.contact[i]
            for g, other in ((c.geom1, c.geom2), (c.geom2, c.geom1)):
                gb = m.body_id2name(m.geom_bodyid[g]) or ""
                if (gb.startswith(mine[0]) or (m.geom_id2name(g) or "").startswith(mine[1])):
                    ob = m.body_id2name(m.geom_bodyid[other]) or ""
                    if not (ob.startswith(mine[0]) or (m.geom_id2name(other) or "").startswith(mine[1])):
                        touching.add(ob.split("_main")[0][:40])
        parts = []
        if limits:
            parts.append(f"joint limit: {arm} arm joint {','.join(limits)}")
        if touching:
            parts.append("contact: " + ", ".join(sorted(touching)[:4]))
        return "; ".join(parts) or "reach limit"

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
