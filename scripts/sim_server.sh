#!/bin/sh
# Start / stop the RB-Y1 RoboCasa sim server as a Docker container on this host.
#   scripts/sim_server.sh start [BIND_IP] [PORT]   (default: this host's tailnet IP, 5590)
#   scripts/sim_server.sh stop | logs | status
# Any host with Docker + an NVIDIA GPU works: clone this repo, run scripts/setup_ext.sh --assets,
# build the image (README), then start. Clients connect to tcp://BIND_IP:PORT.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
NAME=${RBY1_ROBOCASA_NAME:-rby1-robocasa-sim}
IMAGE=${RBY1_ROBOCASA_IMAGE:-rby1-robocasa:latest}
case "$1" in
  start)
    IP=${2:-$(tailscale ip -4 2>/dev/null | head -1)}
    IP=${IP:-127.0.0.1}
    PORT=${3:-5590}
    docker run -d --name "$NAME" --restart unless-stopped --gpus all --network host \
      -u "$(id -u):$(id -g)" -e HOME=/tmp -e MUJOCO_GL=egl -e PYOPENGL_PLATFORM=egl \
      -v "$ROOT":/work -v "$ROOT/ext":/ext "$IMAGE" \
      python -m rby1_robocasa.server.rpc --bind "tcp://$IP:$PORT" >/dev/null
    echo "started $NAME on tcp://$IP:$PORT";;
  stop) docker rm -f "$NAME" >/dev/null && echo "stopped $NAME";;
  logs) docker logs --tail 50 "$NAME";;
  status) docker ps --filter "name=^${NAME}$" --format "{{.Names}} {{.Status}}";;
  *) echo "usage: $0 start [IP] [PORT] | stop | logs | status"; exit 1;;
esac
