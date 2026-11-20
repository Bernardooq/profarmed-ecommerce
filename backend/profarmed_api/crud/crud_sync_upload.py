"""
CRUD e Ingesta de Sincronización Masiva Asíncrona (ERP Upload & Bulk Ingest).

Funciones y Operaciones:
- Ingesta por lotes de Catálogo de Productos y Categorías (`process_products_from_json`).
- Ingesta por lotes de Listas de Precios y Markups (`process_price_lists_from_json` / `process_price_items_from_json`).
- Ingesta por lotes de Usuarios y Colaboradores (`process_commercial_users_from_json`).
- Ingesta por lotes de Clientes y Asignación Automática a Grupos Comerciales (`process_customers_from_json`).

Garantías:
- Upserts idempotentes mediante PostgreSQL `ON CONFLICT DO UPDATE`.
- Deduplicación por llave primaria dentro de cada chunk para evitar `CardinalityViolation`.
- Respeto estricto de productos bloqueados (`lock == True`).
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import and_, case, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from crud.crud_customer import get_password_hash
from db.base import Category, Customer, CustomerInfo, PriceList, PriceListItem, Product, Role, User
from utils.sales_group_utils import bulk_assign_customers_to_agent_groups, bulk_ensure_user_groups

logger = logging.getLogger(__name__)


def _get_locked_product_ids(db: Session) -> set:
    """Retorna el conjunto de product_id bloqueados manualmente (lock == True)."""
    locked_rows = db.query(Product.product_id).filter(Product.lock == True).all()
    locked_pids = set()
    for (raw_pid,) in locked_rows:
        if raw_pid is not None:
            locked_pids.add(raw_pid)
            locked_pids.add(str(raw_pid).strip())
    return locked_pids


def _build_password_hashes(records: List[Dict]) -> Dict[str, str]:
    """Pre-calcula hashes Argon2 solo para contraseñas únicas dentro del lote."""
    hashes = {}
    for item in records:
        pwd = item.get("password")
        if pwd and pwd not in hashes:
            hashes[pwd] = get_password_hash(pwd)
    return hashes


def _resolve_target_role_id(db: Session, role_slug: str = "seller", role_id: Optional[int] = None) -> int:
    """Resuelve dinámicamente el role_id destino a partir de ID o slug."""
    if role_id is not None:
        return role_id

    matched_role = db.query(Role).filter(Role.slug == role_slug).first()
    if not matched_role:
        matched_role = db.query(Role).filter(Role.slug.ilike(f"{role_slug}%")).first()
    if not matched_role and role_slug == "seller":
        matched_role = db.query(Role).filter(Role.role_id == 2).first()
    if not matched_role:
        matched_role = db.query(Role).filter(Role.slug != "admin").first()
    return matched_role.role_id if matched_role else 2


def _build_sync_summary(created: int, updated: int, errors: int = 0, **extra) -> Dict[str, int]:
    """Construye diccionario de respuesta uniforme (inglés y español retrocompatible)."""
    summary = {
        "created": created,
        "updated": updated,
        "errors": errors,
        "creados": created,
        "actualizados": updated,
        "errores": errors,
    }
    summary.update(extra)
    return summary


# ============================================================================
# CATÁLOGO: CATEGORÍAS Y PRODUCTOS
# ============================================================================


def _parse_optional_datetime(val):
    """Parsea datetime opcional (objeto datetime o string ISO) preservando UTC."""
    if val is None or val == "":
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo is not None else val.replace(tzinfo=timezone.utc)
    if isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val.strip().replace("Z", "+00:00"))
            return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def process_products_from_json(
    categories: List[str] = None,
    products: List[Dict] = None,
    db: Session = None,
    categorias: List[str] = None,
    productos: List[Dict] = None,
    **kwargs,
) -> Dict[str, int]:
    """Procesa JSON pre-parseado de categorías y productos mediante UPSERT por chunks."""
    if categories is None and categorias is not None:
        categories = categorias
    if products is None and productos is not None:
        products = productos
    categories = categories or []
    products = products or []

    sync_time = datetime.now(timezone.utc)

    # 1. UPSERT Categorías (deduplicadas)
    unique_categories = list(dict.fromkeys([c for c in categories if c]))
    logger.info(f"Upserting {len(unique_categories)} categories...")

    if unique_categories:
        categories_data = [{"name": cat_name, "updated_at": sync_time} for cat_name in unique_categories]
        stmt = insert(Category).values(categories_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["name"],
            set_={"updated_at": stmt.excluded.updated_at},
        )
        db.execute(stmt)
        db.commit()

    db_categories = db.query(Category.category_id, Category.name).filter(
        Category.name.in_(unique_categories)
    ).all() if unique_categories else []
    cat_map = {c.name: c.category_id for c in db_categories}
    logger.info(f"Mapped {len(cat_map)} categories to IDs")

    # 2. UPSERT Productos (omitiendo lock == True y deduplicando por product_id)
    logger.info(f"Upserting {len(products)} products...")
    locked_pids = _get_locked_product_ids(db)
    all_pids = [str(p.get("product_id")).strip() for p in products if p.get("product_id") is not None]
    existing_created_rows = db.query(Product.product_id, Product.created_at).filter(
        Product.product_id.in_(all_pids)
    ).all() if all_pids else []
    existing_created_map = {row.product_id: row.created_at for row in existing_created_rows}

    products_by_id = {}
    skipped_locked_count = 0
    for p in products:
        raw_pid = p.get("product_id")
        prod_id = str(raw_pid).strip() if raw_pid is not None else None
        if not prod_id:
            continue

        if prod_id in locked_pids or raw_pid in locked_pids:
            skipped_locked_count += 1
            continue

        category_id = cat_map.get(p.get("category_name")) if p.get("category_name") else None
        incoming_created_at = _parse_optional_datetime(p.get("created_at"))
        if incoming_created_at is not None:
            resolved_created_at = incoming_created_at
        elif prod_id in existing_created_map:
            resolved_created_at = existing_created_map[prod_id] or sync_time
        else:
            resolved_created_at = sync_time

        products_by_id[prod_id] = {
            "product_id": prod_id,
            "codebar": str(p.get("codebar")).strip() if p.get("codebar") else None,
            "name": p.get("name", "Producto Sincronizado"),
            "description": p.get("description"),
            "descripcion_2": p.get("descripcion_2"),
            "unidad_medida": p.get("unidad_medida"),
            "base_price": float(p.get("base_price", 0.0)),
            "iva_percentage": float(p.get("iva_percentage", 16.0)),
            "image_url": p.get("image_url"),
            "stock_count": int(p.get("stock_count", 0)),
            "is_active": True,
            "category_id": category_id,
            "created_at": resolved_created_at,
            "updated_at": _parse_optional_datetime(p.get("updated_at")) or sync_time,
        }

    if skipped_locked_count > 0:
        logger.info(f"[SYNC-UPLOAD] Omitidos {skipped_locked_count} productos porque tienen lock=True.")

    products_cleaned = list(products_by_id.values())
    chunk_size = 1000
    for i in range(0, len(products_cleaned), chunk_size):
        chunk = products_cleaned[i:i + chunk_size]
        try:
            stmt = insert(Product).values(chunk)
            stmt = stmt.on_conflict_do_update(
                index_elements=["product_id"],
                set_={
                    "codebar": stmt.excluded.codebar,
                    "name": stmt.excluded.name,
                    "description": stmt.excluded.description,
                    "unidad_medida": stmt.excluded.unidad_medida,
                    "base_price": stmt.excluded.base_price,
                    "iva_percentage": stmt.excluded.iva_percentage,
                    "stock_count": stmt.excluded.stock_count,
                    "is_active": True,
                    "category_id": stmt.excluded.category_id,
                    "image_url": case(
                        (and_(stmt.excluded.image_url.isnot(None), stmt.excluded.image_url != ""), stmt.excluded.image_url),
                        else_=Product.image_url,
                    ),
                    "created_at": stmt.excluded.created_at,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            db.execute(stmt)
            db.commit()
            logger.info(f"[THREAD-SYNC] Products chunk processed: {len(chunk)} items at {datetime.now()}")
        except Exception as exc:
            db.rollback()
            logger.error(f"[THREAD-SYNC-ERROR] Error processing products chunk around index {i}: {exc}")
            continue

    db.commit()
    return _build_sync_summary(created=0, updated=len(products_cleaned))


# ============================================================================
# LISTAS DE PRECIOS E ITEMS
# ============================================================================


def process_price_lists_from_json(
    price_lists: List[Dict] = None,
    db: Session = None,
    listas: List[Dict] = None,
    **kwargs,
) -> Dict[str, int]:
    """Procesa cabeceras de listas de precios desde JSON pre-parseado."""
    if price_lists is None and listas is not None:
        price_lists = listas
    price_lists = price_lists or []

    sync_time = datetime.now(timezone.utc)
    logger.info(f"Processing {len(price_lists)} price lists...")

    lists_by_id = {}
    for lista in price_lists:
        raw_id = lista.get("price_list_id")
        if not raw_id:
            continue
        list_id = int(raw_id)
        lists_by_id[list_id] = {
            "price_list_id": list_id,
            "list_name": lista.get("list_name") or lista.get("name") or f"Lista {list_id}",
            "is_active": True,
            "updated_at": sync_time,
        }

    price_lists_data = list(lists_by_id.values())
    if price_lists_data:
        stmt = insert(PriceList).values(price_lists_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["price_list_id"],
            set_={
                "list_name": stmt.excluded.list_name,
                "updated_at": stmt.excluded.updated_at,
            },
        )
        db.execute(stmt)
        db.commit()

    return _build_sync_summary(created=0, updated=len(price_lists_data))


def process_price_items_from_json(items: List[Dict], db: Session) -> Dict[str, int]:
    """Procesa items y precios asignados a listas de precios validando FKs y locks."""
    sync_time = datetime.now(timezone.utc)
    logger.info(f"Processing {len(items)} price list items...")

    locked_pids = _get_locked_product_ids(db)

    valid_product_map = {}
    for (flat_id,) in db.query(Product.product_id).filter(or_(Product.lock == False, Product.lock.is_(None))).all():
        if flat_id is not None:
            valid_product_map[flat_id] = flat_id
            valid_product_map[str(flat_id).strip()] = flat_id

    valid_list_ids = {
        int(flat_id)
        for (flat_id,) in db.query(PriceList.price_list_id).all()
        if flat_id is not None
    }

    items_by_key = {}
    skipped_count = 0

    for item in items:
        raw_pid = item.get("product_id")
        raw_lid = item.get("price_list_id")
        if raw_pid is None or raw_lid is None:
            skipped_count += 1
            continue

        raw_pid_str = str(raw_pid).strip()
        if raw_pid in locked_pids or raw_pid_str in locked_pids:
            skipped_count += 1
            continue

        matched_pid = valid_product_map.get(raw_pid) or valid_product_map.get(raw_pid_str)
        try:
            list_id_int = int(raw_lid)
        except (ValueError, TypeError):
            skipped_count += 1
            continue

        if matched_pid and list_id_int in valid_list_ids:
            items_by_key[(list_id_int, matched_pid)] = {
                "price_list_id": list_id_int,
                "product_id": matched_pid,
                "markup_percentage": float(item.get("markup_percentage", 0.0)),
                "final_price": float(item.get("final_price", 0.0)),
                "updated_at": sync_time,
            }
        else:
            skipped_count += 1

    items_data = list(items_by_key.values())
    logger.info(f"[SYNC-UPLOAD] Processed price items - Valid: {len(items_data)}, Skipped/Orphans: {skipped_count}")

    chunk_size = 1000
    for i in range(0, len(items_data), chunk_size):
        chunk = items_data[i:i + chunk_size]
        stmt = insert(PriceListItem).values(chunk)
        stmt = stmt.on_conflict_do_update(
            index_elements=["price_list_id", "product_id"],
            set_={c.name: c for c in stmt.excluded if c.name not in ["price_list_id", "product_id"]},
        )
        db.execute(stmt)
        db.commit()

    return _build_sync_summary(created=0, updated=len(items_data), total_items=len(items_data))


# ============================================================================
# COLABORADORES COMERCIALES Y CLIENTES
# ============================================================================


def process_commercial_users_from_json(
    users: List[Dict] = None,
    db: Session = None,
    role_slug: str = "seller",
    role_id: Optional[int] = None,
    ensure_groups: bool = True,
    sellers: List[Dict] = None,
    **kwargs,
) -> Dict[str, int]:
    """Procesa colaboradores comerciales / vendedores desde JSON pre-parseado."""
    if users is None and sellers is not None:
        users = sellers
    users = users or []
    if not users:
        return _build_sync_summary(0, 0, 0)

    logger.info(f"Upserting {len(users)} colaboradores/usuarios...")
    sync_time = datetime.now(timezone.utc)

    try:
        user_ids = list(dict.fromkeys([int(u.get("user_id")) for u in users if u.get("user_id")]))
        existing_ids = {
            u.user_id
            for u in db.query(User.user_id).filter(User.user_id.in_(user_ids)).all()
        }

        password_hashes = _build_password_hashes(users)
        target_role_id = _resolve_target_role_id(db, role_slug=role_slug, role_id=role_id)

        users_by_id = {}
        for u in users:
            u_id = u.get("user_id")
            if not u_id:
                continue
            uid_int = int(u_id)
            username = u.get("username", f"user_{uid_int}")
            users_by_id[uid_int] = {
                "user_id": uid_int,
                "username": username,
                "email": u.get("email") or f"{username}@profarmed.local",
                "full_name": u.get("full_name") or username,
                "password_hash": password_hashes.get(u.get("password")),
                "role_id": u.get("role_id") or target_role_id,
                "is_active": u.get("is_active", True),
                "updated_at": sync_time,
            }

        users_data = list(users_by_id.values())
        updated_count = sum(1 for uid in users_by_id if uid in existing_ids)
        created_count = len(users_by_id) - updated_count

        if users_data:
            stmt = insert(User).values(users_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=["user_id"],
                set_={
                    "email": stmt.excluded.email,
                    "full_name": stmt.excluded.full_name,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            db.execute(stmt)
            db.commit()

            if ensure_groups:
                bulk_ensure_user_groups(db, list(users_by_id.keys()))
                db.commit()

        return _build_sync_summary(created=created_count, updated=updated_count)

    except Exception as exc:
        logger.error(f"Error upserting colaboradores comerciales: {exc}")
        logger.exception("Traceback completo de la falla en colaboradores comerciales:")
        db.rollback()
        return _build_sync_summary(created=0, updated=0, errors=len(users))


# Aliases retrocompatibles
process_users_from_json = process_commercial_users_from_json
process_sellers_from_json = process_commercial_users_from_json


def process_customers_from_json(customers: List[Dict], db: Session) -> Dict[str, int]:
    """Procesa clientes en lote desde JSON pre-parseado (Customer + Info + Grupos)."""
    if not customers:
        return _build_sync_summary(0, 0, 0)

    logger.info(f"Upserting {len(customers)} customers...")
    sync_time = datetime.now(timezone.utc)

    try:
        customer_ids = list(dict.fromkeys([int(c.get("customer_id")) for c in customers if c.get("customer_id")]))
        existing_ids = {
            c.customer_id
            for c in db.query(Customer.customer_id).filter(Customer.customer_id.in_(customer_ids)).all()
        }

        password_hashes = _build_password_hashes(customers)
        valid_user_ids = {u.user_id for u in db.query(User.user_id).all()}
        valid_price_list_ids = {p.price_list_id for p in db.query(PriceList.price_list_id).all()}

        cust_by_id = {}
        info_by_id = {}
        agent_links_by_cid = {}

        for c in customers:
            raw_cid = c.get("customer_id")
            if not raw_cid:
                continue
            try:
                cid = int(raw_cid)
            except (ValueError, TypeError):
                continue

            username = c.get("username", f"cust_{cid}")

            safe_agent_id = None
            raw_aid = c.get("agent_id")
            if raw_aid is not None and str(raw_aid).strip() != "":
                try:
                    cand_aid = int(str(raw_aid).strip())
                    if cand_aid in valid_user_ids:
                        safe_agent_id = cand_aid
                except (ValueError, TypeError):
                    safe_agent_id = None

            safe_pl_id = None
            raw_pl = c.get("price_list_id")
            if raw_pl is not None and str(raw_pl).strip() != "":
                try:
                    cand_pl = int(str(raw_pl).strip())
                    if cand_pl in valid_price_list_ids:
                        safe_pl_id = cand_pl
                except (ValueError, TypeError):
                    safe_pl_id = None

            cust_by_id[cid] = {
                "customer_id": cid,
                "username": username,
                "email": c.get("email") or f"{username}@profarmed.local",
                "full_name": c.get("full_name") or username,
                "password_hash": password_hashes.get(c.get("password")),
                "is_active": True,
                "agent_id": safe_agent_id,
                "updated_at": sync_time,
            }

            info_by_id[cid] = {
                "customer_id": cid,
                "business_name": c.get("business_name") or c.get("full_name") or username,
                "rfc": c.get("rfc"),
                "price_list_id": safe_pl_id,
                "address_1": c.get("address_1"),
                "address_2": c.get("address_2"),
                "address_3": c.get("address_3"),
                "telefono_1": c.get("telefono_1"),
                "telefono_2": c.get("telefono_2"),
            }

            if safe_agent_id is not None:
                agent_links_by_cid[cid] = {"customer_id": cid, "agent_id": safe_agent_id}

        customers_data = list(cust_by_id.values())
        info_data = list(info_by_id.values())
        updated_count = sum(1 for cid in cust_by_id if cid in existing_ids)
        created_count = len(cust_by_id) - updated_count

        chunk_size = 1000
        for i in range(0, len(customers_data), chunk_size):
            chunk_cust = customers_data[i:i + chunk_size]
            chunk_info = info_data[i:i + chunk_size]

            stmt_cust = insert(Customer).values(chunk_cust)
            stmt_cust = stmt_cust.on_conflict_do_update(
                index_elements=["customer_id"],
                set_={
                    "email": stmt_cust.excluded.email,
                    "full_name": stmt_cust.excluded.full_name,
                    "agent_id": stmt_cust.excluded.agent_id,
                    "updated_at": stmt_cust.excluded.updated_at,
                },
            )
            db.execute(stmt_cust)
            db.flush()

            stmt_info = insert(CustomerInfo).values(chunk_info)
            stmt_info = stmt_info.on_conflict_do_update(
                index_elements=["customer_id"],
                set_={
                    "business_name": stmt_info.excluded.business_name,
                    "rfc": stmt_info.excluded.rfc,
                    "price_list_id": stmt_info.excluded.price_list_id,
                    "address_1": stmt_info.excluded.address_1,
                    "telefono_1": stmt_info.excluded.telefono_1,
                    "telefono_2": stmt_info.excluded.telefono_2,
                },
            )
            db.execute(stmt_info)

        if agent_links_by_cid:
            bulk_assign_customers_to_agent_groups(db, list(agent_links_by_cid.values()))

        db.commit()
        return _build_sync_summary(created=created_count, updated=updated_count)

    except Exception as exc:
        logger.error(f"Error upserting customers: {exc}")
        logger.exception("Traceback completo de la falla en clientes:")
        db.rollback()
        return _build_sync_summary(created=0, updated=0, errors=len(customers))
