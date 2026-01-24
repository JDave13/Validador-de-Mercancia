"""
Script para probar notificaciones por Email
Ejecutar: python test_email.py
"""

import os
from dotenv import load_dotenv
from app.services.email_service import email_service

load_dotenv()

def test_email_config():
    """Verifica la configuración de email"""
    
    print("\n" + "="*60)
    print("🧪 TEST: Configuración de Email")
    print("="*60 + "\n")
    
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    
    if not smtp_user or not smtp_password:
        print("❌ ERROR: Faltan credenciales SMTP en .env\n")
        print("Asegúrate de tener:")
        print("  SMTP_SERVER=smtp.gmail.com")
        print("  SMTP_PORT=587")
        print("  SMTP_USER=tu_email@gmail.com")
        print("  SMTP_PASSWORD=tu_app_password\n")
        return False
    
    print(f"✅ SMTP Server: {smtp_server}")
    print(f"✅ SMTP Port: {smtp_port}")
    print(f"✅ SMTP User: {smtp_user}")
    print(f"✅ SMTP Password: {'*' * 16} (configurado)\n")
    
    return True

def test_send_email():
    """Envía un email de prueba"""
    
    print("="*60)
    print("📧 ENVIAR EMAIL DE PRUEBA")
    print("="*60 + "\n")
    
    # Solicitar email destino
    default_email = os.getenv("JEFE_COMPRAS_EMAIL") or os.getenv("SMTP_USER")
    to_email = input(f"Email destino [{default_email}]: ").strip() or default_email
    
    print(f"\n📤 Enviando email de prueba a: {to_email}...\n")
    
    # Simular resultado de validación (ROJO)
    validation_result_rojo = {
        "status": "ROJO",
        "invoice_id": "F-TEST-001",
        "proveedor": "Frutas del Valle (PRUEBA)",
        "desviacion_porcentual": 15.5,
        "totales": {
            "esperado": 125000,
            "facturado": 145000,
            "diferencia": 20000
        },
        "discrepancias": [
            {
                "tipo": "PRECIO_ALTO",
                "severidad": "ALTA",
                "mensaje": "Precio $5,000 más alto que lo pactado en Tomate Chonto"
            },
            {
                "tipo": "SOBRECARGO",
                "severidad": "ALTA",
                "mensaje": "Se facturó 10kg más de lo pedido en Papa Pastusa"
            },
            {
                "tipo": "PRODUCTO_NO_PEDIDO",
                "severidad": "ALTA",
                "mensaje": "Producto 'Cebolla Morada' no fue pedido"
            }
        ]
    }
    
    try:
        success = email_service.send_alert(validation_result_rojo, to_email)
        
        if success:
            print("\n" + "="*60)
            print("✅ EMAIL ENVIADO EXITOSAMENTE")
            print("="*60)
            print(f"\nRevisa la bandeja de entrada de: {to_email}")
            print("(Puede tardar unos segundos en llegar)")
            print("\nSi no lo ves, revisa la carpeta de SPAM")
            print("="*60 + "\n")
        else:
            print("\n❌ Error al enviar email\n")
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}\n")
        
        if "Username and Password not accepted" in str(e):
            print("💡 SOLUCIÓN:")
            print("   1. Verifica que tu email sea correcto")
            print("   2. Asegúrate de usar App Password, NO tu contraseña normal")
            print("   3. Genera nuevo App Password en:")
            print("      https://myaccount.google.com/apppasswords\n")

def test_all_status_types():
    """Envía emails de prueba para todos los tipos de status"""
    
    print("\n" + "="*60)
    print("📧 ENVIAR EMAILS PARA TODOS LOS STATUS")
    print("="*60 + "\n")
    
    to_email = input("Email destino: ").strip()
    
    if not to_email:
        print("❌ Email requerido")
        return
    
    # ROJO
    print("\n1️⃣ Enviando alerta ROJA...")
    validation_rojo = {
        "status": "ROJO",
        "invoice_id": "F-ROJO-001",
        "proveedor": "Proveedor Test ROJO",
        "desviacion_porcentual": 15.0,
        "totales": {"esperado": 100000, "facturado": 115000, "diferencia": 15000},
        "discrepancias": [
            {"tipo": "PRECIO_ALTO", "mensaje": "Precios muy elevados"}
        ]
    }
    email_service.send_alert(validation_rojo, to_email)
    
    # AMARILLO
    print("2️⃣ Enviando alerta AMARILLA...")
    validation_amarillo = {
        "status": "AMARILLO",
        "invoice_id": "F-AMARILLO-001",
        "proveedor": "Proveedor Test AMARILLO",
        "desviacion_porcentual": 7.5,
        "totales": {"esperado": 100000, "facturado": 107500, "diferencia": 7500},
        "discrepancias": [
            {"tipo": "SOBRECARGO", "mensaje": "Cantidad ligeramente mayor"}
        ]
    }
    email_service.send_alert(validation_amarillo, to_email)
    
    print("\n✅ Emails enviados! Revisa tu bandeja de entrada.\n")

if __name__ == "__main__":
    print("\n📧 EMAIL SERVICE - TESTING SUITE\n")
    print("Selecciona una opción:")
    print("1. Verificar configuración")
    print("2. Enviar email de prueba (ROJO)")
    print("3. Enviar todos los tipos de alertas")
    print("4. Todo lo anterior")
    
    choice = input("\nOpción (1/2/3/4): ").strip()
    
    if choice == "1":
        test_email_config()
    elif choice == "2":
        if test_email_config():
            test_send_email()
    elif choice == "3":
        if test_email_config():
            test_all_status_types()
    elif choice == "4":
        if test_email_config():
            print("\n" + "="*60)
            input("Presiona ENTER para continuar con las pruebas...")
            test_send_email()
            print("\n" + "="*60)
            input("Presiona ENTER para enviar todos los tipos...")
            test_all_status_types()
    else:
        print("Opción inválida")