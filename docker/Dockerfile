# RB-Y1 RoboCasa runtime (sim server, tests): robosuite + RoboCasa dependencies only.
# Sources (pinned in ext.lock) and ~10GB kitchen assets live in ./ext on the host
# and are mounted at /ext; see scripts/setup_ext.sh.
FROM python:3.11-slim-trixie
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/work:/ext/robosuite:/ext/robocasa \
    MUJOCO_GL=egl PYOPENGL_PLATFORM=egl \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics
RUN apt-get update && apt-get install -y --no-install-recommends \
      git ca-certificates build-essential linux-libc-dev libgl1 libegl1 libosmesa6 libglib2.0-0 libgomp1 ffmpeg \
    && rm -rf /var/lib/apt/lists/*
# NVIDIA EGL vendor entry so MUJOCO_GL=egl uses the GPU when run with --gpus
RUN mkdir -p /usr/share/glvnd/egl_vendor.d && printf '{"file_format_version":"1.0.0","ICD":{"library_path":"libEGL_nvidia.so.0"}}\n' \
      > /usr/share/glvnd/egl_vendor.d/10_nvidia.json
COPY docker/requirements.txt /tmp/requirements.txt
RUN pip install --extra-index-url https://download.pytorch.org/whl/cu124 -r /tmp/requirements.txt
WORKDIR /work
