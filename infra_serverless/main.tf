terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4.2"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# 1. DATA SOURCES
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

# 2. DYNAMODB (Keep existing logic)
resource "aws_dynamodb_table" "metadata" {
  name           = "CaseChat_Metadata"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "case_id"
  range_key      = "doc_id"
  table_class    = "STANDARD"

  attribute {
    name = "case_id"
    type = "S"
  }
  attribute {
    name = "doc_id"
    type = "S"
  }
}

resource "aws_dynamodb_table" "audit" {
  name           = "CaseChat_Audit"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "log_id"
  range_key      = "timestamp"

  attribute {
    name = "log_id"
    type = "S"
  }
  attribute {
    name = "timestamp"
    type = "S"
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"
}

resource "aws_dynamodb_table" "history_db" {
  name         = "CaseChat_History"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "session_id"
  range_key    = "timestamp"

  attribute {
    name = "session_id"
    type = "S"
  }
  attribute {
    name = "timestamp"
    type = "S"
  }
}

# 3. S3 BUCKETS (Backend + Frontend)

# Evidence Vault
resource "aws_s3_bucket" "evidence_vault" {
  bucket        = "casechat-evidence-${random_string.suffix.result}"
  force_destroy = true
}

resource "aws_s3_bucket_cors_configuration" "evidence_cors" {
  bucket = aws_s3_bucket.evidence_vault.id
  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "POST", "GET"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# Frontend Hosting
resource "aws_s3_bucket" "frontend" {
  bucket        = "casechat-frontend-${random_string.suffix.result}"
  force_destroy = true
}

resource "aws_s3_bucket_website_configuration" "frontend_hosting" {
  bucket = aws_s3_bucket.frontend.id

  index_document {
    suffix = "index.html"
  }
  error_document {
    key = "index.html"
  }
}

# Public Access Block (Unblock for Website)
resource "aws_s3_bucket_public_access_block" "frontend_public" {
  bucket = aws_s3_bucket.frontend.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# 4. AWS AMPLIFY (Professional Hosting)
resource "aws_amplify_app" "lexguard" {
  name       = "lexguard-app"
  repository = "https://github.com/Deepanshu-Verma-Work/LexGuard"
  access_token = var.github_token

  # Build settings
  build_spec = <<-EOT
    version: 1
    applications:
      - frontend:
          phases:
            preBuild:
              commands:
                - cd frontend
                - npm install
            build:
              commands:
                - echo "window.config = { API_URL: \"$API_URL\" };" > public/config.js
                - npm run build
          artifacts:
            baseDirectory: frontend/dist
            files:
              - '**/*'
          cache:
            paths:
              - node_modules/**/*
  EOT

  environment_variables = {
    API_URL = aws_apigatewayv2_api.gateway.api_endpoint
  }
}

resource "aws_amplify_branch" "main" {
  app_id      = aws_amplify_app.lexguard.id
  branch_name = "main"
}

resource "aws_s3_bucket_policy" "frontend_policy" {
  bucket = aws_s3_bucket.frontend.id
  depends_on = [aws_s3_bucket_public_access_block.frontend_public]
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.frontend.arn}/*"
      },
    ]
  })
}

# 4. LAMBDA (No VPC)

# Zip Code
data "archive_file" "backend_zip" {
  type        = "zip"
  source_dir  = "../backend"  # Zips the whole backend folder
  output_path = "${path.module}/backend_deploy.zip"
  excludes    = ["**/__pycache__", "**/*.pyc", "venv", ".env"]
}

resource "aws_iam_role" "lambda_role" {
  name = "casechat_serverless_role" # Rename to avoid collision with old role

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_permissions" {
  name = "casechat_serverless_permissions"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject", "s3:PutObject", "s3:ListBucket", "s3:GeneratePresignedUrl",
          "bedrock:InvokeModel",
          "dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"
        ]
        Effect   = "Allow"
        Resource = "*" # Simplified for demo speed, or scope if strict
      }
    ]
  })
}

# Upload Zip to S3
resource "aws_s3_object" "lambda_code" {
  bucket = aws_s3_bucket.evidence_vault.id
  key    = "backend_deploy.zip"
  source = data.archive_file.backend_zip.output_path
  etag   = data.archive_file.backend_zip.output_md5
}

resource "aws_lambda_function" "ingest" {
  s3_bucket        = aws_s3_bucket.evidence_vault.id
  s3_key           = aws_s3_object.lambda_code.key
  function_name    = "casechat-ingest-sls"
  role             = aws_iam_role.lambda_role.arn
  handler          = "ingest.index.handler"
  
  runtime          = "python3.12"
  source_code_hash = data.archive_file.backend_zip.output_base64sha256
  timeout          = 300
  memory_size      = 512

  environment {
    variables = {
      TABLE_NAME       = aws_dynamodb_table.metadata.name
      AUDIT_TABLE_NAME = aws_dynamodb_table.audit.name
      HISTORY_TABLE    = aws_dynamodb_table.history_db.name
      BUCKET_NAME      = aws_s3_bucket.evidence_vault.bucket
      PINECONE_API_KEY = var.pinecone_api_key
      PINECONE_INDEX   = "casechat-index"
    }
  }
}

resource "aws_lambda_function" "query" {
  s3_bucket        = aws_s3_bucket.evidence_vault.id
  s3_key           = aws_s3_object.lambda_code.key
  function_name    = "casechat-query-sls"
  role             = aws_iam_role.lambda_role.arn
  handler          = "query.index.handler"
  
  runtime          = "python3.12"
  source_code_hash = data.archive_file.backend_zip.output_base64sha256
  timeout          = 300
  memory_size      = 512

  environment {
    variables = {
      TABLE_NAME       = aws_dynamodb_table.metadata.name
      AUDIT_TABLE_NAME = aws_dynamodb_table.audit.name
      HISTORY_TABLE    = aws_dynamodb_table.history_db.name
      BUCKET_NAME      = aws_s3_bucket.evidence_vault.bucket
      PINECONE_API_KEY = var.pinecone_api_key
      PINECONE_INDEX   = "casechat-index"
    }
  }
}

# Trigger Ingest on S3 Upload
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.evidence_vault.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.ingest.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".pdf"
  }
   lambda_function {
    lambda_function_arn = aws_lambda_function.ingest.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".txt"
  }
}

resource "aws_lambda_permission" "allow_bucket" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest.arn
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.evidence_vault.arn
}


# 5. API GATEWAY (HTTP API)
resource "aws_apigatewayv2_api" "gateway" {
  name          = "casechat_sls_api"
  protocol_type = "HTTP"
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["POST", "GET", "OPTIONS", "PUT"]
    allow_headers = ["content-type", "authorization"]
    max_age       = 300
  }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.gateway.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_apigatewayv2_integration" "lambda_handler" {
  api_id           = aws_apigatewayv2_api.gateway.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.query.invoke_arn # Point to Query Lambda
}

resource "aws_apigatewayv2_route" "any_route" {
  api_id    = aws_apigatewayv2_api.gateway.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_handler.id}"
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.query.function_name # Query Lambda
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.gateway.execution_arn}/*/*"
}

# 6. OUTPUTS
output "api_endpoint" {
  value = aws_apigatewayv2_api.gateway.api_endpoint
}

output "website_endpoint" {
  value = aws_s3_bucket_website_configuration.frontend_hosting.website_endpoint
}

output "evidence_bucket" {
  value = aws_s3_bucket.evidence_vault.bucket
}

output "frontend_bucket" {
    value = aws_s3_bucket.frontend.bucket
}

output "amplify_url" {
  value = "https://main.${aws_amplify_app.lexguard.default_domain}"
}
