#!/bin/bash -xe

# Check if the correct number of arguments are provided
if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <region> <repository>"
  exit 1
fi

REGION=$1
REPOSITORY=$2

aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $REPOSITORY.dkr.ecr.$REGION.amazonaws.com