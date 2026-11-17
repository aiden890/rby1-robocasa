"""Minimal monkeypatches so stock robosuite/RoboCasa code runs with robots="RBY1" (ext/ unmodified).

- load_composite_controller_config(controller=None, robot="RBY1") returns the RB-Y1 config
  (robosuite looks for default_<robot>.json inside its own package otherwise).
- RoboCasa's robot-relative cameras sit behind/above the base for PandaOmron; the RB-Y1 is
  taller, so CAM_CONFIGS["RBY1"] moves the third-person views higher and further back.
- a list robot argument (robocasa bench_speed passes argparse nargs="+") is reduced to its
  first name; stock robosuite calls .lower() on it and crashes.
"""
import robosuite.controllers as rc
import robosuite.controllers.composite.composite_controller_factory as ccf

from rby1_sim.robot import controller_config_path

_orig = ccf.load_composite_controller_config


def _is_rby1(robot):
    if isinstance(robot, (list, tuple)):
        robot = robot[0] if robot else None
    return isinstance(robot, str) and robot.upper() == "RBY1"


def load_composite_controller_config(controller=None, robot=None):
    if isinstance(robot, (list, tuple)):
        robot = robot[0] if robot else None
    if controller is None and _is_rby1(robot):
        return _orig(controller=controller_config_path())
    return _orig(controller=controller, robot=robot)


RBY1_CAMS = {
    "robot0_agentview_center": dict(pos=[-0.95, 0.0, 1.85]),
    "robot0_agentview_left": dict(pos=[-0.85, 0.45, 1.75]),
    "robot0_agentview_right": dict(pos=[-0.85, -0.45, 1.75]),
    "robot0_frontview": dict(pos=[-0.85, 0.0, 1.65]),
}


def apply():
    try:
        from robocasa.utils import camera_utils

        camera_utils.CAM_CONFIGS["RBY1"] = RBY1_CAMS
    except ImportError:
        pass
    ccf.load_composite_controller_config = load_composite_controller_config
    rc.load_composite_controller_config = load_composite_controller_config
    try:
        import robocasa.utils.env_utils as eu

        eu.load_composite_controller_config = load_composite_controller_config
    except ImportError:
        pass
