#!/bin/bash
set -e

echo "⚠️  WARNING: You are about to DESTROY the entire LexGuard environment."
echo "This will delete all data in DynamoDB, S3, and remove all Lambda functions."
read -p "Are you sure you want to proceed? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo "--------------------------------------"
echo "🧹 Cleaning up S3 Buckets (Required for Terraform Destroy)..."

cd infra_serverless
FRONTEND_BUCKET=$(terraform output -raw frontend_bucket 2>/dev/null || echo "")
EVIDENCE_BUCKET=$(terraform output -raw evidence_bucket 2>/dev/null || echo "")

if [ ! -z "$FRONTEND_BUCKET" ]; then
    echo "Emptying Frontend Bucket: $FRONTEND_BUCKET"
    aws s3 rm s3://$FRONTEND_BUCKET --recursive
fi

if [ ! -z "$EVIDENCE_BUCKET" ]; then
    echo "Emptying Evidence Bucket: $EVIDENCE_BUCKET"
    aws s3 rm s3://$EVIDENCE_BUCKET --recursive
fi

echo "--------------------------------------"
echo "🔥 Destroying Infrastructure via Terraform..."
terraform destroy -auto-approve

echo "--------------------------------------"
echo "✅ Destruction Complete. No further charges will be incurred."
