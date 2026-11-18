# 📋 Ficha de Parámetros & Requerimientos: CloudFormation Stack (EC2 ASG + S3 + CloudFront + IAM)

Este documento sirve como plantilla de entrada para diseñar e implementar el template maestro de **AWS CloudFormation (IaC)** bajo el principio de **Mínimo Privilegio**, arquitectura inmutable y despliegue automatizado vía GitHub Actions.

> 📝 **Instrucciones:** Llena los campos marcados con `[ COMPLETAR ]` o confirma los valores propuestos. Una vez llenado, procederemos a codificar el template YAML/JSON de CloudFormation y las políticas IAM exactas.

---

## 🏗️ 1. Parámetros Globales & Naming Convention

| Parámetro | Valor Propuesto (Ejemplo) | Tu Valor / Nombre Exacto |
| :--- | :--- | :--- |
| **Nombre del Stack / Prefijo de Recursos** | `profarmed` / `profarmed` / `profarmed` | `[ profarmed ]` |
| **Región de AWS** | `us-east-1` (N. Virginia) | `[ us-east-1 ]` |
| **AWS Account ID** (para ARNs de políticas) | `817697649850` | `[ 817697649850 ]` |
| **ID de la VPC Existente** | `vpc-xxxxxxxxx` | `[ vpc-070b6ee4688c64481 ]` |
| **Subnets Públicas para EC2 / ASG** | `subnet-aaaaa`, `subnet-bbbbb` | `["b2b-subnet-public1-us-east-1a" "subnet-0b2993eddac596b58" "b2b-subnet-public2-us-east-1b" "subnet-0989ba4d8e9ae4e6a"]` |
| **ID del Target Group Existente del ALB** | `arn:aws:elasticloadbalancing:...:targetgroup/profarmed-tg/...` | `[ arn:aws:elasticloadbalancing:us-east-1:817697649850:targetgroup/tg-profarmed/3826737b46df4fa6 target group vacio pq no esta aun ag group]` |
| **Security Group del Load Balancer (sg-alb)** | `sg-xxxxxxxx` (para autorizar tráfico al puerto 80) | `[ sg-096226a27e574f4cc es el ag del load balancer y ya tiene reglas de entrada http y https salida todo, es necesario q sea el de entrada del grupo de las instancias ]` |
| **Tu IP Pública de Admin (para SSH/Admin)** | `XXX.XXX.XXX.XXX/32` | `[ por default permitiremos todo trafico ssh, igual para la plantilla ya tengo descargadas pem keys este es id profarmed-ecommerce-pem rsa key-0a78a412f17cf9461]` |

---

## 💻 2. Auto Scaling Group & EC2 (Launch Template)

| Parámetro | Valor Predeterminado / Propuesto | Tu Elección / Modificación |
| :--- | :--- | :--- |
| **Tipo de Instancia** | `t4g.nano` (ARM64 Graviton2) | `[ t4g.nano ]` |
| **Arquitectura de AMI** | `arm64` | `[ arm64 ]` |
| **AMI ID Base / Personalizada** | `ami-xxxxxxxxxxxxxxxxx` (Ubuntu 22.04 / Amazon Linux 2023) | `[ ami-0b2c9d1f3edcfd709 es amazon linux 2023 en arm64 ]` |
| **Capacidad ASG (Min / Deseada / Max)** | Min: `1`, Deseada: `1`, Max: `5` | `[ 1 1 5 ]` |
| **Key Pair Existente (para SSH)** | `profarmed-key` / `profarmed-key` | `[ profarmed-ecommerce-pem ]` |
| **User Data / Script de Inicialización** | Script que: <br>1. Descarga `.env` desde SSM Parameter Store.<br>2. Autentica Docker contra ECR.<br>3. Hace `docker run` con `--restart always` en puerto 8000:8000. | `[ Si debemos afinarlo para q no lo baje del ecr de profarmed sino del ecr q crearemos aqui al igual q el parameter store q crearemos #!/bin/bash
# 1. Actualizar el sistema e instalar Docker y jq
dnf update -y
dnf install -y docker jq
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# 2. Definición de Variables (Ajustar según tu cuenta)
REGION="us-east-1"
ACCOUNT_ID="817697649850" # Tu ID de cuenta AWS
REPO_NAME="profarmed-api"
ECR_URL="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO_NAME}:latest"

# 3. Descargar el archivo .env encriptado desde AWS SSM Parameter Store
aws ssm get-parameter \
    --name "profarmed-env" \
    --with-decryption \
    --region $REGION \
    --query "Parameter.Value" \
    --output text > /home/ec2-user/.env

chmod 600 /home/ec2-user/.env
chown ec2-user:ec2-user /home/ec2-user/.env

# 4. Autenticar Docker con Amazon ECR
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URL

# 5. Descargar la última imagen del contenedor
docker pull $ECR_URL

# 6. Ejecutar el contenedor mapeando el puerto 80 del EC2 al 80 del contenedor
# Mapea también la red local y asigna el archivo de variables de entorno descargado
docker run -d \
  --name profarmed-backend-app \
  --restart always \
  -p 80:80 \
  --env-file /home/ec2-user/.env \
  $ECR_URL

echo "Arranque de contenedor finalizado exitosamente." ]` |

---

## 📈 3. Monitoreo, Alarmas CloudWatch y SNS

| Parámetro | Configuración Estándar | Tu Configuración |
| :--- | :--- | :--- |
| **Métrica de Alarma CPU** | Promedio de CPU del ASG > `40%` sostenido por 2 periodos de 1 min | `[40%]` |
| **Email para Notificaciones SNS** | `alertas-devops@tudominio.com` | `[ bernardoorozcoquirarte@gmail.com ]` |
| **Política de Auto Scaling (Scale Out)** | +1 instancia cuando CPU > 20% | `+1 instancia cuando CPU > 40%` |
| **Política de Auto Scaling (Scale In)** | -1 instancia cuando CPU < 10% | `-1 instancia cuando CPU < 20%` |

---

## 🪣 4. Almacenamiento S3 (4 Buckets) & CloudFront (3 CDNs)

El stack creará y configurará los 4 buckets S3 con cifrado SSE-S3 y bloqueo de acceso público, además de las políticas OAC (Origin Access Control) para CloudFront:

| Bucket | Propósito | CDN / CloudFront Asociada | Dominio Personalizado / CNAME (Opcional) |
| :--- | :--- | :--- | :--- |
| **1. Frontend React** | Archivos estáticos (`dist/`) | **CDN 1** (SPA con fallback a `index.html`) | `[profarmed.com.mx]` |
| **2. Imágenes Catálogo** | Fotos de productos (`*.webp`) | **CDN 2** (Cache agresivo 1 año) | `[imgecommerce.profarmed.com.mx]` |
| **3. Banners & Promos** | Promociones dinámicas (`promos/`) | **CDN 3** (Cache optimizado) | `[promosecommerce.profarmed.com.mx]` |
| **4. Documentos Privados** | Documentos fiscales/sanitarios | **SIN CDN (Privado 100%)**.<br>Acceso solo vía URLs prefirmadas desde FastAPI. | *N/A (Acceso restringido)* |

> 🔒 **Certificado SSL/ACM:** Si usas dominios personalizados para CloudFront, se requiere el ARN del certificado ACM en `us-east-1`. Si no, se usan las URLs por defecto `*.cloudfront.net`.  
> ARN de ACM (opcional): `[ arn:aws:acm:us-east-1:817697649850:certificate/23c30556-235c-42b8-ab0a-e253cc687eae ]`

---

## 🔐 5. Seguridad IAM & Mínimo Privilegio

El template de CloudFormation generará automáticamente los siguientes **Roles y Políticas IAM específicos**:

### A. Rol IAM de la Instancia EC2 (`EC2InstanceProfileRole`) ESTE ROL SUS POLITICAS ESTAN EN C:\Users\berna\Documents\GitProjects\profarmed-ecommerce\aws\policies\aws-ssm-policy.json y C:\Users\berna\Documents\GitProjects\profarmed-ecommerce\aws\policies\aws-ecr-policy.json actualmente con los nombres ssm-profarmed-policy y ecr-profarmed-policy pero necesitanos tmbn q el cf stack los cree bajo el nombre y condicines de ssm-ecommerce-profarmed-ec2-policy y ecr-ecommerce-profarmed-ec2-policy, actualmente la instancia toma env variables con un user y pswd con aceso al bucket, pero cambiaremos esto, sera tambien por rol asi q en el mismo rol crearas otra policy llamada ssm-ecommerce-profarmed-ec2-policy como esto C:\Users\berna\Documents\GitProjects\profarmed-ecommerce\aws\policies\aws-s3-policy.json para los s3 bucketsd q igual creemos con esta cf stack.

- ✅ **SSM Parameter Store**: Permiso `ssm:GetParameter` / `ssm:GetParameters` **únicamente** sobre la ruta `/app/[prefijo]/.env`.
- ✅ **Amazon ECR**: Permiso `ecr:GetAuthorizationToken` (global) y `ecr:BatchGetImage`, `ecr:GetDownloadUrlForLayer` **exclusivamente** sobre el repositorio ECR de la app.
- ✅ **Amazon S3**: Permiso `s3:GetObject`, `s3:PutObject` **exclusivamente** sobre los buckets de imágenes, promociones y documentos privados.
- ✅ **CloudWatch Agent**: Permisos para enviar métricas y logs de la instancia.

Este usuario puedes crearlo haciendo la policy como la q esta aqui C:\Users\berna\Documents\GitProjects\profarmed-ecommerce\aws\policies\aws-pipeline-policy.json y le pones los permisos y nombre q quieras pero adoc con la nomenclatura de names q tenemos.
### B. Usuario IAM para CI/CD (GitHub Actions Deployer)
- ✅ **ECR Push**: `ecr:PutImage`, `ecr:InitiateLayerUpload`, `ecr:UploadLayerPart`, `ecr:CompleteLayerUpload` sobre el repo backend.
- ✅ **S3 Frontend Deploy**: `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket` **únicamente** sobre el bucket del frontend React.
- ✅ **CloudFront Invalidation**: `cloudfront:CreateInvalidation` **únicamente** sobre la distribución del frontend.
- ✅ **Auto Scaling Refresh**: `autoscaling:StartInstanceRefresh` para desplegar la nueva imagen de Docker sin downtime en las instancias EC2.

---

## 🗃️ 6. Almacén de Parámetros (SSM Parameter Store)
lo tenemos como securtestring Parameter Store

Mis parámetros

Parámetros públicos

Configuración
Ready to scale? Enable higher throughput to handle more API calls - Manage Settings to increase TPS.
Manage settings
Mis parámetros

Ver los detalles
Editar
Eliminar
Crear el parámetro

1


Nombre
	
Capa
	
Tipo
	
Última modificación

Nombre
	
Capa
	
Tipo
	
Última modificación

profarmed-env
Estándar
SecureString
Fri, 24 Jul 2026 23:46:27 GMT

profarmed-env
Estándar
SecureString
Fri, 24 Jul 2026 23:46:59 GMT, y tal cual tipo asi

# === CONFIGURACIÓN DE BASE DE DATOS ===
DATABASE_URL=postgresql:...

# === SEGURIDAD Y JWT ===
SECRET_KEY=...
ALGORITHM=HS256

# === CONFIGURACIÓN DE LA API ===
PROJECT_NAME=Profarmed API
FRONTEND_URL=*

# === CONFIGURACIÓN DE EMAIL (SMTP MAILERSEND profarmed.com.mx) ===
SMTP_HOST=smtp.mailersend.net
SMTP_PORT=587
SMTP_USER=MS_h2MMmm@profarmed.com.mx
SMTP_PASSWORD=mssp.kYPE0QA.yzkq3409w004d796.IGkw05g
SENDER=MS_h2MMmm@profarmed.com.mx

# === CONFIGURACIÓN DE TERCEROS ===
TURNSTILE_SECRET_KEY=...

# === CONFIGURACIÓN DE AWS (S3) ===
AWS_ACCESS_KEY_ID=no necesario si tenemos el rol para acceder a s3
AWS_SECRET_ACCESS_KEY=no necesario si tenemos el rol para acceder a s3
AWS_REGION=us-east-1 

BUCKET_DOCS=...

BUCKET_PROMOS=...
CLOUDFRONT_PROMOS_URL=...

BUCKET_IMGS=...
CLOUDFRONT_IMGS_URL=...
| Nombre del Parámetro | Tipo | Contenido |
| :--- | :--- | :--- |
| `/[prefijo]/production/.env` | `SecureString` (KMS) | Cadena completa del archivo `.env` del backend (DATABASE_URL, SECRET_KEY, SMTP, etc.) |

---

## 🚀 Siguiente Paso
Una vez que llenes los valores de este archivo:
1. Procederemos a generar el archivo **`aws/cloudformation/infra-stack.yaml`**.
2. Diseñaremos el pipeline de GitHub Actions para el despliegue continuo de infraestructura y código.

como vez todo es circular y debe seguir una nomenclatrira de nombre aparte debes crear un tema de sns llamado ecommerce-profarmed-alerts para que funcione lo de alarmas de cloudwatch y las metricas de cpu de los ec2. 

este cf s6tack es para esta infra todo loq tenga nombre profarmed se deve estandarizar en barables ejeplo variable name profarmed, su cambio eso ecommerce-blabla-alerts cambia, el nombre del parametro profarmed-env o profarmed-env cambia a blabla-env, claro ejeplo y asi cada policy ro lo q tenga nombres aca aso q a trabajar 

tambien te faltaron 
#=== CONFIGURACIÓN DE INSTANCE ROLE ===
ECR_IMAGE_URL= el ecr q crearemos
ASG_NAME= ...ProfarmedAGGroup generalmente se llaman asi asi q podemos usar blabla-asg
LAUNCH_TEMPLATE_NAME= el q se creara en el cf stack
#=== CONFIGURACIÓN DE INSTANCE ROLE ===
AWS_REGION=us-east-1
ECR_IMAGE_URL= ...
ASG_NAME= ...
LAUNCH_TEMPLATE_NAME= ...