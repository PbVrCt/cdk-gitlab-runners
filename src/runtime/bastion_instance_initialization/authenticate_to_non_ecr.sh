#!/bin/bash -xe

# Check if the correct number of arguments are provided
if [ "$#" -ne 3 ]; then
  echo "Usage: $0 <repository> <username> <password>"
  exit 1
fi

REPOSITORY=$1
USERNAME=$2
PASSWORD=$3

docker login $REPOSITORY -u $USERNAME -p $PASSWORD