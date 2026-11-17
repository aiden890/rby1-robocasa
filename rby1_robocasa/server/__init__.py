"""RoboCasa RB-Y1 simulation server (runs in the Docker image on any GPU host).

  core.py        SimCore: episode (task reset, success), control stepping, frames
  arm.py         ArmPart: ee pose, Cartesian/joint moves, wrench   (robo-synapse Arm)
  gripper.py     GripperPart: open/close, width, held object        (robo-synapse Gripper)
  base.py        BasePart: body-frame velocity lease, odometry      (robo-synapse MobileBase)
  body.py        BodyPart: torso (6) and head (2) joint targets
  perception.py  PerceptionPart: cameras (RGB, metric depth, K, T), ground-truth objects
  rpc.py         ZMQ server: "<part>.<method>" -> part method
Frames: link_torso_5 (x forward, y left, z up), quaternions (x, y, z, w), metres.
"""
