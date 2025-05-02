variable "ecr_repo_name" {
  description = "Nombre del repositorio ECR para la imagen de la app"
  type        = string
}

variable "app_runner_service_name" {
  description = "Nombre del servicio AWS App Runner"
  type        = string
}

variable "environment" {
  description = "Entorno de despliegue (dev, prod, etc.)"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "Región de AWS donde desplegar"
  type        = string
  default     = "us-east-1"
}

variable "s3_bucket_name" {
  description = "Nombre del bucket S3 para datos"
  type        = string
}

variable "dynamodb_table_name" {
  description = "Nombre de la tabla DynamoDB para metadatos"
  type        = string
}

variable "raw_table_name" {
  description = "Nombre de la tabla RawPrices"
  type        = string
}

variable "iv_table_name" {
  description = "Nombre de la tabla ImpliedVols"
  type        = string
}

variable "lambda_role_name" {
  description = "Nombre del role de ejecución de Lambda"
  type        = string
}

variable "scraper_lambda_name" {
  description = "Nombre de la función Lambda para scraper"
  type        = string
}

variable "iv_lambda_name" {
  description = "Nombre de la función Lambda para cálculo de IV"
  type        = string
} 