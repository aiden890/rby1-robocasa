"""Time env creation, hard/soft reset and stepping (single and SubprocVectorEnv).

python scripts/bench_env.py --task PickPlaceCounterToCabinet --resets 5 --steps 200 --workers 1 4
Prints a markdown table.
"""
import argparse
import time

import numpy as np

from rby1_robocasa.env.envs import make
from rby1_robocasa.env.vec import make_vec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="PickPlaceCounterToCabinet")
    ap.add_argument("--resets", type=int, default=5)
    ap.add_argument("--steps", type=int, default=200)
    ap.add_argument("--workers", type=int, nargs="+", default=[1, 4])
    ap.add_argument("--image-hw", type=int, nargs=2, default=[240, 320])
    ap.add_argument("--cameras", nargs="+", default=["robot0_head_camera", "robot0_right_wrist_camera"])
    a = ap.parse_args()
    kw = dict(cameras=a.cameras, image_hw=tuple(a.image_hw))
    rows = []

    t = time.time(); env = make(a.task, seed=0, **kw); rows.append(("create", time.time() - t, 1))
    t = time.time(); env.reset(); rows.append(("first reset", time.time() - t, 1))
    for mode in (True, False):
        env.hard_reset = mode
        ts = []
        for _ in range(a.resets):
            t = time.time(); env.reset(); ts.append(time.time() - t)
        rows.append((f"reset ({'new scene' if mode else 'same scene'})", float(np.mean(ts)), a.resets))
    zero = np.zeros(env.action_dim)
    t = time.time()
    for _ in range(a.steps):
        env.step(zero)
    dt = time.time() - t
    env.close()
    print(f"| item | value | n |\n|---|---|---|")
    for k, v, n in rows:
        print(f"| {k} | {v:.2f} s | {n} |")
    print(f"| step, 1 env | {a.steps/dt:.1f} steps/s | {a.steps} |")
    for w in a.workers:
        if w <= 1:
            continue
        venv = make_vec(a.task, w, **kw)
        t = time.time(); venv.reset(); r = time.time() - t
        act = np.zeros((w, len(zero)))
        t = time.time()
        for _ in range(a.steps):
            venv.step(act)
        dt = time.time() - t
        venv.close()
        print(f"| step, {w} workers (total) | {w*a.steps/dt:.1f} steps/s | {w*a.steps} |")
        print(f"| parallel first reset, {w} workers | {r:.2f} s | {w} |")


if __name__ == "__main__":
    main()
