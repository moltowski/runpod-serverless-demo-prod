# CONTEXT - RunPod ComfyUI Serverless Template

> **Public documentation for the RunPod serverless video generation system.**

---

## What is this project?

A **serverless video generation system** using:
- **ComfyUI** for workflow management
- **WAN 2.2** model for text-to-video
- **RunPod Serverless** for GPU compute
- **Docker** for containerization

---

## Quick Start

### 1. Setup your environment

\\\ash
# Copy env template
cp .env.example .env

# Edit .env with your credentials
# RUNPOD_API_KEY=your_key_here
# ENDPOINT_ID=your_endpoint_id
\\\

### 2. Deploy to RunPod

\\\ash
# Build and push Docker image
docker build -t your-username/comfyui-serverless:latest .
docker push your-username/comfyui-serverless:latest

# Create endpoint on RunPod Console
# - Image: your-username/comfyui-serverless:latest
# - GPU: A100 80GB
# - Timeout: 900s
\\\

### 3. Test the endpoint

\\\ash
python test_client.py <YOUR_API_KEY> <YOUR_ENDPOINT_ID>
\\\

---

## Project Structure

\\\
.
├── handler_production.py   # Main handler
├── utils.py                # Helper functions
├── Dockerfile              # Container definition
├── wan-2.2.json            # ComfyUI workflow
├── requirements.txt        # Python dependencies
└── .github/
    └── workflows/          # CI/CD automation
\\\

---

## Configuration

### Environment Variables

Create a \.env\ file:

\\\ash
RUNPOD_API_KEY=your_runpod_api_key
ENDPOINT_ID=your_endpoint_id
\\\

### Workflow Parameters

Edit \wan-2.2.json\ to customize:
- Resolution (480-1024px)
- Duration (41-200 frames)
- Steps (8-15)
- Interpolation multiplier (2x/4x)

---

## Documentation

- **README.md** - Full documentation
- **WORKFLOW-CUSTOMIZATION.md** - Parameter guide
- **BREAKTHROUGH.md** - Development timeline

---

## License

MIT License - See LICENSE file

---

## Contact

For issues or questions, open a GitHub issue.
