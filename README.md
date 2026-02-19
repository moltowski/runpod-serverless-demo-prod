# RunPod Serverless ComfyUI-WAN Demo v2

## Overview
Serverless template pour ComfyUI + WAN 2.2 two-stage (high/low noise) avec network storage. Optimisé pour démo NSFW/action LoRAs. Cold start 15-25s, metrics auto (temps, cost). Économies 57% vs pod 24/7 ($154/mois pour 100 jobs).

## Features
- Workflow: test-workflow-api.json (WAN T2V/I2V, prompt/LoRA/seed injection).
- Models: /workspace/models/checkpoints/wan_2.2.safetensors, /workspace/models/loras/action-lora/.
- Handler: Python avec ComfyUI API, error handling, metrics.
- Test Client: Benchmarks pour cold start, processing, cost.

## Quick Start
1. Build Image: `./build_and_push.sh` (push v2 sur Docker Hub).
2. RunPod Serverless Endpoint:
   - Image: `moltowski/comfyui-serverless-demo:v2`
   - GPU: RTX 4090 PRO (1x)
   - Workers: Min 0, Max 2, FlashBoot ON
   - Mount: Network Volume 1TB à `/workspace` (models/workflows).
   - Timeouts: Execution 600s.
3. Test:
   ```
   python test_client.py --endpoint ID --api-key KEY --prompt "Femme en action, NSFW"
   ```
   Expected: Video output, cold ~20s, cost ~$0.08.

## RunPod Hub Status
[![RunPod Hub](https://img.shields.io/badge/RunPod-Hub-blue?logo=runpod)](https://www.runpod.io/console/templates)

Template publié sur RunPod Hub pour démo serverless WAN 2.2. Compatible pods + serverless.

## Architecture
- Network Storage: /workspace (models, workflows, temp outputs).
- ComfyUI: Internal sur 8188 (handler calls /prompt, /history).
- LoRA Dynamic: Input param pour loader (ex: fem_mast_v1.safetensors).

## Cost Analysis
- 100 jobs/jour: $4.03/jour + $100 storage/mois = $221/mois.
- Vs Pod 24/7 RTX 4090: $360/mois (économies $139, 39%).

## Troubleshooting
- Models Missing: Vérif /workspace/models/ via pod connect.
- Timeout: Augmente execution_timeout pour two-stage complex.
- LoRA Not Loaded: Check paths in test-workflow-api.json.

## Next Steps
- Intégrer Ostris pour LoRA training serverless.
- Multi-GPU pour batch jobs.
- Monitoring avec RunPod metrics.

Fork/Contrib: Bienvenue ! Contact: mollet.geoffrey@gmail.com