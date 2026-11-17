"""Cameras (robosuite camera utilities) and ground-truth objects, in link_torso_5."""
import numpy as np
from robosuite.utils import camera_utils as CU
from robosuite.utils import transform_utils as T

from rby1_robocasa.server.gripper import GripperPart


class PerceptionPart:
    def __init__(self, core, gripper: GripperPart, image_hw=(480, 640)):
        self.core, self.gripper, self.image_hw = core, gripper, tuple(image_hw)

    def cameras(self):
        m = self.core.sim.model
        return [m.camera(i).name for i in range(m.ncam) if m.camera(i).name.startswith("robot0_")]

    def camera(self, name, depth=True, hw=None):
        """rgb (H, W, 3 uint8, top row first), depth (H, W float32 metres), K (3x3) and
        T_base_cam (4x4, link_torso_5 <- camera with OpenCV axes: x right, y down, z forward)."""
        sim = self.core.sim
        h, w = hw or self.image_hw
        out = sim.render(camera_name=name, height=h, width=w, depth=depth)
        rgb, dep = out if depth else (out, None)
        res = {"rgb": np.flipud(rgb).copy(), "K": CU.get_camera_intrinsic_matrix(sim, name, h, w).tolist()}
        if depth:
            res["depth"] = np.flipud(CU.get_real_depth_map(sim, dep)).astype(np.float32).copy()
        tp, TR = self.core.torso5()
        T_w_t5 = np.eye(4)
        T_w_t5[:3, :3], T_w_t5[:3, 3] = TR, tp
        res["T_base_cam"] = (np.linalg.inv(T_w_t5) @ CU.get_camera_extrinsic_matrix(sim, name)).tolist()
        return res

    def objects(self):
        """Task objects: centre, top/bottom z, horizontal footprint (long, short), yaw of the long
        side, category and which arm holds it."""
        env = self.core.env
        _, TR = self.core.torso5()
        held = {a: self.gripper.held_object(a) for a in ("right", "left")}
        out = []
        for name, obj in env.objects.items():
            bid = env.obj_body_id[name]
            pos, R = env.sim.data.body_xpos[bid], env.sim.data.body_xmat[bid].reshape(3, 3)
            pts = np.array([self.core.to_t5(p) for p in obj.get_bbox_points(trans=pos, rot=T.mat2quat(R))])  # takes a quaternion
            lo, hi = pts.min(0), pts.max(0)
            Rt, size = TR.T @ R, np.array(obj.size)
            horiz = sorted([(size[i], Rt[:, i]) for i in range(3) if abs(Rt[2, i]) < 0.7], key=lambda t: -t[0])
            out.append({
                "name": name, "category": getattr(obj, "category", None) or name,
                "center": ((lo + hi) / 2).tolist(), "top_z": float(hi[2]), "bottom_z": float(lo[2]),
                "size": [float(s) for s, _ in horiz[:2]] or [float(hi[0] - lo[0]), float(hi[1] - lo[1])],
                "yaw": float(np.arctan2(horiz[0][1][1], horiz[0][1][0])) if horiz else 0.0,
                "held_by": next((a for a, h in held.items() if h == name), None),
            })
        return out
