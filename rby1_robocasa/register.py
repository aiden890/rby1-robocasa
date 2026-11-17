"""Register the RB-Y1 with robosuite and RoboCasa. Import once before creating environments."""
import importlib.util

from robosuite.robots import ROBOT_CLASS_MAPPING, WheeledRobot

import rby1_robocasa.robot.models  # noqa: F401  (registers RBY1, RBY1Gripper)

ROBOT_NAME = "RBY1"
_done = False


def register():
    global _done
    if _done:
        return
    ROBOT_CLASS_MAPPING[ROBOT_NAME] = WheeledRobot
    # RoboCasa is optional (plain robosuite use works without it); any other import error is a bug
    if importlib.util.find_spec("robocasa") is not None:
        from rby1_robocasa.env import patch

        patch.apply()
        import rby1_robocasa.tasks  # noqa: F401  (registers the lab-assistant tasks)
    _done = True


register()
