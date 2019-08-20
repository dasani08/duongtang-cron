#!/bin/sh

IMAGE=registry.gitlab.com/clgt/duongtang-cron
VERSION=$1

echo "version: $VERSION"
echo $VERSION > VERSION

docker build -t $IMAGE:latest .

docker tag $IMAGE:latest $IMAGE:$VERSION

docker push $IMAGE:latest
docker push $IMAGE:$VERSION
