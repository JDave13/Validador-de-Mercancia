"""
Servicio de notificaciones por Email (alternativa a WhatsApp)
Más fácil de configurar y 100% gratis
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from typing import Dict

class EmailService:
    def __init__(self):
        # Configuración SMTP (Gmail ejemplo)
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        
        # Emails de contacto
        self.jefe_compras_email = os.getenv("JEFE_COMPRAS_EMAIL")
        self.supervisor_email = os.getenv("SUPERVISOR_EMAIL")
        
        self.enabled = bool(self.smtp_user and self.smtp_password)
        
        if not self.enabled:
            print("⚠️ Email no configurado - notificaciones deshabilitadas")
    
    def format_alert_html(self, validation_result: Dict) -> str:
        """Formatea alerta en HTML para email"""
        
        status = validation_result["status"]
        
        # Colores según status
        colors = {
            "ROJO": {"bg": "#fee2e2", "border": "#ef4444", "text": "#991b1b"},
            "AMARILLO": {"bg": "#fef3c7", "border": "#f59e0b", "text": "#92400e"},
            "VERDE": {"bg": "#d1fae5", "border": "#10b981", "text": "#065f46"}
        }
        
        color = colors.get(status, colors["AMARILLO"])
        emoji = "🔴" if status == "ROJO" else "🟡" if status == "AMARILLO" else "🟢"
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ 
                    background: {color['bg']}; 
                    border-left: 4px solid {color['border']}; 
                    padding: 20px;
                    margin-bottom: 20px;
                }}
                .header h1 {{ 
                    color: {color['text']}; 
                    margin: 0;
                }}
                .info {{ background: #f9fafb; padding: 15px; border-radius: 8px; margin-bottom: 15px; }}
                .info-row {{ display: flex; justify-content: space-between; margin-bottom: 8px; }}
                .label {{ font-weight: bold; color: #374151; }}
                .value {{ color: #6b7280; }}
                .discrepancias {{ background: #fff; border: 1px solid #e5e7eb; padding: 15px; border-radius: 8px; }}
                .discrepancia-item {{ 
                    border-left: 3px solid {color['border']}; 
                    padding: 10px;
                    margin-bottom: 10px;
                    background: {color['bg']};
                }}
                .footer {{ text-align: center; color: #9ca3af; margin-top: 20px; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{emoji} ALERTA DE VALIDACIÓN - {status}</h1>
                </div>
                
                <div class="info">
                    <div class="info-row">
                        <span class="label">📄 Factura:</span>
                        <span class="value">{validation_result.get('invoice_id', 'N/A')}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">🏢 Proveedor:</span>
                        <span class="value">{validation_result['proveedor']}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">📊 Desviación:</span>
                        <span class="value">{validation_result['desviacion_porcentual']}%</span>
                    </div>
                </div>
                
                <div class="info">
                    <h3 style="margin-top: 0;">💰 Totales</h3>
                    <div class="info-row">
                        <span class="label">Esperado:</span>
                        <span class="value">${validation_result['totales']['esperado']:,.0f}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Facturado:</span>
                        <span class="value">${validation_result['totales']['facturado']:,.0f}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Diferencia:</span>
                        <span class="value">${validation_result['totales']['diferencia']:,.0f}</span>
                    </div>
                </div>
        """
        
        # Agregar discrepancias
        if validation_result['discrepancias']:
            html += """
                <div class="discrepancias">
                    <h3 style="margin-top: 0;">⚠️ Problemas Encontrados</h3>
            """
            
            for disc in validation_result['discrepancias'][:10]:
                html += f"""
                    <div class="discrepancia-item">
                        <strong>{disc['tipo']}:</strong> {disc['mensaje']}
                    </div>
                """
            
            if len(validation_result['discrepancias']) > 10:
                html += f"<p>... y {len(validation_result['discrepancias']) - 10} más</p>"
            
            html += "</div>"
        
        # Acción requerida
        action = "🚫 FACTURA BLOQUEADA - Revisar urgente" if status == "ROJO" else "⏸️ Requiere revisión manual"
        
        html += f"""
                <div class="info">
                    <p style="margin: 0; font-weight: bold;">{action}</p>
                </div>
                
                <div class="footer">
                    <p>Validador de Mercancía v1.0</p>
                    <p>Este es un mensaje automático, no responder</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def send_alert(
        self,
        validation_result: Dict,
        to_email: str = None
    ) -> bool:
        """Envía alerta por email"""
        
        if not self.enabled:
            print("⚠️ Email deshabilitado - alerta no enviada")
            return False
        
        # Determinar destinatario
        if to_email is None:
            status = validation_result["status"]
            to_email = self.jefe_compras_email if status == "ROJO" else self.supervisor_email
        
        if not to_email:
            print("⚠️ Email destino no configurado")
            return False
        
        try:
            # Crear mensaje
            msg = MIMEMultipart('alternative')
            msg['From'] = self.smtp_user
            msg['To'] = to_email
            msg['Subject'] = f"⚠️ Alerta Validación - {validation_result['status']} - {validation_result['proveedor']}"
            
            # Agregar HTML
            html_content = self.format_alert_html(validation_result)
            msg.attach(MIMEText(html_content, 'html'))
            
            # Enviar
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            print(f"✅ Email enviado a: {to_email}")
            return True
            
        except Exception as e:
            print(f"❌ Error enviando email: {str(e)}")
            return False

# Singleton
email_service = EmailService()