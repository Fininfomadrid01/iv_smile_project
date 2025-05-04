variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "ecr_repo_name" {
  description = "Name of the ECR repository for the app runner service"
  type        = string
}

variable "app_runner_service_name" {
  description = "Name of the AWS App Runner service"
  type        = string
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket for data"
  type        = string
}

variable "dynamodb_table_name" {
  description = "Name of the DynamoDB table for metadata"
  type        = string
}

variable "raw_table_name" {
  description = "Name of the DynamoDB raw prices table"
  type        = string
}

variable "iv_table_name" {
  description = "Name of the DynamoDB implied volatilities table"
  type        = string
}

variable "lambda_role_name" {
  description = "Name of the IAM role for Lambda execution"
  type        = string
}

variable "scraper_lambda_name" {
  description = "Function name for the scraper Lambda"
  type        = string
}

variable "iv_lambda_name" {
  description = "Function name for the iv_calc Lambda"
  type        = string
} 