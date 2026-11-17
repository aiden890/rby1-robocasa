"""Scene reuse + parallel workers, built on existing robosuite/tianshou mechanisms.

- SceneReuse: robosuite's own `hard_reset` switch. RoboCasa forces hard_reset=True (new layout,
  style and objects compiled on every reset); here a new scene is compiled only every
  `new_scene_every` resets, otherwise reset() re-places robot/objects in the compiled scene.
- make_vec: tianshou SubprocVectorEnv (already a RoboCasa dependency), one seed per worker;
  workers stay alive, so each keeps its compiled scene between episodes.
"""
import functools

from rby1_robocasa.env.envs import make


class SceneReuse:
    def __init__(self, env, new_scene_every=10):
        self.env = env
        self.every = max(1, int(new_scene_every))
        self.n = 0

    def reset(self):
        self.env.hard_reset = (self.n % self.every == 0)
        self.n += 1
        return self.env.reset()

    def __getattr__(self, k):
        return getattr(self.env, k)


def _build(task, seed, new_scene_every, kwargs):
    import rby1_robocasa.register  # noqa: F401  (spawned workers start from a fresh interpreter)

    return SceneReuse(make(task, seed=seed, **kwargs), new_scene_every)


def make_vec(task, n, seed=0, new_scene_every=10, **kwargs):
    """Workers are spawned (not forked): a forked child inherits the parent's EGL context and
    MuJoCo's offscreen framebuffer fails (error 0x8cdd)."""
    import multiprocessing as mp

    from tianshou.env import SubprocVectorEnv

    mp.set_start_method("spawn", force=True)  # tianshou 0.4.10 has no context argument
    fns = [functools.partial(_build, task, seed + i, new_scene_every, kwargs) for i in range(n)]
    return SubprocVectorEnv(fns)
