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