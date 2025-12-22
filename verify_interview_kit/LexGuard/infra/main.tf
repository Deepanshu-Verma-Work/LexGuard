provider "aws" {
  region = "us-east-1"
}

# -----------------------------------------------------------------------------
# VPC & Networking (Required for Enterprise Security)
# -----------------------------------------------------------------------------
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = { Name = "CaseChat-VPC" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
}

resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index + 10) # Offset to avoid conflict
  availability_zone = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = { Name = "CaseChat-Public-${count.index}" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = { Name = "CaseChat-Private-${count.index}" }
}

data "aws_availability_zones" "available" {}
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "aws_security_group" "lambda_sg" {
  name        = "casechat-lambda-sg"
  description = "Security group for CaseChat Lambdas"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "CaseChat-Lambda-SG" }
}

# -----------------------------------------------------------------------------
# Cognito (Identity & Access Management - RBAC)
# -----------------------------------------------------------------------------
resource "aws_cognito_user_pool" "pool" {
  name = "casechat-users"
  
  password_policy {
    minimum_length    = 12
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }

  auto_verified_attributes = ["email"]
}

resource "aws_cognito_user_pool_client" "client" {
  name = "casechat-app-client"
  user_pool_id = aws_cognito_user_pool.pool.id
  explicit_auth_flows = ["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]
}

resource "aws_cognito_user_group" "admin_group" {
  name         = "SystemAdmin"
  user_pool_id = aws_cognito_user_pool.pool.id
  description  = "Super admins with full billing/infra access"
}

resource "aws_cognito_user_group" "partner_group" {
  name         = "Partner"
  user_pool_id = aws_cognito_user_pool.pool.id
  description  = "Senior legal partners - can delete cases"
}

resource "aws_cognito_user_group" "associate_group" {
  name         = "Associate"
  user_pool_id = aws_cognito_user_pool.pool.id
  description  = "Standard legal associates - read/write only"
}

# -----------------------------------------------------------------------------
# S3 Buckets (Storage)
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# S3 Buckets (Storage)
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "evidence_vault" {
  bucket_prefix = "casechat-evidence-"
  force_destroy = true 
}

resource "aws_s3_bucket_cors_configuration" "evidence_cors" {
  bucket = aws_s3_bucket.evidence_vault.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "POST", "GET"]
    allowed_origins = ["*"] # Lock this down in prod
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

resource "aws_s3_bucket" "frontend" {
  bucket = "casechat-frontend-${random_string.suffix.result}"
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

resource "aws_s3_bucket_public_access_block" "frontend_public" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "frontend_policy" {
  bucket = aws_s3_bucket.frontend.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.frontend.arn}/*"
      }
    ]
  })
  
  depends_on = [aws_s3_bucket_public_access_block.frontend_public]
}

# -----------------------------------------------------------------------------
# DynamoDB (NoSQL Data)
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "metadata" {
  name           = "CaseChat_Metadata"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "case_id"
  range_key      = "doc_id"

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
  name             = "CaseChat_Audit"
  billing_mode     = "PAY_PER_REQUEST"
  hash_key         = "case_id"
  range_key        = "timestamp"
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  attribute {
    name = "case_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }
}

resource "aws_dynamodb_table" "history_db" {
  name           = "CaseChat_History"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "session_id"
  range_key      = "timestamp"

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }
}

# -----------------------------------------------------------------------------
# IAM Roles & Policies
# -----------------------------------------------------------------------------
resource "aws_iam_role" "lambda_role" {
  name = "casechat_lambda_role"

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
  name = "casechat_permissions"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject", "s3:PutObject", "s3:ListBucket",
          "bedrock:InvokeModel",
          "dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"
        ]
        Effect   = "Allow"
        Resource = [
          "arn:aws:s3:::${aws_s3_bucket.evidence_vault.id}",
          "arn:aws:s3:::${aws_s3_bucket.evidence_vault.id}/*",
          "arn:aws:dynamodb:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:table/${aws_dynamodb_table.metadata.name}",
          "arn:aws:dynamodb:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:table/${aws_dynamodb_table.audit.name}",
          "arn:aws:dynamodb:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:table/${aws_dynamodb_table.history_db.name}",
          "arn:aws:bedrock:${data.aws_region.current.name}::foundation-model/*"
        ]
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# Lambda Functions (Placeholders)
# -----------------------------------------------------------------------------
resource "aws_lambda_function" "ingest" {
  filename      = data.archive_file.backend_zip.output_path
  function_name = "casechat-ingest"
  role          = aws_iam_role.lambda_role.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 300
  memory_size   = 512
  source_code_hash = data.archive_file.backend_zip.output_base64sha256

  environment {
    variables = {
      BUCKET_NAME      = aws_s3_bucket.evidence_vault.id
      TABLE_NAME       = aws_dynamodb_table.metadata.name
      PINECONE_API_KEY = "pcsk_4hZwDu_dHfHj65h3qxykUyxHZ1TuYkL6qikDuovXabSWWdjw2SHWVUzqoMryBnQRCtt6g"
      PINECONE_INDEX   = "casechat-index"
    }
  }
}

resource "aws_lambda_function" "query" {
  filename      = data.archive_file.backend_zip.output_path
  function_name = "casechat-query"
  role          = aws_iam_role.lambda_role.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 300
  memory_size   = 512
  source_code_hash = data.archive_file.backend_zip.output_base64sha256

  environment {
    variables = {
      BUCKET_NAME      = aws_s3_bucket.evidence_vault.id
      TABLE_NAME       = aws_dynamodb_table.metadata.name
      PINECONE_API_KEY = "pcsk_4hZwDu_dHfHj65h3qxykUyxHZ1TuYkL6qikDuovXabSWWdjw2SHWVUzqoMryBnQRCtt6g"
      PINECONE_INDEX   = "casechat-index"
    }
  }
}

# -----------------------------------------------------------------------------
# Event Triggers & API Access
# -----------------------------------------------------------------------------
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.evidence_vault.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.ingest.arn
    events              = ["s3:ObjectCreated:*"]
  }

  depends_on = [aws_lambda_permission.allow_s3]
}

resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.evidence_vault.arn
}

resource "aws_apigatewayv2_api" "gateway" {
  name          = "casechat-api"
  protocol_type = "HTTP"
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["POST", "GET", "OPTIONS"]
    allow_headers = ["content-type"]
  }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id = aws_apigatewayv2_api.gateway.id
  name   = "$default"
  auto_deploy = true
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id           = aws_apigatewayv2_api.gateway.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.query.invoke_arn
  integration_method = "POST"
}

resource "aws_apigatewayv2_route" "default_route" {
  api_id    = aws_apigatewayv2_api.gateway.id
  route_key = "POST /chat"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "upload_route" {
  api_id    = aws_apigatewayv2_api.gateway.id
  route_key = "GET /upload-url"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "documents_route" {
  api_id    = aws_apigatewayv2_api.gateway.id
  route_key = "GET /documents"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "audit_route" {
  api_id    = aws_apigatewayv2_api.gateway.id
  route_key = "GET /audit"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_lambda_permission" "allow_api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.query.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.gateway.execution_arn}/*/*"
}

output "api_url" {
  value = aws_apigatewayv2_api.gateway.api_endpoint
}

output "frontend_url" {
  value = "http://${aws_s3_bucket_website_configuration.frontend_hosting.website_endpoint}"
}

output "frontend_bucket" {
    value = aws_s3_bucket.frontend.bucket
}

data "archive_file" "backend_zip" {
  type        = "zip"
  output_path = "${path.module}/backend.zip"
  source_dir  = "${path.module}/../backend/query"
  excludes    = ["*.zip", "__pycache__", "vertex_images"] 
}
