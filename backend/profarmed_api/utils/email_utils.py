"""
Utilidades para envío de Correos Electrónicos - PROFARMED
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from datetime import datetime

from core.config import settings

# Configurar logging
logger = logging.getLogger(__name__)

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f8fafc;
            color: #1a1a1a;
            margin: 0;
            padding: 0;
            -webkit-font-smoothing: antialiased;
        }}
        .wrapper {{
            width: 100%;
            background-color: #f8fafc;
            padding: 24px 0;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid #e5e7eb;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01);
        }}
        .header {{
            background: linear-gradient(135deg, {primary_color} 0%, {primary_dark} 100%);
            padding: 32px 24px;
            text-align: center;
        }}
        .header-badge {{
            display: inline-block;
            background: rgba(255, 255, 255, 0.22);
            color: #ffffff;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            padding: 4px 14px;
            border-radius: 20px;
            margin-bottom: 12px;
        }}
        .header h1 {{
            color: #ffffff;
            margin: 0;
            font-size: 26px;
            font-weight: 800;
            letter-spacing: -0.03em;
        }}
        .content {{
            padding: 28px 24px;
            line-height: 1.65;
        }}
        .content h2 {{
            color: #1a1a1a;
            font-size: 20px;
            font-weight: 700;
            margin-top: 0;
            margin-bottom: 16px;
            letter-spacing: -0.02em;
        }}
        .content p {{
            margin-top: 0;
            margin-bottom: 20px;
            color: #4b5563;
            font-size: 15px;
        }}
        .button-container {{
            text-align: center;
            margin: 32px 0 16px 0;
        }}
        .button {{
            display: inline-block;
            background: linear-gradient(135deg, {primary_color} 0%, {primary_dark} 100%);
            color: #ffffff !important;
            text-decoration: none;
            padding: 14px 32px;
            border-radius: 10px;
            font-size: 15px;
            font-weight: 700;
            letter-spacing: 0.02em;
            box-shadow: 0 4px 14px 0 {shadow_color};
        }}
        .footer {{
            background-color: #f8fafc;
            padding: 24px 20px;
            text-align: center;
            border-top: 1px solid #e5e7eb;
        }}
        .footer p {{
            margin: 0;
            margin-bottom: 8px;
            color: #9ca3af;
            font-size: 12px;
            line-height: 1.5;
        }}
        .footer a {{
            color: {primary_color};
            text-decoration: underline;
            font-weight: 600;
        }}

        @media only screen and (max-width: 600px) {{
            .wrapper {{
                padding: 12px 0 !important;
            }}
            .container {{
                border-radius: 12px !important;
                border-left: none !important;
                border-right: none !important;
            }}
            .header {{
                padding: 24px 16px !important;
            }}
            .header h1 {{
                font-size: 22px !important;
            }}
            .content {{
                padding: 20px 14px !important;
            }}
            .content h2 {{
                font-size: 18px !important;
            }}
            .content p {{
                font-size: 14px !important;
            }}
            .button {{
                padding: 12px 24px !important;
                font-size: 14px !important;
                width: 85% !important;
                box-sizing: border-box !important;
            }}
            .footer {{
                padding: 20px 14px !important;
            }}
        }}
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="container">
            <div class="header">
                <div class="header-badge">Notificación Oficial</div>
                <h1>{brand_name}</h1>
            </div>
            <div class="content">
                {body_content}
            </div>
            <div class="footer">
                <p>Este es un correo automático, por favor no respondas directamente.</p>
                <p>&copy; {year} {brand_name}. Todos los derechos reservados.</p>
                <p>¿No deseas recibir notificaciones? Puedes cambiar tus preferencias en tu <a href="{profile_url}">perfil de usuario</a>.</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

def parse_recipient_emails(raw_email: str) -> list[str]:
    """
    Parsea una cadena de correos que puede contener múltiples direcciones separadas por ';' o ','.
    Filtra correos válidos, elimina duplicados manteniendo el orden y limita a un máximo de 3 destinatarios.
    """
    if not raw_email:
        return []
    
    clean_raw = raw_email.replace('\r', '').replace('\n', '')
    parts = clean_raw.replace(',', ';').split(';')
    valid_emails = []
    for part in parts:
        email = part.strip()
        if email and '@' in email and email.lower() not in [e.lower() for e in valid_emails]:
            valid_emails.append(email)
            if len(valid_emails) == 3:
                break
                
    return valid_emails


def send_email_background(to_email: str, subject: str, html_body: str, reply_to: str = None, brand_name: str = None) -> bool:
    """
    Función genérica para enviar emails en segundo plano.
    """
    try:
        recipient_emails = parse_recipient_emails(to_email)
        if not recipient_emails:
            logger.warning(f"No hay direcciones de correo válidas destinatarias en '{to_email}'. Se omite el envío.")
            return False

        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.warning("SMTP_USER o SMTP_PASSWORD no están configurados. El envío de correo se simulará.")
            logger.info(f"[EMAIL MOCK] Destinatario(s): {', '.join(recipient_emails)}, Asunto: {subject}")
            return False
            
        if "gmail" in settings.SMTP_HOST.lower():
            sender_email = settings.SMTP_USER
        else:
            sender_email = getattr(settings, 'SENDER', settings.SMTP_USER)
            
        if sender_email and sender_email.startswith("MS_"):
            parts = sender_email.split("@")
            if len(parts) == 2:
                domain = parts[1]
                if "mlsender.net" in domain:
                    sender_email = f"info@{domain}"
                elif "profarmed.com.mx" in domain:
                    sender_email = f"notificaciones@{domain}"
                else:
                    sender_email = f"notificaciones.profarmed@{domain}"
            
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        
        display_name = brand_name or "Profarmed"
        msg["From"] = f"{display_name} <{sender_email}>"
        msg["To"] = ", ".join(recipient_emails)
        
        if reply_to:
            msg["Reply-To"] = reply_to
            
        part = MIMEText(html_body, "html")
        msg.attach(part)
        
        logger.info(f"Conectando al servidor SMTP {settings.SMTP_HOST}:{settings.SMTP_PORT}...")
        smtp_port = int(settings.SMTP_PORT or 587)
        
        if smtp_port == 465:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, smtp_port, timeout=10) as server:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(sender_email, recipient_emails, msg.as_string())
        else:
            with smtplib.SMTP(settings.SMTP_HOST, smtp_port, timeout=10) as server:
                try:
                    server.starttls()
                except smtplib.SMTPNotSupportedError:
                    logger.warning("STARTTLS no es soportado por el servidor SMTP, continuando transmisión...")
                except Exception as tls_err:
                    logger.warning(f"Aviso en starttls: {tls_err}, continuando envío...")
                
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(sender_email, recipient_emails, msg.as_string())
            
        logger.info(f"Email enviado exitosamente a {', '.join(recipient_emails)}")
        return True
        
    except Exception as e:
        logger.error(f"Error enviando email a {to_email}: {str(e)}")
        return False

def send_order_shipped_email(to_email: str, order_id: int, customer_name: str) -> bool:
    """
    Envía un correo notificando que el pedido ha sido enviado.
    Soporta pedidos masivos (ej. 100+ productos) limitando visualmente a los primeros 15
    para evitar que Gmail u Outlook recorten el correo por sobrepeso.
    """
    primary_color = "#4F46E5"
    primary_dark = "#4338CA"
    shadow_color = "rgba(79, 70, 229, 0.35)"
    brand_name = "Profarmed"
    year = datetime.now().year
    
    base_url = "https://profarmed.com.mx"
    if settings.FRONTEND_URL and settings.FRONTEND_URL != "*":
        base_url = settings.FRONTEND_URL.rstrip("/")
        
    profile_url = f"{base_url}/profile"
    orders_url = f"{base_url}/profile"
    
    subject = f"Tu pedido #{order_id} ha sido enviado"
    
    items_html = ""
    subtotal_val = 0.0
    shipping_val = 0.0
    total_val = 0.0
    
    from db.session import SessionLocal
    from db.base import Order, OrderItem, Product
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if order:
            shipping_val = float(order.shipping_cost or 0)
            total_val = float(order.total_amount or 0)
            
            # Calcular subtotal exacto de TODOS los items
            for item in order.items:
                u_price = float(item.final_price or 0)
                subtotal_val += u_price * item.quantity
                
            # Limitar visualmente a máximo 15 items para evitar 'email clipping'
            MAX_DISPLAY_ITEMS = 15
            all_items = list(order.items)
            total_item_count = len(all_items)
            display_items = all_items[:MAX_DISPLAY_ITEMS]
            more_items_count = total_item_count - len(display_items)
            
            rows = []
            for item in display_items:
                prod_name = item.product.name if item.product else f"Producto {item.product_id}"
                qty = item.quantity
                u_price = float(item.final_price or 0)
                sub_price = u_price * qty
                
                rows.append(f"""
                <tr>
                    <td style="padding: 10px 10px; border-bottom: 1px solid #f1f5f9; color: #334155; font-weight: 500; word-break: break-word; overflow-wrap: break-word;">{prod_name}</td>
                    <td style="padding: 10px 6px; border-bottom: 1px solid #f1f5f9; text-align: center; color: #64748b; font-weight: 600;">{qty}</td>
                    <td style="padding: 10px 8px; border-bottom: 1px solid #f1f5f9; text-align: right; color: #475569; white-space: nowrap;">${u_price:,.2f}</td>
                    <td style="padding: 10px 10px; border-bottom: 1px solid #f1f5f9; text-align: right; color: #0f172a; font-weight: 600; white-space: nowrap;">${sub_price:,.2f}</td>
                </tr>
                """)
            
            if more_items_count > 0:
                rows.append(f"""
                <tr>
                    <td colspan="4" style="padding: 12px 10px; text-align: center; color: #64748b; font-size: 13px; font-weight: 600; background-color: #f8fafc; border-bottom: 1px solid #e2e8f0;">
                        ... y {more_items_count} producto{'s' if more_items_count > 1 else ''} más en este pedido
                    </td>
                </tr>
                """)
            
            if subtotal_val == 0.0:
                subtotal_val = max(0.0, total_val - shipping_val)
                
            items_html = "".join(rows)
    except Exception as e:
        logger.error(f"Error cargando detalles del pedido para email: {str(e)}")
    finally:
        db.close()
        
    summary_table_html = ""
    if items_html:
        summary_table_html = f"""
        <div style="background: #f8fafc; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; margin-top: 24px; width: 100%;">
            <div style="background: #f1f5f9; padding: 12px 14px; font-size: 12px; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #e2e8f0;">
                Resumen del Pedido #{order_id}
            </div>
            <div style="overflow-x: auto; width: 100%; -webkit-overflow-scrolling: touch;">
                <table style="width: 100%; min-width: 280px; border-collapse: collapse; font-size: 13px; background-color: #ffffff; table-layout: auto;">
                    <thead>
                        <tr style="background-color: #ffffff;">
                            <th style="padding: 10px 10px; text-align: left; font-weight: 700; color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 1px solid #e2e8f0;">Producto</th>
                            <th style="padding: 10px 6px; text-align: center; font-weight: 700; color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 1px solid #e2e8f0; width: 45px;">Cant.</th>
                            <th style="padding: 10px 8px; text-align: right; font-weight: 700; color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 1px solid #e2e8f0; width: 75px;">Precio</th>
                            <th style="padding: 10px 10px; text-align: right; font-weight: 700; color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 1px solid #e2e8f0; width: 75px;">Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_html}
                    </tbody>
                </table>
            </div>
            
            <table style="width: 100%; border-top: 1px solid #e2e8f0; background-color: #f8fafc; padding: 12px 14px; font-size: 13px;">
                <tr>
                    <td style="text-align: right; color: #64748b; padding: 4px 6px;">Subtotal:</td>
                    <td style="text-align: right; font-weight: 600; color: #1e293b; padding: 4px 6px; width: 85px;">${subtotal_val:,.2f}</td>
                </tr>
                <tr>
                    <td style="text-align: right; color: #64748b; padding: 4px 6px;">Envío:</td>
                    <td style="text-align: right; font-weight: 600; color: #1e293b; padding: 4px 6px; width: 85px;">${shipping_val:,.2f}</td>
                </tr>
                <tr style="font-size: 15px; font-weight: 700;">
                    <td style="text-align: right; color: #0f172a; padding: 6px 6px 4px 6px;">Total:</td>
                    <td style="text-align: right; color: {primary_color}; padding: 6px 6px 4px 6px; width: 85px; font-size: 16px;">${total_val:,.2f}</td>
                </tr>
            </table>
        </div>
        """
    
    body_content = f"""
    <h2>¡Hola, {customer_name}!</h2>
    <p>Te informamos que tu pedido <strong>#{order_id}</strong> ha sido enviado y está en camino.</p>
    <p>Pronto recibirás tus productos en el domicilio indicado. Puedes consultar el detalle de tu pedido ingresando a tu perfil.</p>
    
    {summary_table_html}
    
    <div class="button-container">
        <a href="{orders_url}" class="button">Ver Mi Pedido</a>
    </div>
    """
    
    html_body = HTML_TEMPLATE.format(
        subject=subject,
        primary_color=primary_color,
        primary_dark=primary_dark,
        shadow_color=shadow_color,
        brand_name=brand_name,
        body_content=body_content,
        year=year,
        profile_url=profile_url
    )
    
    return send_email_background(to_email, subject, html_body, brand_name=brand_name)

def send_order_delivered_email(to_email: str, order_id: int, customer_name: str) -> bool:
    """
    Envía un correo notificando que el pedido ha sido entregado.
    Soporta pedidos masivos (ej. 100+ productos) limitando visualmente a los primeros 15.
    """
    primary_color = "#4F46E5"
    primary_dark = "#4338CA"
    shadow_color = "rgba(79, 70, 229, 0.35)"
    brand_name = "Profarmed"
    year = datetime.now().year
    
    base_url = "https://profarmed.com.mx"
    if settings.FRONTEND_URL and settings.FRONTEND_URL != "*":
        base_url = settings.FRONTEND_URL.rstrip("/")
        
    profile_url = f"{base_url}/profile"
    orders_url = f"{base_url}/profile"
    
    subject = f"Tu pedido #{order_id} ha sido entregado"
    
    items_html = ""
    subtotal_val = 0.0
    shipping_val = 0.0
    total_val = 0.0
    
    from db.session import SessionLocal
    from db.base import Order, OrderItem, Product
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if order:
            shipping_val = float(order.shipping_cost or 0)
            total_val = float(order.total_amount or 0)
            
            # Calcular subtotal exacto de TODOS los items
            for item in order.items:
                u_price = float(item.final_price or 0)
                subtotal_val += u_price * item.quantity
                
            # Limitar visualmente a máximo 15 items para evitar 'email clipping'
            MAX_DISPLAY_ITEMS = 15
            all_items = list(order.items)
            total_item_count = len(all_items)
            display_items = all_items[:MAX_DISPLAY_ITEMS]
            more_items_count = total_item_count - len(display_items)
            
            rows = []
            for item in display_items:
                prod_name = item.product.name if item.product else f"Producto {item.product_id}"
                qty = item.quantity
                u_price = float(item.final_price or 0)
                sub_price = u_price * qty
                
                rows.append(f"""
                <tr>
                    <td style="padding: 10px 10px; border-bottom: 1px solid #f1f5f9; color: #334155; font-weight: 500; word-break: break-word; overflow-wrap: break-word;">{prod_name}</td>
                    <td style="padding: 10px 6px; border-bottom: 1px solid #f1f5f9; text-align: center; color: #64748b; font-weight: 600;">{qty}</td>
                    <td style="padding: 10px 8px; border-bottom: 1px solid #f1f5f9; text-align: right; color: #475569; white-space: nowrap;">${u_price:,.2f}</td>
                    <td style="padding: 10px 10px; border-bottom: 1px solid #f1f5f9; text-align: right; color: #0f172a; font-weight: 600; white-space: nowrap;">${sub_price:,.2f}</td>
                </tr>
                """)
            
            if more_items_count > 0:
                rows.append(f"""
                <tr>
                    <td colspan="4" style="padding: 12px 10px; text-align: center; color: #64748b; font-size: 13px; font-weight: 600; background-color: #f8fafc; border-bottom: 1px solid #e2e8f0;">
                        ... y {more_items_count} producto{'s' if more_items_count > 1 else ''} más en este pedido
                    </td>
                </tr>
                """)
            
            if subtotal_val == 0.0:
                subtotal_val = max(0.0, total_val - shipping_val)
                
            items_html = "".join(rows)
    except Exception as e:
        logger.error(f"Error cargando detalles del pedido para email: {str(e)}")
    finally:
        db.close()
        
    summary_table_html = ""
    if items_html:
        summary_table_html = f"""
        <div style="background: #f8fafc; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; margin-top: 24px; width: 100%;">
            <div style="background: #f1f5f9; padding: 12px 14px; font-size: 12px; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #e2e8f0;">
                Resumen del Pedido #{order_id}
            </div>
            <div style="overflow-x: auto; width: 100%; -webkit-overflow-scrolling: touch;">
                <table style="width: 100%; min-width: 280px; border-collapse: collapse; font-size: 13px; background-color: #ffffff; table-layout: auto;">
                    <thead>
                        <tr style="background-color: #ffffff;">
                            <th style="padding: 10px 10px; text-align: left; font-weight: 700; color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 1px solid #e2e8f0;">Producto</th>
                            <th style="padding: 10px 6px; text-align: center; font-weight: 700; color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 1px solid #e2e8f0; width: 45px;">Cant.</th>
                            <th style="padding: 10px 8px; text-align: right; font-weight: 700; color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 1px solid #e2e8f0; width: 75px;">Precio</th>
                            <th style="padding: 10px 10px; text-align: right; font-weight: 700; color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 1px solid #e2e8f0; width: 75px;">Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_html}
                    </tbody>
                </table>
            </div>
            
            <table style="width: 100%; border-top: 1px solid #e2e8f0; background-color: #f8fafc; padding: 12px 14px; font-size: 13px;">
                <tr>
                    <td style="text-align: right; color: #64748b; padding: 4px 6px;">Subtotal:</td>
                    <td style="text-align: right; font-weight: 600; color: #1e293b; padding: 4px 6px; width: 85px;">${subtotal_val:,.2f}</td>
                </tr>
                <tr>
                    <td style="text-align: right; color: #64748b; padding: 4px 6px;">Envío:</td>
                    <td style="text-align: right; font-weight: 600; color: #1e293b; padding: 4px 6px; width: 85px;">${shipping_val:,.2f}</td>
                </tr>
                <tr style="font-size: 15px; font-weight: 700;">
                    <td style="text-align: right; color: #0f172a; padding: 6px 6px 4px 6px;">Total:</td>
                    <td style="text-align: right; color: {primary_color}; padding: 6px 6px 4px 6px; width: 85px; font-size: 16px;">${total_val:,.2f}</td>
                </tr>
            </table>
        </div>
        """
    
    body_content = f"""
    <h2>¡Hola, {customer_name}!</h2>
    <p>Queremos informarte que tu pedido <strong>#{order_id}</strong> ha sido entregado exitosamente.</p>
    <p>Agradecemos tu preferencia. Si tienes alguna duda, comentario o necesitas ayuda, puedes ponerte en contacto con nosotros.</p>
    
    {summary_table_html}
    
    <div class="button-container">
        <a href="{orders_url}" class="button">Ver Mi Pedido</a>
    </div>
    """
    
    html_body = HTML_TEMPLATE.format(
        subject=subject,
        primary_color=primary_color,
        primary_dark=primary_dark,
        shadow_color=shadow_color,
        brand_name=brand_name,
        body_content=body_content,
        year=year,
        profile_url=profile_url
    )
    
    return send_email_background(to_email, subject, html_body, brand_name=brand_name)

def send_announcement_email(to_email: str, title: str, content: str, img_url: str = None) -> bool:
    """
    Envía un correo con una promoción / aviso.
    """
    primary_color = "#4F46E5"
    primary_dark = "#4338CA"
    shadow_color = "rgba(79, 70, 229, 0.35)"
    brand_name = "Profarmed"
    year = datetime.now().year
    
    base_url = "https://profarmed.com.mx"
    if settings.FRONTEND_URL and settings.FRONTEND_URL != "*":
        base_url = settings.FRONTEND_URL.rstrip("/")
        
    profile_url = f"{base_url}/profile"
    store_url = base_url
    
    subject = f"Nueva Promocion: {title}"
    
    img_html = ""
    if img_url:
        img_html = f"""
        <div style="margin: 24px 0; text-align: center; border-radius: 12px; overflow: hidden; max-height: 400px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); border: 1px solid #e2e8f0;">
            <img src="{img_url}" alt="{title}" style="max-width: 100%; height: auto; display: block; margin: 0 auto; border-radius: 12px;" />
        </div>
        """
        
    formatted_content = "".join([f"<p style='margin-bottom: 16px; font-size: 15px; color: #475569; line-height: 1.7;'>{line}</p>" for line in content.split("\n") if line.strip()])
    
    body_content = f"""
    <h2 style="color: #0f172a; font-size: 22px; font-weight: 800; margin-bottom: 20px; line-height: 1.3; letter-spacing: -0.02em;">{title}</h2>
    
    {img_html}
    
    <div style="margin-bottom: 32px;">
        {formatted_content}
    </div>
    
    <div class="button-container">
        <a href="{store_url}" class="button">Visitar Tienda Oficial</a>
    </div>
    """
    
    html_body = HTML_TEMPLATE.format(
        subject=subject,
        primary_color=primary_color,
        primary_dark=primary_dark,
        shadow_color=shadow_color,
        brand_name=brand_name,
        body_content=body_content,
        year=year,
        profile_url=profile_url
    )
    
    return send_email_background(to_email, subject, html_body, brand_name=brand_name)


def send_mass_announcement_emails(
    recipient_emails: list[str],
    title: str,
    content: str,
    img_url: str = None,
    brand_name: str = None
) -> dict:
    """
    Envía promociones/avisos de manera masiva (ej. 1,000+ clientes) reutilizando
    una única sesión SMTP persistente para máxima eficiencia sin congelar la API.
    """
    if not recipient_emails:
        return {"sent": 0, "failed": 0, "total": 0}
        
    display_brand = brand_name or "Profarmed"
    primary_color = "#4F46E5"
    primary_dark = "#4338CA"
    shadow_color = "rgba(79, 70, 229, 0.35)"
    year = datetime.now().year
    
    base_url = "https://profarmed.com.mx"
    if settings.FRONTEND_URL and settings.FRONTEND_URL != "*":
        base_url = settings.FRONTEND_URL.rstrip("/")
        
    profile_url = f"{base_url}/profile"
    store_url = base_url
    subject = f"Nueva Promocion: {title}"
    
    img_html = ""
    if img_url:
        img_html = f"""
        <div style="margin: 24px 0; text-align: center; border-radius: 12px; overflow: hidden; max-height: 400px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); border: 1px solid #e2e8f0;">
            <img src="{img_url}" alt="{title}" style="max-width: 100%; height: auto; display: block; margin: 0 auto; border-radius: 12px;" />
        </div>
        """
        
    formatted_content = "".join([f"<p style='margin-bottom: 16px; font-size: 15px; color: #475569; line-height: 1.7;'>{line}</p>" for line in content.split("\n") if line.strip()])
    
    body_content = f"""
    <h2 style="color: #0f172a; font-size: 22px; font-weight: 800; margin-bottom: 20px; line-height: 1.3; letter-spacing: -0.02em;">{title}</h2>
    {img_html}
    <div style="margin-bottom: 32px;">
        {formatted_content}
    </div>
    <div class="button-container">
        <a href="{store_url}" class="button">Visitar Tienda Oficial</a>
    </div>
    """
    
    html_body = HTML_TEMPLATE.format(
        subject=subject,
        primary_color=primary_color,
        primary_dark=primary_dark,
        shadow_color=shadow_color,
        brand_name=display_brand,
        body_content=body_content,
        year=year,
        profile_url=profile_url
    )
    
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning(f"[MASS EMAIL MOCK] Simulación de envío a {len(recipient_emails)} destinatarios.")
        return {"sent": len(recipient_emails), "failed": 0, "total": len(recipient_emails)}
        
    sender_email = getattr(settings, 'SENDER', settings.SMTP_USER)
    if sender_email and sender_email.startswith("MS_"):
        parts = sender_email.split("@")
        if len(parts) == 2:
            domain = parts[1]
            if "mlsender.net" in domain:
                sender_email = f"info@{domain}"
            elif "profarmed.com.mx" in domain:
                sender_email = f"notificaciones@{domain}"
            else:
                sender_email = f"notificaciones.profarmed@{domain}"

    smtp_port = int(settings.SMTP_PORT or 587)
    sent_count = 0
    fail_count = 0
    
    try:
        def _send_loop(server):
            nonlocal sent_count, fail_count
            for email in recipient_emails:
                try:
                    clean_email = email.strip()
                    if not clean_email or '@' not in clean_email:
                        fail_count += 1
                        continue
                        
                    msg = MIMEMultipart("alternative")
                    msg["Subject"] = subject
                    msg["From"] = f"{display_brand} <{sender_email}>"
                    msg["To"] = clean_email
                    msg.attach(MIMEText(html_body, "html"))
                    
                    server.sendmail(sender_email, [clean_email], msg.as_string())
                    sent_count += 1
                except Exception as item_err:
                    logger.error(f"Error enviando correo a {email}: {item_err}")
                    fail_count += 1

        logger.info(f"Iniciando envío masivo a {len(recipient_emails)} destinatarios...")
        if smtp_port == 465:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, smtp_port, timeout=15) as server:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                _send_loop(server)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, smtp_port, timeout=15) as server:
                try:
                    server.starttls()
                except Exception:
                    pass
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                _send_loop(server)
                
    except Exception as connection_err:
        logger.error(f"Error en sesión SMTP masiva: {connection_err}")

    logger.info(f"Envío masivo completado. Éxito: {sent_count}, Fallidos: {fail_count}")
    return {"sent": sent_count, "failed": fail_count, "total": len(recipient_emails)}
