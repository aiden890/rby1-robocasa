"""Register the RB-Y1 with robosuite and RoboCasa. Import once before creating environments."""
from robosuite.robots import ROBOT_CLASS_MAPPING, WheeledRobot

import rby1_sim.robot.models  # noqa: F401  (registers RBY1, RBY1Gripper)

ROBOT_NAME = "RBY1"
_done = False


def register():
    global _done
    if _done:
        return
    ROBOT_CLASS_MAPPING[ROBOT_NAME] = WheeledRobot
    try:
        from rby1_sim.sim import robocasa_patch

        robocasa_patch.apply()
        import rby1_sim.tasks  # noqa: F401  (registers lab-assistant tasks)
    except ImportError:  # robocasa not on the path: plain robosuite use still works
        pass
    _done = True


register()
