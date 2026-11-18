# ==========================================
# 📊 OUTPUTS DE LA INFRAESTRUCTURA
# ==========================================

# output "rds_endpoint" {
#   description = "Dirección host (endpoint) de la base de datos RDS para colocar en Parameter Store"
#   value       = aws_db_instance.postgres.endpoint
# }
# 
# output "rds_address" {
#   description = "Dirección IP/host de la base de datos (sin el puerto)"
#   value       = aws_db_instance.postgres.address
# }


output "iam_instance_profile_name" {
  description = "Nombre del Instance Profile de IAM para el Launch Template"
  value       = aws_iam_instance_profile.ec2_instance_profile.name
}

output "sg_alb_id" {
  description = "ID del Security Group para el ALB"
  value       = aws_security_group.sg_alb.id
}

output "sg_backend_id" {
  description = "ID del Security Group para las instancias EC2 del Backend"
  value       = aws_security_group.sg_backend.id
}

output "sg_rds_id" {
  description = "ID del Security Group para el RDS"
  value       = aws_security_group.sg_rds.id
}

output "s3_bucket_react" {
  description = "Nombre del bucket para la web estática de React"
  value       = aws_s3_bucket.bucket_react.id
}

output "s3_bucket_imgs" {
  description = "Nombre del bucket para las imágenes de catálogo"
  value       = aws_s3_bucket.bucket_imgs.id
}

output "s3_bucket_promos" {
  description = "Nombre del bucket para promociones"
  value       = aws_s3_bucket.bucket_promos.id
}

output "s3_bucket_docs" {
  description = "Nombre del bucket privado de documentos"
  value       = aws_s3_bucket.bucket_docs.id
}
