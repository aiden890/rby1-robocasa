"""Lightweight client for the RB-Y1 RoboCasa sim server (numpy + pyzmq + msgpack only).

Install into another project (e.g. robo-synapse) without the simulator's dependencies:
    pip install -e /path/to/rby1-robocasa        # installs only this package

    from rby1_robocasa_client import SimClient, SimArm, SimGripper, SimMobileBase
    sim = SimClient("tcp://100.86.183.64:5590")
    sim.episode.reset("FetchColaFromFridge", seed=0)
    arm = SimArm(sim, "right")                    # robo-synapse common.interfaces.Arm
"""
from rby1_robocasa_client.client import SimClient, SimCallError, SimUnavailable  # noqa: F401
from rby1_robocasa_client.devices import SimArm, SimBody, SimGripper, SimMobileBase  # noqa: F401

DEFAULT_URL_ENV = "RBY1_ROBOCASA_URL"
