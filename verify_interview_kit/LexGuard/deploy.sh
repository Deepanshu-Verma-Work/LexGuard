#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=== CaseChat Enterprise Deployment ===${NC}"

# 1. Deploy Infrastructure
echo -e "${BLUE}[1/5] Deploying Serverless Backend...${NC}"
cd infra
terraform init -no-color
terraform apply -auto-approve -no-color

# 2. Extract Outputs
echo -e "${BLUE}[2/5] Extracting Configuration...${NC}"
API_URL=$(terraform output -raw api_url)
FRONTEND_BUCKET=$(terraform output -raw frontend_bucket)
FRONTEND_URL=$(terraform output -raw frontend_url)

echo -e "      API Endpoint: ${GREEN}$API_URL${NC}"
echo -e "      Frontend Bucket: ${GREEN}$FRONTEND_BUCKET${NC}"
echo -e "      Target URL: ${GREEN}$FRONTEND_URL${NC}"

cd ..

# 3. Configure Frontend
echo -e "${BLUE}[3/5] Configuring Frontend...${NC}"
# Write dynamic config
cat > frontend/public/config.js <<EOF
window.config = {
  API_URL: "$API_URL"
};
EOF

# 4. Build Frontend
echo -e "${BLUE}[4/5] Building Optimised Frontend...${NC}"
cd frontend
npm install
npm run build
cd ..

# 5. Deploy to S3
echo -e "${BLUE}[5/5] Publishing to Global S3 CDN...${NC}"
aws s3 sync frontend/dist s3://$FRONTEND_BUCKET --delete

echo -e "\n${GREEN}=== DEPLOYMENT SUCCESSFUL ===${NC}"
echo -e "Your application is ready at:"
echo -e "${BLUE}👉 $FRONTEND_URL${NC}"
echo -e "\nNote: Open this URL in your browser to start the demo."
