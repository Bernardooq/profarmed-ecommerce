"""
CRUD de Sincronización Directa por Lotes (Sync Batch -> PostgreSQL).

Operaciones síncronas invocadas desde `/api/v1/sync/*`:
- Categorías (`save_or_update_category`)
- Listas de precios (`save_or_update_price_list`)
- Productos (`bulk_sync_products`)
- Items de listas de precios (`bulk_upsert_price_list_items`)
- Clientes (`bulk_upsert_customers`)
- Colaboradores comerciales (`bulk_upsert_users`)
- Limpieza segura post-sync (`cleanup_unsynced_items`)
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, case, column, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from crud.crud_customer import get_password_hash
from db.base import Category, Customer, CustomerInfo, PriceList, PriceListItem, Product, Role, User
from utils.sales_group_utils import bulk_assign_customers_to_agent_groups, bulk_ensure_user_groups


def _build_password_hashes(records: List[dict]) -> Dict[str, str]:
    """Pre-calcula hashes Argon2 únicamente para contraseñas distintas en el lote."""
    hashes = {}
    for item in records:
        pwd = item.get("password")
        if pwd and pwd not in hashes:
            hashes[pwd] = get_password_hash(pwd)
    return hashes


def _resolve_target_role_id(db: Session, role_slug: str = "seller", role_id: Optional[int] = None) -> int:
    """Resuelve dinámicamente el role_id destino según role_id explícito o role_slug."""
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


# ============================================================================
# CATEGORÍAS Y LISTAS DE PRECIOS
# ============================================================================


def save_or_update_category(
    db: Session,
    name: str,
    description: str = None,
    updated_at: datetime = None,
) -> Tuple[bool, Optional[str]]:
    """Guarda o actualiza una categoría usando savepoint para no revertir filas previas."""
    try:
        with db.begin_nested():
            stmt = insert(Category).values(
                name=name,
                description=description,
                updated_at=updated_at or datetime.now(timezone.utc),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["name"],
                set_={
                    "description": stmt.excluded.description,
                    "updated_at": stmt.excluded.updated_at,
                },
            ).returning(Category.category_id, (column("xmax") == 0).label("is_insert"))

            result = db.execute(stmt).first()
            if result:
                return (bool(result.is_insert), None)
            return (False, "No result from upsert")
    except Exception as exc:
        return (False, str(exc))


def check_if_price_list_exists(db: Session, list_id: int) -> bool:
    """Verifica si una lista de precios ya existe."""
    return db.query(PriceList).filter(PriceList.price_list_id == list_id).first() is not None


verificar_si_lista_existe = check_if_price_list_exists


def save_or_update_price_list(
    db: Session,
    list_id: int = None,
    name: str = None,
    description: str = None,
    is_active: bool = True,
    updated_at: datetime = None,
    **kwargs,
) -> Tuple[bool, Optional[str]]:
    """Guarda o actualiza una cabecera de lista de precios mediante UPSERT."""
    try:
        if list_id is None and "lista_id" in kwargs:
            list_id = kwargs["lista_id"]
        if name is None and "nombre" in kwargs:
            name = kwargs["nombre"]
        if description is None and "descripcion" in kwargs:
            description = kwargs["descripcion"]
        if "esta_activa" in kwargs:
            is_active = kwargs["esta_activa"]

        already_exists = check_if_price_list_exists(db, list_id)
        stmt = insert(PriceList).values(
            price_list_id=list_id,
            list_name=name,
            description=description,
            is_active=is_active,
            updated_at=updated_at or datetime.now(timezone.utc),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["price_list_id"],
            set_={
                "list_name": stmt.excluded.list_name,
                "description": stmt.excluded.description,
                "updated_at": stmt.excluded.updated_at,
            },
        )
        db.execute(stmt)
        return (not already_exists, None)
    except Exception as exc:
        return (False, str(exc))


# ============================================================================
# PRODUCTOS E ITEMS DE LISTAS DE PRECIOS
# ============================================================================


def bulk_sync_products(db: Session, products: List[dict]) -> Tuple[int, int, List[str]]:
    """Bulk UPSERT de productos respetando productos bloqueados (lock == True)."""
    if not products:
        return 0, 0, []

    errors = []
    try:
        category_names = {p.get("category_name") for p in products if p.get("category_name")}
        categories = db.query(Category).filter(Category.name.in_(category_names)).all() if category_names else []
        cat_map = {c.name: c.category_id for c in categories}

        product_ids = [p.get("product_id") for p in products if p.get("product_id")]
        existing_products = db.query(Product.product_id, Product.lock).filter(
            Product.product_id.in_(product_ids)
        ).all() if product_ids else []
        locked_ids = {p.product_id for p in existing_products if p.lock}
        existing_ids = {p.product_id for p in existing_products}

        prod_by_id = {}
        for p in products:
            p_id = p.get("product_id")
            if not p_id or p_id in locked_ids:
                continue

            prod_by_id[p_id] = {
                "product_id": p_id,
                "codebar": p.get("codebar"),
                "name": p.get("name", "Producto Sincronizado"),
                "description": p.get("description"),
                "descripcion_2": p.get("descripcion_2"),
                "unidad_medida": p.get("unidad_medida"),
                "base_price": float(p.get("base_price", 0.0)),
                "iva_percentage": float(p.get("iva_percentage", 0.0)),
                "stock_count": int(p.get("stock_count", 0)),
                "is_active": p.get("is_active", True),
                "category_id": cat_map.get(p.get("category_name")),
                "image_url": p.get("image_url"),
                "updated_at": p.get("updated_at") or datetime.now(timezone.utc),
            }

        prod_data_list = list(prod_by_id.values())
        if not prod_data_list:
            return 0, 0, errors

        updated_count = sum(1 for pid in prod_by_id if pid in existing_ids)
        created_count = len(prod_by_id) - updated_count

        stmt = insert(Product).values(prod_data_list)
        stmt = stmt.on_conflict_do_update(
            index_elements=["product_id"],
            set_={
                "codebar": stmt.excluded.codebar,
                "name": stmt.excluded.name,
                "description": stmt.excluded.description,
                "descripcion_2": stmt.excluded.descripcion_2,
                "unidad_medida": stmt.excluded.unidad_medida,
                "base_price": stmt.excluded.base_price,
                "iva_percentage": stmt.excluded.iva_percentage,
                "stock_count": stmt.excluded.stock_count,
                "is_active": stmt.excluded.is_active,
                "category_id": stmt.excluded.category_id,
                "image_url": case(
                    (and_(stmt.excluded.image_url.isnot(None), stmt.excluded.image_url != ""), stmt.excluded.image_url),
                    else_=Product.image_url,
                ),
                "updated_at": stmt.excluded.updated_at,
            },
        )
        db.execute(stmt)
        return created_count, updated_count, errors

    except Exception as exc:
        errors.append(f"Error en bulk UPSERT de productos: {exc}")
        return 0, 0, errors


bulk_sync_prods = bulk_sync_products


def bulk_upsert_price_list_items(db: Session, items: List[dict]) -> Tuple[int, int, int, List[str]]:
    """Bulk UPSERT de items de listas de precios validando producto desbloqueado y lista existente."""
    if not items:
        return 0, 0, 0, []

    skipped_count = 0
    errors = []

    try:
        product_ids = list({item.get("product_id") for item in items if item.get("product_id")})
        list_ids = list({item.get("price_list_id") for item in items if item.get("price_list_id")})

        existing_products = db.query(Product.product_id, Product.lock).filter(
            Product.product_id.in_(product_ids)
        ).all() if product_ids else []
        valid_unlocked_product_ids = {p.product_id for p in existing_products if not p.lock}

        valid_list_ids = {
            lid for (lid,) in db.query(PriceList.price_list_id).filter(
                PriceList.price_list_id.in_(list_ids)
            ).all()
        } if list_ids else set()

        valid_by_key = {}
        for item in items:
            p_id = item.get("product_id")
            l_id = item.get("price_list_id")
            if p_id in valid_unlocked_product_ids and l_id in valid_list_ids:
                valid_by_key[(l_id, p_id)] = item
            else:
                skipped_count += 1

        valid_items = list(valid_by_key.values())
        if not valid_items:
            return 0, 0, skipped_count, []

        existing_keys = {
            (row.price_list_id, row.product_id)
            for row in db.query(PriceListItem.price_list_id, PriceListItem.product_id).filter(
                PriceListItem.price_list_id.in_(list({k[0] for k in valid_by_key}))
            ).all()
        }

        updated_count = sum(1 for k in valid_by_key if k in existing_keys)
        created_count = len(valid_by_key) - updated_count

        stmt = insert(PriceListItem).values(valid_items)
        stmt = stmt.on_conflict_do_update(
            index_elements=["price_list_id", "product_id"],
            set_={
                "markup_percentage": stmt.excluded.markup_percentage,
                "final_price": stmt.excluded.final_price,
                "updated_at": stmt.excluded.updated_at,
            },
        )
        db.execute(stmt)
        return created_count, updated_count, skipped_count, errors

    except Exception as exc:
        errors.append(f"Error en bulk upsert: {exc}")
        return 0, 0, skipped_count, errors


# ============================================================================
# CLIENTES Y COLABORADORES COMERCIALES
# ============================================================================


def bulk_upsert_customers(db: Session, customers: List[dict]) -> Tuple[int, int, List[str]]:
    """Inserta o actualiza múltiples clientes + info comercial y grupos en una sola operación."""
    if not customers:
        return 0, 0, []

    errors = []
    try:
        customer_ids = [c.get("customer_id") for c in customers if c.get("customer_id")]
        existing_ids = {
            c.customer_id
            for c in db.query(Customer.customer_id).filter(Customer.customer_id.in_(customer_ids)).all()
        } if customer_ids else set()

        password_hashes = _build_password_hashes(customers)
        valid_user_ids = {u.user_id for u in db.query(User.user_id).all()}
        valid_price_list_ids = {p.price_list_id for p in db.query(PriceList.price_list_id).all()}

        cust_by_id = {}
        info_by_id = {}
        agent_links_by_cid = {}

        for c in customers:
            c_id = c.get("customer_id")
            if not c_id:
                continue

            username = c.get("username", f"cust_{c_id}")

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

            cust_by_id[c_id] = {
                "customer_id": c_id,
                "username": username,
                "email": c.get("email") or f"{username}@profarmed.local",
                "full_name": c.get("full_name") or username,
                "password_hash": password_hashes.get(c.get("password")),
                "is_active": True,
                "agent_id": safe_agent_id,
                "updated_at": c.get("updated_at") or datetime.now(timezone.utc),
            }

            info_by_id[c_id] = {
                "customer_id": c_id,
                "business_name": c.get("business_name") or c.get("full_name") or f"Cliente {c_id}",
                "rfc": c.get("rfc"),
                "price_list_id": safe_pl_id,
                "address_1": c.get("address_1"),
                "address_2": c.get("address_2"),
                "address_3": c.get("address_3"),
                "telefono_1": c.get("telefono_1"),
                "telefono_2": c.get("telefono_2"),
            }

            if safe_agent_id is not None:
                agent_links_by_cid[int(c_id)] = {"customer_id": int(c_id), "agent_id": safe_agent_id}

        customers_data = list(cust_by_id.values())
        customers_info_data = list(info_by_id.values())
        if not customers_data:
            return 0, 0, errors

        updated_count = sum(1 for cid in cust_by_id if cid in existing_ids)
        created_count = len(cust_by_id) - updated_count

        stmt_customer = insert(Customer).values(customers_data)
        stmt_customer = stmt_customer.on_conflict_do_update(
            index_elements=["customer_id"],
            set_={
                "email": stmt_customer.excluded.email,
                "full_name": stmt_customer.excluded.full_name,
                "agent_id": stmt_customer.excluded.agent_id,
                "updated_at": stmt_customer.excluded.updated_at,
            },
        )
        db.execute(stmt_customer)
        db.flush()

        stmt_info = insert(CustomerInfo).values(customers_info_data)
        stmt_info = stmt_info.on_conflict_do_update(
            index_elements=["customer_id"],
            set_={
                "business_name": stmt_info.excluded.business_name,
                "rfc": stmt_info.excluded.rfc,
                "price_list_id": stmt_info.excluded.price_list_id,
                "address_1": stmt_info.excluded.address_1,
                "address_2": stmt_info.excluded.address_2,
                "address_3": stmt_info.excluded.address_3,
                "telefono_1": stmt_info.excluded.telefono_1,
                "telefono_2": stmt_info.excluded.telefono_2,
            },
        )
        db.execute(stmt_info)

        if agent_links_by_cid:
            bulk_assign_customers_to_agent_groups(db, list(agent_links_by_cid.values()))

        return created_count, updated_count, errors

    except Exception as exc:
        errors.append(f"Error en bulk upsert de clientes: {exc}")
        return 0, 0, errors


def bulk_upsert_users(
    db: Session,
    users: List[dict] = None,
    role_slug: str = "seller",
    role_id: Optional[int] = None,
    ensure_groups: bool = True,
    sellers: List[dict] = None,
    **kwargs,
) -> Tuple[int, int, List[str]]:
    """Inserta o actualiza múltiples colaboradores o usuarios sincronizados."""
    if users is None and sellers is not None:
        users = sellers
    users = users or []
    if not users:
        return 0, 0, []

    errors = []
    try:
        user_ids = list(dict.fromkeys([u.get("user_id") for u in users if u.get("user_id")]))
        existing_ids = {
            u.user_id
            for u in db.query(User.user_id).filter(User.user_id.in_(user_ids)).all()
        } if user_ids else set()

        password_hashes = _build_password_hashes(users)
        target_role_id = _resolve_target_role_id(db, role_slug=role_slug, role_id=role_id)

        users_by_id = {}
        for u in users:
            u_id = u.get("user_id")
            if not u_id:
                continue
            username = u.get("username", f"user_{u_id}")
            users_by_id[u_id] = {
                "user_id": u_id,
                "username": username,
                "email": u.get("email") or f"{username}@profarmed.local",
                "full_name": u.get("full_name") or username,
                "password_hash": password_hashes.get(u.get("password")),
                "role_id": u.get("role_id") or target_role_id,
                "is_active": u.get("is_active", True),
                "updated_at": u.get("updated_at") or datetime.now(timezone.utc),
            }

        users_data = list(users_by_id.values())
        if not users_data:
            return 0, 0, errors

        updated_count = sum(1 for uid in users_by_id if uid in existing_ids)
        created_count = len(users_by_id) - updated_count

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

        if ensure_groups:
            bulk_ensure_user_groups(db, list(users_by_id.keys()))

        return created_count, updated_count, errors

    except Exception as exc:
        errors.append(f"Error en bulk upsert de usuarios: {exc}")
        return 0, 0, errors


# Aliases retrocompatibles
bulk_upsert_sellers = bulk_upsert_users
bulk_upsert_commercial_users = bulk_upsert_users


# ============================================================================
# LIMPIEZA POST-SYNC
# ============================================================================


def cleanup_unsynced_items(db: Session, last_sync: datetime, force: bool = False) -> bool:
    """Desactiva productos, categorías, listas e items antiguos con buffer de seguridad."""
    last_sync_buffered = last_sync - timedelta(minutes=20)

    total_products = db.query(Product).count()
    to_deactivate = db.query(Product).filter(
        Product.updated_at < last_sync_buffered,
        Product.is_active == True,
        Product.lock == False,
    ).count()

    if total_products > 100 and to_deactivate > (total_products * 0.70) and not force:
        print(
            f"SAFETY ABORT: Se intentaron desactivar {to_deactivate} productos de {total_products} "
            f"({(to_deactivate / total_products) * 100:.1f}%). El límite de seguridad es 70%."
        )
        return False

    db.query(Product).filter(
        Product.updated_at < last_sync_buffered,
        Product.lock == False,
    ).update({Product.is_active: False}, synchronize_session=False)

    subq = select(Product.category_id).distinct()
    db.query(Category).filter(
        Category.updated_at < last_sync_buffered,
        ~Category.category_id.in_(subq),
    ).delete(synchronize_session=False)

    updated_items_count = db.query(PriceListItem).filter(
        PriceListItem.updated_at >= last_sync_buffered
    ).count()

    if updated_items_count > 0:
        locked_subq = select(Product.product_id).filter(Product.lock == True)
        public_lists_subq = select(PriceList.price_list_id).filter(
            or_(PriceList.is_public_storefront == True, PriceList.is_public_internal == True)
        )
        db.query(PriceListItem).filter(
            PriceListItem.updated_at < last_sync_buffered,
            ~PriceListItem.product_id.in_(locked_subq),
            ~PriceListItem.price_list_id.in_(public_lists_subq),
        ).delete(synchronize_session=False)
    else:
        print("SAFETY SKIP: No se eliminaron PriceListItem porque no hubo items actualizados.")

    db.query(PriceList).filter(
        PriceList.updated_at < last_sync_buffered,
        PriceList.is_public_storefront == False,
        PriceList.is_public_internal == False,
    ).update({PriceList.is_active: False}, synchronize_session=False)

    return True
