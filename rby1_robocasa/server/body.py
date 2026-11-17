"""Torso (6 joints) and head (2 joints): absolute joint targets, held between commands."""
import numpy as np

from rby1_robocasa.server.core import CONTROL_HZ


class BodyPart:
    def __init__(self, core):
        self.core = core

    def joint_names(self, part):
        return self.core.part_joints(part)

    def joint_positions(self, part):
        names = self.core.part_joints(part)
        return dict(zip(names, self.core.qpos(names).tolist()))

    def set_torso(self, targets, tol_rad=0.02, timeout_s=6.0):
        self.core.torso_target = np.asarray(targets, float)
        return self._settle("torso", tol_rad, timeout_s)

    def set_head(self, targets, tol_rad=0.02, timeout_s=3.0):
        self.core.head_target = np.asarray(targets, float)
        return self._settle("head", tol_rad, timeout_s)

    def _settle(self, part, tol, timeout_s):
        target = self.core.torso_target if part == "torso" else self.core.head_target
        err = np.inf
        for _ in range(int(timeout_s * CONTROL_HZ)):
            err = float(np.max(np.abs(self.core.qpos(self.core.part_joints(part)) - target)))
            if err < tol:
                return {"ok": True, "error_rad": err}
            self.core.step()
        return {"ok": False, "error_rad": err, "reason": "timeout"}
