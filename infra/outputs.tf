output "s3_bucket_id" {
  value       = aws_s3_bucket.data_bucket.id
  description = "Nombre/ID del bucket S3 creado"
}

output "dynamodb_table_name" {
  value       = aws_dynamodb_table.data_table.name
  description = "Nombre de la tabla DynamoDB creada"
} 