# Imágenes Pendientes — Página de Inicio (Profarmed)

Este documento lista las imágenes pendientes por sección para completar la página de **Inicio** (`Home.jsx`), configuradas desde `react/src/config/content.json`.

---

## 1. Hero Principal (`Hero.jsx`)
- **Estado:** Usando imagen por defecto actual (`react/src/images/inicio.webp`).
- **Pendiente:** Fotografía o banner definitivo de portada para reemplazar `inicio.webp`.

## 2. Sección "Tus aliados en distribución" (`inicio.allies.imageUrl`)
- **Ubicación en `content.json`:** `inicio.allies.imageUrl`
- **Pendiente:** SVG / fotografía del repartidor/aliado dando la mano con caja Profarmed (actualmente muestra un contenedor reservado pendiente).

## 3. Sección "+150 socios comerciales" (`Labs.jsx`)
- **Estado:** Usando los 25 logotipos actuales en `react/src/images/labs/*.webp` dentro del carrusel 2x5.
- **Opcional:** Si se desean agregar o reemplazar logotipos de laboratorios específicos, colocarlos en `react/src/images/labs/`.

## 4. Sección "+500 clientes satisfechos" (`inicio.reviews.items[].avatarUrl`)
- **Ubicación en `content.json`:**
  - `inicio.reviews.items[0].avatarUrl` — **Karla Montes**
  - `inicio.reviews.items[1].avatarUrl` — **Lulu Díaz**
  - `inicio.reviews.items[2].avatarUrl` — **Héctor Bracamontes**
- **Pendiente:** Fotografías circulares de cada cliente para las reseñas (actualmente muestran círculos placeholder en `#211f42`).

---

> **Nota:** Los íconos de soluciones (`Recibe hoy mismo.png`, `Trato con gente íntegra.png`, `Calidad de productos.png`), píldora de barra de confianza (`Palmita.png`), marca de agua (`pildora veloz marca de agua.png`), redes sociales (`Facebook.png`, `Instagram.png`, `Whatsapp.png`), logotipo y favicon ya fueron integrados en `react/public/images/brand/` y `react/public/images/logo.png`.
