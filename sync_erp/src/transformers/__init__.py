"""
Módulo de transformación y construcción de datos para la API de Profarmed.
"""

from .data_cleaning import (
    limpiar_texto,
    normalizar_texto,
    limpiar_nombre,
    limpiar_numero,
    limpiar_digitos,
    limpiar_lada,
    construir_telefono,
    crear_username
)

from .builders import (
    build_producto_dict,
    build_categoria_dict,
    build_vendedor_dict,
    build_cliente_dict,
    build_lista_precios_dict,
    build_item_lista_dict,
    build_cotiza3_rows,
)

__all__ = [
    'limpiar_texto',
    'normalizar_texto',
    'limpiar_nombre',
    'limpiar_numero',
    'limpiar_digitos',
    'limpiar_lada',
    'construir_telefono',
    'crear_username',
    'build_producto_dict',
    'build_categoria_dict',
    'build_vendedor_dict',
    'build_cliente_dict',
    'build_lista_precios_dict',
    'build_item_lista_dict',
    'build_cotiza3_rows',
]

