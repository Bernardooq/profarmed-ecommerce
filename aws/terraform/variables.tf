variable "aws_region" {
  description = "Región de AWS donde se desplegarán los recursos"
  type        = string
  default     = "us-east-1"
}

variable "aws_account_id" {
  description = "ID de la cuenta de AWS"
  type        = string
  default     = "817697649850"
}

variable "environment" {
  description = "Ambiente de despliegue (producción, staging, etc.)"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Nombre del proyecto"
  type        = string
  default     = "profarmed"
}

# --- VPC y Subnets ---
variable "vpc_id" {
  description = "ID de la VPC existente donde se desplegará la infraestructura"
  type        = string
  # Deja esto vacío para que el usuario deba proveerlo, o añade un placeholder
  default     = "vpc-0123456789abcdef0" 
}

variable "public_subnet_ids" {
  description = "Lista de Subnets públicas (para el Application Load Balancer)"
  type        = list(string)
  default     = ["subnet-11111111", "subnet-22222222"]
}

variable "private_subnet_ids" {
  description = "Lista de Subnets privadas (para las instancias EC2 y RDS)"
  type        = list(string)
  default     = ["subnet-33333333", "subnet-44444444"]
}

# --- Base de Datos RDS ---
variable "db_name" {
  description = "Nombre de la base de datos de producción"
  type        = string
  default     = "profarmed_db"
}

variable "db_username" {
  description = "Nombre del usuario maestro de la base de datos (administrador)"
  type        = string
  default     = "postgres"
}

variable "db_password" {
  description = "Contraseña maestra de la base de datos RDS"
  type        = string
  sensitive   = true
}

# --- Tags ---
variable "common_tags" {
  description = "Tags comunes que se aplicarán a todos los recursos de AWS"
  type        = map(string)
  default = {
    Project     = "Profarmed"
    Environment = "production"
    ManagedBy   = "Terraform"
  }
}
