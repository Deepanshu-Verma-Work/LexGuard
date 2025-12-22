#!/bin/bash
set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${RED}=== TEARING DOWN CASECHAT INFRASTRUCTURE ===${NC}"
echo -e "This will delete all active services to stop billing."

cd infra
terraform init -no-color
terraform destroy -auto-approve -no-color

echo -e "\n${GREEN}=== CLEANUP COMPLETE ===${NC}"
echo -e "All EC2 instances, S3 buckets, and Lambdas have been deleted."
echo -e "You are now cost-free until you run ./deploy_ami.sh again."
