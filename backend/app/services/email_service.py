import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv 
from datetime import datetime

# Cargar variables de entorno
load_dotenv()

class EmailService:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = os.getenv("SMTP_USER")
        self.sender_password = os.getenv("SMTP_PASSWORD")
        self.receiver_email = os.getenv("JEFE_COMPRAS_EMAIL")

    def format_currency(self, value):
        """Convierte números a formato visual colombiano ($ 12.500)"""
        try:
            if value is None or value == 0: return '<span style="color:#ccc">--</span>'
            val = float(value)
            return "$ {:,.0f}".format(val).replace(",", ".")
        except:
            return "$ 0"
            
    def format_percentage(self, value):
        try:
            val = float(value)
            # Si viene en decimal (0.05), pasarlo a entero (5)
            # Si ya viene en entero (5.0), dejarlo así.
            # Asumimos que si es < 1.0 es decimal porcentual
            if abs(val) <= 1.0 and val != 0: 
                val = val * 100
            return f"{val:.1f}%"
        except:
            return "0%"

    # --- CAMBIO 1: AHORA ES ASYNC PARA PODER USAR AWAIT EN MAIN.PY ---
    async def send_alert(self, data):
        if not self.sender_email or not self.sender_password:
            print("⚠️ Faltan credenciales de email.")
            return

        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = self.receiver_email
        
        # Datos generales
        factura_id = data.get('factura_id', 'SIN-ID')
        estado_global = data.get('status', 'ALERTA')
        proveedor = data.get('proveedor', 'Desconocido')
        desviacion = data.get('desviacion_porcentual', 0)
        
        msg['Subject'] = f"[{estado_global}] Factura {factura_id} - {proveedor}"

        # --- CAMBIO 2: LÓGICA DE COLORES DEL ENCABEZADO ---
        if estado_global == "ROJO":
            header_bg = "#d32f2f" # Rojo
            header_text = "#ffffff"
        elif estado_global == "AMARILLO":
            header_bg = "#fbc02d" # Amarillo mostaza
            header_text = "#000000" # Texto negro para leer mejor
        else:
            header_bg = "#2e7d32" # Verde
            header_text = "#ffffff"

        # --- CONSTRUCCIÓN DE FILAS (TABLA) ---
        items_html = ""
        items = data.get('items', [])
        
        # Compatibilidad: Si items viene vacio, intentar buscar en matchResults
        if not items: items = data.get('matchResults', [])

        for item in items:
            # Extracción de datos
            nombre = item.get('product_name', item.get('original_name', '---'))
            match_name = item.get('matched_name', '')
            
            precio_factura = float(item.get('unit_price', 0))
            precio_esperado = float(item.get('expected_price', 0))
            cantidad = item.get('quantity', 0)
            
            # En main.py guardamos 'score', aseguramos leerlo
            similarity = item.get('score', item.get('similarity', 0))

            # --- LÓGICA DE ERROR DE PRECIO ---
            es_error_precio = False
            error_msg = ""
            
            if precio_esperado > 0:
                if precio_factura > precio_esperado:
                    diff = precio_factura - precio_esperado
                    pct_diff = (diff / precio_esperado)
                    
                    # Marcar rojo si la diferencia es > 5% en el item individual
                    if pct_diff > 0.05:
                        es_error_precio = True
                        error_msg = f'<div style="color: #d32f2f; font-weight:bold; font-size:11px;">⚠️ +{pct_diff*100:.0f}% Sobreprecio</div>'

            # Estilos de fila
            bg_color = "#fff0f0" if es_error_precio else "#ffffff"
            text_color = "#b71c1c" if es_error_precio else "#333333"
            
            # Subtitulo del match
            match_html = ""
            if match_name and match_name != "No encontrado" and match_name != nombre:
                match_html = f'<div style="color: #666; font-size: 11px; font-style: italic;">DB: {match_name}</div>'

            # Construcción de la fila
            items_html += f"""
            <tr style="background-color: {bg_color}; border-bottom: 1px solid #eee;">
                <td style="padding: 10px; color: {text_color}; vertical-align: middle;">
                    <strong>{nombre}</strong>
                    {match_html}
                    {error_msg}
                </td>
                <td style="padding: 10px; text-align: center;">{cantidad}</td>
                <td style="padding: 10px; text-align: right; font-weight: bold;">{self.format_currency(precio_factura)}</td>
                <td style="padding: 10px; text-align: right; color: #555;">{self.format_currency(precio_esperado)}</td>
                <td style="padding: 10px; text-align: center;">
                    <span style="background: #eee; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold;">
                        {self.format_percentage(similarity)}
                    </span>
                </td>
            </tr>
            """

        totales = data.get('totales', {})
        if not totales: totales = data.get('totals', {})

        # --- HTML EMAIL TEMPLATE ---
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; background-color: #f4f4f4; padding: 20px;">
            <div style="max-width: 650px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                
                <div style="background-color: {header_bg}; color: {header_text}; padding: 20px; text-align: center;">
                    <h2 style="margin:0;">Reporte: {estado_global}</h2>
                    <p style="margin:5px 0 0;">{proveedor} | ID: {factura_id}</p>
                    <p style="margin:5px 0 0; font-size: 14px;">Desviación Total: <strong>{self.format_percentage(desviacion)}</strong></p>
                </div>
                
                <div style="padding: 20px;">
                    <table style="width: 100%; margin-bottom: 20px; background: #f8f9fa; padding: 10px; border-radius: 6px;">
                        <tr>
                            <td><strong>Total Esperado:</strong> <br> {self.format_currency(totales.get('esperado', totales.get('total_esperado')))}</td>
                            <td><strong>Total Facturado:</strong> <br> <span style="font-size:1.2em; color:#000;">{self.format_currency(totales.get('facturado', totales.get('total_facturado')))}</span></td>
                            <td style="text-align:right;"><strong>Diferencia:</strong> <br> <span style="color: #d32f2f; font-weight:bold;">{self.format_currency(totales.get('diferencia', 0))}</span></td>
                        </tr>
                    </table>

                    <h3 style="border-bottom: 2px solid #ddd; padding-bottom: 5px;">Detalle de Items</h3>
                    <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                        <thead>
                            <tr style="background-color: #eee; text-transform: uppercase; color: #666; font-size: 11px;">
                                <th style="padding: 8px; text-align: left;">Producto</th>
                                <th style="padding: 8px; text-align: center;">Cant.</th>
                                <th style="padding: 8px; text-align: right;">Factura</th>
                                <th style="padding: 8px; text-align: right;">Bodega</th>
                                <th style="padding: 8px; text-align: center;">Similitud</th>
                            </tr>
                        </thead>
                        <tbody>
                            {items_html}
                        </tbody>
                    </table>
                    
                    <div style="margin-top: 30px; text-align: center; color: #888; font-size: 12px;">
                        Sistema de Validación Automática - {datetime.now().strftime('%Y-%m-%d %H:%M')}
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_content, 'html'))

        try:
            # NOTA: smtplib es síncrono por naturaleza, pero al estar dentro de async def
            # no generará error de sintaxis con el 'await' del main.py.
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            print(f"📧 Alerta enviada a {self.receiver_email}")
        except Exception as e:
            print(f"❌ Error enviando email: {e}")

email_service = EmailService()