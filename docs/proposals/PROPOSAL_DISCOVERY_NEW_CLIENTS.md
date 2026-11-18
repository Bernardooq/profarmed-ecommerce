# 📘 Guía del Producto y Cuaderno de Descubrimiento Operativo
## Implementación SaaS B2B para Directores y Dueños: Demian & Héctor Soltero

> **Dirigido a:** Directores Generales, Dueños y Responsables Operativos de Distribuidoras Farmacéuticas.  
> **Propósito:** Mostrarles con total claridad qué hace nuestra plataforma base probada en producción (Profarmed/Profarmed), cómo resuelve el día a día de sus clientes y su equipo, y definir juntos cómo adaptaremos sus procesos únicos sin tecnicismos innecesarios.

---

# SECCIÓN I: MANUAL Y GUÍA DE LO QUE YA HACE LA PLATAFORMA

Esta es la solución que hoy ya opera en el mercado farmacéutico, diseñada para que vendas más, atiendas mejor y reduzcas errores humanos al levantar pedidos.

---

### 1.1 ¿Qué experimentan tus Clientes (Farmacias y Clínicas)?

Tus clientes farmacias ya no dependen de que un vendedor les conteste un WhatsApp a deshoras o les mande un PDF pesado y desactualizado. Tienen un portal y una app ágil en su celular o computadora:

1. **Catálogo con Información Farmacéutica Completa:**
   - Cada producto muestra su foto, nombre comercial, **sustancia activa (sal)**, laboratorio fabricante y código de barras.
   - **El gancho comercial:** La farmacia ve su **Precio Mayoreo** y el **Precio Sugerido al Público**, y la pantalla le calcula en automático su **Ganancia Estimada** (en pesos y porcentaje). La farmacia compra viendo cuánto dinero va a ganar.
   - **Listas de Precios Automáticas:** Cada cliente ve únicamente los precios o descuentos que tú le tienes asignados en tu sistema. Nadie ve precios de más ni de menos.
   - **Productos Similares / Sustitutos:** Si se te agota una marca, la plataforma le sugiere de inmediato medicamentos alternativos con la misma sal activa para que no pierdas la venta.

2. **Herramientas para Comprar en 2 Minutos:**
   - **Carrito que nunca se borra:** Si la farmacia mete 10 productos desde su celular y luego abre su computadora en el mostrador, sus productos siguen ahí.
   - **Subir pedido desde Excel:** Si el cliente ya tiene su lista de compras armada en Excel, la arrastra a la página y el carrito se llena en segundos.
   - **Listas de Favoritos (Reorden Semanal):** La farmacia puede guardar su "Cuadro Básico" y pedir exactamente lo mismo cada semana en dos clics.
   - **Múltiples Direcciones:** Si el cliente tiene 2 o 3 sucursales, elige a cuál quiere que le mandes la camioneta.

3. **Transparencia y Soporte:**
   - La farmacia ve en todo momento el avance de su pedido: `Pendiente` ➔ `Autorizado` ➔ `En Camino` ➔ `Entregado`.
   - Si tiene alguna duda o aclaración sobre facturación o faltantes, puede levantar un reporte formal con número de folio en el módulo de ayuda o presionar el botón de WhatsApp para contactar a su asesor comercial.

---

### 1.2 ¿Cómo opera tu Vendedor en Campo?

1. **Su Propia Cartera de Clientes:**
   - Cada vendedor tiene asignadas sus farmacias. Al entrar al sistema, **únicamente ve a sus clientes y sus pedidos**. No se cruza la información ni se comisionan clientes ajenos.
2. **Levantamiento de Pedidos en Mostrador (Venta Asistida):**
   - Cuando el vendedor visita la farmacia, saca su celular o tablet, selecciona a la farmacia en su pantalla y captura el pedido en vivo con los precios autorizados para ese cliente.
3. **Seguimiento de Ventas:**
   - Sabe exactamente qué pedidos ya fueron aprobados, cuáles van en camioneta y qué pedidos ya se cobraron o entregaron.

---

### 1.3 ¿Cómo opera tu Supervisor / Validador de Pedidos?

Es el filtro de control de tu empresa antes de comprometer mercancía o mandar a surtir:

1. **Bandeja Central de Pedidos:**
   - Todos los pedidos que levantan los vendedores en campo o que piden las farmacias directo en la madrugada caen a su pantalla en estado **`Pendiente de Validación`**.
2. **Auditoría Comercial y de Crédito:**
   - El supervisor revisa: ¿El cliente debe facturas? ¿Tiene crédito disponible? ¿Las cantidades pedidas son razonables?
   - Si un producto necesita cambiarse, el supervisor puede editar cantidades o cambiar partidas directamente en pantalla. Si una existencia cambió en bodega mientras revisaba, el sistema le avisa de inmediato para ajustar piezas sin sorpresas.
3. **Paso al Sistema y Facturación (Cero Tecleo Manual):**
   - Cuando todo está en orden, da clic en **Aprobar Pedido** y el sistema descarga automáticamente el archivo listo con el formato exacto que absorbe tu sistema administrativo (Alpha ERP). Se acabó pasar horas capturando a mano pedidos de WhatsApp o notas de papel.

---

### 1.4 ¿Cómo se Sincroniza el Inventario (El Caso Profarmed)?

- La tienda web se actualiza de forma automática cada 5 minutos con las existencias reales que tienes en tu sistema en bodega.
- **¿Qué pasa si quedan 3 piezas de un producto y dos clientes lo piden al mismo tiempo?**
  - En Profarmed, la regla operativa es: **"El primero que paga (o el primer pedido que el supervisor mete al sistema) se lo lleva"**.
  - A ambos clientes se les permite levantar el pedido para no frenar la venta en web. Cuando el supervisor autoriza el primero y lo mete a Alpha ERP, el inventario de Alpha se descuenta. En la siguiente actualización de 5 minutos, la web muestra stock en cero y al segundo cliente se le avisa que el producto se agotó para ofrecerle un sustituto o cancelarlo.

---

# SECCIÓN II: DISCOVERY Y ADAPTACIONES PARA CLIENTE 1 — DEMIAN (ALPHA ERP)

Demian cuenta con una operación compacta y muy clara de **~3 personas**:
- 1 Vendedor (atiende a sus farmacias).
- 1 Supervisor (revisa todos los pedidos de la empresa, los autoriza y los pasa a Alpha ERP).
- Almacenistas (hacen el surtido físico en bodega).

---

### 2.1 El Gran Cambio: De Hojas de Papel a Tablets en Bodega

Hoy en día, tu gente imprime los pedidos en hojas de papel y los almacenistas hacen una **doble revisión en papel** (uno surte y otro checa). La meta es **eliminar el gasto y desorden de papel** usando tablets económicas:

#### La Propuesta del Checklist Digital:
1. **Paso 1 (Surtido en Pasillos):** El Almacenista 1 abre la tablet en el carrito. La tablet le muestra la lista de medicamentos ordenada por su ubicación en bodega (Pasillo / Anaquel / Nivel) para que camine en una sola dirección. Conforme toma cada caja del anaquel, presiona `[✓]` en la pantalla.
2. **Paso 2 (Doble Verificación en Mesa de Empaque):** El carrito llega a la mesa de salida. El Almacenista 2 (o supervisor) toma la tablet, revisa el pedido físico contra la pantalla y da el visto bueno final antes de cerrar la caja y poner cinta.

#### Preguntas para Demian (Para diseñar tu pantalla de tablet):
1. **La Revisión Final:** En la mesa de empaque, ¿el segundo almacenista vuelve a contar pieza por pieza, o solo confirma el número de cajas cerradas y bultos grandes?
2. **Si falta producto en el anaquel:** Si el pedido pedía 10 cajas y físicamente solo encuentran 6 en bodega:
   - ¿El almacenista cambia el número a 6 en la tablet y el sistema ajusta la cuenta en automático?
   - ¿O prefieres que la tablet le avise al supervisor para que él autorice el cambio?
3. **Ubicación en Bodega:** En tu Alpha ERP, ¿tienen hoy capturado el número de pasillo o anaquel de cada producto en alguna casilla, o ese acomodo está en hojas de Excel o en la memoria de los muchachos?

---

### 2.2 Control de Existencias: ¿Esquema Profarmed o Apartado en Nube?

- En Profarmed los pedidos entran y el primero que paga se lo lleva al meter la orden a Alpha.
- **La pregunta para Demian:** ¿A ti te funciona este mismo esquema ágil, o prefieres que desarrollemos un **"Apartado Temporal"** en la nube? Es decir: que en cuanto un cliente confirme un pedido, esas piezas se "bloqueen" en la web para que nadie más las pueda pedir mientras tu supervisor revisa y mete la orden a Alpha ERP.

---

# SECCIÓN III: DISCOVERY Y ADAPTACIONES PARA CLIENTE 2 — HÉCTOR SOLTERO (ERP EN SQL SERVER)

Héctor cuenta con un sistema administrativo propio sobre SQL Server y tiene un ingeniero de sistemas en su equipo. 

---

### 3.1 Tu Preocupación Principal: ¿Qué pasa cuando se cae el WiFi en la Bodega?

Sabemos que en tu bodega **a veces se corta el internet o el WiFi falla**. Con nuestra arquitectura **no tienes nada de qué preocuparte**:
- Tu sistema interno de la oficina y bodega **sigue trabajando normal de forma local sin internet**; tus muchachos pueden seguir facturando, cobrando y surtiendo sin detenerse.
- Nosotros montamos un conector silencioso: en el momento exacto en que regresa el internet, el sistema solito y sin que nadie mueva un dedo envía los pedidos nuevos y actualiza las existencias en la tienda web. Cero riesgo de parar tu operación.

---

### 3.2 Módulos Comerciales Listos para Activar en tu Sandbox de AWS

Te montaremos un portal de pruebas (Sandbox) completamente aislado en la nube de Amazon (AWS) para que pruebes con tu equipo sin tocar tu base de datos de producción:
1. **Sección de Publicidad y Ofertas:**
   - **Stories estilo Instagram:** Círculos interactivos en la cabecera de la tienda para que presumas ofertas del día, lanzamientos de laboratorios o avisos urgentes a tus farmacias.
   - **Banners y Popups:** Avisos emergentes al ingresar a la tienda y cintillos de ofertas en la parte inferior.
   - **Ofertas por Cliente y por Producto:** Puedes ponerle precios especiales a un cliente consentido o rematar un lote específico con descuento abierto a todas las farmacias.

---

### 3.3 Lo que le pediremos a tu Ingeniero de Sistemas (Solo 3 cosas claras)

Héctor, no necesitas meterte en detalles técnicos. Solo pídele a tu ingeniero que tenga una llamada breve con nosotros o nos envíe estos 3 puntos de su base de datos:
1. **El Diagrama o Estructura de sus Tablas:** Cómo están organizados en su SQL los Artículos, los Lotes de medicamentos, sus Clientes, sus Listas de Precios y sus Pedidos.
2. **La Fórmula de tu Costo Promedio Ponderado:** Tu sistema calcula el precio base promediando compras anteriores para cuidar tu margen de ganancia. Necesitamos que tu ingeniero nos explique si ese costo ya está guardado en una casilla de su sistema, o si su sistema hace la cuenta matemática cada vez que alguien cotiza (y que nos pase esa fórmula/consulta).
3. **El Control de Lotes y Caducidades:** Cómo decide hoy su sistema qué lote sacar primero para asegurar que siempre salga el producto más próximo a vencer (primeras caducidades primero).
4. **Cómo prefiere recibir los pedidos:** Si prefiere que le mandemos los pedidos aprobados de la web a una tabla puente de entrada, o mediante una función automática de su sistema.
