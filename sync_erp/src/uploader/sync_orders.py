"""
Pipeline de Sincronización ERP: PEDIDOS E-Commerce -> dbo.cotiza3 (SQL Server 2000).

Descarga los pedidos con `is_synced = false` desde el backend y realiza un
UPSERT / reconciliación atómica por (NUMERO, BARCODE) en `dbo.cotiza3`:
- Inserta artículos nuevos agregados al pedido.
- Actualiza artículos existentes que fueron editados (cantidad, precio, vendedor, etc.) y restablece DONE = 0.
- Elimina artículos que fueron removidos del pedido en el E-Commerce.
- Al concluir el COMMIT en SQL Server, marca el pedido como `is_synced = true` vía PATCH.
"""

from datetime import datetime
import sys
from pathlib import Path

# Permitir ejecución directa como script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.database import get_erp_transaction, adapt_sql_placeholders
from src.transformers import build_cotiza3_rows
from src.uploader.api_client import (
    login,
    fetch_unsynced_orders,
    fetch_order_details,
    mark_order_synced,
)


INSERT_COTIZA3_SQL = """
INSERT INTO dbo.cotiza3 (
    TIENDA, NUMERO, BARCODE, CANTIDAD, PRECIO, DESCUEN, DESCRI, NETO,
    CLIENTE, CAJERO, VENDEDOR, FECHA, CAJA, CORTE, EMPLEADO,
    SOCIO, COSTO, COBRADA, LOTE, caduca, V2, DONE, TICKET, REVISADO, barras
) VALUES (
    ?, ?, ?, ?, ?, ?, ?, ?,
    NULL, ?, ?, ?, ?, NULL, NULL,
    ?, ?, NULL, ?, ?, ?, ?, NULL, NULL, ?
)
"""

UPDATE_COTIZA3_SQL = """
UPDATE dbo.cotiza3
SET TIENDA = ?,
    CANTIDAD = ?,
    PRECIO = ?,
    DESCUEN = ?,
    DESCRI = ?,
    NETO = ?,
    VENDEDOR = ?,
    FECHA = ?,
    SOCIO = ?,
    COSTO = ?,
    LOTE = ?,
    caduca = ?,
    V2 = ?,
    DONE = ?,
    barras = ?
WHERE NUMERO = ?
  AND RTRIM(LTRIM(BARCODE)) = ?
"""


def _row_to_barcode_count(row) -> tuple:
    """Extrae (barcode, count) de una fila devuelta por pyodbc (tupla) o pymssql (dict)."""
    if isinstance(row, dict):
        barcode = (row.get("barcode") or row.get("BARCODE") or "").strip()
        count = int(row.get("row_count") or row.get("ROW_COUNT") or 0)
        return barcode, count
    barcode = str(row[0] or "").strip()
    count = int(row[1] or 0)
    return barcode, count


def _insert_params(row: dict) -> tuple:
    return (
        row["TIENDA"],
        row["NUMERO"],
        row["BARCODE"],
        row["CANTIDAD"],
        row["PRECIO"],
        row["DESCUEN"],
        row["DESCRI"],
        row["NETO"],
        row["CAJERO"],
        row["VENDEDOR"],
        row["FECHA"],
        row["CAJA"],
        row["SOCIO"],
        row["COSTO"],
        row["LOTE"],
        row["CADUCA"],
        row["V2"],
        row["DONE"],
        row["BARRAS"],
    )


def _update_params(row: dict) -> tuple:
    return (
        row["TIENDA"],
        row["CANTIDAD"],
        row["PRECIO"],
        row["DESCUEN"],
        row["DESCRI"],
        row["NETO"],
        row["VENDEDOR"],
        row["FECHA"],
        row["SOCIO"],
        row["COSTO"],
        row["LOTE"],
        row["CADUCA"],
        row["V2"],
        row["DONE"],
        row["BARRAS"],
        row["NUMERO"],
        row["BARCODE"],
    )


def upsert_order_to_cotiza3(order_id: int, rows: list, is_cancelled: bool = False) -> dict:
    """
    Reconcilia atómicamente los renglones de un pedido en `dbo.cotiza3` para `NUMERO = order_id`.
    Soporta pedidos nuevos, re-sincronización por edición (alta/edición/eliminación de partidas)
    y limpieza de renglones pendientes en pedidos cancelados.
    """
    inserted = 0
    updated = 0
    deleted = 0

    with get_erp_transaction() as (_, cursor, paramstyle):
        if is_cancelled:
            sql_del_cancelled = adapt_sql_placeholders(
                "DELETE FROM dbo.cotiza3 WHERE NUMERO = ? AND (DONE IS NULL OR DONE = 0)",
                paramstyle,
            )
            cursor.execute(sql_del_cancelled, (order_id,))
            deleted = max(0, cursor.rowcount or 0)
            return {"inserted": 0, "updated": 0, "deleted": deleted}

        sql_existing = adapt_sql_placeholders(
            "SELECT RTRIM(LTRIM(BARCODE)) AS barcode, COUNT(*) AS row_count "
            "FROM dbo.cotiza3 WHERE NUMERO = ? GROUP BY RTRIM(LTRIM(BARCODE))",
            paramstyle,
        )
        cursor.execute(sql_existing, (order_id,))
        existing_counts = {}
        for db_row in cursor.fetchall():
            bc, cnt = _row_to_barcode_count(db_row)
            if bc:
                existing_counts[bc] = cnt

        incoming_map = {r["BARCODE"]: r for r in rows}

        sql_delete_item = adapt_sql_placeholders(
            "DELETE FROM dbo.cotiza3 WHERE NUMERO = ? AND RTRIM(LTRIM(BARCODE)) = ?",
            paramstyle,
        )
        sql_update_item = adapt_sql_placeholders(UPDATE_COTIZA3_SQL, paramstyle)
        sql_insert_item = adapt_sql_placeholders(INSERT_COTIZA3_SQL, paramstyle)

        # 1. Eliminar partidas que ya no están en el pedido del E-Commerce
        for old_barcode, old_cnt in existing_counts.items():
            if old_barcode not in incoming_map:
                cursor.execute(sql_delete_item, (order_id, old_barcode))
                deleted += old_cnt

        # 2. Actualizar partidas existentes o insertar las nuevas
        for barcode, row in incoming_map.items():
            if barcode in existing_counts:
                if existing_counts[barcode] == 1:
                    cursor.execute(sql_update_item, _update_params(row))
                    updated += 1
                else:
                    # Si hubiera filas duplicadas previas del mismo artículo, consolidar a 1 sola fila
                    cursor.execute(sql_delete_item, (order_id, barcode))
                    deleted += existing_counts[barcode]
                    cursor.execute(sql_insert_item, _insert_params(row))
                    inserted += 1
            else:
                cursor.execute(sql_insert_item, _insert_params(row))
                inserted += 1

    return {"inserted": inserted, "updated": updated, "deleted": deleted}


def run_orders_sync(token: str) -> int:
    """Descarga pedidos con is_synced=false, los upsertea en dbo.cotiza3 y los marca sincronizados."""
    print("\n--- PULL & UPSERT DE PEDIDOS PENDIENTES -> dbo.cotiza3 ---")
    pending_orders = fetch_unsynced_orders(token)
    if not pending_orders:
        print("  Sin pedidos pendientes por sincronizar (is_synced=false).")
        return 0

    print(f"  Pedidos pendientes encontrados: {len(pending_orders)}")
    failed = 0

    for summary in pending_orders:
        order_id = summary.get("order_id")
        if not order_id:
            continue

        try:
            order = fetch_order_details(order_id, token)
            status_val = str(order.get("status") or "").lower()
            is_cancelled = status_val == "cancelled"

            if is_cancelled:
                stats = upsert_order_to_cotiza3(order_id, [], is_cancelled=True)
                mark_order_synced(order_id, token, True)
                print(
                    f"  [OK] Pedido #{order_id} (cancelado): "
                    f"eliminados_pendientes={stats['deleted']} -> marcado is_synced=true"
                )
                continue

            rows = build_cotiza3_rows(order)
            if not rows:
                print(f"  [!] Pedido #{order_id} sin partidas válidas; se omite para revisión manual.")
                continue

            stats = upsert_order_to_cotiza3(order_id, rows, is_cancelled=False)
            mark_order_synced(order_id, token, True)
            print(
                f"  [OK] Pedido #{order_id} -> dbo.cotiza3 "
                f"(insertados={stats['inserted']}, actualizados={stats['updated']}, "
                f"eliminados={stats['deleted']}) -> marcado is_synced=true"
            )
        except Exception as e:
            failed += 1
            print(f"  [ERROR] Falló sincronización del pedido #{order_id}: {e}")

    return failed


def main():
    start = datetime.now()
    print("=" * 60)
    print(f"INICIANDO SINCRONIZACIÓN DE PEDIDOS -> dbo.cotiza3: {start}")
    print("=" * 60)

    token = login()
    if not token:
        print("[CRITICAL] Abortando por fallo de autenticación.")
        sys.exit(1)

    try:
        failed = run_orders_sync(token)
    except Exception as e:
        print(f"\n[CRITICAL FAILURE]: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    end = datetime.now()
    duration = (end - start).total_seconds()
    print("=" * 60)
    if failed:
        print(f"PROCESO FINALIZADO CON {failed} ERROR(ES) EN {duration:.2f}s")
        sys.exit(1)
    print(f"PROCESO DE PEDIDOS FINALIZADO CON ÉXITO EN {duration:.2f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()

