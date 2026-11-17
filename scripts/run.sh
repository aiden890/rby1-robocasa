#!/bin/sh
# Run a command in the sim container. Usage: scripts/run.sh [--gpu] python -m ...
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
GPU=""
if [ "$1" = "--gpu" ]; then GPU="--gpus all"; shift; fi
IMAGE=${RBY1_SIM_IMAGE:-rby1-sim2real:latest}
MUJOCO_GL_VALUE=${MUJOCO_GL:-$([ -n "$GPU" ] && echo egl || echo osmesa)}
exec docker run --rm -i $GPU -u "$(id -u):$(id -g)" -e HOME=/tmp \
  -e MUJOCO_GL="$MUJOCO_GL_VALUE" -e PYOPENGL_PLATFORM="$MUJOCO_GL_VALUE" \
  --shm-size 2g -v "$ROOT":/work -v "$ROOT/ext":/ext -v "${RBY1_OUTPUTS:-$ROOT/outputs}":/work/outputs \
  "$IMAGE" "$@"
