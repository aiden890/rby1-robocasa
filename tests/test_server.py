"""Sim server through the real transport: ZMQ server thread + client device adapters."""
import threading

import numpy as np
import pytest

from rby1_robocasa_client import SimArm, SimBody, SimClient, SimGripper, SimMobileBase


@pytest.fixture(scope="module")
def sim():
    import msgpack
    import msgpack_numpy
    import zmq

    from rby1_robocasa.server.rpc import SimServer

    msgpack_numpy.patch()
    server = SimServer(image_hw=(240, 320))
    sock = zmq.Context.instance().socket(zmq.REP)
    port = sock.bind_to_random_port("tcp://127.0.0.1")

    def loop():
        while True:
            req = msgpack.unpackb(sock.recv())
            if req.get("method") == "__stop__":
                sock.send(msgpack.packb({"ok": True}))
                break
            sock.send(msgpack.packb(server.handle(req)))

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    client = SimClient(f"tcp://127.0.0.1:{port}", timeout_s=300)
    client.ping()
    info = client.episode.reset("PickPlaceCounterToCabinet", seed=0, layout=1, style=1)
    assert info["lang"] and info["objects"]
    yield client
    server.close()


def test_unknown_method_is_refused(sim):
    from rby1_robocasa_client import SimCallError
    with pytest.raises(SimCallError):
        sim.call("episode.close")


def test_arm_moves_in_torso_frame(sim):
    arm = SimArm(sim, "right")
    assert len(arm.joint_names) == 7
    p0 = np.array(arm.ee_pose()["position"])
    assert arm.move_to_pose(tuple(p0 + [0.0, 0.0, 0.05]))
    p1 = np.array(arm.ee_pose()["position"])
    assert abs(p1[2] - p0[2] - 0.05) < 0.01 and np.linalg.norm(p1[:2] - p0[:2]) < 0.01
    assert len(arm.external_wrench()) == 6 and arm.tare_wrench()


def test_gripper(sim):
    g = SimGripper(sim, "right")
    g.close_gripper()
    closed = g.gripper_state()["widthMeters"]
    g.open_gripper()
    opened = g.gripper_state()["widthMeters"]
    assert closed < 0.02 < 0.08 < opened
    assert g.gripper_state()["hasObject"] is False


def test_base_velocity_lease(sim):
    """RoboCasa spawns the robot facing a counter: back away from it."""
    base = SimMobileBase(sim, lease_s=0.1)
    x0 = base.odom_pose()[0]
    for _ in range(10):        # 1 s at 0.2 m/s backwards
        base.set_velocity(-0.2, 0.0, 0.0)
    dx = base.odom_pose()[0] - x0
    assert -0.25 < dx < -0.15, dx


def test_body(sim):
    body = SimBody(sim)
    q = body.joint_positions("torso")
    assert len(q) == 6
    assert body.look(0.0, 0.4)


def test_camera_frames_agree_with_objects(sim):
    """An object's centre projected with K and T_base_cam lands where the depth image sees
    roughly that distance: frames, intrinsics and image orientation agree."""
    cam = sim.perception.camera("robot0_head_camera")
    rgb, depth = np.asarray(cam["rgb"]), np.asarray(cam["depth"])
    assert rgb.shape == (240, 320, 3) and depth.shape == (240, 320)
    K, T = np.asarray(cam["K"]), np.asarray(cam["T_base_cam"])
    objs = sim.perception.objects()
    assert objs
    hits = 0
    for o in objs:
        p_cam = np.linalg.inv(T) @ np.r_[o["center"], 1.0]
        if p_cam[2] <= 0.1:
            continue
        u, v = (K @ (p_cam[:3] / p_cam[2]))[:2]
        if 0 <= u < 320 and 0 <= v < 240:
            d = depth[int(v), int(u)]
            hits += abs(d - p_cam[2]) < 0.15
    assert hits >= 1
