import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import os
from dotenv import load_dotenv 
from datetime import datetime
import base64  # <--- NUEVO: Necesario para decodificar la imagen

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
        """Formatea porcentajes."""
        try:
            val = float(value)
            return f"{val:.2f}%"
        except:
            return "0%"

    def _clean_image_data(self, image_data):
        """
        NUEVO: Limpia y decodifica la imagen.
        Si viene en base64 (string), lo convierte a bytes.
        """
        if not image_data:
            return None
        
        # Si ya son bytes, perfecto
        if isinstance(image_data, bytes):
            return image_data
            
        # Si es string (Base64), hay que decodificar
        if isinstance(image_data, str):
            try:
                # Quitar cabecera "data:image/jpeg;base64," si existe
                if "base64," in image_data:
                    image_data = image_data.split("base64,")[1]
                
                # Decodificar a bytes reales
                return base64.b64decode(image_data)
            except Exception as e:
                print(f"⚠️ Error decodificando imagen Base64: {e}")
                return None
        return None

    async def send_alert(self, data):
        if not self.sender_email or not self.sender_password:
            print("⚠️ Faltan credenciales de email.")
            return

        # Detectar estado de calidad
        quality_info = data.get('quality_inspection') or {}
        quality_status = quality_info.get('status')
        rechazo_total = data.get('rechazo_total', False)
        
        if quality_status == 'RECHAZADO':
            rechazo_total = True
        
        # CASO 1: Rechazo total por calidad
        if rechazo_total:
            if data.get('factura_id') and data.get('items'):
                await self._send_combined_rejection_email(data)
            else:
                await self._send_quality_rejection_email(data)
            
            # Detener ejecución para no enviar doble alerta
            return 
        
        # CASO 2: Validación financiera normal
        status_financiero = data.get('status')
        if status_financiero in ['ROJO', 'AMARILLO']:
            await self._send_validation_email(data)
        
        # CASO 3: Todo OK
        else:
            print(f"ℹ️ No se requiere envío de email (Status: {status_financiero})")

    async def _send_combined_rejection_email(self, data):
        """Email combinado: Rechazado por CALIDAD FÍSICA con datos completos"""
        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = self.receiver_email
        
        factura_id = data.get('factura_id', 'SIN-ID')
        proveedor = data.get('proveedor', 'Desconocido')
        quality_data = data.get('quality_inspection', {})
        issues = quality_data.get('issues', [])
        product_type = quality_data.get('product_type', 'Desconocido')
        confidence = quality_data.get('confidence', 0) * 100
        recommendation = quality_data.get('recommendation', 'Rechazar producto')
        
        totales = data.get('totales', {})
        desviacion = data.get('desviacion_porcentual', 0)
        items = data.get('items', [])
        
        # --- PROCESAR IMAGEN ---
        raw_image = data.get('product_image_bytes')
        product_image_bytes = self._clean_image_data(raw_image)
        product_image_filename = data.get('product_image_filename', 'producto.jpg')
        
        msg['Subject'] = f"🚨 [RECHAZO TOTAL] Factura {factura_id} - Calidad Física Deficiente"

        issues_html = ""
        for issue in issues:
            issues_html += f'<li style="color: #d32f2f; padding: 5px 0;">{issue}</li>'

        items_html = ""
        for item in items:
            nombre = item.get('product_name', '---')
            cantidad = item.get('quantity', 0)
            precio_factura = item.get('unit_price', 0)
            precio_esperado = item.get('expected_price', 0)
            
            items_html += f"""
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 10px;">{nombre}</td>
                <td style="padding: 10px; text-align: center;">{cantidad}</td>
                <td style="padding: 10px; text-align: right;">{self.format_currency(precio_factura)}</td>
                <td style="padding: 10px; text-align: right; color: #555;">{self.format_currency(precio_esperado)}</td>
            </tr>
            """

        image_section = ""
        if product_image_bytes:
            image_section = f"""
            <div style="margin: 25px 0; text-align: center; background: #fff; padding: 15px; border-radius: 8px; border: 2px solid #d32f2f;">
                <h3 style="color: #b71c1c; margin-bottom: 15px; font-size: 18px;">
                    📸 Evidencia fotográfica del rechazo
                </h3>
                <img src="cid:product_image" style="max-width: 100%; max-height: 400px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);" alt="Producto Rechazado">
                <p style="margin-top: 10px; font-size: 12px; color: #666;">
                    Archivo: {product_image_filename}
                </p>
            </div>
            """

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; background-color: #f4f4f4; padding: 20px;">
            <div style="max-width: 700px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
                
                <div style="background: linear-gradient(135deg, #b71c1c 0%, #d32f2f 100%); color: #ffffff; padding: 30px; text-align: center;">
                    <h1 style="margin:0; font-size: 32px; text-shadow: 0 2px 4px rgba(0,0,0,0.2);">[🚨 ALERTA ROJA]</h1>
                    <p style="margin:10px 0 0; font-size: 20px; font-weight: bold;">Calidad Física Deficiente</p>
                    <div style="margin-top: 15px; padding: 10px; background: rgba(255,255,255,0.1); border-radius: 6px;">
                        <p style="margin: 0; font-size: 16px;">Factura: <strong>{factura_id}</strong></p>
                        <p style="margin: 5px 0 0; font-size: 14px;">Proveedor: {proveedor}</p>
                    </div>
                </div>
                
                <div style="padding: 30px;">
                    <div style="background-color: #ffebee; border-left: 6px solid #d32f2f; padding: 20px; margin-bottom: 25px; border-radius: 4px;">
                        <h3 style="margin: 0 0 10px 0; color: #b71c1c; font-size: 20px;">⛔ MERCANCÍA NO ACEPTADA</h3>
                        <p style="margin: 0; font-size: 15px; line-height: 1.6;">
                            La inspección de calidad visual detectó defectos críticos que impiden la recepción del producto.
                            <strong style="display: block; margin-top: 10px; color: #d32f2f;">
                            Esta factura ha sido rechazada automáticamente.
                            </strong>
                        </p>
                    </div>
                    <div style="background: #fff3e0; border: 2px solid #ff9800; border-radius: 8px; padding: 20px; margin-bottom: 25px;">
                        <h3 style="margin: 0 0 15px 0; color: #e65100; font-size: 18px; border-bottom: 2px solid #ff9800; padding-bottom: 10px;">
                            Resultado de la inspección  visual
                        </h3>
                        <table style="width: 100%;">
                            <tr>
                                <td style="padding: 8px 0;"><strong>Tipo de Producto:</strong></td>
                                <td style="padding: 8px 0; text-align: right;">{product_type}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0;"><strong>Confianza del Análisis:</strong></td>
                                <td style="padding: 8px 0; text-align: right; font-weight: bold; color: #d32f2f;">{confidence:.0f}%</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0;"><strong>Estado de Calidad:</strong></td>
                                <td style="padding: 8px 0; text-align: right;">
                                    <span style="background: #d32f2f; color: white; padding: 6px 14px; border-radius: 4px; font-weight: bold; font-size: 14px;">
                                        RECHAZADO
                                    </span>
                                </td>
                            </tr>
                        </table>
                    </div>

                    {image_section}
                    <div style="margin-bottom: 25px;">
                        <h3 style="border-bottom: 2px solid #d32f2f; padding-bottom: 10px; color: #b71c1c; font-size: 18px; margin-bottom: 15px;">
                            📋 Problemas detectados por la IA
                        </h3>
                        <ul style="margin: 0; padding-left: 25px; line-height: 2;">
                            {issues_html}
                        </ul>
                    </div>
                    <div style="background: #e3f2fd; border-left: 4px solid #2196f3; padding: 15px; margin-bottom: 25px; border-radius: 4px;">
                        <h4 style="margin: 0 0 8px 0; color: #1565c0;">💡 Recomendación del Sistema</h4>
                        <p style="margin: 0; font-size: 14px; line-height: 1.6;">{recommendation}</p>
                    </div>

                    <div style="background: #f8f9fa; border-radius: 8px; padding: 20px; margin-bottom: 25px;">
                        <h3 style="margin: 0 0 15px 0; color: #333; font-size: 18px; border-bottom: 2px solid #ddd; padding-bottom: 10px;">
                            Detalles de la factura rechazada
                        </h3>
                        <table style="width: 100%; margin-bottom: 15px;">
                            <tr>
                                <td style="padding: 8px 0;"><strong>Total Facturado:</strong></td>
                                <td style="padding: 8px 0; text-align: right; font-size: 18px; font-weight: bold; color: #000;">
                                    {self.format_currency(totales.get('facturado', 0))}
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0;"><strong>Total Esperado:</strong></td>
                                <td style="padding: 8px 0; text-align: right;">
                                    {self.format_currency(totales.get('esperado', 0))}
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0;"><strong>Diferencia:</strong></td>
                                <td style="padding: 8px 0; text-align: right; color: #d32f2f; font-weight: bold;">
                                    {self.format_currency(totales.get('diferencia', 0))}
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0;"><strong>Desviación:</strong></td>
                                <td style="padding: 8px 0; text-align: right; font-weight: bold;">
                                    {self.format_percentage(desviacion)}
                                </td>
                            </tr>
                        </table>

                        <h4 style="margin: 20px 0 10px 0; color: #555; font-size: 14px; text-transform: uppercase;">
                            Items de la Factura
                        </h4>
                        <table style="width: 100%; border-collapse: collapse; font-size: 13px; background: white; border-radius: 6px; overflow: hidden;">
                            <thead>
                                <tr style="background-color: #e0e0e0; text-transform: uppercase; color: #666; font-size: 11px;">
                                    <th style="padding: 10px; text-align: left;">Producto</th>
                                    <th style="padding: 10px; text-align: center;">Cant.</th>
                                    <th style="padding: 10px; text-align: right;">Factura</th>
                                    <th style="padding: 10px; text-align: right;">Esperado</th>
                                </tr>
                            </thead>
                            <tbody>
                                {items_html}
                            </tbody>
                        </table>
                    </div>
                    <div style="background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%); border: 2px solid #ff9800; border-radius: 8px; padding: 20px;">
                        <h3 style="margin: 0 0 15px 0; color: #e65100; font-size: 18px;">
                            📌 Acciones requeridas inmediatas
                        </h3>
                        <ul style="margin: 0; padding-left: 25px; line-height: 2; font-size: 14px;">
                            <li><strong style="color: #d32f2f;">❌ NO ACEPTAR</strong> la mercancía en bodega</li>
                            <li>📞 <strong>Contactar al proveedor</strong> ({proveedor}) para devolución</li>
                            <li>📋 Solicitar <strong>reemplazo inmediato</strong> o nota crédito</li>
                            <li>📸 Evidencia fotográfica adjunta en este email</li>
                            <li>📝 Registrar incidente en sistema de control de calidad</li>
                            <li>⚠️ Evaluar penalizaciones contractuales si aplican</li>
                        </ul>
                    </div>

                    <div style="margin-top: 30px; padding-top: 20px; border-top: 2px solid #eee; text-align: center; color: #888; font-size: 12px;">
                        <p style="margin: 0;">
                            🤖 Sistema de Validación Automática<br>
                            Inspección de Calidad Visual con IA + Validación Financiera<br>
                            {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                        </p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_content, 'html'))

        if product_image_bytes:
            try:
                image_embed = MIMEImage(product_image_bytes)
                image_embed.add_header('Content-ID', '<product_image>')
                image_embed.add_header('Content-Disposition', 'inline', filename=product_image_filename)
                msg.attach(image_embed)
                
                image_attachment = MIMEImage(product_image_bytes)
                image_attachment.add_header('Content-Disposition', 'attachment', filename=product_image_filename)
                msg.attach(image_attachment)
                
                print(f"   ✅ Imagen adjunta: {product_image_filename}")
            except Exception as e:
                print(f"   ⚠️ Error adjuntando imagen: {e}")

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            print(f"📧 Alerta de RECHAZO TOTAL enviada a {self.receiver_email}")
        except Exception as e:
            print(f"❌ Error enviando email: {e}")

    async def _send_quality_rejection_email(self, data):
        """Email para rechazo de calidad SIN datos de factura"""
        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = self.receiver_email
        
        factura_id = data.get('factura_id', 'RECHAZO-SIN-ID')
        product_name = data.get('product_name', 'Producto Desconocido')
        quality_data = data.get('quality_inspection', {})
        issues = quality_data.get('issues', [])
        product_type = quality_data.get('product_type', 'Desconocido')
        confidence = quality_data.get('confidence', 0) * 100
        recommendation = quality_data.get('recommendation', 'Rechazar producto')
        
        # --- PROCESAR IMAGEN ---
        raw_image = data.get('product_image_bytes')
        product_image_bytes = self._clean_image_data(raw_image)
        product_image_filename = data.get('product_image_filename', 'producto.jpg')
        
        msg['Subject'] = f"🚨 [RECHAZO CALIDAD] {product_name} - ID: {factura_id}"

        issues_html = ""
        for issue in issues:
            issues_html += f'<li style="color: #d32f2f; padding: 5px 0;">{issue}</li>'

        image_section = ""
        if product_image_bytes:
            image_section = f"""
            <div style="margin: 25px 0; text-align: center;">
                <h3 style="border-bottom: 2px solid #d32f2f; padding-bottom: 8px; color: #b71c1c; margin-bottom: 15px;">
                    📸 Evidencia fotográfica
                </h3>
                <img src="cid:product_image" style="max-width: 100%; border-radius: 8px; border: 3px solid #d32f2f;" alt="Producto Rechazado">
                <p style="margin-top: 10px; font-size: 12px; color: #666;">
                    Archivo: {product_image_filename}
                </p>
            </div>
            """

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; background-color: #f4f4f4; padding: 20px;">
            <div style="max-width: 650px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                
                <div style="background-color: #b71c1c; color: #ffffff; padding: 30px; text-align: center;">
                    <h1 style="margin:0; font-size: 28px;">🚨 PRODUCTO RECHAZADO</h1>
                    <p style="margin:10px 0 0; font-size: 18px; font-weight: bold;">{product_name}</p>
                    <p style="margin:5px 0 0; font-size: 14px; opacity: 0.9;">ID: {factura_id}</p>
                </div>
                
                <div style="padding: 30px;">
                    
                    <div style="background-color: #ffebee; border-left: 4px solid #d32f2f; padding: 15px; margin-bottom: 25px;">
                        <h3 style="margin: 0 0 10px 0; color: #b71c1c;">⚠️ Producto No Apto para Recepción</h3>
                        <p style="margin: 0; font-size: 14px;">
                            El sistema detectó problemas críticos de calidad que impiden la aceptación del producto.
                        </p>
                    </div>

                    <table style="width: 100%; margin-bottom: 25px; background: #f8f9fa; padding: 15px; border-radius: 6px;">
                        <tr>
                            <td style="padding: 8px 0;"><strong>Producto:</strong></td>
                            <td style="padding: 8px 0; text-align: right; font-weight: bold; color: #d32f2f;">{product_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Tipo Identificado:</strong></td>
                            <td style="padding: 8px 0; text-align: right;">{product_type}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Confianza del Análisis:</strong></td>
                            <td style="padding: 8px 0; text-align: right; font-weight: bold; color: #d32f2f;">{confidence:.0f}%</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Estado:</strong></td>
                            <td style="padding: 8px 0; text-align: right;">
                                <span style="background: #d32f2f; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold;">
                                    RECHAZADO
                                </span>
                            </td>
                        </tr>
                    </table>

                    {image_section}

                    <div style="margin-bottom: 25px;">
                        <h3 style="border-bottom: 2px solid #d32f2f; padding-bottom: 8px; color: #b71c1c;">
                            🔍 Problemas Detectados
                        </h3>
                        <ul style="margin: 15px 0; padding-left: 25px; line-height: 1.8;">
                            {issues_html}
                        </ul>
                    </div>

                    <div style="background: #fff3e0; border-left: 4px solid #ff9800; padding: 15px; margin-bottom: 25px;">
                        <h4 style="margin: 0 0 8px 0; color: #e65100;">💡 Recomendación del Sistema</h4>
                        <p style="margin: 0; font-size: 14px;">{recommendation}</p>
                    </div>

                    <div style="background: #e3f2fd; border-left: 4px solid #2196f3; padding: 15px;">
                        <h4 style="margin: 0 0 8px 0; color: #1565c0;">📋 Acciones Recomendadas</h4>
                        <ul style="margin: 8px 0; padding-left: 25px; font-size: 14px;">
                            <li>❌ <strong>No aceptar el producto en bodega</strong></li>
                            <li>📞 Contactar al proveedor inmediatamente</li>
                            <li>🔄 Solicitar reemplazo o devolución</li>
                            <li>📸 Documentar el incidente (imagen adjunta)</li>
                            <li>📝 Registrar en sistema de control de calidad</li>
                        </ul>
                    </div>

                    <div style="margin-top: 30px; text-align: center; color: #888; font-size: 12px; border-top: 1px solid #eee; padding-top: 20px;">
                        Sistema de Validación Automática - Inspección de Calidad<br>
                        {datetime.now().strftime('%Y-%m-%d %H:%M')}
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_content, 'html'))

        if product_image_bytes:
            try:
                image_embed = MIMEImage(product_image_bytes)
                image_embed.add_header('Content-ID', '<product_image>')
                image_embed.add_header('Content-Disposition', 'inline', filename=product_image_filename)
                msg.attach(image_embed)
                
                image_attachment = MIMEImage(product_image_bytes)
                image_attachment.add_header('Content-Disposition', 'attachment', filename=product_image_filename)
                msg.attach(image_attachment)
            except Exception as e:
                print(f"   ⚠️ Error adjuntando imagen: {e}")

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            print(f"📧 Alerta de RECHAZO DE CALIDAD enviada a {self.receiver_email}")
        except Exception as e:
            print(f"❌ Error enviando email de calidad: {e}")

    async def _send_validation_email(self, data):
        """Email para validación de factura (AMARILLO/ROJO por precio/cantidad)"""
        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = self.receiver_email
        
        factura_id = data.get('factura_id', 'SIN-ID')
        estado_global = data.get('status', 'ALERTA')
        proveedor = data.get('proveedor', 'Desconocido')
        desviacion = data.get('desviacion_porcentual', 0)
        
        msg['Subject'] = f"[{estado_global}] Factura {factura_id} - {proveedor}"

        if estado_global == "ROJO":
            header_bg = "#d32f2f"
            header_text = "#ffffff"
        elif estado_global == "AMARILLO":
            header_bg = "#fbc02d"
            header_text = "#000000"
        else:
            header_bg = "#2e7d32"
            header_text = "#ffffff"

        items_html = ""
        items = data.get('items', [])
        if not items: items = data.get('matchResults', [])

        for item in items:
            nombre = item.get('product_name', item.get('original_name', '---'))
            match_name = item.get('matched_name', '')
            
            precio_factura = float(item.get('unit_price', 0))
            precio_esperado = float(item.get('expected_price', 0))
            cantidad = item.get('quantity', 0)
            similarity = item.get('score', item.get('similarity', 0))

            es_error_precio = False
            error_msg = ""
            
            if precio_esperado > 0:
                if precio_factura > precio_esperado:
                    diff = precio_factura - precio_esperado
                    pct_diff = (diff / precio_esperado)
                    
                    if pct_diff > 0.05:
                        es_error_precio = True
                        error_msg = f'<div style="color: #d32f2f; font-weight:bold; font-size:11px;">⚠️ +{pct_diff*100:.0f}% Sobreprecio</div>'

            bg_color = "#fff0f0" if es_error_precio else "#ffffff"
            text_color = "#b71c1c" if es_error_precio else "#333333"
            
            match_html = ""
            if match_name and match_name != "No encontrado" and match_name != nombre:
                match_html = f'<div style="color: #666; font-size: 11px; font-style: italic;">DB: {match_name}</div>'

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
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            print(f"📧 Alerta de validación enviada a {self.receiver_email}")
        except Exception as e:
            print(f"❌ Error enviando email de validación: {e}")

email_service = EmailService()