"""Convert RoboCasa demonstration HDF5 (robocasa.scripts.collect_demos, robots RBY1) to a
LeRobot dataset in the real RB-Y1 format (rby1_sim/data/real_format.py).

Replays the recorded MuJoCo states the same way robosuite's playback script does
(reset_from_xml_string + set_state_from_flattened) and reads poses/images from the sim.

python -m rby1_sim.run scripts/convert_to_real_format.py --hdf5 demo.hdf5 --out outputs/datasets/NAME
(or: python scripts/convert_to_real_format.py ...; it imports rby1_sim.register itself)
"""
import argparse
import json
from pathlib import Path

import h5py
import numpy as np
import robosuite

import rby1_sim.register  # noqa: F401
from rby1_sim.data import real_format as RF

CAMS = {"top": "robot0_head_camera", "wrist_right": "robot0_right_wrist_camera", "wrist_left": "robot0_left_wrist_camera"}


def features(hw, sim_extras=False):
    img = lambda: {"dtype": "video", "shape": (hw[0], hw[1], 3), "names": ["height", "width", "channels"]}
    f32 = lambda n: {"dtype": "float32", "shape": (n,), "names": None}
    return {
        "observation.images.top": img(),
        "observation.images.wrist": img(),
        "observation.state": f32(RF.STATE_DIM),
        "action": f32(RF.ACTION_DIM),
    } | ({"observation.base": f32(3)} if sim_extras else {})


def make_env(env_info, hw):
    cfg = json.loads(env_info)
    for k in ("has_renderer", "has_offscreen_renderer", "use_camera_obs", "camera_names", "camera_heights",
              "camera_widths", "render_camera", "renderer"):
        cfg.pop(k, None)
    cfg["translucent_robot"] = False
    return robosuite.make(**cfg, has_renderer=False, has_offscreen_renderer=True, use_camera_obs=True,
                          camera_names=list(CAMS.values()), camera_heights=hw[0], camera_widths=hw[1],
                          ignore_done=True)


def poses(env, arm):
    sim = env.sim
    sid = sim.model.site_name2id
    tp, TR = sim.data.site_xpos[sid("robot0_right_center")], sim.data.site_xmat[sid("robot0_right_center")].reshape(3, 3)
    ep, ER = sim.data.site_xpos[sid(f"gripper0_{arm}_grip_site")], sim.data.site_xmat[sid(f"gripper0_{arm}_grip_site")].reshape(3, 3)
    p, R = RF.ee_in_torso(ep, ER, tp, TR)
    robot = env.robots[0]
    names = [j for j in robot.robot_model.joints if f"{arm}_arm_" in j]
    q = np.array([sim.data.qpos[sim.model.get_joint_qpos_addr(j)] for j in names])
    width = float(np.sum(np.abs(sim.data.qpos[robot._ref_gripper_joint_pos_indexes[arm]])))
    bid = sim.model.body_name2id("mobilebase0_support")
    R0 = sim.data.xmat[bid].reshape(3, 3)
    base = np.array([sim.data.xpos[bid][0], sim.data.xpos[bid][1], np.arctan2(R0[1, 0], R0[0, 0])])
    return p, R, q, width, base


def active_arm(env, actions):
    split = env.robots[0].composite_controller._action_split_indexes
    mag = {arm: np.abs(actions[:, split[arm][0]:split[arm][1]]).sum() for arm in ("right", "left")}
    return max(mag, key=mag.get), split


def convert(hdf5, out, hw=(240, 320), repo_id=None, sim_extras=False):
    """sim_extras adds observation.base and action.sim (full composite action); leave them off
    for policies meant for the real robot, which has neither input."""
    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    f = h5py.File(hdf5, "r")
    env = make_env(f["data"].attrs["env_info"], hw)
    env.reset()
    feats = features(hw, sim_extras)
    ds = None
    n_ep = 0
    for demo in sorted(f["data"].keys(), key=lambda s: int(s.split("_")[-1])):
        g = f["data"][demo]
        states, actions = g["states"][()], g["actions"][()]
        if "ep_meta" in g.attrs and hasattr(env, "set_ep_meta"):
            env.set_ep_meta(json.loads(g.attrs["ep_meta"]))
        env.reset()
        env.reset_from_xml_string(env.edit_model_xml(g.attrs["model_file"]))
        env.sim.reset()
        arm, split = active_arm(env, actions)
        if ds is None:
            if sim_extras:
                feats["action.sim"] = {"dtype": "float32", "shape": (actions.shape[1],), "names": None}
            ds = LeRobotDataset.create(repo_id=repo_id or f"rby1_sim/{Path(out).name}", fps=20, features=feats,
                                       root=out, robot_type="rby1m_sim", use_videos=True, image_writer_threads=4)
        lang = json.loads(g.attrs["ep_meta"]).get("lang", "") if "ep_meta" in g.attrs else ""
        frames = []
        for s in states:
            env.sim.set_state_from_flattened(s)
            env.sim.forward()
            obs = env._get_observations(force_update=True)
            frames.append((poses(env, arm), obs))
        gs, ge = split[f"{arm}_gripper"]
        for t in range(len(frames) - 1):
            (p0, R0, q0, w0, b0), obs = frames[t]
            (p1, R1, *_), _ = frames[t + 1]
            grip = 1.0 if actions[t, gs] > 0 else 0.0
            frame = {
                "observation.images.top": np.flipud(obs[f"{CAMS['top']}_image"]).copy(),
                "observation.images.wrist": np.flipud(obs[f"{CAMS['wrist_' + arm]}_image"]).copy(),
                "observation.state": RF.state15(q0, p0, R0, w0),
                "action": RF.ee_delta(p0, R0, p1, R1, grip),
            }
            if sim_extras:
                frame["observation.base"] = b0.astype(np.float32)
                frame["action.sim"] = actions[t].astype(np.float32)
            ds.add_frame(frame, task=lang)
        ds.save_episode()
        n_ep += 1
    f.close()
    env.close()
    return n_ep


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--hdf5", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--image-hw", type=int, nargs=2, default=[240, 320])
    ap.add_argument("--sim-extras", action="store_true", help="also store base pose and the full sim action")
    a = ap.parse_args()
    print(convert(a.hdf5, a.out, tuple(a.image_hw), sim_extras=a.sim_extras), "episodes ->", a.out)
