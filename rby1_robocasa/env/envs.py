"""Environment factory: RoboCasa's own create_env with robots="RBY1"."""
import rby1_robocasa.register  # noqa: F401
from robocasa.utils.env_utils import create_env

# robot cameras (robot0_ prefix added by robosuite); real roles: top = head, wrist = right wrist
CAMERAS = ["robot0_head_camera", "robot0_right_wrist_camera", "robot0_left_wrist_camera", "robot0_agentview_center"]


def make(task, *, layout=None, style=None, seed=None, cameras=CAMERAS, image_hw=(240, 320), **kwargs):
    return create_env(
        task, robots="RBY1", camera_names=list(cameras), camera_heights=image_hw[0], camera_widths=image_hw[1],
        seed=seed, layout_ids=layout, style_ids=style, **kwargs,
    )
