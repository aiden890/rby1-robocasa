"""Client-side frame convention (no sim needed): RB-Y1 facade pose <-> sim fingertip pose."""
import numpy as np

from rby1_robocasa_client.devices import SimArm, _mat_to_quat, _quat_to_mat


class FakeSim:
    class _Arm:
        def __init__(self):
            # fingertip 0.5 m ahead, approach straight down (sim tip frame: z = approach)
            R = np.array([[1.0, 0, 0], [0, -1.0, 0], [0, 0, -1.0]])
            self.pose = {"position": [0.5, -0.2, -0.1], "orientation": list(_mat_to_quat(R))}
            self.sent = None

        def ee_pose(self, side):
            return self.pose

        def move_to_pose(self, side, position, orientation, cartesian):
            self.sent = (position, orientation)
            return {"ok": True}

    def __init__(self):
        self.arm = self._Arm()


def test_rby1_convention_round_trip():
    sim = FakeSim()
    arm = SimArm(sim, "right")
    ee = arm.ee_pose()
    R_ee = _quat_to_mat(ee["orientation"])
    # fingers along -z of the facade frame = straight down; wrist 7.4 cm above the fingertip
    assert np.allclose(-R_ee[:, 2], [0, 0, -1], atol=1e-9)
    assert np.allclose(ee["position"], [0.5, -0.2, -0.1 + 0.074], atol=1e-9)
    assert arm.move_to_pose(ee["position"], orientation=ee["orientation"])
    tip, q = sim.arm.sent
    assert np.allclose(tip, sim.arm.pose["position"], atol=1e-9)
    assert np.allclose(_quat_to_mat(q), _quat_to_mat(sim.arm.pose["orientation"]), atol=1e-9)
