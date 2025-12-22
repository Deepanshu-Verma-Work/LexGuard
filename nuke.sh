#!/bin/bash
echo "=== NUKING CASECHAT RESOURCES ==="

# 1. DynamoDB
echo "Deleting Tables..."
aws dynamodb delete-table --table-name CaseChat_Metadata 2>/dev/null || echo "Metadata table gone"
aws dynamodb delete-table --table-name CaseChat_Audit 2>/dev/null || echo "Audit table gone"
aws dynamodb delete-table --table-name CaseChat_History 2>/dev/null || echo "History table gone"

# 2. Lambda
echo "Deleting Lambdas..."
aws lambda delete-function --function-name casechat-ingest 2>/dev/null || echo "Ingest lambda gone"
aws lambda delete-function --function-name casechat-query 2>/dev/null || echo "Query lambda gone"

# 3. IAM
echo "Deleting Roles..."
# Detach policies first
POLICY_ARN=$(aws iam list-policies --query "Policies[?PolicyName=='casechat-lambda-policy'].Arn" --output text)
if [ ! -z "$POLICY_ARN" ]; then
    aws iam detach-role-policy --role-name casechat_lambda_role --policy-arn "$POLICY_ARN" 2>/dev/null
    aws iam delete-policy --policy-arn "$POLICY_ARN" 2>/dev/null
fi
aws iam delete-role --role-name casechat_lambda_role 2>/dev/null || echo "Lambda Role gone"

echo "Deleting EC2 Role..."
aws iam remove-role-from-instance-profile --instance-profile-name casechat_demo_profile --role-name casechat_demo_role 2>/dev/null
aws iam delete-instance-profile --instance-profile-name casechat_demo_profile 2>/dev/null
aws iam detach-role-policy --role-name casechat_demo_role --policy-arn arn:aws:iam::aws:policy/AdministratorAccess 2>/dev/null
aws iam delete-role --role-name casechat_demo_role 2>/dev/null || echo "EC2 Role gone"

echo "Deleting Key Pair..."
aws ec2 delete-key-pair --key-name casechat_demo_key 2>/dev/null || echo "Key Pair gone"


# 4. S3
echo "Deleting Buckets..."
BUCKETS=$(aws s3api list-buckets --query "Buckets[?contains(Name, 'casechat-')].Name" --output text)
for b in $BUCKETS; do
    echo "Deleting $b..."
    aws s3 rb s3://$b --force 2>/dev/null
done

echo "=== NUKE COMPLETE ==="
