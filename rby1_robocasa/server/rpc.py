"""ZMQ REQ/REP server for one simulated RB-Y1 (msgpack + msgpack_numpy).

  request {"method": "<part>.<name>", "args": [...], "kwargs": {...}}
  reply   {"ok": true, "result": ...} | {"ok": false, "error": "...", "type": "..."}
Parts: episode, arm, gripper, base, body, perception (see server/__init__.py).

python -m rby1_robocasa.server.rpc --bind tcp://<ip>:5590      (scripts/sim_server.sh)
"""
import argparse
import time
import traceback

from rby1_robocasa.server.arm import ArmPart
from rby1_robocasa.server.base import BasePart
from rby1_robocasa.server.body import BodyPart
from rby1_robocasa.server.core import SimCore
from rby1_robocasa.server.gripper import GripperPart
from rby1_robocasa.server.perception import PerceptionPart

PROTOCOL = 2


class SimServer:
    """Routes "<part>.<method>" to the part objects; only listed methods are callable."""

    API = {
        "episode": ("reset", "info", "success", "step"),
        "arm": ("joint_names", "joint_positions", "ee_pose", "move_to_pose", "send_joint_trajectory",
                "external_wrench", "tare_wrench"),
        "gripper": ("open", "close", "state", "width", "held_object"),
        "base": ("set_velocity", "odom_pose", "world_pose", "stop"),
        "body": ("joint_names", "joint_positions", "set_torso", "set_head"),
        "perception": ("cameras", "camera", "objects"),
    }

    def __init__(self, image_hw=(480, 640), new_scene_every=1):
        self.core = SimCore(new_scene_every)
        gripper = GripperPart(self.core)
        self.parts = {"episode": self.core, "arm": ArmPart(self.core), "gripper": gripper,
                      "base": BasePart(self.core), "body": BodyPart(self.core),
                      "perception": PerceptionPart(self.core, gripper, image_hw)}

    def handle(self, req):
        method = str(req.get("method", ""))
        if method == "ping":
            return {"ok": True, "result": {"protocol": PROTOCOL, "time": time.time(), "task": self.core.task}}
        part, _, name = method.partition(".")
        if name not in self.API.get(part, ()):
            return {"ok": False, "error": f"unknown method {method!r}", "type": "ValueError"}
        try:
            return {"ok": True, "result": getattr(self.parts[part], name)(*req.get("args", []), **req.get("kwargs", {}))}
        except Exception as e:
            return {"ok": False, "error": str(e), "type": type(e).__name__, "trace": traceback.format_exc(limit=4)}

    def close(self):
        self.core.close()


def serve(bind, image_hw):
    import msgpack
    import msgpack_numpy
    import zmq

    msgpack_numpy.patch()
    server = SimServer(image_hw=image_hw)
    sock = zmq.Context.instance().socket(zmq.REP)
    sock.bind(bind)
    print(f"RB-Y1 RoboCasa sim server on {bind} (protocol {PROTOCOL})", flush=True)
    try:
        while True:
            req = msgpack.unpackb(sock.recv())
            sock.send(msgpack.packb(server.handle(req if isinstance(req, dict) else {})))
    finally:
        server.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bind", default="tcp://127.0.0.1:5590",
                    help="ZMQ bind address; the host's tailnet IP serves remote clients")
    ap.add_argument("--image-hw", type=int, nargs=2, default=[480, 640])
    a = ap.parse_args()
    serve(a.bind, tuple(a.image_hw))
