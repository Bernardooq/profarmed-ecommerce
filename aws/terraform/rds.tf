# ==========================================
# 🗄️ BASE DE DATOS RDS (POSTGRESQL) - DESACTIVADO (YA EXISTE EN PRODUCCIÓN)
# ==========================================

# 1. Crear el Grupo de Subnets para la Base de Datos (en subnets privadas)
# resource "aws_db_subnet_group" "rds_subnet_group" {
#   name        = "${var.project_name}-rds-subnet-group"
#   description = "Subnets privadas asignadas para la base de datos RDS de Profarmed"
#   subnet_ids  = var.private_subnet_ids
# 
#   tags = merge(var.common_tags, {
#     Name = "${var.project_name}-rds-subnet-group"
#   })
# }

# 2. Instancia de la Base de Datos RDS (PostgreSQL)
# resource "aws_db_instance" "postgres" {
#   identifier           = "${var.project_name}-db"
#   allocated_storage    = 20
#   max_allocated_storage = 100 # Habilita almacenamiento auto-escalable
#   storage_type         = "gp3"
#   engine               = "postgres"
#   engine_version       = "17.6"
#   instance_class       = "db.t4g.micro"
#   
#   # Credenciales Maestras Administrativas
#   db_name              = var.db_name
#   username             = var.db_username
#   password             = var.db_password
# 
#   # Redes y Seguridad
#   db_subnet_group_name   = aws_db_subnet_group.rds_subnet_group.name
#   vpc_security_group_ids = [aws_security_group.sg_rds.id]
#   publicly_accessible    = false # Privada, inaccesible desde internet
# 
#   # Mantenimiento y Respaldos
#   backup_retention_period = 7
#   deletion_protection     = false # Cambia a true en producción definitiva para evitar borrados accidentales
#   skip_final_snapshot     = true  # Cambia a false para respaldos automáticos antes de borrar con terraform destroy
# 
#   tags = merge(var.common_tags, {
#     Name = "${var.project_name}-db"
#   })
# }

