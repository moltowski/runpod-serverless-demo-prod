#!/bin/bash
# Build and Push Script for RunPod Serverless Demo

echo "🚀 Building RunPod Serverless ComfyUI-WAN Demo..."
echo "================================================="

# Configuration
IMAGE_NAME="moltowski/comfyui-serverless-demo"
TAG="v1"
FULL_IMAGE="${IMAGE_NAME}:${TAG}"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

# Check if logged in to Docker Hub
echo "🔐 Checking Docker Hub authentication..."
if ! docker info &> /dev/null; then
    echo "❌ Docker daemon not running or not accessible."
    exit 1
fi

# Build the image
echo "🏗️  Building image: ${FULL_IMAGE}"
docker build -t "${FULL_IMAGE}" . --no-cache

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
else
    echo "❌ Build failed!"
    exit 1
fi

# Check image size
echo "📊 Image details:"
docker images "${IMAGE_NAME}" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

# Push to Docker Hub
echo "📤 Pushing to Docker Hub..."
docker push "${FULL_IMAGE}"

if [ $? -eq 0 ]; then
    echo "✅ Push successful!"
    echo ""
    echo "🎯 Image ready for RunPod deployment:"
    echo "   Image: ${FULL_IMAGE}"
    echo "   Use this in RunPod Console when creating serverless endpoint"
    echo ""
else
    echo "❌ Push failed! Check Docker Hub credentials."
    exit 1
fi

# Optional: Tag as latest
read -p "🏷️  Tag as 'latest'? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker tag "${FULL_IMAGE}" "${IMAGE_NAME}:latest"
    docker push "${IMAGE_NAME}:latest"
    echo "✅ Latest tag pushed!"
fi

echo ""
echo "🎉 All done! Your serverless template is ready."
echo "   Next: Follow README.md to setup network storage and deploy endpoint"