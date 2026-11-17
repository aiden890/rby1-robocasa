"""Gripper part: robo-synapse Gripper contract (open, close, widthMeters / hasObject)."""
import numpy as np


class GripperPart:
    def __init__(self, core):
        self.core = core

    def width(self, arm):
        idx = self.core.robot._ref_gripper_joint_pos_indexes[arm]
        return float(np.sum(np.abs(self.core.sim.data.qpos[idx])))

    def open(self, arm, steps=25):
        self.core.grip[arm] = -1.0
        self.core.step(steps)
        return True

    def close(self, arm, width_m=None, steps=25):
        self.core.grip[arm] = 1.0
        for _ in range(steps):
            self.core.step()
            if width_m is not None and self.width(arm) <= width_m:
                break
        return True

    def held_object(self, arm):
        """The object touching both finger pads of `arm`, else None."""
        env, sim = self.core.env, self.core.sim
        pads = {sim.model.geom_name2id(f"gripper0_{arm}_finger{i}_pad") for i in (1, 2)}
        roots = {bid: name for name, bid in env.obj_body_id.items()}
        touching = {}
        for i in range(sim.data.ncon):
            c = sim.data.contact[i]
            for g, other in ((c.geom1, c.geom2), (c.geom2, c.geom1)):
                if g in pads:
                    b = sim.model.geom_bodyid[other]
                    while b > 0 and b not in roots:
                        b = sim.model.body_parentid[b]
                    if b in roots:
                        touching.setdefault(roots[b], set()).add(g)
        both = [n for n, gs in touching.items() if len(gs) == 2]
        return both[0] if both else None

    def state(self, arm):
        held = self.held_object(arm)
        return {"available": True, "widthMeters": self.width(arm), "hasObject": held is not None,
                "raw": {"held": held, "command": "close" if self.core.grip[arm] > 0 else "open"}}
