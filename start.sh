#!/bin/bash

CONTAINER_NAME="playwright-aio"
IMAGE_NAME="playwright-aio:local"

echo "Building and starting Playwright AIO Runner..."

# Stop and remove existing container if running
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Stopping and removing existing container..."
    docker stop $CONTAINER_NAME 2>/dev/null
    docker rm $CONTAINER_NAME 2>/dev/null
fi

# Build the image
echo "Building Docker image..."
docker build -t $IMAGE_NAME .

if [ $? -ne 0 ]; then
    echo "Docker build failed!"
    exit 1
fi

# Run the container
echo "Starting container..."
docker run -d \
    --name $CONTAINER_NAME \
    -p 8080:8080 \
    -p 6080:6080 \
    --shm-size=2gb \
    $IMAGE_NAME

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "Playwright AIO Runner is now running!"
    echo "=========================================="
    echo ""
    echo "Web Interface: http://localhost:8080"
    echo ""
    echo "To stop the container, run: ./stop.sh"
    echo ""
else
    echo "Failed to start container!"
    exit 1
fi
