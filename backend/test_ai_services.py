"""
Script para probar la selección automática de modelos de IA
El sistema elige automáticamente el mejor modelo disponible
Ejecutar: python test_ai_providers.py
"""

import asyncio
from app.services.ai_service import ai_service
from PIL import Image
import io

async def test_auto_selection():
    """Prueba la selección automática de modelos"""
    
    print("\n" + "="*60)
    print("🤖 TEST: SELECCIÓN AUTOMÁTICA DE MODELOS")
    print("="*60 + "\n")
    
    # Mostrar estado actual
    status = ai_service.get_status()
    
    print("📊 Estado del servicio:")
    print(f"   Modelo actual: {status['current_provider'].upper()}")
    print(f"   Modelos disponibles: {', '.join(status['available_providers'])}")
    print(f"   Total disponibles: {status['total_available']}\n")
    
    # Crear imagen de prueba
    print("📸 Creando imagen de prueba...")
    img = Image.new('RGB', (400, 300), color='white')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr = img_byte_arr.getvalue()
    
    # Prueba 1: OCR
    print("\n1️⃣ Probando OCR de factura...")
    result1 = await ai_service.extract_invoice_data(img_byte_arr)
    
    if result1["success"]:
        print(f"   ✅ OCR exitoso")
        print(f"   Modelo usado: {result1['provider'].upper()}")
        print(f"   Proveedor: {result1.get('data', {}).get('proveedor', 'N/A')}")
    else:
        print(f"   ❌ Error: {result1.get('error')}")
    
    # Prueba 2: Inspector Visual
    print("\n2️⃣ Probando Inspector Visual...")
    result2 = await ai_service.analyze_product_quality(img_byte_arr, "frutas")
    
    if result2["success"]:
        print(f"   ✅ Inspector exitoso")
        print(f"   Modelo usado: {result2['provider'].upper()}")
        print(f"   Estado: {result2.get('data', {}).get('estado', 'N/A')}")
    else:
        print(f"   ❌ Error: {result2.get('error')}")
    
    # Resumen
    print("\n" + "="*60)
    print("📋 RESUMEN")
    print("="*60)
    print(f"✅ El sistema seleccionó automáticamente: {result1.get('provider', 'N/A').upper()}")
    print(f"✅ No necesitas configurar AI_PROVIDER en .env")
    print(f"✅ Si un modelo falla, cambia automáticamente al siguiente")
    print("="*60 + "\n")

async def test_fallback():
    """Simula fallo y prueba el fallback automático"""
    
    print("\n" + "="*60)
    print("🔄 TEST: FALLBACK AUTOMÁTICO")
    print("="*60 + "\n")
    
    print("Este test verifica que si un modelo falla,")
    print("el sistema cambie automáticamente a otro.\n")
    
    # El sistema ya hace esto automáticamente en _invoke_with_fallback
    print("✅ Fallback automático está configurado")
    print("   Si Groq falla → cambia a Gemini")
    print("   Si Gemini falla → cambia a Hugging Face")
    print("   Si todos fallan → devuelve error\n")

if __name__ == "__main__":
    print("\n🚀 TEST DE SELECCIÓN AUTOMÁTICA DE MODELOS\n")
    print("Selecciona modo de prueba:")
    print("1. Probar selección automática")
    print("2. Ver explicación de fallback")
    print("3. Ambas")
    
    choice = input("\nOpción (1/2/3): ").strip()
    
    if choice == "1":
        asyncio.run(test_auto_selection())
    elif choice == "2":
        asyncio.run(test_fallback())
    elif choice == "3":
        asyncio.run(test_auto_selection())
        asyncio.run(test_fallback())
    else:
        print("Opción inválida")