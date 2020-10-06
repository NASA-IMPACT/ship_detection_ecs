#!/bin/bash
docker build . -f Dockerfile -t ship_detection:$VERSION \
 --build-arg API_KEY=$API_KEY

if [[ $PUSH = '1' ]]
then
  export ECR_URL="853558080719.dkr.ecr.us-east-1.amazonaws.com"

  aws ecr get-login-password --region us-east-1 --profile $PROFILE | \
    docker login --password-stdin --username AWS $ECR_URL

  docker tag ship_detection:$VERSION $ECR_URL/ship_detection:latest

  docker push $ECR_URL/ship_detection:latest
fi
