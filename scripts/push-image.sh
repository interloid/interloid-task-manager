#!/bin/bash

set -e

DOCKER_USERNAME="amaldas12345"
IMAGE_NAME="interloid-task-manager"
TAG="v1.2.6"

FULL_IMAGE_NAME="${DOCKER_USERNAME}/${IMAGE_NAME}:${TAG}"
LATEST_IMAGE_NAME="${DOCKER_USERNAME}/${IMAGE_NAME}:latest"

echo "Building Docker image..."

docker build \
    -t "${FULL_IMAGE_NAME}" \
    -t "${LATEST_IMAGE_NAME}" \
    .

echo "Pushing versioned image..."

docker push "${FULL_IMAGE_NAME}"

echo "Pushing latest image..."

docker push "${LATEST_IMAGE_NAME}"

echo "Docker images pushed successfully."
