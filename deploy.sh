#!/bin/bash
set -e

echo "🚀 Deploying LexGuard (Amplify & Serverless)..."

# 1. AWS Infrastructure
echo "📡 Provisioning Infrastructure..."
cd infra_serverless
terraform init
terraform apply -auto-approve
API_URL=$(terraform output -raw api_endpoint)
cd ..

# 2. Trigger Amplify Build
# Since we use AWS Amplify with Git integration, we just need to push to main.
# The API_URL is already mapped as an environment variable in Terraform.
echo "⚙️  Triggering Amplify CI/CD via Git..."
git add .
git commit -m "chore: deploy LexGuard updates" || echo "No changes to commit"
git push origin main

echo "✅ Deployment Initiated!"
echo "🌍 Monitor Build At: https://us-east-1.console.aws.amazon.com/amplify/home"
