terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# S3 bucket para datos
resource "aws_s3_bucket" "data_bucket" {
  bucket = var.s3_bucket_name
  acl    = "private"

  versioning {
    enabled = true
  }

  tags = {
    Name        = var.s3_bucket_name
    Environment = var.environment
  }
}

# DynamoDB table para metadatos
resource "aws_dynamodb_table" "data_table" {
  name         = var.dynamodb_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  tags = {
    Name        = var.dynamodb_table_name
    Environment = var.environment
  }
}

# Tabla DynamoDB para raw prices
resource "aws_dynamodb_table" "raw_prices" {
  name         = var.raw_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  stream_enabled   = true
  stream_view_type = "NEW_IMAGE"

  tags = {
    Name        = var.raw_table_name
    Environment = var.environment
  }
}

# Tabla DynamoDB para implied vols
resource "aws_dynamodb_table" "implied_vols" {
  name         = var.iv_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  tags = {
    Name        = var.iv_table_name
    Environment = var.environment
  }
}

# Repositorio ECR para la aplicación
resource "aws_ecr_repository" "app" {
  name = var.ecr_repo_name
}

# Permisos para App Runner a ECR
resource "aws_iam_role" "apprunner_ecr_access" {
  name = "${var.app_runner_service_name}-ecr-access"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "build.apprunner.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "apprunner_ecr_policy" {
  role   = aws_iam_role.apprunner_ecr_access.name
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ],
        Resource = aws_ecr_repository.app.arn
      },
      {
        Effect   = "Allow",
        Action   = ["ecr:GetAuthorizationToken"],
        Resource = "*"
      }
    ]
  })
}

# Servicio AWS App Runner
resource "aws_apprunner_service" "app" {
  service_name = var.app_runner_service_name

  source_configuration {
    image_repository {
      image_identifier      = aws_ecr_repository.app.repository_url
      image_repository_type = "ECR"
    }
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_ecr_access.arn
    }
  }

  instance_configuration {
    cpu    = "1024"
    memory = "2048"
  }

  tags = {
    Environment = var.environment
  }
}

# IAM Assume Role Policy para Lambdas
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# Rol de ejecución para Lambdas
resource "aws_iam_role" "lambda_exec" {
  name               = var.lambda_role_name
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

# Permisos básicos de Lambda
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Política de acceso a DynamoDB para Lambdas
resource "aws_iam_policy" "lambda_dynamodb" {
  name        = "${var.lambda_role_name}-dynamodb-access"
  description = "Permite acceso a tablas DynamoDB para Lambdas"
  policy      = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "dynamodb:BatchWriteItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ],
        Resource = [
          aws_dynamodb_table.raw_prices.arn,
          aws_dynamodb_table.implied_vols.arn
        ]
      }
    ]
  })
}

# Adjuntar política de DynamoDB al rol de Lambda
resource "aws_iam_role_policy_attachment" "lambda_dynamodb_attach" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_dynamodb.arn
}

output "ecr_repo_url" {
  value       = aws_ecr_repository.app.repository_url
  description = "URL del repositorio ECR creado"
}

output "app_url" {
  value       = aws_apprunner_service.app.service_url
  description = "URL pública de App Runner"
} 