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

# ECR repository for the application image
resource "aws_ecr_repository" "app" {
  name                 = var.ecr_repo_name
  image_scanning_configuration {
    scan_on_push = true
  }
  tags = {
    Name        = var.ecr_repo_name
    Environment = var.environment
  }
}

# IAM role para App Runner acceder a ECR
resource "aws_iam_role" "apprunner_ecr_access" {
  name = "${var.app_runner_service_name}-ecr-access-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "build.apprunner.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "apprunner_ecr_policy" {
  role       = aws_iam_role.apprunner_ecr_access.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# App Runner Service
resource "aws_apprunner_service" "app" {
  service_name = var.app_runner_service_name

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_ecr_access.arn
    }
    auto_deployments_enabled = true
    image_repository {
      image_identifier      = "${aws_ecr_repository.app.repository_url}:latest"
      image_repository_type = "ECR"
      image_configuration {
        port = "8501"
      }
    }
  }

  tags = {
    Name        = var.app_runner_service_name
    Environment = var.environment
  }
} 