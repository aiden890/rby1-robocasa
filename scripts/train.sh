#!/bin/sh
# Train a LeRobot policy (lerobot 0.3.3 CLI, unchanged) on a real-format dataset.
# Usage: scripts/train.sh DATASET_DIR RUN_NAME [extra lerobot args...]
#   e.g. scripts/train.sh outputs/datasets/fetch_cola fetch_cola_act --steps=50000 --batch_size=8
set -e
DATA=$1; NAME=$2; shift 2
exec "$(dirname "$0")/run.sh" --gpu python -m lerobot.scripts.train \
  --dataset.repo_id="rby1_sim/$(basename "$DATA")" --dataset.root="$DATA" --dataset.video_backend=pyav \
  --policy.type=act --policy.device=cuda --policy.push_to_hub=false \
  --output_dir="outputs/train/$NAME" --job_name="$NAME" --wandb.enable=false "$@"
