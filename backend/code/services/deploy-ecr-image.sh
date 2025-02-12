#!/bin/bash
set -e

# Check if MAIDA_DEPLOYMENT_ENVIRONMENT is already set, if not set it to "01072024"
if [ -z "${MAIDA_DEPLOYMENT_ENVIRONMENT}" ]; then
  export MAIDA_DEPLOYMENT_ENVIRONMENT=dev
fi
# Check if MAIDA_REPOSITORY_NAME is already set, if not set it to "01072024"
if [ -z "${MAIDA_REPOSITORY_NAME}" ]; then
  export MAIDA_REPOSITORY_NAME=cdk-hnb659fds-container-assets-555043101106-eu-west-3
fi
# Check if MAIDA_IMAGE_TAG is already set, if not set it to "01072024"
if [ -z "${MAIDA_IMAGE_TAG}" ]; then
  export MAIDA_IMAGE_TAG=$(echo "$(date +%s%N)$(uuidgen)" | sha256sum | awk '{print $1}')
fi

# Check if MAIDA_IMAGE_TAG is already set, if not set it to "01072024"
if [ -z "${MAIDA_REGION_TAG}" ]; then
  export MAIDA_REGION_TAG=eu-west-3
fi

if [ -z "${MAIDA_AWS_ACCOUNT}" ]; then
  export MAIDA_AWS_ACCOUNT=555043101106
fi


##EXISTING
aws ecr get-login-password --region $MAIDA_REGION_TAG | docker login --username AWS --password-stdin $MAIDA_AWS_ACCOUNT.dkr.ecr.$MAIDA_REGION_TAG.amazonaws.com &&
docker build -t $MAIDA_REPOSITORY_NAME:$MAIDA_IMAGE_TAG . &&
docker tag $MAIDA_REPOSITORY_NAME:$MAIDA_IMAGE_TAG $MAIDA_AWS_ACCOUNT.dkr.ecr.$MAIDA_REGION_TAG.amazonaws.com/$MAIDA_REPOSITORY_NAME:$MAIDA_IMAGE_TAG &&
docker tag $MAIDA_REPOSITORY_NAME:$MAIDA_IMAGE_TAG locally:$MAIDA_IMAGE_TAG &&
docker push $MAIDA_AWS_ACCOUNT.dkr.ecr.$MAIDA_REGION_TAG.amazonaws.com/$MAIDA_REPOSITORY_NAME:$MAIDA_IMAGE_TAG
##########

