variable "aws_region" {
  description = "Región de AWS donde desplegar"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Entorno de despliegue (dev, prod, etc.)"
  type        = string
  default     = "dev"
}

variable "s3_bucket_name" {
  description = "Nombre del bucket S3 para datos"
  type        = string
}

variable "dynamodb_table_name" {
  description = "Nombre de la tabla DynamoDB para metadatos"
  type        = string
} 