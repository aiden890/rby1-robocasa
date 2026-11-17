"""Record a short RB-Y1 episode with robosuite's DataCollectionWrapper, gather it with
RoboCasa's gather_demonstrations_as_hdf5, convert it, and check the real-format contract:
replaying each ee_delta from the recorded pose reproduces the next pose."""
import json
import os
import sys
from pathlib import Path

import numpy as np
import robosuite
from robosuite.wrappers import DataCollectionWrapper

import rby1_sim.register  # noqa: F401
from robosuite.controllers import load_composite_controller_config
from rby1_sim.data import real_format as RF

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from convert_to_real_format import convert  # noqa: E402


def test_record_gather_convert(tmp_path):
    os.environ.setdefault("PYNPUT_BACKEND", "dummy")  # collect_demos imports keyboard input (needs X otherwise)
    from robocasa.scripts.collect_demos import gather_demonstrations_as_hdf5
    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    config = dict(env_name="PickPlaceCounterToCabinet", robots="RBY1",
                  controller_configs=load_composite_controller_config(controller=None, robot="RBY1"),
                  layout_ids=1, style_ids=1, seed=0)
    env = robosuite.make(**config, has_renderer=False, has_offscreen_renderer=False, use_camera_obs=False,
                         ignore_done=True, control_freq=20)
    raw = tmp_path / "eps"
    env = DataCollectionWrapper(env, str(raw), use_env_xml_for_reset=True)
    env.reset()
    split = env.robots[0].composite_controller._action_split_indexes
    for t in range(30):
        a = np.zeros(env.action_dim)
        s, e = split["right"]
        a[s:s + 3] = [0.3, 0.0, 0.2 if t < 15 else -0.2]
        a[split["right_gripper"][0]] = 1.0 if t > 20 else -1.0
        env.step(a)
    env.close()
    gather_demonstrations_as_hdf5(str(raw), str(tmp_path), json.dumps({k: v for k, v in config.items()}))
    out = tmp_path / "lerobot"
    assert convert(str(tmp_path / "demo.hdf5"), str(out), hw=(64, 64)) == 1

    ds = LeRobotDataset(repo_id="rby1_sim/lerobot", root=out, video_backend="pyav")
    assert ds.num_episodes == 1 and ds.num_frames >= 25
    st = np.stack([ds[i]["observation.state"].numpy() for i in range(ds.num_frames)])
    act = np.stack([ds[i]["action"].numpy() for i in range(ds.num_frames)])
    assert st.shape[1] == RF.STATE_DIM and act.shape[1] == RF.ACTION_DIM
    assert np.abs(act[:, :3]).sum() > 0.01  # the arm moved
    # contract: state[t] + action[t] == state[t+1] (positions, link_torso_5)
    assert np.allclose(st[:-1, 7:10] + act[:-1, :3], st[1:, 7:10], atol=1e-4)
    assert act[-1, 6] == 1.0 and act[0, 6] == 0.0
