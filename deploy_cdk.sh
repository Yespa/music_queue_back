#!/bin/bash

echo "Execution starts"

# Conf env despliegue
AWS_DEFAULT_REGION=us-west-2

# Install Layers
pip install google-api-python-client -t lambda_layers/google-api-python-client/python/lib/python3.10/site-packages/

# Inicializo bootstrap 
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
cdk bootstrap aws://${ACCOUNT_ID}/${AWS_DEFAULT_REGION}

# Deploy Stack cdk
cdk deploy -c PROJECT_NAME=music_queue_backend -c DEPLOY_ENV=prod --require-approval never