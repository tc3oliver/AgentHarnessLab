#!/usr/bin/env bash
# Serve one model on ONE idle MI325X for evaluation. Publishes on localhost and Docker's bridge gateway only.
# Checks that the GPU holds less than 1 GB; also look for other users and jobs first. Stop: docker rm -f agentlab-vllm (or $NAME)
# Device isolation: only one render node is passed in. No privileged mode, capabilities or seccomp changes.
# PORT (default 8100) is the host port. BRIDGE=0 publishes on localhost only, for use behind
# `python -m agent_harness_lab.monitoring.proxy`, which then listens on the bridge gateway instead.
# ADAPTER_DIR (optional) is one fixed adapter, mounted at /adapter for `--lora-modules name=/adapter`.
# LORA_DIR (optional, training servers only) is mounted read-only at /adapters and turns on runtime LoRA loading
# (`/v1/load_lora_adapter`, `/v1/unload_lora_adapter`) for adapters a trainer writes there. Both can be set. vLLM
# also needs `--enable-lora --max-lora-rank <r>` (and `--max-loras`), passed as arguments. Anyone with the API key
# can then load or unload adapters, and evaluation trials hold that key, so use LORA_DIR only with BRIDGE=0 and
# never on a server that evaluation sandboxes reach directly. The monitoring proxy refuses these paths.
set -euo pipefail
: "${VLLM_API_KEY:?}" "${MODEL_DIR:?}" "${RENDER:?e.g. renderD184}"
IMAGE=vllm/vllm-openai-rocm@sha256:4fcd39b758b660c4e9c345c021e2ea8f0ccdb31e3c32507d676cc3005ae83fba
bus=$(basename "$(readlink -f "/sys/class/drm/$RENDER/device")")
busy=$(cat "/sys/bus/pci/devices/$bus/mem_info_vram_used")
echo "GPU $bus VRAM used: $busy bytes"
[ "$busy" -lt 1000000000 ] || { echo "GPU $bus is not idle" >&2; exit 1; }
export VLLM_API_KEY
docker run -d --name "${NAME:-agentlab-vllm}" --device /dev/kfd --device "/dev/dri/$RENDER" \
  --group-add "$(getent group video | cut -d: -f3)" --group-add "$(getent group render | cut -d: -f3)" \
  --security-opt no-new-privileges --shm-size 16g --memory 200g \
  -p "127.0.0.1:${PORT:-8100}:8000" $([ "${BRIDGE:-1}" = 1 ] && echo "-p 172.17.0.1:${PORT:-8100}:8000") \
  -e VLLM_API_KEY -e HF_HUB_OFFLINE=1 -e OMP_NUM_THREADS=8 \
  -v "$MODEL_DIR:/model:ro" ${ADAPTER_DIR:+-v "$ADAPTER_DIR:/adapter:ro"} \
  ${LORA_DIR:+-v "$LORA_DIR:/adapters:ro" -e VLLM_ALLOW_RUNTIME_LORA_UPDATING=True} \
  "$IMAGE" /model --served-model-name Qwen/Qwen3.8-27B --host 0.0.0.0 --port 8000 \
  --language-model-only --max-model-len 131072 --gpu-memory-utilization 0.85 \
  --enable-prefix-caching --mamba-cache-mode align \
  --enable-auto-tool-choice --tool-call-parser qwen3_xml --reasoning-parser qwen3 \
  --default-chat-template-kwargs '{"enable_thinking": false}' \
  --override-generation-config '{"temperature": 0.8, "top_p": 1.0}' \
  --enable-log-requests "$@"  # logs sampling parameters, not prompts
