import { useState } from 'react';

export const ALL_COLUMNS = [
  { id: 'img', label: 'Imagen / Miniatura', defaultVisible: true, required: false },
  { id: 'codebar', label: 'Código de Barras EAN', defaultVisible: true, required: false },
  { id: 'name', label: 'Nombre del Producto', defaultVisible: true, required: true },
  { id: 'category', label: 'Categoría', defaultVisible: true, required: false },
  { id: 'unit', label: 'Unidad de Medida', defaultVisible: false, required: false },
  { id: 'stock', label: 'Stock Disponible', defaultVisible: true, required: false },
  { id: 'price', label: 'Precio Unitario', defaultVisible: true, required: false },
  { id: 'description', label: 'Descripción / Fórmula / Detalle', defaultVisible: false, required: false },
  { id: 'actions', label: 'Acción (Cantidad / Agregar)', defaultVisible: true, required: true }
];

const DEFAULT_COLUMNS = ALL_COLUMNS.filter(col => col.defaultVisible).map(col => col.id);

export function useCatalogSettings() {
  const [viewMode, setViewModeState] = useState(() => {
    return localStorage.getItem('catalog_view_mode') || 'ecommerce';
  });

  const [visibleColumns, setVisibleColumnsState] = useState(() => {
    try {
      const saved = localStorage.getItem('pos_catalog_columns');
      return saved ? JSON.parse(saved) : DEFAULT_COLUMNS;
    } catch {
      return DEFAULT_COLUMNS;
    }
  });

  const setViewMode = (mode) => {
    setViewModeState(mode);
    localStorage.setItem('catalog_view_mode', mode);
  };

  const setVisibleColumns = (columns) => {
    setVisibleColumnsState(columns);
    localStorage.setItem('pos_catalog_columns', JSON.stringify(columns));
  };

  const toggleColumn = (columnId) => {
    const colObj = ALL_COLUMNS.find(c => c.id === columnId);
    if (colObj?.required) return; // Obligatoria, no se puede desmarcar

    if (visibleColumns.includes(columnId)) {
      setVisibleColumns(visibleColumns.filter(id => id !== columnId));
    } else {
      setVisibleColumns([...visibleColumns, columnId]);
    }
  };

  const resetColumns = () => {
    setVisibleColumns(DEFAULT_COLUMNS);
  };

  const isColumnVisible = (columnId) => visibleColumns.includes(columnId);

  return {
    viewMode,
    setViewMode,
    visibleColumns,
    setVisibleColumns,
    toggleColumn,
    resetColumns,
    isColumnVisible,
    allColumns: ALL_COLUMNS
  };
}
