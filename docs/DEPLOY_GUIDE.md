# 🚀 Guía de Despliegue y Arquitectura AWS Full-Stack - Profarmed

Esta guía documenta la arquitectura de grado de producción (Solutions Architect) para la plataforma **Profarmed**. Está diseñada para ser segura, elástica, inmutable y totalmente automatizada mediante pipelines de CI/CD.

---

## 🏗️ Diagrama General de la Arquitectura

```
                       [ HTTPS (443) ]
                              │
       ┌──────────────────────┼──────────────────────┐
       ▼                      ▼                      ▼
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│  CloudFront  │       │  CloudFront  │       │  CloudFront  │
│  (Web React) │       │  (Imágenes)  │       │ (Promociones)│
└──────┬───────┘       └──────┬───────┘       └──────┬───────┘
       ▼                      ▼                      ▼
┌───────────────┐       ┌──────────────┐       ┌────────────────┐
│  S3 Static    │       │  S3 Images   │       │  S3 Promos     │
│(profarmed-rct)│       │(profarmed-img)│      │(profarmed-prm) │
└───────────────┘       └──────────────┘       └────────────────┘

                              │ [ HTTPS (443) ]
                              ▼
                       ┌──────────────┐
                       │  ALB (Load   │  <-- sg-alb (80/443 de 0.0.0.0/0)
                       │  Balancer)   │
                       └──────┬───────┘
                              │ [ HTTP (80) ]
                              ▼
                       ┌──────────────┐
                       │ Auto Scaling │
                       │    Group     │  <-- sg-backend (80 de sg-alb, 22 de Admin)
                       │ (EC2 Docker) │
                       └──────┬───────┘
                              │
             ┌────────────────┴────────────────┐
             ▼                                 ▼
      ┌──────────────┐                  ┌──────────────┐
      │  S3 Docs     │                  │  RDS Postgres│  <-- sg-rds (5432 de sg-backend)
      │(profarmed-doc)│                 │(profarmed-db)│
      │  [PRIVADO]   │                  └──────────────┘
      └──────────────┘
```

---

## 🔒 Fase 1: Base de Datos RDS PostgreSQL (Menor Privilegio)

No utilizaremos el usuario administrativo principal (como `postgres` o `profarmeddb`) para la conexión diaria del backend. En su lugar, crearemos una base de datos limpia `profarmed_db` y un usuario `profarmed_user` con permisos limitados **exclusivamente** sobre dicha base de datos.

### 1.1 Conexión Inicial como Administrador (`postgres`)

```bash
# Desde cualquier EC2 con acceso al RDS
psql "host=profarmed-db.ccn22ys0s7ya.us-east-1.rds.amazonaws.com \
user=postgres \
dbname=postgres \
port=5432 \
sslmode=require"
```

### 1.2 Comandos SQL para Inicializar la Base de Datos
Una vez conectado como `postgres`, ejecuta las siguientes instrucciones para crear la base de datos del proyecto y el usuario restringido:

```sql
-- 1. Crear la base de datos para la aplicación
CREATE DATABASE profarmed_db;

-- 2. Crear el usuario dedicado de Profarmed
CREATE USER profarmed_user WITH PASSWORD 'TU_CONTRASEÑA_SUPER_SEGURA_AQUI';

-- 3. Asignar todos los permisos de la base de datos profarmed_db al usuario dedicado
GRANT ALL PRIVILEGES ON DATABASE profarmed_db TO profarmed_user;

-- 4. Conectarse a la nueva base de datos para habilitar permisos en el esquema público
\c profarmed_db

-- ⚠️ IMPORTANTE PARA POSTGRESQL 15+:
-- En versiones recientes, el esquema público ya no permite creación de tablas por defecto 
-- a usuarios no propietarios. Debemos otorgar el permiso explícitamente:
GRANT ALL ON SCHEMA public TO profarmed_user;
```

### 1.3 Conexión de Prueba como Usuario de la Aplicación (`profarmed_user`)

```bash
# Desde cualquier EC2 con acceso al RDS
psql "host=profarmed-db.ccn22ys0s7ya.us-east-1.rds.amazonaws.com \
user=profarmed \
dbname=postgres \
port=5432 \
sslmode=require"
```

---

## 🔑 Fase 2: Gestión Segura de Secretos (`.env`) y Seguridad en ECR

### ⚠️ El principio de desacoplamiento de secretos para ECR
Al compilar y empaquetar nuestro contenedor para **Amazon ECR**, aplicamos el principio de seguridad de **desacoplamiento de secretos**:
1. **Nunca** copies el archivo `.env` o credenciales dentro de la imagen de Docker durante el proceso de build. Esto garantiza que cualquier persona con acceso de lectura a ECR no pueda comprometer las credenciales del sistema.
2. La imagen compilada y subida a ECR es **entorno-agnóstica** (el mismo contenedor puede correr en staging o producción).
3. Las variables de entorno reales se inyectan en tiempo de ejecución (`runtime`). El Auto Scaling Group aprovisiona las instancias EC2, las cuales descargan los secretos de forma segura desde **AWS Systems Manager (SSM) Parameter Store** al momento de iniciar y se los pasan al contenedor de Docker mediante el parámetro `--env-file`.

### 2.1 Configuración de Variables en Parameter Store
1. Abre la consola de AWS y ve a **Systems Manager** -> **Parameter Store**.
2. Crea un nuevo parámetro:
   - **Name**: `profarmed-env`
   - **Tier**: `Standard`
   - **Type**: `SecureString` (Esto lo encripta en reposo usando KMS)
   - **Value**: Copia y pega las credenciales reales de producción (asegúrate de que los usuarios y nombres coincidan con la fase de base de datos y S3):
     ```env
     DATABASE_URL=postgresql://profarmed_user:TU_CONTRASEÑA_SUPER_SEGURA_AQUI@profarmed-db.ccn22ys0s7ya.us-east-1.rds.amazonaws.com:5432/profarmed_db?sslmode=require
     SECRET_KEY=TU_JWT_SECRET_VERY_SECURE
     ALLOWED_ORIGINS=https://tu-cloudfront-react.cloudfront.net,http://localhost:3000
     FRONTEND_URL=https://tu-cloudfront-react.cloudfront.net
     TURNSTILE_SECRET_KEY=0x4AAAAAADhNYEokcYrvlo35LYQjXgOslLg
     ENVIRONMENT=production
     # Configuración S3 para el backend (para almacenar/leer documentos y firmar URLs)
     AWS_STORAGE_BUCKET_NAME=profarmed-docs
     ```
3. Guarda el parámetro. La máquina EC2 descargará y desencriptará este archivo en memoria al arrancar.

---

## 📦 Fase 3: Frontend y Almacenamiento (S3 & CloudFront)

La infraestructura utiliza **4 buckets de S3** y **3 distribuciones de CloudFront** para segmentar de forma eficiente los archivos públicos de los privados.

| Recurso S3 | CloudFront Dist. | Acceso | Propósito | Lógica / Configuración |
| :--- | :---: | :---: | :--- | :--- |
| `profarmed-react` | **Sí** | Público | Web React compilada | Distribución asociada al bucket. El bucket es privado y el acceso es exclusivo de CloudFront a través de OAC (Origin Access Control). |
| `profarmed-imgs` | **Sí** | Público | Catálogo e Imágenes | Distribución asociada para optimización de entrega de imágenes y cacheado. |
| `profarmed-promos` | **Sí** | Público | Banners y Promos | Distribución asociada para recursos publicitarios cambiantes de marketing. |
| `profarmed-docs`| **No** | Privado | Documentos Admin/Ventas | **Sin CloudFront**. El backend genera URLs firmadas (`S3 Presigned URLs`) temporales para que el administrador descargue reportes o facturas. |

### Lógica de URLs Firmadas (S3 Presigned URLs)
Cuando un administrador autenticado solicita acceder a un documento en el bucket `profarmed-docs` (ej: un reporte de ventas en PDF), el backend de FastAPI ejecuta una llamada a AWS S3 utilizando la SDK de Boto3 para generar una URL temporal:
```python
# Ejemplo conceptual en FastAPI:
import boto3
from botocore.exceptions import ClientError

s3_client = boto3.client('s3', region_name='us-east-1')
try:
    presigned_url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': 'profarmed-docs', 'Key': 'reporte_ventas_2026.pdf'},
        ExpiresIn=900 # Válido por 15 minutos (900 segundos)
    )
except ClientError as e:
    # Manejar error
    pass
```
Esto asegura que el archivo PDF nunca sea público en internet y expire automáticamente.

---

## 🛡️ Fase 4: Seguridad de Red (Security Groups)

Configuraremos tres grupos de seguridad en cascada para encapsular el tráfico:

### 1. `sg-alb` (Application Load Balancer)
- **Reglas de Entrada (Ingress)**:
  - Puerto `80` (HTTP) desde `0.0.0.0/0`.
  - Puerto `443` (HTTPS) desde `0.0.0.0/0`.
- **Reglas de Salida (Egress)**:
  - Todo el tráfico hacia `sg-backend` en puerto `80`.

### 2. `sg-backend` (EC2 en Auto Scaling Group)
- **Reglas de Entrada (Ingress)**:
  - Puerto `80` (HTTP) **solamente** permitiendo como origen el Security Group `sg-alb`. (Impide conexiones directas evadiendo el ALB).
  - Puerto `22` (SSH) solo permitiendo la IP del administrador (opcional).
- **Reglas de Salida (Egress)**:
  - Todo el tráfico permitido (`0.0.0.0/0`) para permitir llamadas a ECR, S3, SSM y actualización de paquetes del OS.

### 3. `sg-rds` (Base de Datos RDS)
- **Reglas de Entrada (Ingress)**:
  - Puerto `5432` (PostgreSQL) **solamente** permitiendo como origen el Security Group `sg-backend`. (Ninguna entidad externa o IP de internet puede comunicarse con la base de datos).

---

## 🐳 Fase 5: Repositorio ECR y Push de la Imagen Backend

### 5.1 Crear el Repositorio ECR
1. Ve a **Elastic Container Registry (ECR)** en AWS.
2. Crea un repositorio privado llamado `profarmed-api`.

### 5.2 Comandos Manuales de Push (Para configurar o probar)
Si quieres compilar y subir manualmente desde tu terminal local:
```bash
# Definir variables locales
AWS_REGION="us-east-1"
AWS_ACCOUNT="817697649850" # Tu ID de cuenta AWS
REPO_NAME="profarmed-api"

# 1. Autenticar Docker local con ECR

# Opción A (Para terminal Bash / Git Bash):
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com

# Opción B (Para AWS Tools for PowerShell en Windows):
(Get-ECRLoginCommand).Password | docker login --username AWS --password-stdin 817697649850.dkr.ecr.us-east-1.amazonaws.com

# 2. Compilar la imagen de Docker (desde la raíz de /backend)
docker build -t profarmed-api backend/

# 3. Etiquetar la imagen
docker tag profarmed-api:latest $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/profarmed-api:latest

# 4. Subir la imagen
docker push $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/profarmed-api:latest
```

---

## ⚖️ Fase 6: Application Load Balancer (ALB) y Target Group

### 6.1 Crear el Target Group
1. Ve a **EC2** -> **Target Groups** -> **Create target group**.
2. Selecciona **Target type**: `Instances`.
3. **Target group name**: `profarmed-backend-tg`.
4. **Protocol / Port**: `HTTP` / `80` (El tráfico dentro de la red privada de AWS viaja por el puerto 80 hacia las EC2).
5. **VPC**: Selecciona la VPC donde reside tu base de datos RDS.
6. **Health checks**:
   - Protocol: `HTTP`
   - Path: `/api/v1/health` (O la ruta que responda `200 OK` en tu FastAPI).
7. Haz clic en **Create**.

### 6.2 Crear el Load Balancer (ALB)
1. Ve a **Load Balancers** -> **Create Application Load Balancer**.
2. **Name**: `profarmed-alb`.
3. **Scheme**: Internet-facing.
4. **Network mapping**: Selecciona tu VPC y al menos 2 Subnets públicas (en distintas zonas de disponibilidad).
5. **Security Groups**: Selecciona el `sg-alb`.
6. **Listeners and routing**:
   - **HTTP (80)**: Configura una regla para redirigir todo el tráfico a HTTPS (443).
   - **HTTPS (443)**: Redirige al Target Group `profarmed-backend-tg`. Selecciona el certificado ACM correspondiente a tu dominio `profarmed.com.mx`.

---

## 📝 Fase 7: Launch Template y Script de User Data

### 7.1 Crear Rol IAM (`ProfarmedEC2Role`)
Antes de crear el Launch Template, crea un rol en IAM para que la EC2 tenga permisos de consultar AWS de forma nativa sin almacenar llaves de acceso estáticas:
1. Crea un rol de IAM para **EC2**.
2. Asígnale las siguientes políticas administradas de AWS:
   - `AmazonEC2ContainerRegistryReadOnly` (Para permitir que Docker en la EC2 descargue la imagen del backend desde ECR).
   - `AmazonSSMManagedInstanceCore` (Para permitir el registro del nodo con AWS Systems Manager, por ejemplo, para Session Manager).
3. **Crear y asignar la Política de S3 (Inline Policy)**:
   - Crea una política inline en la consola de IAM para dar permisos de lectura y escritura en los buckets de S3.
   - Pega el siguiente JSON en la consola de IAM:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket",
                "s3:GetBucketLocation"
            ],
            "Resource": [
                "arn:aws:s3:::profarmed-imgs",
                "arn:aws:s3:::profarmed-docs",
                "arn:aws:s3:::profarmed-promos"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject"
            ],
            "Resource": [
                "arn:aws:s3:::profarmed-imgs/*",
                "arn:aws:s3:::profarmed-docs/*",
                "arn:aws:s3:::profarmed-promos/*"
            ]
        }
    ]
}
```

4. **Crear y asignar la Política de SSM Parameter Store (Inline Policy)**:
   - ⚠️ **IMPORTANTE**: La política `AmazonSSMManagedInstanceCore` **no** otorga acceso por defecto para leer parámetros personalizados en Parameter Store. Para solucionar esto, crea otra política inline para que el EC2 pueda leer el secreto `profarmed-env` y desencriptarlo con KMS.
   - Pega el siguiente JSON en la consola de IAM:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ssm:GetParameter",
                "ssm:GetParameters"
            ],
            "Resource": "arn:aws:ssm:us-east-1:817697649850:parameter/profarmed-env"
        },
        {
            "Effect": "Allow",
            "Action": [
                "kms:Decrypt"
            ],
            "Resource": "arn:aws:kms:us-east-1:817697649850:key/*"
        }
    ]
}
```

5. **Crear y asignar la Política de ECR (Inline Policy) - Alternativa más segura**:
   - *Nota*: Por defecto, puedes usar la política administrada de AWS `AmazonEC2ContainerRegistryReadOnly`. Sin embargo, si deseas aplicar el principio de mínimo privilegio estricto para que la máquina solo pueda consultar y descargar de tu repositorio específico `profarmed-api`, crea una política inline adicional.
   - Pega el siguiente JSON en la consola de IAM:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "ECRAuth",
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken"
            ],
            "Resource": "*"
        },
        {
            "Sid": "ECRPull",
            "Effect": "Allow",
            "Action": [
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage"
            ],
            "Resource": "arn:aws:ecr:us-east-1:817697649850:repository/profarmed-api"
        }
    ]
}
```

6. Nombra al rol `ProfarmedEC2Role`.

### 7.2 Crear el Launch Template
1. Ve a **EC2** -> **Launch Templates** -> **Create template**.
2. **Name**: `profarmed-backend-template`.
3. **AMI**: Amazon Linux 2023.
4. **Instance Type**: `t3.micro` o `t3.small`.
5. **Key pair**: Tu llave SSH habitual.
6. **Network Settings**: Selecciona el grupo de seguridad `sg-backend`.
7. **Advanced Details**:
   - **IAM instance profile**: Selecciona `ProfarmedEC2InstanceProfile`.
   - **User Data**: Pega el siguiente script, el cual automatiza la descarga de Docker, autenticación con ECR, lectura de secretos y ejecución del contenedor en el puerto 80:

```bash
#!/bin/bash
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

echo "✅ Arranque de contenedor finalizado exitosamente."
```

---

## 📈 Fase 8: Auto Scaling Group (ASG)

1. Ve a **Auto Scaling Groups** -> **Create**.
2. **Name**: `ProfarmedAGGroup`.
3. **Launch template**: Selecciona `profarmed-backend-template` (usa la versión `$Latest`).
4. **VPC & Subnets**: Selecciona tu VPC y subnets privadas (o públicas, dependiendo de la topología elegida).
5. **Load balancing**: Selecciona **Attach to an existing load balancer** y elige tu Target Group `profarmed-backend-tg`. Habilita los **ELB Health checks**.
6. **Group size**:
   - Capacidad Deseada: `2`
   - Capacidad Mínima: `2`
   - Capacidad Máxima: `6`
7. **Scaling policies**: Selecciona **Target tracking scaling policy** usando la métrica **Average CPU Utilization** al `70%`.

---

## 🤖 Fase 9: Automatización CI/CD con GitHub Actions

Para automatizar completamente el flujo, configuramos dos flujos independientes en GitHub Actions y creamos un usuario con permisos limitados en AWS para ejecutar las tareas.

### 9.1 Crear Usuario IAM para GitHub Actions (`pipeline-profarmed`)
Por seguridad, el pipeline de GitHub Actions no debe usar tus credenciales principales. Crearemos un usuario dedicado con menor privilegio:
1. Ve a la consola de **IAM** -> **Users** -> **Create user**.
2. Nombra al usuario como `pipeline-profarmed`.
3. Crea y asígnale de forma directa una **política de permisos inline (Custom Policy)** para permitirle realizar push a ECR, refrescar el ASG, sincronizar con el S3 de frontend e invalidar la caché de CloudFront.
   - Pega el siguiente JSON en la consola de IAM:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "ECRAuth",
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken"
            ],
            "Resource": "*"
        },
        {
            "Sid": "ECRPush",
            "Effect": "Allow",
            "Action": [
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload",
                "ecr:PutImage"
            ],
            "Resource": "arn:aws:ecr:us-east-1:817697649850:repository/profarmed-api"
        },
        {
            "Sid": "ASGRefresh",
            "Effect": "Allow",
            "Action": [
                "autoscaling:StartInstanceRefresh",
                "autoscaling:CancelInstanceRefresh"
            ],
            "Resource": "arn:aws:autoscaling:us-east-1:817697649850:autoScalingGroup:b10527b2-8043-421b-b8d8-e5bb0cea7ef7:autoScalingGroupName/ProfarmedAGGroup"
        },
        {
            "Sid": "S3FrontendSync",
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket",
                "s3:GetBucketLocation"
            ],
            "Resource": "arn:aws:s3:::profarmed-react"
        },
        {
            "Sid": "S3FrontendCRUD",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::profarmed-react/*"
        },
        {
            "Sid": "CFInvalidation",
            "Effect": "Allow",
            "Action": [
                "cloudfront:CreateInvalidation"
            ],
            "Resource": "arn:aws:cloudfront::817697649850:distribution/E2KRC8L9XXF6LX"
        }
    ]
}
```

4. Crea las **Access Keys (Claves de acceso)** para el usuario `pipeline-profarmed` (elige la opción **interfaz de línea de comandos (CLI)** o **Código local**).
5. Descarga el archivo de credenciales e introdúcelas en tu repositorio de GitHub bajo **Settings** -> **Secrets and variables** -> **Actions** -> **New repository secret** como `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY`.

### 9.2 Automatización del Backend (`.github/workflows/deploy-backend.yml`)
Este workflow compila la nueva imagen de Docker, la sube a ECR y desencadena un **Instance Refresh** progresivo (soft rollout) en el Auto Scaling Group para evitar caídas de servicio.

> [!NOTE]
> Crea este archivo en `.github/workflows/deploy-backend.yml`.

```yaml
name: Deploy Backend to AWS ECR & ASG

on:
  push:
    branches:
      - main
    paths:
      - 'backend/**'

jobs:
  deploy:
    name: Build & Rolling Deploy Backend
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build, Tag and Push Image to ECR
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPOSITORY: profarmed-api
          IMAGE_TAG: latest
        run: |
          # Compilar el contenedor del backend
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG backend/
          # Subir la imagen a ECR
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG

      - name: Trigger Auto Scaling Group Soft Refresh
        run: |
          # Inicia el refresco progresivo en el ASG de forma controlada
          echo "Checking/cancelling existing instance refresh if in progress..."
          aws autoscaling cancel-instance-refresh --auto-scaling-group-name ProfarmedAGGroup || true
          
          sleep 5
          
          echo "Starting new instance refresh..."
          aws autoscaling start-instance-refresh \
            --auto-scaling-group-name ProfarmedAGGroup \
            --preferences '{"MinHealthyPercentage": 50, "InstanceWarmup": 90}'
          
          echo "✅ Instance Refresh iniciado exitosamente. AWS reemplazará las instancias de forma soft."
```

### 9.3 Automatización del Frontend (`.github/workflows/deploy-frontend.yml`)
Este workflow compila la aplicación React (Vite), sincroniza el resultado en el bucket S3 estático eliminando elementos antiguos, y finalmente invalida la caché de CloudFront para que los usuarios vean los cambios inmediatamente.

> [!NOTE]
> Crea este archivo en `.github/workflows/deploy-frontend.yml`.

```yaml
name: Deploy Frontend to S3 & CloudFront

on:
  push:
    branches:
      - main
    paths:
      - 'react/**'

jobs:
  deploy:
    name: Build & Publish Frontend
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 18
          cache: 'npm'
          cache-dependency-path: react/package-lock.json

      - name: Install Dependencies & Build
        run: |
          cd react
          npm ci
          npm run build # Genera la carpeta 'dist/'

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Sync React dist to S3 Bucket
        run: |
          # Sincroniza la carpeta dist/ de Vite con el bucket, removiendo del bucket lo que ya no existe en dist/
          aws s3 sync react/dist/ s3://profarmed-react --delete

      - name: Invalidate CloudFront Cache
        run: |
          # Reemplaza por tu ID de distribución de CloudFront real
          aws cloudfront create-invalidation \
            --distribution-id E2KRC8L9XXF6LX \
            --paths "/*"
          
          echo "✅ Sincronización e invalidación de CloudFront completadas exitosamente."
```

---

## 🔑 Fase 10: Configuración de Credenciales Fuera de AWS (Desarrollo Local y Data Center)

Para que tu código local y el script de sincronización en tu centro de datos (Data Center) puedan interactuar con S3, necesitas configurar un **Usuario IAM** con llaves de acceso estáticas (`Access Key` y `Secret Access Key`).

### 10.1 Creación del Usuario IAM y Selección de la Opción de AWS
1. Ve a la consola de **IAM** -> **Users** -> **Create user**.
2. Nombra al usuario (ej: `s3-sync-profarmed`).
3. En la sección de permisos, asígnale de forma directa la política inline creada a partir de `aws-s3-policy.json`.
4. Crea la **Clave de acceso (Access Key)**:
   - AWS te mostrará una advertencia sobre alternativas de seguridad.
   - **¿Qué opción seleccionar?**: Selecciona **"Aplicación ejecutada fuera de AWS"** (ya que se ejecutará en tu Data Center físico para sincronizar las imágenes) o **"Código local"** (para desarrollo local de docs, imgs y promos).
   - Marca la casilla **"Entiendo la recomendación anterior y deseo proceder a la creación de una clave de acceso"**.
   - Haz clic en **Siguiente** (Next) y descarga/guarda de forma segura las credenciales (`Access Key` y `Secret Access Key`).

### 10.2 Configuración en tu Computadora Local y en el Servidor del Data Center
En ambos entornos (desarrollo local y el servidor de sincronización del Data Center), instala la AWS CLI y ejecuta el comando de configuración:

```bash
# Ejecuta el asistente de configuración de AWS asignando el perfil de profarmed
aws configure --profile s3-sync-profarmed

# AWS te pedirá ingresar los datos de tu credencial descargada:
# AWS Access Key ID [None]: TU_ACCESS_KEY_ID_AQUI
# AWS Secret Access Key [None]: TU_SECRET_ACCESS_KEY_AQUI
# Default region name [None]: us-east-1
# Default output format [None]: json
```

Una vez configurado, tu entorno local y el servidor del Data Center podrán realizar comandos como:
```bash
# Sincronización del Data Center al bucket de imágenes:
aws s3 sync /ruta/local/imagenes/ s3://profarmed-imgs --delete --profile s3-sync-profarmed
```

---

## 🛠️ Fase 11: Automatización de Infraestructura con Terraform (IaC - Opcional)

Para evitar la creación manual de los recursos base, se ha provisto un proyecto de Terraform en la carpeta `aws/terraform/`.

### 11.1 Recursos Automatizados por Terraform
* **Grupos de Seguridad**: Crea `sg-alb`, `sg-backend` (EC2) y `sg-rds` vinculados entre sí.
* **Almacenamiento S3**: Crea los 4 buckets (`profarmed-react`, `profarmed-imgs`, `profarmed-promos`, `profarmed-docs`) bloqueando accesos públicos directos.
* **Roles de IAM**: Crea `ProfarmedEC2Role` e inyecta las políticas locales de `aws-s3-policy.json` y `aws-ssm-policy.json` como políticas inline, y genera el *Instance Profile* listo para usar en tu Launch Template.

### 11.2 Instrucciones de Uso
1. Ve a la carpeta `aws/terraform/` desde tu terminal.
2. Crea un archivo local llamado `terraform.tfvars` (este archivo está en `.gitignore` para no subir contraseñas) y rellena tus variables:
   ```hcl
   # Contraseña para la base de datos (si aplica rds en pruebas)
   db_password = "TU_CONTRASEÑA_SUPER_SEGURA"
   
   # IDs de red reales de tu cuenta AWS
   vpc_id             = "vpc-0123456789abcdef0"
   public_subnet_ids  = ["subnet-xxxxxx", "subnet-yyyyyy"]
   private_subnet_ids = ["subnet-zzzzzz", "subnet-wwwwww"]
   ```
3. Inicializa y aplica el plan de Terraform:
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

### ⚠️ Intervención Manual Necesaria (Fuera de Terraform)
Aunque Terraform automatiza el core, los siguientes pasos requieren interacción manual o flujos externos por motivos de seguridad o verificación de dominios:
1. **SSM Parameter Store**: Debes crear el parámetro encriptado `profarmed-env` manualmente (Fase 2) y pegar tus variables reales.
2. **Certificados ACM y dominios**: La compra de dominios, la validación de DNS y la creación del certificado SSL en AWS Certificate Manager (ACM) se hacen en la consola web para validar la propiedad.
3. **CloudFront y CDN**: Las distribuciones de CloudFront se configuran apuntando a tus buckets y certificados.
4. **Launch Template y ASG**: Se configuran en la interfaz web de AWS para asignarles el script de *User Data* e Instance Profile creado por Terraform.

---

## ⚡ Fase 12: Memoria Swap de 1GB en EC2 (Prevenir OOM Crashes)

Las instancias `t3.micro` tienen únicamente 1GB de memoria RAM. Para evitar que el backend sufra caídas silenciosas por falta de memoria (**Out-of-Memory / SIGKILL**), es obligatorio configurar un espacio de intercambio (Swap) de 1GB en el host EC2:

```bash
# 1. Crear el archivo swap
sudo dd if=/dev/zero of=/swapfile bs=1M count=1024

# 2. Configurar permisos seguros
sudo chmod 600 /swapfile

# 3. Formatear como área swap
sudo mkswap /swapfile

# 4. Activar el swap
sudo swapon /swapfile

# 5. Hacerlo persistente tras reinicios
echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab

# 6. Verificar que está activo
free -h
```

---

## 🛠️ Centro de Control y Resolución de Problemas

* **Verificar Logs del Backend en EC2**:
  Si una instancia reporta problemas o da un error en el Load Balancer, entra a ella por SSH y ejecuta:
  ```bash
  docker ps -a               # Ver si el contenedor está en ejecución
  docker logs profarmed-backend-app  # Leer los logs en tiempo real de FastAPI/Nginx
  ```
* **Ver logs de inicialización del OS (User Data)**:
  Si el contenedor ni siquiera se levantó al arrancar la EC2, inspecciona el log del sistema:
  ```bash
  cat /var/log/cloud-init-output.log
  ```
* **Actualizaciones del archivo `.env`**:
  Si necesitas modificar una variable de entorno:
  1. Ve a **SSM Parameter Store** y edita `profarmed-env`.
  2. Ejecuta un **Instance Refresh** en el ASG para que las instancias se re-desplieguen y descarguen las credenciales actualizadas de forma limpia.

* **Ejecutar Scripts Administrativos dentro de Docker**:
  Si necesitas ejecutar utilidades o scripts administrativos (como la creación de administradores iniciales o el restablecimiento de contraseñas) desde la terminal del servidor:
  ```bash
  # 1. Crear los usuarios administradores iniciales en la base de datos de producción
  docker exec -it profarmed-backend-app python /app/create_initial_admins.py

  # 2. Reestablecer o cambiar contraseñas de usuarios administradores
  docker exec -it profarmed-backend-app python /app/reset_password.py
  ```