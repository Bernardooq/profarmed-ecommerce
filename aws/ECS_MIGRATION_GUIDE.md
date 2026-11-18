# 🚀 Guía de Migración CI/CD: De EC2 Instance Refresh a Amazon ECS

Este documento detalla el procedimiento exacto para migrar tus workflows de GitHub Actions (`.github/workflows/deploy-backend.yml`) de la arquitectura tradicional basada en **EC2 Instance Refresh** hacia **Amazon ECS (EC2 Launch Type)**.

> 💡 **Nota:** Esta guía está preparada para ejecutarse en el momento en que decidas hacer el switch a ECS. Tu infraestructura aprovisionada por CloudFormation ya cuenta con el cluster ECS, la Task Definition y el Service listos.

---

## 🎯 ¿Por qué este cambio?

| Métrica / Flujo | Flujo Anterior (Auto Scaling Instance Refresh) | Nuevo Flujo (Amazon ECS Rolling Update) |
| :--- | :--- | :--- |
| **Tiempo de Despliegue** | 4 a 6 minutos por instancia | **15 a 35 segundos** |
| **Impacto en EC2** | Destruye y recrea la máquina virtual | **Mantiene la VM viva**, solo reemplaza el contenedor |
| **Aislamiento de RAM** | Riesgo de OOM / congelamiento de SO | Cgroups a nivel kernel (límite estricto 768 MB) |
| **Verificación de Salud** | Espera al health check del ALB en frío | Drain progresivo y switch atómico vía Target Group |

---

## 📝 Paso 1: Variables y Secretos en GitHub Actions

Asegúrate de tener definidas las siguientes variables en tu repositorio (Settings -> Secrets and variables -> Actions):

- `AWS_REGION`: `us-east-1`
- `ECS_CLUSTER_NAME`: `${ProjectName}-cluster` (ej. `profarmed-cluster` o `profarmed-cluster`)
- `ECS_SERVICE_NAME`: `${ProjectName}-backend-service` (ej. `profarmed-backend-service` o `profarmed-backend-service`)

*(Alternativamente, puedes hardcodear los nombres directamente en el archivo `.yml`).*

---

## 🛠️ Paso 2: Actualización de `.github/workflows/deploy-backend.yml`

En tu workflow actual de backend, localiza el paso final de despliegue donde se llama a `aws autoscaling start-instance-refresh`:

### ❌ Código Anterior (Instance Refresh):
```yaml
      - name: Trigger Auto Scaling Instance Refresh
        run: |
          aws autoscaling cancel-instance-refresh --auto-scaling-group-name ProfarmedAGGroup || true
          aws autoscaling start-instance-refresh \
            --auto-scaling-group-name ProfarmedAGGroup \
            --preferences '{"MinHealthyPercentage": 50, "InstanceWarmup": 90}'
          echo "✅ Instance Refresh iniciado exitosamente. AWS reemplazará las instancias de forma soft."
```

### ✅ Código Nuevo (ECS Rolling Update con Zero Downtime):
```yaml
      - name: Deploy to Amazon ECS Service
        run: |
          echo "🚀 Forzando nuevo despliegue en ECS Service..."
          aws ecs update-service \
            --cluster profarmed-cluster \
            --service profarmed-backend-service \
            --force-new-deployment \
            --region us-east-1

          echo "⏳ Esperando a que el nuevo contenedor esté Healthy en el ALB..."
          aws ecs wait services-stable \
            --cluster profarmed-cluster \
            --services profarmed-backend-service \
            --region us-east-1

          echo "✅ Despliegue completado exitosamente en Amazon ECS con Zero Downtime."
```

---

## 🔐 Paso 3: Permisos IAM del Deployer

El usuario de despliegue (`github-actions-${ProjectName}-deployer`) ya tiene aprovisionados en CloudFormation los permisos necesarios:
- `ecs:UpdateService`
- `ecs:DescribeServices`
- `ecr:*` (para empujar imágenes)

No requieres crear roles adicionales en AWS IAM.

---

## 🔄 Rollback Inmediato (En caso de emergencia)

Si una versión nueva del contenedor falla al arrancar (ej. error de sintaxis en FastAPI):
1. ECS detectará que el health check del Load Balancer falla.
2. **ECS no apagará el contenedor anterior**, protegiendo tu producción contra caídas.
3. Puedes hacer rollback manual en un solo comando:
   ```bash
   aws ecs update-service --cluster profarmed-cluster --service profarmed-backend-service --task-definition <task-definition-anterior>
   ```

