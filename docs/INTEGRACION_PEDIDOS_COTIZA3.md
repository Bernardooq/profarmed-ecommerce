# 📦 Guía de Integración de Pedidos E-Commerce a SQL Server 2000 (`dbo.cotiza3`)

> **Proyecto:** Profarmed / Profarmed B2B E-Commerce  
> **Base de Datos Destino:** Microsoft SQL Server 2000 SP4 (`gdmi.ddns.net:1433`, BD: `angeles`)  
> **Tabla Destino:** `dbo.cotiza3`  
> **Propósito:** Documentar la arquitectura, mapeo de campos, reglas de cálculo y acuerdos técnicos para insertar pedidos generados en el E-Commerce hacia el ERP local.

---

## 1. 🏛️ Arquitectura General y Separación de Canales

El ERP local utiliza un esquema de tablas separadas según el origen de la venta:

| Tabla ERP | Canal de Venta | Descripción / Uso |
| :--- | :--- | :--- |
| **`dbo.cotiza`** | Mostrador Físico / POS | Histórico general de cotizaciones y tickets generados en sucursal (+3.5 millones de filas). |
| **`dbo.cotiza2`** | App Móvil de Preventa | Utilizada por la aplicación interna de los preventistas para enviar pedidos a almacén. |
| **`dbo.cotiza3`** | **E-Commerce B2B (Nosotros)** | **Canal exclusivo y aislado para las órdenes de la tienda en línea.** |

### Flujo Próximo de Ingesta (Roadmap con SQS / Lambda):
```
[Cliente B2B en Tienda Web] 
       │
       ▼
[Checkout E-Commerce API] 
       │
       ▼
[Evento / Mensaje SQS o Webhook] 
       │
       ▼
[Lambda / Worker Ingestor] 
       │  (Inserta filas con DONE = 0 y precios sin IVA)
       ▼
[dbo.cotiza3 en SQL Server 2000]
       │
       ▼
[Trigger / Proceso del ERP de Héctor]
       │  (Jala las órdenes, genera ticket/remisión/factura y pasa a pedidos internos)
       ▼
[Almacén / Surtido Local]
```

---

## 2. 💰 Reglas de Oro de Precios e Impuestos (Confirmado en BD)

1. **Los precios ingresan 100% SIN IVA:**
   * Al auditar `dbo.cotiza2`, se comprobó que tanto productos exentos (`EXIVA = 1`) como productos gravados (`EXIVA = 0`, IVA al 16%) ingresan con su **precio de lista neto antes de impuestos**.
   * `PRECIO`: Precio unitario antes de IVA (`order_item.price_without_iva`).
   * `DESCUEN`: Porcentaje de descuento comercial aplicado a la línea (`0.00` si no aplica).
   * `NETO`: Subtotal de la línea antes de IVA:
     $$\text{NETO} = \text{CANTIDAD} \times \text{PRECIO} \times \left(1 - \frac{\text{DESCUEN}}{100}\right)$$
   * El cálculo del IVA y su desglose fiscal se realiza en el ERP local al momento del timbrado/facturación en `dbo.facturas`.

2. **Folio de Orden (`NUMERO`):**
   * Se utiliza directamente el **`order_id` del E-Commerce** (ejemplo: `10521`).
   * **Ventajas:** Cero colisiones de concurrencia y trazabilidad inmediata 1 a 1 entre el panel web del cliente y la pantalla del almacenista.

3. **Bandera de Formato (`V2`):**
   * Se asigna siempre **`V2 = 1`**.
   * Representa "Versión 2" (el layout extendido que soporta lotes y fechas de vencimiento). Garantiza que el código/trigger del ERP procese el registro sin fallas de compatibilidad.

4. **Estado de Procesamiento (`DONE`):**
   * Se inserta con **`DONE = 0`**.
   * Indica al ERP que es un pedido nuevo pendiente de surtido/revisión. Cuando el ERP local lo jala o procesa, su sistema actualiza este estado.

---

## 3. 📋 Mapeo Completo de Campos en `dbo.cotiza3` (25 Columnas)

Cada fila en `dbo.cotiza3` representa un **renglón (item)** del pedido:

| # | Columna | Tipo de Dato | Origen / Valor asignado | Descripción / Ejemplo |
| :-: | :--- | :--- | :--- | :--- |
| **1** | `TIENDA` | `numeric(18,0)` | **`1`** (Fijo) | Sucursal / Bodega principal. |
| **2** | `NUMERO` | `numeric(18,0)` | `order.order_id` | ID del pedido en el E-Commerce (ej. `10521`). Todos los renglones de una misma orden comparten este número. |
| **3** | `BARCODE` | `char(100)` | `item.product_id` | Código maestro del producto (ej. `'VALPROATO DE MG-T/40'`). |
| **4** | `CANTIDAD` | `numeric(18,2)` | `item.quantity` | Unidades solicitadas (ej. `10.00`). |
| **5** | `PRECIO` | `numeric(18,2)` | `item.price_without_iva` | Precio unitario de lista **sin IVA** (ej. `45.92`). |
| **6** | `DESCUEN` | `numeric(18,2)` | `item.discount_pct` | Porcentaje de descuento aplicado (ej. `0.00` o `5.00`). |
| **7** | `DESCRI` | `char(100)` | `Product.name` | Nombre del producto (hasta 100 caracteres). |
| **8** | `NETO` | `numeric(18,2)` | Subtotal línea | $\text{CANTIDAD} \times \text{PRECIO} \times (1 - \text{DESCUEN}/100)$ (ej. `459.20`). |
| **9** | `CLIENTE` | `char(8)` | `NULL` | No se usa en preventa (el cliente se guarda en `SOCIO`). |
| **10** | `CAJERO` | `numeric(18,0)` | **`1`** (Fijo) | Identificador de cajero default. |
| **11** | `VENDEDOR` | `numeric(18,0)` | `Customer.agent_id` o `NULL` | ID del agente asignado al cliente en `dbo.empleado` (`NUMERO`). |
| **12** | `FECHA` | `datetime` | `order.created_at` | Fecha y hora local de creación del pedido. |
| **13** | `CAJA` | `numeric(18,0)` | **`1`** (Fijo) | Número de caja default. |
| **14** | `CORTE` | `numeric(18,0)` | `NULL` | No aplica para pedidos pendientes. |
| **15** | `EMPLEADO` | `numeric(18,0)` | `NULL` | No aplica. |
| **16** | `SOCIO` | `numeric(18,0)` | `order.customer_id` | ID del cliente en `dbo.socios` (`NUMERO`, ej. `104`). |
| **17** | `COSTO` | `numeric(18,2)` | `0.00` | Costo base (en cotizaciones entra en 0.00). |
| **18** | `COBRADA` | `numeric(18,0)` | `NULL` | Se llena en el ERP al cobrar. |
| **19** | `LOTE` | `char(100)` | **`'-'`** (Fijo) | Marcador de lote por defecto. |
| **20** | `caduca` | `datetime` | **`'2030-01-01'`** (Fijo) | Fecha dummy de vencimiento que espera el layout V2. |
| **21** | `V2` | `numeric(18,0)` | **`1`** (Fijo) | Bandera que confirma layout Versión 2. |
| **22** | `DONE` | `numeric(18,0)` | **`0`** (Fijo) | Estado: **0 = Pendiente de procesar/jalar**. |
| **23** | `TICKET` | `numeric(18,0)` | `NULL` | Se asigna cuando el ERP genera el ticket definitivo. |
| **24** | `REVISADO` | `numeric(18,0)` | `NULL` | Control de auditoría de almacén. |
| **25** | `barras` | `char(120)` | `NULL` | Opcional (código de barras alterno). |

---

## 4. 💻 Ejemplo de Sentencia SQL de Inserción

Para un pedido con ID `#10521` del cliente con código de socio `104` que compró 2 productos:

```sql
INSERT INTO dbo.cotiza3 (
    TIENDA, NUMERO, BARCODE, CANTIDAD, PRECIO, DESCUEN, DESCRI, NETO,
    CLIENTE, CAJERO, VENDEDOR, FECHA, CAJA, CORTE, EMPLEADO,
    SOCIO, COSTO, COBRADA, LOTE, caduca, V2, DONE, TICKET, REVISADO, barras
) VALUES (
    1,                                                           -- TIENDA
    10521,                                                       -- NUMERO (order_id e-commerce)
    'VALPROATO DE MG-T/40',                                      -- BARCODE
    10.00,                                                       -- CANTIDAD
    45.92,                                                       -- PRECIO (Sin IVA)
    0.00,                                                        -- DESCUEN
    'VALPROATO DE MG. GI PSICOFARMA TABS. 200 MG. C/40',        -- DESCRI
    459.20,                                                      -- NETO
    NULL,                                                        -- CLIENTE
    1,                                                           -- CAJERO
    3,                                                           -- VENDEDOR (Agente Héctor Soltero)
    GETDATE(),                                                   -- FECHA
    1,                                                           -- CAJA
    NULL,                                                        -- CORTE
    NULL,                                                        -- EMPLEADO
    104,                                                         -- SOCIO (Cliente ID)
    0.00,                                                        -- COSTO
    NULL,                                                        -- COBRADA
    '-',                                                         -- LOTE
    '2030-01-01 00:00:00',                                       -- caduca
    1,                                                           -- V2
    0,                                                           -- DONE (Pendiente)
    NULL,                                                        -- TICKET
    NULL,                                                        -- REVISADO
    NULL                                                         -- barras
),
(
    1,
    10521,
    'ARGLIPTIN D-T/28',
    5.00,
    167.19,
    0.00,
    'SITAGLIPTINA/METFORMINA TABS. 50/850 MG. C/28',
    835.95,
    NULL,
    1,
    3,
    GETDATE(),
    1,
    NULL,
    NULL,
    104,
    0.00,
    NULL,
    '-',
    '2030-01-01 00:00:00',
    1,
    0,
    NULL,
    NULL,
    NULL
);
```

---

## 5. 🤝 Puntos Clave para la Coordinación con Héctor y su Ingeniero ERP

1. **Idempotencia y Re-sincronización (Upsert por `NUMERO` y `BARCODE`):**  
   El script `sync_erp/src/uploader/sync_orders.py` descarga pedidos con `is_synced = false` y reconcilia atómicamente sus renglones en `dbo.cotiza3` dentro de una transacción (`BEGIN TRAN ... COMMIT`):
   - **Pedido nuevo:** Inserta todos los renglones con `DONE = 0`.
   - **Pedido modificado en E-Commerce (`is_synced` restablecido a `false`):** Compara las partidas actuales contra `SELECT RTRIM(LTRIM(BARCODE)) FROM dbo.cotiza3 WHERE NUMERO = @order_id`:
     - **Artículos editados:** `UPDATE` de `CANTIDAD`, `PRECIO`, `DESCRI`, `NETO`, `VENDEDOR`, `SOCIO`, `FECHA` y restablece `DONE = 0`.
     - **Artículos agregados:** `INSERT` de los nuevos renglones con `DONE = 0`.
     - **Artículos eliminados:** `DELETE` de los renglones que ya no existen en el pedido.
   - Una vez confirmado el `COMMIT` en SQL Server, marca el pedido como `is_synced = true` vía `PATCH /sync-upload/orders/{order_id}/sync`.
2. **Lectura del Trigger:**  
   El ingeniero del ERP solo necesita programar un lector o trigger sobre `dbo.cotiza3` con la misma lógica que ya tienen para `dbo.cotiza2` (`WHERE DONE = 0`).
3. **Actualización de Estado:**  
   Una vez que el ERP procese el pedido a su tabla interna, puede marcar `DONE = 1` o moverlo a su histórico `dbo.cotiza`, dejando libre `dbo.cotiza3`.

