#!/bin/bash
echo $AWS_SECRET_ACCESS_KEY
docker build . -f Dockerfile -t ship_detection:$VERSION \
 --build-arg AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
 --build-arg AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID

if [[ $PUSH = '1' ]]
then
  export ECR_URL="853558080719.dkr.ecr.us-east-1.amazonaws.com"
  aws ecr get-login-password --region us-east-1 --profile covid-response | docker login --username AWS --password-stdin $ECR_URL

  docker tag ship_detection:$VERSION $ECR_URL/ship_detection:latest
  docker push $ECR_URL/ship_detection:latest
fi
