"""Serve a LeRobot checkpoint to robo-synapse's RB-Y1 "Policy 실행" panel.

Protocol = robo-synapse CONTROL_API.md section 3 (ZMQ REQ/REP + msgpack, msgpack_numpy):
  {"action": "health"}   -> {"status": "ok"}
  {"action": "metadata"} -> {policy_type, image_keys, image_shapes, state_dim, action_dim, fps, chunk_size, device}
  {"action": "reset"}    -> {"ok": true}
  {"action": "infer", "images": {role: HxWx3 uint8}, "state": (15,), "task": str} -> {"action": (7,)}
The panel itself enforces the real-robot limits (10 mm / 5 deg per step, 0.3 m path, watchdog).

python -m rby1_sim.serve.policy_server --checkpoint outputs/train/RUN/checkpoints/last/pretrained_model --port 5569
"""
import argparse

import numpy as np

from rby1_sim.data import real_format as RF


class LeRobotPolicy:
    """Wraps a lerobot PreTrainedPolicy (loaded with lerobot's own from_pretrained)."""

    def __init__(self, path, device="cuda"):
        import torch
        from lerobot.configs.policies import PreTrainedConfig
        from lerobot.policies.factory import get_policy_class

        self.torch = torch
        cfg = PreTrainedConfig.from_pretrained(path)
        cfg.device = device
        self.policy = get_policy_class(cfg.type).from_pretrained(path, config=cfg)
        self.policy.to(device).eval()
        self.device = device
        self.cfg = cfg
        self.image_keys = [k for k in cfg.input_features if k.startswith("observation.images.")]
        self.image_shapes = {k: list(cfg.input_features[k].shape[1:]) for k in self.image_keys}
        self.state_dim = int(cfg.input_features["observation.state"].shape[0])
        self.action_dim = int(cfg.output_features["action"].shape[0])
        self.chunk_size = int(getattr(cfg, "n_action_steps", 1))
        self.type = cfg.type

    def reset(self):
        self.policy.reset()

    def infer(self, images, state, task=""):
        t = self.torch
        batch = {"observation.state": t.as_tensor(state, dtype=t.float32, device=self.device)[None]}
        for k in self.image_keys:
            img = np.asarray(images[k.rsplit(".", 1)[-1]], dtype=np.float32) / 255.0
            batch[k] = t.as_tensor(img, device=self.device).permute(2, 0, 1)[None]
        batch["task"] = [task]
        with t.no_grad():
            return self.policy.select_action(batch)[0].cpu().numpy().astype(np.float32)


def handle(policy, req, fps):
    kind = req.get("action") if isinstance(req, dict) else None
    if kind == "health":
        return {"status": "ok"}
    if kind == "metadata":
        return {"policy_type": policy.type, "image_keys": policy.image_keys, "image_shapes": policy.image_shapes,
                "state_dim": policy.state_dim, "action_dim": policy.action_dim, "fps": fps,
                "chunk_size": policy.chunk_size, "device": policy.device}
    if kind == "reset":
        policy.reset()
        return {"ok": True}
    if kind == "infer":
        state = np.asarray(req.get("state"), dtype=np.float32)
        images = req.get("images") or {}
        if state.shape != (policy.state_dim,):
            return {"error": f"bad state shape {state.shape}, expected ({policy.state_dim},)"}
        missing = [k for k in policy.image_keys if k.rsplit(".", 1)[-1] not in images]
        if missing:
            return {"error": f"missing images {missing}"}
        for k in policy.image_keys:
            got = tuple(np.asarray(images[k.rsplit('.', 1)[-1]]).shape)
            if got != tuple(policy.image_shapes[k]) + (3,):
                return {"error": f"image {k} shape {got}, expected {tuple(policy.image_shapes[k]) + (3,)}"}
        action = policy.infer(images, state, req.get("task", ""))
        if action.shape != (RF.ACTION_DIM,) or not np.all(np.isfinite(action)):
            return {"error": f"policy produced invalid action {action}"}
        return {"action": action}
    return {"error": f"unknown request {kind!r}"}


def serve(policy, host, port, fps):
    import msgpack
    import msgpack_numpy
    import zmq

    msgpack_numpy.patch()
    sock = zmq.Context.instance().socket(zmq.REP)
    sock.bind(f"tcp://{host}:{port}")
    print(f"serving {policy.type} on tcp://{host}:{port}", flush=True)
    while True:
        req = msgpack.unpackb(sock.recv())
        try:
            res = handle(policy, req, fps)
        except Exception as e:  # keep serving; the panel shows the error and stops
            res = {"error": f"{type(e).__name__}: {e}"}
        sock.send(msgpack.packb(res))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5569)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--fps", type=float, default=20.0, help="dataset fps (sim demos are recorded at 20 Hz)")
    a = ap.parse_args()
    serve(LeRobotPolicy(a.checkpoint, a.device), a.host, a.port, a.fps)
