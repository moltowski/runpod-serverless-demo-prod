# RunPod Serverless Demo - Production Ready (Updated 2026-02-19)

## Current Status
✅ **Network Storage Setup Complete** (by Jeff)
- 1TB volume created and mounted
- Models installed: WAN 2.2, Z-Image-Turbo, LoRAs (action-lora/fem_mast_v1.safetensors)
- Workflows uploaded: test-workflow-api.json (WAN 2.2 two-stage, high/low noise)
- Pod tested and confirmed working

⚠️ **Previous Deployment Issues Resolved** (by Jeff)
- Template updates made due to initial failures
- Ready for serverless integration

🔄 **Template Updates Needed**
- Handler.py: Load specific 'test-workflow-api.json' from /workspace/workflows/
- Support two-stage WAN workflow (prompt injection into text node)
- Metrics and error handling already robust

## Architecture
- **Mount Point:** /workspace (network storage)
- **ComfyUI Path:** /ComfyUI (container internal)
- **Workflows:** /workspace/workflows/test-workflow-api.json
- **Models:** /workspace/models/checkpoints/, /workspace/models/loras/
- **Outputs:** /workspace/temp/ (temp), /ComfyUI/output/ (final)
- **Handler:** Python script using ComfyUI API (/prompt, /history)
- **Serverless Config:** RTX 4090 PRO, min=0, max=2, FlashBoot=ON, execution_timeout=300s

## Key Files
- **Dockerfile:** Optimized (no embedded models, ~2GB image)
- **handler.py:** Network-aware, metrics-enabled, ComfyUI starter
- **requirements.txt:** ComfyUI + runpod + requests
- **test_client.py:** Benchmark scripts with prompts, timing, costs
- **README.md:** Full instructions
- **build_and_push.sh:** Docker build/push script

## Performance Expectations (Updated)
- **Cold Start:** 10-20s (FlashBoot + pre-warmed ComfyUI)
- **Processing (WAN 2.2 two-stage):** 180-300s (depending on complexity)
- **Success Rate:** 95%+ (with models present)
- **Cost per Job:** ~$0.05-0.10 (RTX 4090 PRO, 5min exec)
- **Monthly (100 jobs):** ~$154 + $100 storage = $254 vs $360 pod (29% savings)

## Demo Flow
1. **Jeff:** Ensure workflow file named 'test-workflow-api.json' in /workspace/workflows/
2. **Moltbot:** Final handler update for specific workflow
3. **Build & Push:** Updated image to Docker Hub
4. **Jeff:** Create serverless endpoint, mount network volume
5. **Test:** Run test_client.py with sample prompts
6. **Metrics:** Collect cold start, processing time, cost
7. **Demo:** Share results/screenshots with devs

## Next Steps
1. Update handler.py to default load 'test-workflow-api.json'
2. Build and push new image: moltowski/comfyui-serverless-demo:v2
3. Jeff deploys endpoint with mount
4. Run tests, gather metrics
5. Update demo presentation with real numbers

## Risks & Mitigations
- **Model Paths Mismatch:** Verify exact paths in workflow JSON
- **Two-Stage Complexity:** Test locally if possible; fallback to single-stage
- **Timeout:** Set execution_timeout=600s for complex videos
- **VRAM:** WAN 2.2 needs 16GB+; confirm GPU config

## Decisions Log
- 2026-02-19: Switched to specific user workflow (two-stage WAN)
- 2026-02-19: Network storage confirmed ready
- Prior: Initial template created, deployment fixed by user updates

Last Updated: 2026-02-19 07:50 UTC
