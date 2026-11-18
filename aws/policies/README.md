# AWS IAM & Security Policies (Plantillas Genéricas)

Esta carpeta contiene las políticas de seguridad en formato JSON nativo de AWS, organizadas por actor/recurso y estandarizadas para coincidir 1:1 con la arquitectura definida en [infra-stack.yaml](../cloudformation/infra-stack.yaml).

---

## Índice de Políticas

| Archivo | Asignado A | Propósito |
| :--- | :--- | :--- |
| [ec2-ssm-policy.json](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/aws/policies/ec2-ssm-policy.json) | **EC2 Role** (`ecommerce-${PROJECT_NAME}-ec2-role`) | Permite a la instancia EC2 descargar y descifrar de forma segura las variables de entorno `.env` desde SSM Parameter Store. |
| [ec2-ecr-policy.json](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/aws/policies/ec2-ecr-policy.json) | **EC2 Role** (`ecommerce-${PROJECT_NAME}-ec2-role`) | Permite a la instancia EC2 autenticarse en Amazon ECR y descargar (`docker pull`) la imagen Docker de backend. |
| [ec2-s3-policy.json](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/aws/policies/ec2-s3-policy.json) | **EC2 Role** (`ecommerce-${PROJECT_NAME}-ec2-role`) | Permite a la aplicación backend leer/escribir/borrar objetos en los buckets de Imágenes, Promociones y Documentos sin credenciales estáticas en el código. |
| [github-actions-deployer-policy.json](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/aws/policies/github-actions-deployer-policy.json) | **CI/CD User** (`github-actions-${PROJECT_NAME}-deployer`) | Política de mínimo privilegio para GitHub Actions: push a ECR, refresh de instancias en el Auto Scaling Group, sincronización de Frontend a S3 e invalidación de caché en CloudFront. |
| [s3-bucket-oac-policy.json](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/aws/policies/s3-bucket-oac-policy.json) | **S3 Bucket Policies** (Frontend, Imgs, Promos) | Restringe el acceso a los buckets S3 para que únicamente el servicio de CloudFront con OAC (Origin Access Control) pueda leer su contenido. |

---

## Variables Parametrizadas en los JSONs

* `${PROJECT_NAME}`: Prefijo del proyecto (ej. `profarmed`, `profarmed`, `profarmed`).
* `${AWS_REGION}`: Región de AWS (ej. `us-east-1`).
* `${AWS_ACCOUNT_ID}`: ID de la cuenta de AWS de 12 dígitos.
* `${FRONTEND_BUCKET_NAME}`: Nombre del bucket de Frontend React.
* `${IMGS_BUCKET_NAME}`: Nombre del bucket de imágenes de productos.
* `${PROMOS_BUCKET_NAME}`: Nombre del bucket de promociones.
* `${DOCS_BUCKET_NAME}`: Nombre del bucket privado de documentos.
* `${FRONTEND_CLOUDFRONT_DISTRIBUTION_ID}`: ID de la distribución de CloudFront del Frontend.
