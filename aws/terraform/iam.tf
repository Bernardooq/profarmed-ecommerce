# ==========================================
# 🔑 ROLES Y POLÍTICAS DE IAM
# ==========================================

# 1. Definición del Rol de IAM para la instancia EC2
resource "aws_iam_role" "ec2_role" {
  name = "ProfarmedEC2Role"

  # Relación de confianza para permitir que el servicio EC2 asuma este Rol
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.common_tags, {
    Name = "ProfarmedEC2Role"
  })
}

# 2. Adjuntar la política administrada de AWS: Acceso de lectura a ECR
resource "aws_iam_role_policy_attachment" "ecr_readonly" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# 3. Adjuntar la política administrada de AWS: Core de Systems Manager (SSM Agent)
resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# 4. Adjuntar la Política Inline de S3 cargando el JSON desde la carpeta de políticas
resource "aws_iam_role_policy" "s3_access_policy" {
  name   = "ProfarmedS3AccessPolicy"
  role   = aws_iam_role.ec2_role.id
  policy = file("${path.module}/../policies/aws-s3-policy.json")
}

# 5. Adjuntar la Política Inline de SSM Parameter Store y KMS cargando el JSON
resource "aws_iam_role_policy" "ssm_decrypt_policy" {
  name   = "ProfarmedSSMParameterAccessPolicy"
  role   = aws_iam_role.ec2_role.id
  policy = file("${path.module}/../policies/aws-ssm-policy.json")
}

# 6. Crear el Instance Profile que se asignará al Launch Template de EC2
resource "aws_iam_instance_profile" "ec2_instance_profile" {
  name = "ProfarmedEC2InstanceProfile"
  role = aws_iam_role.ec2_role.name

  tags = merge(var.common_tags, {
    Name = "ProfarmedEC2InstanceProfile"
  })
}
