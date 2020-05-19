#!/bin/bash

docker build . -f Dockerfile -t nasa-impact/ship_detection:$VERSION \
 --build-arg AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
 --build-arg AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID

if [ $PUSH = '1' ]
then
  aws ecr get-login --region us-east-1 --no-include-email | source /dev/stdin

  docker tag nasa-impact/ship_detection:$VERSION 853558080719.dkr.ecr.us-east-1.amazonaws.com/ship_detection:latest
  docker push 853558080719.dkr.ecr.us-east-1.amazonaws.com/ship_detection:latest
fi
