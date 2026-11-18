terraform {
  required_version = ">= 1.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ==========================================
# 🛡️ GRUPOS DE SEGURIDAD (SECURITY GROUPS)
# ==========================================

# 1. Grupo de Seguridad para el Application Load Balancer (ALB)
resource "aws_security_group" "sg_alb" {
  name        = "${var.project_name}-sg-alb"
  description = "Permite trafico HTTP y HTTPS desde internet hacia el ALB"
  vpc_id      = var.vpc_id

  ingress {
    description      = "HTTP desde internet"
    from_port        = 80
    to_port          = 80
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  ingress {
    description      = "HTTPS desde internet"
    from_port        = 443
    to_port          = 443
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  egress {
    description = "Trafico saliente ilimitado"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-sg-alb"
  })
}

# 2. Grupo de Seguridad para las Instancias EC2 del Backend (ASG)
resource "aws_security_group" "sg_backend" {
  name        = "${var.project_name}-sg-backend"
  description = "Permite trafico HTTP solo desde el sg-alb y SSH administrativo"
  vpc_id      = var.vpc_id

  ingress {
    description     = "HTTP solo desde el Load Balancer"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.sg_alb.id]
  }

  ingress {
    description      = "SSH solo para administracion"
    from_port        = 22
    to_port          = 22
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"] # Recomiendase restringir a tu IP publica
  }

  egress {
    description = "Trafico saliente ilimitado para descargar Docker, ECR y SSM"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-sg-backend"
  })
}

# 3. Grupo de Seguridad para la Base de Datos RDS (PostgreSQL)
resource "aws_security_group" "sg_rds" {
  name        = "${var.project_name}-sg-rds"
  description = "Permite trafico PostgreSQL solo desde el sg-backend"
  vpc_id      = var.vpc_id

  ingress {
    description     = "PostgreSQL desde las instancias del backend"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.sg_backend.id]
  }

  egress {
    description = "Trafico saliente limitado"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-sg-rds"
  })
}

# ==========================================
# 📦 ALMACENAMIENTO (S3 BUCKETS)
# ==========================================

# 1. Bucket para la Pagina Estatica de React (Web)
resource "aws_s3_bucket" "bucket_react" {
  bucket        = "${var.project_name}-react"
  force_destroy = false

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-react"
  })
}

# Bloquear acceso publico directo a React (para forzar uso de CloudFront con OAC)
resource "aws_s3_bucket_public_access_block" "block_react" {
  bucket = aws_s3_bucket.bucket_react.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# 2. Bucket para Imagenes generales y del catalogo
resource "aws_s3_bucket" "bucket_imgs" {
  bucket        = "${var.project_name}-imgs"
  force_destroy = false

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-imgs"
  })
}

resource "aws_s3_bucket_public_access_block" "block_imgs" {
  bucket = aws_s3_bucket.bucket_imgs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# 3. Bucket para Promociones y Banners de Marketing
resource "aws_s3_bucket" "bucket_promos" {
  bucket        = "${var.project_name}-promos"
  force_destroy = false

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-promos"
  })
}

resource "aws_s3_bucket_public_access_block" "block_promos" {
  bucket = aws_s3_bucket.bucket_promos.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# 4. Bucket Privado para Documentos (Sin CloudFront, acceso por URLs firmadas)
resource "aws_s3_bucket" "bucket_docs" {
  bucket        = "${var.project_name}-docs"
  force_destroy = false

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-docs"
  })
}

resource "aws_s3_bucket_public_access_block" "block_docs" {
  bucket = aws_s3_bucket.bucket_docs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
