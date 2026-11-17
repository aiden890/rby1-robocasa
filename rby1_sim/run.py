"""Run a stock robosuite/RoboCasa script with the RB-Y1 registered.

python -m rby1_sim.run robocasa.scripts.bench_speed --env PickPlaceCounterToCabinet --robots RBY1
"""
import runpy
import sys

import rby1_sim.register  # noqa: F401  (robot, gripper, controller-config patch, lab tasks)

if __name__ == "__main__":
    module = sys.argv[1]
    sys.argv = [module] + sys.argv[2:]
    runpy.run_module(module, run_name="__main__", alter_sys=True)
