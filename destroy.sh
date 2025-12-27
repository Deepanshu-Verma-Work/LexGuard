#!/bin/bash
set -e

# Support for non-interactive mode
FORCE=false
if [[ "$1" == "-y" ]]; then
    FORCE=true
fi

if [ "$FORCE" = false ]; then
    echo "⚠️  WARNING: You are about to DESTROY LexGuard."
    read -p "Proceed? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

echo "--------------------------------------"
echo "🧹 Clearing S3 buckets (Required for Terraform Destroy)..."
cd infra_serverless
EVIDENCE_BUCKET=$(terraform output -raw evidence_bucket 2>/dev/null || echo "")
FRONTEND_BUCKET=$(terraform output -raw frontend_bucket 2>/dev/null || echo "")

if [ ! -z "$EVIDENCE_BUCKET" ]; then
    echo "Emptying Evidence Vault: $EVIDENCE_BUCKET"
    aws s3 rm s3://$EVIDENCE_BUCKET --recursive || true
fi

if [ ! -z "$FRONTEND_BUCKET" ]; then
    echo "Emptying Frontend: $FRONTEND_BUCKET"
    aws s3 rm s3://$FRONTEND_BUCKET --recursive || true
fi

echo "--------------------------------------"
echo "🔥 Destroying Resources via Terraform..."
terraform destroy -auto-approve
cd ..
echo "--------------------------------------"
echo "✅ Environment Nuked. No further charges will be incurred."
