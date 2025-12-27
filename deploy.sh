#!/bin/bash
set -e # Exit on error

echo "🚀 Starting Deployment of LexGuard..."

# 1. Deploy Infrastructure
echo "--------------------------------------"
echo "📡 Applying Terraform Infrastructure..."
cd infra_serverless
terraform init
terraform apply -auto-approve
# Capture outputs
FRONTEND_BUCKET=$(terraform output -raw frontend_bucket)
WEBSITE_URL=$(terraform output -raw website_endpoint)
API_ENDPOINT=$(terraform output -raw api_endpoint)
cd ..

# 2. Update Frontend Config
echo "--------------------------------------"
echo "⚙️  Updating Frontend Configuration..."
echo "window.config = { API_URL: \"$API_ENDPOINT\" };" > frontend/public/config.js

# 3. Build Frontend
echo "--------------------------------------"
echo "🎨 Building Frontend..."
cd frontend
npm install
npm run build
cd ..

# 4. Upload to S3
echo "--------------------------------------"
echo "☁️  Syncing to S3 Bucket: $FRONTEND_BUCKET"
aws s3 sync frontend/dist s3://$FRONTEND_BUCKET --delete

echo "--------------------------------------"
echo "✅ Deployment Complete!"
echo "🌍 Live URL: http://$WEBSITE_URL"
echo "--------------------------------------"
