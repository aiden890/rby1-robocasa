"""RPC client for rby1_robocasa.server.rpc (ZMQ REQ/REP, msgpack + msgpack_numpy)."""
import os
import threading


class SimUnavailable(ConnectionError):
    """The sim server did not answer within the timeout."""


class SimCallError(RuntimeError):
    """The server ran the call and it failed (message = the server's reason)."""

    def __init__(self, message, kind="", trace=""):
        super().__init__(message)
        self.kind, self.trace = kind, trace


class _Part:
    """sim.arm.ee_pose("right") -> call("arm.ee_pose", "right")"""

    def __init__(self, client, part):
        self._client, self._part = client, part

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return lambda *a, **k: self._client.call(f"{self._part}.{name}", *a, **k)


class SimClient:
    """Parts: episode, arm, gripper, base, body, perception (rby1_robocasa/server/__init__.py)."""

    PROTOCOL = 2
    PARTS = ("episode", "arm", "gripper", "base", "body", "perception")

    def __init__(self, url=None, timeout_s=120.0):
        self.url = url or os.environ.get("RBY1_ROBOCASA_URL", "tcp://127.0.0.1:5590")
        self.timeout_ms = int(timeout_s * 1000)
        self._lock = threading.Lock()   # REQ sockets are strictly send/recv alternating
        self._sock = None
        for part in self.PARTS:
            setattr(self, part, _Part(self, part))

    def _socket(self):
        import zmq

        if self._sock is None:
            self._sock = zmq.Context.instance().socket(zmq.REQ)
            self._sock.setsockopt(zmq.LINGER, 0)
            self._sock.setsockopt(zmq.RCVTIMEO, self.timeout_ms)
            self._sock.setsockopt(zmq.SNDTIMEO, self.timeout_ms)
            self._sock.connect(self.url)
        return self._sock

    def call(self, method, *args, **kwargs):
        import msgpack
        import msgpack_numpy
        import zmq

        msgpack_numpy.patch()
        with self._lock:
            sock = self._socket()
            try:
                sock.send(msgpack.packb({"method": method, "args": list(args), "kwargs": kwargs}))
                rep = msgpack.unpackb(sock.recv())
            except zmq.Again:
                # a REQ socket is unusable after a missed reply: drop it, the next call reconnects
                sock.close()
                self._sock = None
                raise SimUnavailable(f"sim server {self.url} did not answer {method} within {self.timeout_ms/1000:.0f} s")
        if not rep.get("ok"):
            raise SimCallError(rep.get("error", "failed"), rep.get("type", ""), rep.get("trace", ""))
        return rep.get("result")

    def ping(self):
        r = self.call("ping")
        if r.get("protocol") != self.PROTOCOL:
            raise SimCallError(f"protocol {r.get('protocol')} != client {self.PROTOCOL}")
        return r

    def close(self):
        if self._sock is not None:
            self._sock.close()
            self._sock = None
