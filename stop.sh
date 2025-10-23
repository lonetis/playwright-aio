#!/bin/bash

CONTAINER_NAME="playwright-aio"

echo "Stopping Playwright AIO Runner..."

# Stop the container
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    docker stop $CONTAINER_NAME
    echo "Container stopped."
else
    echo "Container is not running."
fi

# Remove the container
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    docker rm $CONTAINER_NAME
    echo "Container removed."
else
    echo "Container does not exist."
fi

echo "Playwright AIO Runner has been stopped and removed."
