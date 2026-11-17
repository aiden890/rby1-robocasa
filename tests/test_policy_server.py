"""Policy server speaks the robo-synapse contract (stub policy, no checkpoint needed)."""
import numpy as np

from rby1_sim.serve.policy_server import handle


class Stub:
    type = "stub"
    image_keys = ["observation.images.top", "observation.images.wrist"]
    image_shapes = {k: [48, 64] for k in image_keys}
    state_dim, action_dim, chunk_size, device = 15, 7, 1, "cpu"

    def reset(self):
        self.n = 0

    def infer(self, images, state, task):
        return np.full(7, 0.001, np.float32)


def test_contract():
    p = Stub()
    assert handle(p, {"action": "health"}, 20) == {"status": "ok"}
    meta = handle(p, {"action": "metadata"}, 20)
    assert meta["state_dim"] == 15 and meta["action_dim"] == 7 and meta["fps"] == 20
    assert handle(p, {"action": "reset"}, 20) == {"ok": True}
    img = np.zeros((48, 64, 3), np.uint8)
    ok = handle(p, {"action": "infer", "images": {"top": img, "wrist": img}, "state": np.zeros(15)}, 20)
    assert ok["action"].shape == (7,)
    assert "error" in handle(p, {"action": "infer", "images": {"top": img}, "state": np.zeros(15)}, 20)
    assert "error" in handle(p, {"action": "infer", "images": {"top": img, "wrist": img}, "state": np.zeros(14)}, 20)
