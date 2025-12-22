#!/bin/bash
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== CaseChat EC2 'One-Box' Deployment ===${NC}"

# 1. Deploy Infra (creates EC2 + Buckets)
echo -e "${BLUE}[1/5] Provisioning Cloud Infrastructure...${NC}"
cd infra
terraform init -no-color
terraform apply -auto-approve -no-color

# Extract Info
API_URL=$(terraform output -raw api_url)
DEMO_IP=$(terraform output -raw demo_ip)
# Find bucket name dynamically (terraform output would be better, but we grep for now or add output)
# Let's add output 'evidence_bucket' to main.tf if not there? 
# We used 'frontend_bucket' and 'api_url'. Let's find bucket via AWS CLI to be safe.
BUCKET=$(aws s3api list-buckets --query "Buckets[?contains(Name, 'casechat-evidence')].Name" --output text | awk '{print $1}')

echo -e "      Instance IP: ${GREEN}$DEMO_IP${NC}"
echo -e "      Asset Bucket: ${GREEN}$BUCKET${NC}"
echo -e "      API URL: ${GREEN}$API_URL${NC}"

cd ..

# 2. Package Source Code
echo -e "${BLUE}[2/5] Packaging Source Code...${NC}"
zip -r -q source.zip . -x "**/node_modules/*" -x "**/.git/*" -x "**/.terraform/*" -x "*.zip"

# 3. Upload Artifacts to S3 (for EC2 to grab)
echo -e "${BLUE}[3/5] Uploading Deployment Artifacts...${NC}"
echo "$API_URL" > api_url.txt
aws s3 cp source.zip s3://$BUCKET/source.zip
aws s3 cp api_url.txt s3://$BUCKET/api_url.txt
rm source.zip api_url.txt

# 4. Wait for Instance (Optional Reboot if updating)
echo -e "${BLUE}[4/5] Waiting for Instance Setup...${NC}"
# If user data already ran, we might need to SSH and force update.
# For a fresh interview, destroying and creating is cleanest, but slow.
# We will use SSH to force the update script if it exists, roughly simulating 'deploy'.
# Save key permission
chmod 400 infra/casechat_demo_key.pem

echo "Attempting to connect..."
# Loop until SSH is up
for i in {1..30}; do
    ssh -o "StrictHostKeyChecking=no" -i infra/casechat_demo_key.pem ubuntu@$DEMO_IP "echo 'Connected'" && break
    echo "Waiting for SSH..."
    sleep 5
done

# Force the deploy script content (same as User Data) to run again to pick up new zip
# Simplest way: just reboot logs? No, run commands.
# actually, let's just trust the User Data for the *first* launch. 
# The user wants "Deploy -> Link".
# If the instance was just created, it's running User Data.

echo -e "\n${GREEN}=== DEPLOYMENT STARTED ON INSTANCE ===${NC}"
echo -e "The instance is now installing dependencies and building the app."
echo -e "This takes about 3-5 minutes."
echo -e "\nAccess your Demo Box here:"
echo -e "${BLUE}👉 http://$DEMO_IP${NC}"
echo -e "\n(Refresh the page in a few minutes once Nginx starts)"
