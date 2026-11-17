"""Lab-assistant tasks load with the RB-Y1, reset, and are not solved at reset."""
import numpy as np
import pytest

from rby1_sim.sim.envs import make
from rby1_sim.tasks import TASKS


@pytest.mark.parametrize("key", sorted(TASKS))
def test_task_resets(key):
    env = make(TASKS[key], seed=0, cameras=["robot0_head_camera"], image_hw=(64, 64))
    obs = env.reset()
    for _ in range(5):
        obs, *_ = env.step(np.zeros(env.action_dim))
    assert obs["robot0_head_camera_image"].shape == (64, 64, 3)
    assert not env._check_success()
    assert env.get_ep_meta()["lang"]
    env.close()
