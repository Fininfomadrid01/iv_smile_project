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

# Repositorio ECR para la aplicación
resource "aws_ecr_repository" "app" {
  name = var.ecr_repo_name
}

# Permisos para que App Runner lea de ECR
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
      image_identifier      = "${aws_ecr_repository.app.repository_url}:latest"
      image_repository_type = "ECR"
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

# Outputs de la infraestructura
output "s3_bucket_id" {
  value       = aws_s3_bucket.data_bucket.id
  description = "Nombre/ID del bucket S3 creado"
}

output "dynamodb_table_name" {
  value       = aws_dynamodb_table.data_table.name
  description = "Nombre de la tabla DynamoDB creada"
}

output "ecr_repo_url" {
  value       = aws_ecr_repository.app.repository_url
  description = "URL del repositorio ECR creado"
}

# Output con la URL pública de App Runner
output "app_url" {
  value       = aws_apprunner_service.app.service_url
  description = "URL pública del servicio App Runner"
} 