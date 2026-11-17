"""Episode and control stepping shared by the part modules.

Simulation time only advances inside commands (control at 20 Hz). Each control step sends one
composite action: arm OSC deltas (link_torso_5), gripper commands, torso/head steered to their
joint targets, base joint velocities.
"""
import numpy as np

import rby1_robocasa.register  # noqa: F401
from rby1_robocasa.env.envs import make
from rby1_robocasa.env.vec import SceneReuse

ARMS = ("right", "left")
CONTROL_HZ = 20
# controller output per unit action (robot/configs/controller_default.json)
POS_SCALE, ROT_SCALE, TORSO_SCALE, HEAD_SCALE = 0.05, 0.5, 0.03, 0.05


class SimError(RuntimeError):
    pass


class SimCore:
    def __init__(self, new_scene_every=1):
        self.new_scene_every = new_scene_every
        self.wrapped = None
        self.task = None
        self.grip = {a: -1.0 for a in ARMS}
        self.torso_target = None
        self.head_target = None
        self.reset_hooks = []      # parts register per-episode reset callbacks
        self.steps = 0             # control steps taken (lets a part tell whether others stepped)

    # -------------------------------------------------------------- episode
    def reset(self, task, seed=None, layout=None, style=None, task_kwargs=None):
        if self.wrapped is None or task != self.task:
            self.close()
            # cameras are rendered on request (PerceptionPart); RoboCasa's create_env always turns
            # camera observations on, so the env keeps one tiny observation camera
            env = make(task, seed=seed, layout=layout, style=style, cameras=["robot0_head_camera"],
                       image_hw=(8, 8), **(task_kwargs or {}))
            self.wrapped = SceneReuse(env, self.new_scene_every)
            self.task = task
        self.wrapped.reset()
        self.grip = {a: -1.0 for a in ARMS}
        self.torso_target = self.qpos(self.part_joints("torso"))
        self.head_target = self.qpos(self.part_joints("head"))
        for hook in self.reset_hooks:
            hook()
        self.step(5)
        return self.info()

    def info(self):
        e = self.env
        return {"task": self.task, "lang": e.get_ep_meta().get("lang", ""), "layout": e.layout_id,
                "style": e.style_id, "control_hz": CONTROL_HZ, "sim_time": float(e.sim.data.time),
                "objects": sorted(e.objects.keys())}

    def success(self):
        return bool(self.env._check_success())

    def close(self):
        if self.wrapped is not None:
            self.wrapped.close()
            self.wrapped = None

    @property
    def env(self):
        if self.wrapped is None:
            raise SimError("no episode: call episode.reset(task) first")
        return self.wrapped.env

    @property
    def sim(self):
        return self.env.sim

    @property
    def robot(self):
        return self.env.robots[0]

    # -------------------------------------------------------------- stepping
    def part_joints(self, part):
        return list(self.robot.composite_controller.part_controllers[part].joint_names)

    def qpos(self, joints):
        sim = self.sim
        return np.array([sim.data.qpos[sim.model.get_joint_qpos_addr(j)] for j in joints])

    def step(self, n=1, arm_cmd=None, base=None):
        """arm_cmd: {arm: 6 OSC delta values in link_torso_5}. The arm controllers take world-frame
        deltas (a torso-fixed controller frame let torso sway feed back into the arm goal and
        oscillate), so the command is rotated into world here."""
        e = self.env
        split = self.robot.composite_controller._action_split_indexes
        for _ in range(int(n)):
            a = np.zeros(e.action_dim)
            if arm_cmd:
                _, TR = self.torso5()
            for arm, cmd in (arm_cmd or {}).items():
                s, t = split[arm]
                cmd = np.asarray(cmd, float)
                a[s:t] = np.clip(np.concatenate([TR @ cmd[:3], TR @ cmd[3:6]]), -1, 1)
            for arm in ARMS:
                a[split[f"{arm}_gripper"][0]] = self.grip[arm]
            for part, target, scale in (("torso", self.torso_target, TORSO_SCALE),
                                        ("head", self.head_target, HEAD_SCALE)):
                s, t = split[part]
                a[s:t] = np.clip((target - self.qpos(self.part_joints(part))) / scale, -1, 1)
            if base is not None:
                s, t = split["base"]
                a[s:t] = np.clip(base, -1, 1)
            e.step(a)
            self.steps += 1
        return {"sim_time": float(e.sim.data.time)}

    # -------------------------------------------------------------- frames
    def site(self, name):
        i = self.sim.model.site_name2id(name)
        return self.sim.data.site_xpos[i].copy(), self.sim.data.site_xmat[i].reshape(3, 3).copy()

    def torso5(self):
        return self.site("robot0_right_center")

    def to_t5(self, p_w, R_w=None):
        tp, TR = self.torso5()
        p = TR.T @ (np.asarray(p_w) - tp)
        return (p, TR.T @ R_w) if R_w is not None else p
