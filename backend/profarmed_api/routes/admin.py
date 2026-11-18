"""
Routes de Administracion de Usuarios Internos

Endpoints CRUD para gestion de usuarios del sistema:
- GET /users - Lista de usuarios con filtros y soporte dinámico de roles
- POST /users - Crear usuario interno
- GET /users/{id} - Detalle de usuario
- PUT /users/{id} - Actualizar usuario
- DELETE /users/{id} - Eliminar usuario
- PUT /users/{id}/role - Asignación dinámica de rol

Permisos: Control basado en PBAC granular (users.view, users.create, users.edit, users.delete, roles.assign, reports.export)

Nota: Este módulo gestiona colaboradores y usuarios internos con roles dinámicos (RBAC / PBAC).
Para clientes B2B, ver routes/customers.py
"""

from schemas.user import UserRoleChangeRequest
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from dependencies import get_db, require_permission
from db.base import User, Role
from crud import crud_customer
from crud.crud_commercial_group import get_user_groups
from crud.crud_customer import get_customer_by_email, get_customer_by_username
from schemas.user import User as UserSchema, UserUpdate, UserCreate
from crud.crud_user import (
    get_users, get_user, update_user, delete_user,
    create_user, get_user_by_username, get_user_by_email
)
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from fastapi.responses import StreamingResponse
from datetime import datetime
from db.base import (
    Customer, CustomerInfo, SalesGroup, GroupUser,
    Category, Product, PriceList, PriceListItem
)
from crud.crud_product import get_products

router = APIRouter()

""" GET /users - Lista de usuarios con filtros """
@router.get("/users", response_model=List[UserSchema])
def read_all_users(
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(100, ge=1, le=200, description="Maximo de registros"),
    role: Optional[str] = Query(None, description="Filtrar por slug de rol (ej: admin, marketing, seller, warehouse)"),
    search: Optional[str] = Query(None, description="Buscar por nombre o username"),
    team_only: bool = Query(False, description="Excluir usuarios administradores del sistema"),
    current_user: User = Depends(require_permission("users.view")),
    db: Session = Depends(get_db)
):
    caller_slug = getattr(current_user.role_rel, "slug", "") if current_user.role_rel else ""
    is_caller_admin = (caller_slug == "admin" or current_user.role_id == 1 or current_user.has_permission("system.admin"))

    # Si quien consulta no es admin y solicita datos del rol admin, no enviar nada
    if not is_caller_admin and role and str(role).strip().lower() in ("admin", "1"):
        return []

    # Lista de usuarios internos con soporte de roles dinámicos
    users = get_users(db, skip=skip, limit=limit, role=role, search=search)

    # Si no es admin o se solicita team_only, excluir estrictamente usuarios del rol 'admin'
    if team_only or not is_caller_admin:
        users = [
            u for u in users 
            if u.role_id != 1 and getattr(getattr(u, "role_rel", None), "slug", "") != "admin"
        ]

    return users

""" POST /users - Crear usuario """
@router.post("/users", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
def create_new_user(
    user: UserCreate,
    current_user: User = Depends(require_permission("users.create")),
    db: Session = Depends(get_db)
):
    # Constraint: No se puede crear un usuario con roles del sistema salvo que quien lo cree posea 'system.admin' o rol 'admin'
    target_role_record = db.query(Role).filter(Role.role_id == user.role_id).first() if user.role_id else None
    target_is_system = False
    if target_role_record:
        target_is_system = target_role_record.is_system or target_role_record.slug == "admin" or target_role_record.role_id == 1 or any(rp.permission_code == "system.admin" for rp in (target_role_record.permissions or []))
    elif user.role:
        target_slug = user.role.value if hasattr(user.role, "value") else str(user.role)
        target_is_system = (target_slug == "admin")

    caller_slug = getattr(current_user.role_rel, "slug", "") if current_user.role_rel else ""
    is_caller_admin = (caller_slug == "admin" or current_user.role_id == 1)

    if target_is_system and not is_caller_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo usuarios con rol 'admin' (Administrador General) pueden crear usuarios administradores del sistema"
        )

    db_user = get_user_by_username(db, username=user.username)
    db_customer = get_customer_by_username(db, username=user.username)
    if db_user or db_customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya esta registrado"
        )
    
    return create_user(db=db, user=user)

""" GET /users/{user_id} - Detalle de usuario """
@router.get("/users/{user_id}", response_model=UserSchema)
def read_user_by_id(
    user_id: int,
    current_user: User = Depends(require_permission("users.view")),
    db: Session = Depends(get_db)
):
    user = get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    caller_slug = getattr(current_user.role_rel, "slug", "") if current_user.role_rel else ""
    is_caller_admin = (caller_slug == "admin" or current_user.role_id == 1 or current_user.has_permission("system.admin"))
    is_target_admin = (user.role_id == 1 or getattr(getattr(user, "role_rel", None), "slug", "") == "admin")

    if is_target_admin and not is_caller_admin and current_user.user_id != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene autorización para consultar información de administradores del sistema."
        )

    return user

""" PUT /users/{user_id} - Actualizar usuario """
@router.put("/users/{user_id}", response_model=UserSchema)
def update_user_info(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(require_permission("users.edit")),
    db: Session = Depends(get_db)
):
    target_user = get_user(db, user_id=user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    # Constraint de Inmutabilidad: Ningún usuario puede degradar o modificar a un usuario con 'system.admin' o rol de sistema salvo con rol 'admin'
    target_role = getattr(target_user, "role_rel", None)
    is_target_sys = (target_role and (target_role.is_system or target_role.slug == "admin" or target_role.role_id == 1)) or target_user.has_permission("system.admin") or target_user.role_id == 1
    caller_slug = getattr(current_user.role_rel, "slug", "") if current_user.role_rel else ""
    is_caller_admin = (caller_slug == "admin" or current_user.role_id == 1)

    if is_target_sys and not is_caller_admin and current_user.user_id != target_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo usuarios con rol 'admin' (Administrador General) pueden modificar a un Administrador General"
        )

    db_customer = get_customer_by_username(db, username=user_update.username) if user_update.username else None
    if db_customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya esta registrado"
        )

    user = update_user(db, user_id=user_id, user=user_update)
    if not user:    
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    return user
    
""" DELETE /users/{user_id} - Eliminar usuario """
@router.delete("/users/{user_id}")
def delete_user_account(
    user_id: int,
    current_user: User = Depends(require_permission("users.delete")),
    db: Session = Depends(get_db)
):
    target_user = get_user(db, user_id=user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    # Constraint Crítica: Jamás se puede eliminar a un usuario con rol del sistema inmutable ni con 'system.admin'
    target_role = getattr(target_user, "role_rel", None)
    if (target_role and (target_role.is_system or target_role.slug == "admin" or target_role.role_id == 1)) or target_user.has_permission("system.admin") or target_user.role_id == 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar un usuario Administrador General del sistema"
        )

    user = delete_user(db, user_id=user_id)
    return {"message": "Usuario eliminado exitosamente"}


""" PUT /users/{user_id}/role y /users/{user_id}/promote - Cambiar rol entre roles operativos o dinámicos """
@router.put("/users/{user_id}/role")
@router.put("/users/{user_id}/promote")
def change_user_role(
    user_id: int,
    payload: Optional[UserRoleChangeRequest] = None,
    role: Optional[str] = Query(None),
    current_user: User = Depends(require_permission("roles.assign")),
    db: Session = Depends(get_db)
):
    """
    Cambia el rol de un usuario entre los roles configurados en el sistema (PBAC dinámico).
    Maneja la migración o limpieza de membresías de grupos comerciales según capacidades del nuevo rol.
    Requiere permiso 'roles.assign'.
    """
    from crud.crud_user import auto_crear_grupo_usuario
    from db.base import Role

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    # Bloquear alteración de usuarios con privilegios de sistema salvo autorización de system.admin
    if user.has_permission("system.admin") or (user.role_rel and user.role_rel.is_system):
        if not current_user.has_permission("system.admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo usuarios con 'system.admin' pueden cambiar el rol de un administrador o usuario del sistema"
            )

    # Determinar el rol objetivo
    target_role_str = None
    if payload and payload.role:
        target_role_str = payload.role.strip().lower()
    elif role:
        target_role_str = role.strip().lower()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe especificar el nuevo rol ('role') en el cuerpo de la petición o como parámetro"
        )

    # Buscar el rol correspondiente en la tabla roles
    target_role = db.query(Role).filter(Role.slug == target_role_str).first()
    if not target_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El rol '{target_role_str}' no existe en el catálogo de roles"
        )

    target_perms = {rp.permission_code for rp in target_role.permissions} if target_role.permissions else set()
    if target_role.slug == "admin" or "system.admin" in target_perms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se permite promover a administrador mediante este endpoint"
        )

    # Si ya tiene ese rol asignado, responder sin mutaciones
    if user.role_id == target_role.role_id:
        perms = [rp.permission_code for rp in target_role.permissions] if target_role.permissions else []
        return {
            "message": f"El usuario '{user.full_name}' ya tiene el rol '{target_role.name}'",
            "user_id": user.user_id,
            "role_id": target_role.role_id,
            "role": target_role.slug,
            "role_slug": target_role.slug,
            "role_name": target_role.name,
            "new_role": target_role.slug,
            "permissions": perms,
            "full_name": user.full_name
        }

    # Asegurar grupo automático para cualquier usuario operativo no-admin si aún no cuenta con uno
    if target_role.slug != "admin" and not user.group_memberships:
        auto_crear_grupo_usuario(db, user)

    # Asignar la nueva FK de rol
    user.role_id = target_role.role_id
    db.commit()
    db.refresh(user)

    perms = [rp.permission_code for rp in target_role.permissions] if target_role.permissions else []

    return {
        "message": f"Rol de '{user.full_name}' actualizado a {target_role.name} exitosamente",
        "user_id": user.user_id,
        "role_id": target_role.role_id,
        "role": target_role.slug,
        "role_slug": target_role.slug,
        "role_name": target_role.name,
        "new_role": target_role.slug,
        "permissions": perms,
        "full_name": user.full_name
    }

""" GET /export-xlsx - Exportar data del sistema a Excel por tipo """
@router.get("/export-xlsx")
def export_data_xlsx(
    type: str = Query(..., description="Tipo de datos o rol a exportar: clientes, productos, grupos, usuarios, roles o cualquier slug/ID de rol dinámico"),
    role: Optional[str] = Query(None, description="Filtro opcional por rol (slug o ID) cuando se exportan usuarios"),
    role_id: Optional[int] = Query(None, description="Filtro opcional por role_id"),
    group_id: Optional[int] = Query(None, description="Filtro opcional por grupo comercial"),
    # Filtros para productos (solo aplican cuando type=productos)
    category_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    stock_filter: Optional[str] = Query(None),
    image: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    codebar_search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_order: Optional[str] = Query("asc"),
    current_user: User = Depends(require_permission("reports.export")),
    db: Session = Depends(get_db)
):
    """
    Exporta datos a XLSX de forma adaptativa según el recurso, rol dinámico y pantalla solicitada.
    Soporta:
    - clientes / customers: Aislamiento por rol comercial del usuario o global para admin.
    - productos / catalogo / inventario: Exporta catálogo filtrado por categoría, stock, búsqueda.
    - grupos / sales_groups: Exporta grupos y miembros según permisos de visibilidad.
    - usuarios / equipo / users: Exporta colaboradores, filtrable por rol, búsqueda, grupo y estado.
    - roles / permisos: Exporta catálogo de roles del sistema y matriz de permisos PBAC.
    - <slug_o_id_de_rol>: Exporta colaboradores pertenecientes a ese rol específico con sus grupos asignados.
    """
    target_type = type.strip().lower()
    target_role = None
    base_entities = (
        "clientes", "customers", "productos", "catalogo", "catalog",
        "inventario", "grupos", "sales_groups", "usuarios", "equipo", "users",
        "roles", "permisos"
    )

    # Identificar rol dinámico por ID numérico o slug
    if target_type not in base_entities:
        if target_type.isdigit():
            target_role = db.query(Role).filter(Role.role_id == int(target_type)).first()
        else:
            target_role = db.query(Role).filter(Role.slug == target_type).first()
            if not target_role:
                # Alias de conveniencia histórica
                if target_type in ("vendedor", "vendedores"):
                    target_role = db.query(Role).filter(Role.slug == "seller").first()
                elif target_type in ("almacen", "almacenista"):
                    target_role = db.query(Role).filter(Role.slug == "warehouse").first()

    # Si se solicitó exportar usuarios pero se especificó un rol por parámetro adicional
    if target_type in ("usuarios", "equipo", "users") and not target_role:
        if role_id:
            target_role = db.query(Role).filter(Role.role_id == role_id).first()
        elif role:
            r_str = role.strip()
            if r_str.isdigit():
                target_role = db.query(Role).filter(Role.role_id == int(r_str)).first()
            else:
                target_role = db.query(Role).filter(Role.slug == r_str.lower()).first()

    # Control de acceso PBAC granular por recurso y rol
    if not current_user.has_permission("system.admin"):
        if target_type in ("clientes", "customers"):
            if not current_user.has_permission("customers.view"):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requiere permiso 'customers.view' para exportar clientes")
        elif target_type in ("productos", "catalogo", "catalog", "inventario"):
            if not (current_user.has_permission("catalog.export") or current_user.has_permission("catalog.view")):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requiere permiso 'catalog.export' o 'catalog.view' para exportar catálogo/inventario")
        elif target_type in ("grupos", "sales_groups"):
            if not current_user.has_permission("groups.view"):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requiere permiso 'groups.view' para exportar grupos comerciales")
        elif target_type in ("roles", "permisos"):
            if not current_user.has_permission("users.view"):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requiere permiso 'users.view' para exportar configuración de roles")
        elif target_type in ("usuarios", "equipo", "users") or target_role is not None:
            if not current_user.has_permission("users.view"):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requiere permiso 'users.view' para exportar personal interno")
            if target_role and target_role.slug == "admin":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requiere privilegios de 'system.admin' para exportar usuarios administradores")
        else:
            active_slugs = [r[0] for r in db.query(Role.slug).filter(Role.is_active == True).all()]
            valid_options = ["clientes", "productos", "grupos", "usuarios", "roles"] + active_slugs
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de exportación '{type}' no soportado. Opciones válidas: {', '.join(valid_options)}"
            )

    if target_type not in base_entities and not target_role:
        active_slugs = [r[0] for r in db.query(Role.slug).filter(Role.is_active == True).all()]
        valid_options = ["clientes", "productos", "grupos", "usuarios", "roles"] + active_slugs
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de exportación '{type}' no soportado. Opciones válidas: {', '.join(valid_options)}"
        )

    wb = Workbook()
    ws = wb.active

    # Estilos para headers
    header_font = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")

    def style_headers(sheet, headers):
        sheet.append(headers)
        for col_idx, _ in enumerate(headers, 1):
            cell = sheet.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment

    def auto_width(sheet):
        for col in sheet.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                val = str(cell.value) if cell.value is not None else ""
                max_len = max(max_len, len(val))
            sheet.column_dimensions[col_letter].width = min(max_len + 3, 50)

    # -------------------------------------------------------------------------
    # 1. CLIENTES (Con aislamiento según rol de usuario / comercial)
    # -------------------------------------------------------------------------
    if target_type in ("clientes", "customers"):
        ws.title = "Clientes"
        style_headers(ws, [
            "ID", "Username", "Email", "Nombre Completo", "Activo", "Notificaciones", "Agente ID",
            "Razón Social", "RFC", "Grupo Ventas ID", "Lista Precios ID",
            "Dirección 1", "Dirección 2", "Dirección 3", "Teléfono 1", "Teléfono 2", "Creado"
        ])
        customers_list = crud_customer.get_customers(
            db, skip=0, limit=99999, search=search,
            user_id=current_user.user_id, user_role=current_user
        )
        for c in customers_list:
            ci = getattr(c, "customer_info", None)
            ws.append([
                c.customer_id, c.username, c.email, c.full_name, c.is_active,
                "Sí" if getattr(c, "notificate", False) else "No", c.agent_id,
                ci.business_name if ci else "", ci.rfc if ci else "",
                ci.sales_group_id if ci else "", ci.price_list_id if ci else "",
                ci.address_1 if ci else "", ci.address_2 if ci else "", ci.address_3 if ci else "",
                ci.telefono_1 if ci else "", ci.telefono_2 if ci else "",
                c.created_at.strftime("%Y-%m-%d %H:%M") if getattr(c, "created_at", None) else ""
            ])
        filename_label = "clientes"

    # -------------------------------------------------------------------------
    # 2. GRUPOS DE VENTA (Con aislamiento por roles no-admin)
    # -------------------------------------------------------------------------
    elif target_type in ("grupos", "sales_groups"):
        from db.base import OrderStat
        ws.title = "Grupos de Ventas"
        style_headers(ws, [
            "ID", "Nombre", "Descripción", "Activo",
            "Pedidos Pendientes", "Pedidos Aprobados", "Pedidos Enviados",
            "Pedidos Entregados", "Pedidos Cancelados", "Total Pedidos"
        ])
        group_query = db.query(SalesGroup)
        if not current_user.has_permission("system.admin") and not current_user.has_permission("groups.manage"):
            allowed_ids = get_user_groups(db, current_user.user_id)
            group_query = group_query.filter(SalesGroup.sales_group_id.in_(allowed_ids or [-1]))
        if search:
            group_query = group_query.filter(SalesGroup.group_name.ilike(f"%{search}%"))
        groups_list = group_query.order_by(SalesGroup.sales_group_id).all()

        for g in groups_list:
            stats = {row.status: row.count for row in db.query(OrderStat).filter(OrderStat.sales_group_id == g.sales_group_id).all()}
            pending = stats.get("pending_validation", 0)
            approved = stats.get("approved", 0)
            shipped = stats.get("shipped", 0)
            delivered = stats.get("delivered", 0)
            cancelled = stats.get("cancelled", 0)
            total = pending + approved + shipped + delivered + cancelled
            ws.append([
                g.sales_group_id, g.group_name, g.description, g.is_active,
                pending, approved, shipped, delivered, cancelled, total
            ])

        # Segunda hoja: Miembros
        ws2 = wb.create_sheet("Miembros")
        style_headers(ws2, ["Grupo ID", "Grupo Nombre", "Rol", "User ID", "Username", "Nombre Completo"])
        member_query = db.query(GroupUser)
        if not current_user.has_permission("system.admin") and not current_user.has_permission("groups.manage"):
            allowed_ids = get_user_groups(db, current_user.user_id)
            member_query = member_query.filter(GroupUser.sales_group_id.in_(allowed_ids or [-1]))
        for gu in member_query.all():
            group = gu.sales_group
            user = gu.user
            tipo = (user.role_name or user.role_slug) if user else "Usuario"
            ws2.append([
                group.sales_group_id if group else "", group.group_name if group else "",
                tipo, user.user_id if user else "", user.username if user else "",
                user.full_name if user else ""
            ])
        auto_width(ws2)
        filename_label = "grupos_y_miembros"

    # -------------------------------------------------------------------------
    # 3. PRODUCTOS / INVENTARIO
    # -------------------------------------------------------------------------
    elif target_type in ("productos", "catalogo", "catalog", "inventario"):
        ws.title = "Productos"
        can_view_cost = current_user.has_permission("products.cost") or current_user.has_permission("system.admin") or current_user.has_permission("catalog.prices")
        headers = ["ID", "Código Barras", "Nombre", "Descripción", "Desc. 2", "Unidad"]
        if can_view_cost:
            headers.append("Precio Base")
        headers.extend(["IVA %", "Stock", "Activo", "Categoría ID"])
        style_headers(ws, headers)
        productos = get_products(
            db,
            skip=0,
            limit=99999,
            category_id=category_id,
            is_active=is_active,
            stock_filter=stock_filter,
            image=image,
            search=search,
            codebar_search=codebar_search,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        for p in productos:
            row = [
                p.product_id, p.codebar, p.name, p.description, p.descripcion_2,
                p.unidad_medida
            ]
            if can_view_cost:
                row.append(float(p.base_price) if p.base_price else 0)
            row.extend([
                float(p.iva_percentage) if p.iva_percentage else 0,
                p.stock_count, p.is_active, p.category_id
            ])
            ws.append(row)
        filename_label = "inventario"

    # -------------------------------------------------------------------------
    # 4. ROLES Y PERMISOS PBAC (Configuración de Roles de la plataforma)
    # -------------------------------------------------------------------------
    elif target_type in ("roles", "permisos"):
        ws.title = "Roles del Sistema"
        style_headers(ws, ["ID", "Nombre", "Identificador (Slug)", "Descripción", "Sistema", "Activo", "Total Usuarios", "Permisos Asignados"])
        roles_list = db.query(Role).order_by(Role.role_id).all()
        for r in roles_list:
            u_count = db.query(func.count(User.user_id)).filter(User.role_id == r.role_id).scalar() or 0
            perm_codes = ", ".join([p.permission_code for p in r.permissions]) if r.permissions else ""
            ws.append([
                r.role_id, r.name, r.slug, r.description or "",
                "Sí" if r.is_system else "No", "Activo" if r.is_active else "Inactivo",
                u_count, perm_codes
            ])
        filename_label = "roles_y_permisos"

    # -------------------------------------------------------------------------
    # 5. ROL ESPECÍFICO DINÁMICO (Cualquier N rol configurado en la BD)
    # -------------------------------------------------------------------------
    elif target_role is not None:
        ws.title = target_role.name[:30]
        style_headers(ws, ["ID", "Username", "Email", "Nombre Completo", "Rol", "Grupos Asignados", "Activo", "Creado"])
        query = db.query(User).filter(User.role_id == target_role.role_id)
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        if search:
            query = query.filter(
                or_(
                    User.full_name.ilike(f"%{search}%"),
                    User.username.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%")
                )
            )
        if group_id:
            query = query.join(GroupUser, User.user_id == GroupUser.user_id).filter(GroupUser.sales_group_id == group_id)
        users_to_export = query.order_by(User.user_id).all()
        for u in users_to_export:
            groups_str = ", ".join([gm.sales_group.group_name for gm in u.group_memberships if gm.sales_group])
            ws.append([
                u.user_id, u.username, u.email, u.full_name, target_role.name,
                groups_str or "Sin grupo", u.is_active,
                u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else ""
            ])
        filename_label = target_role.slug

    # -------------------------------------------------------------------------
    # 6. EQUIPO COMPLETO DE USUARIOS (Con todos sus N roles dinámicos)
    # -------------------------------------------------------------------------
    elif target_type in ("usuarios", "equipo", "users"):
        ws.title = "Equipo de Usuarios"
        style_headers(ws, ["ID", "Username", "Email", "Nombre Completo", "Rol", "Slug Rol", "Grupos Asignados", "Activo", "Creado"])
        query = db.query(User).join(Role, User.role_id == Role.role_id)
        if not current_user.has_permission("system.admin"):
            query = query.filter(Role.slug != "admin")
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        if search:
            query = query.filter(
                or_(
                    User.full_name.ilike(f"%{search}%"),
                    User.username.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%")
                )
            )
        if group_id:
            query = query.join(GroupUser, User.user_id == GroupUser.user_id).filter(GroupUser.sales_group_id == group_id)
        users_to_export = query.order_by(User.user_id).all()
        for u in users_to_export:
            groups_str = ", ".join([gm.sales_group.group_name for gm in u.group_memberships if gm.sales_group])
            ws.append([
                u.user_id, u.username, u.email, u.full_name,
                u.role_name or u.role, u.role_slug or "",
                groups_str or "Sin grupo", u.is_active,
                u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else ""
            ])
        filename_label = "equipo_usuarios"

    auto_width(ws)

    # Generar respuesta
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"profarmed_{filename_label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
