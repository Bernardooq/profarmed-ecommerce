/**
 * ExcelImportGuideContent.jsx
 * ===========================
 * Documentación visual compartida de los dos formatos aceptados
 * para la importación de pedidos desde Excel.
 */

export const EXCEL_IMPORT_GUIDE_ITEMS = [
  'Formato: El archivo debe ser .xlsx o .xls.',
  'Opción 1 (Rápido): Solo dos columnas: Código de Barras (Columna A) y Cantidad (Columna B). El encabezado no es obligatorio.',
  "Opción 2 (Catálogo descargado): Descarga tu catálogo desde Productos, escribe las cantidades en la columna 'Pedido' y sube ese mismo archivo. Las filas vacías se omitirán automáticamente.",
  'Validación: El sistema verificará automáticamente el stock y si el producto está activo.',
];

export function ExcelImportGuideTables() {
  return (
    <div className="mt-2">
      <p className="mb-2"><strong>Opción 1 — Formato rápido (2 columnas):</strong></p>
      <table className="excel-simulator">
        <thead>
          <tr>
            <th></th>
            <th>A</th>
            <th>B</th>
          </tr>
        </thead>
        <tbody>
          <tr className="excel-simulator__header-row">
            <td className="excel-simulator__col-header">1</td>
            <td>Codigo Barras</td>
            <td>Cantidad</td>
          </tr>
          <tr>
            <td className="excel-simulator__col-header">2</td>
            <td>75010011</td>
            <td>12</td>
          </tr>
          <tr>
            <td className="excel-simulator__col-header">3</td>
            <td>75010022</td>
            <td>5</td>
          </tr>
          <tr>
            <td className="excel-simulator__col-header">4</td>
            <td>75010033</td>
            <td>24</td>
          </tr>
          <tr>
            <td className="excel-simulator__col-header">...</td>
            <td className="text-center">...</td>
            <td className="text-center">...</td>
          </tr>
        </tbody>
      </table>

      <p className="mt-4 mb-2"><strong>Opción 2 — Catálogo descargado:</strong></p>
      <table className="excel-simulator">
        <thead>
          <tr>
            <th></th>
            <th>Código Barras</th>
            <th>...</th>
            <th>Pedido</th>
          </tr>
        </thead>
        <tbody>
          <tr className="excel-simulator__header-row">
            <td className="excel-simulator__col-header">1</td>
            <td>Código Barras</td>
            <td>...</td>
            <td>Pedido</td>
          </tr>
          <tr>
            <td className="excel-simulator__col-header">2</td>
            <td>75010011</td>
            <td>...</td>
            <td>12</td>
          </tr>
          <tr>
            <td className="excel-simulator__col-header">3</td>
            <td>75010022</td>
            <td>...</td>
            <td></td>
          </tr>
          <tr>
            <td className="excel-simulator__col-header">4</td>
            <td>75010033</td>
            <td>...</td>
            <td>24</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
