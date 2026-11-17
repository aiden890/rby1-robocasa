"""Render a task's reset scene from the robot cameras: python scripts/render_scene.py TASK [--layout N --style N]."""
import argparse
from pathlib import Path

import imageio.v2 as imageio
import numpy as np

from rby1_robocasa.env.envs import make, CAMERAS

ap = argparse.ArgumentParser()
ap.add_argument("task")
ap.add_argument("--layout", type=int)
ap.add_argument("--style", type=int)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--out", default="outputs/renders")
a = ap.parse_args()
env = make(a.task, layout=a.layout, style=a.style, seed=a.seed, image_hw=(360, 480))
obs = env.reset()
for _ in range(10):
    obs, *_ = env.step(np.zeros(env.action_dim))  # all parts are delta/velocity: zero = hold
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
tiles = [np.flipud(obs[f"{c}_image"]) for c in CAMERAS]
path = out / f"{a.task}_s{a.seed}.png"
imageio.imwrite(path, np.concatenate(tiles, axis=1))
print(path, env.get_ep_meta().get("lang"), "layout", env.layout_id, "style", env.style_id)
