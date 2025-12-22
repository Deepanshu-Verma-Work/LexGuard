#!/bin/bash
set -e

# Redirect logs
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "=== STARTING DEMO BOX SETUP ==="

# 0. Add Swap (Crucial for t2.micro builds)
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# 1. Install Dependencies
apt-get update
apt-get install -y unzip nginx awscli
# Install Node 20
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs
# Install Terraform
wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | tee /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/hashicorp.list
apt-get update && apt-get install -y terraform

# 2. Setup App Directory
mkdir -p /home/ubuntu/app
cd /home/ubuntu/app
echo "Waiting for Source Code..."
# Simple waiter loop in case IAM propagates slowly
sleep 10 

# 3. Download Source Code (uploaded by deploy script)
# We assume the bucket is the Evidence Vault (or passed via var)
# Since we don't know the exact bucket name easily here without templating, 
# we'll list buckets and find the one that looks like 'casechat-evidence'
BUCKET=$(aws s3api list-buckets --query "Buckets[?contains(Name, 'casechat-evidence')].Name" --output text | awk '{print $1}')
echo "Found Bucket: $BUCKET"

# Wait for source.zip (Race Condition Fix: Upload might lag behind boot)
echo "Waiting for source.zip to appear in S3..."
until aws s3 ls s3://$BUCKET/source.zip; do
  echo "File not found yet. Retrying in 5s..."
  sleep 5
done

aws s3 cp s3://$BUCKET/source.zip source.zip
unzip -o source.zip

# 4. Deploy Backend (Already deployed? We can re-run to be safe or skip)
# For the demo, we assume infrastructure is stable, but let's re-apply to get Outputs
cd infra
terraform init
# terraform apply -auto-approve # Skip to save time/locks? Actually, we need outputs.
# But running terraform inside the box requires state access. 
# SIMPLIFICATION: The deploy script running LOCALLY already has the state.
# Run LOCAL Terraform, get API URL, and write it to a file in S3 that this script reads?
# YES. Much safer than running Terraform twice.

# 5. Build Frontend
cd ../frontend
# Fetch API URL from S3 (uploaded by deploy script)
aws s3 cp s3://$BUCKET/api_url.txt .
API_URL=$(cat api_url.txt)
echo "API URL injected: $API_URL"

# Write Config
mkdir -p public
cat > public/config.js <<EOF
window.config = {
  API_URL: "$API_URL"
};
EOF

# Build
npm install
npm run build

# 6. Serving via Nginx
rm -rf /var/www/html/*
cp -r dist/* /var/www/html/

# Fix Nginx for SPA (React Router support)
cat > /etc/nginx/sites-available/default <<EOF
server {
    listen 80 default_server;
    root /var/www/html;
    index index.html;
    server_name _;
    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
EOF
systemctl restart nginx

echo "=== DEMO BOX READY ==="
