import asyncio
import os
from dotenv import load_dotenv 
from datetime import datetime, timezone

# Cargar variables de entorno
load_dotenv() 

from app.database.mongodb import db 
from app.services.matching_service import matching_service

# --- LISTA MAESTRA CALIBRADA PARA TUS 3 FACTURAS ---
ALL_PRODUCTS_DATA = [
    # ==========================================
    # 🥦 FACTURA 3 (Supermercados SAS - Verduras)
    # ==========================================
    {
        "nombre": "Cebolla Cabezona", 
        "sinonimos": ["Cebolla Blanca", "1,43FV. CEBOLLA CABEZONA"], 
        "categoria": "verduras", 
        "unidad_base": "kg", 
        "precio": 3383  # Exacto según factura
    },
    {
        "nombre": "Cebolla Larga", 
        "sinonimos": ["Cebolla Rama", "0,49FV. CEBOLLA LARGA CON"], 
        "categoria": "verduras", 
        "unidad_base": "atado", 
        "precio": 12500
    },
    {
        "nombre": "Mandarina", 
        "sinonimos": ["Mandarina Oneco", "1,24FV. MANDARINA"], 
        "categoria": "frutas", 
        "unidad_base": "kg", 
        "precio": 6400
    },
    {
        "nombre": "Plátano Hartón", 
        "sinonimos": ["Plátano Verde", "1,28FV. PLATANO HARTON A"], 
        "categoria": "frutas", 
        "unidad_base": "kg", 
        "precio": 5300
    },
    {
        "nombre": "Ajo Nacional", 
        "sinonimos": ["Cabeza de Ajo", "0,05FV. AJO NACIONAL"], 
        "categoria": "verduras", 
        "unidad_base": "kg", 
        "precio": 26800
    },
    {
        "nombre": "Papa Criolla", 
        "sinonimos": ["Papa Amarilla", "1,05FV. PAPA CRIOLLA"], 
        "categoria": "verduras", 
        "unidad_base": "kg", 
        "precio": 4000
    },
    {
        "nombre": "Guayaba Pera", 
        "sinonimos": ["Guayaba", "1,04FV. GUAYABA PERA"], 
        "categoria": "frutas", 
        "unidad_base": "kg", 
        "precio": 4400
    },
    {
        "nombre": "Tomate Chonto", 
        "sinonimos": ["Tomate Rojo", "1,19FV. TOMATE CHONTO"], 
        "categoria": "verduras", 
        "unidad_base": "kg", 
        "precio": 3500
    },

    # ==========================================
    # 🛒 FACTURA 2 (Éxito - Mercado Grande)
    # ==========================================
    {
        "nombre": "Arroz Marca ROA", 
        "sinonimos": ["ARROZ MARCA ROA 25LBRS", "Arroz Blanco"], 
        "categoria": "abarrotes", 
        "unidad_base": "arroba", 
        "precio": 47050
    },
    {
        "nombre": "Pollo Pechuga", 
        "sinonimos": ["POLLO PECHUGA 1,5 LBRS", "Filete de Pollo"], 
        "categoria": "carnes", 
        "unidad_base": "libra", 
        "precio": 9140 # (45.700 / 5) Calculado exacto
    },
    {
        "nombre": "Cerdo Carne", 
        "sinonimos": ["CERDO CARNE 2 LBRS", "Pierna Cerdo"], 
        "categoria": "carnes", 
        "unidad_base": "libra", 
        "precio": 6795 # (13.590 / 2) Calculado exacto
    },
    {
        "nombre": "Lentejas Marca Exito", 
        "sinonimos": ["LENTEJAS MARCA EXITO 1 LBR"], 
        "categoria": "abarrotes", 
        "unidad_base": "libra", 
        "precio": 3800 # PRECIO REAL. Esto hará que la factura salga ROJA (Correcto para demo)
    },
    {
        "nombre": "Queso Doble Crema (Bloque)", 
        "sinonimos": ["QUESO DOBLCREMA ALPINA", "Queso Bloque"], 
        "categoria": "lacteos", 
        "unidad_base": "bloque_peq", 
        "precio": 5500 # Precio Factura 2
    },
    {
        "nombre": "Salchichas Ranchera", 
        "sinonimos": ["SALCHICHAS RANCHERA X5", "Salchicha Manguera"], 
        "categoria": "embutidos", 
        "unidad_base": "paquete", 
        "precio": 7100
    },
    {
        "nombre": "Huevos AAA Cubeta 30", 
        "sinonimos": ["HUEVOS AAA CUBETA", "Cubeta Huevos"], 
        "categoria": "huevos", 
        "unidad_base": "cubeta", 
        "precio": 20350
    },
    {
        "nombre": "Pan Ajo Queso", 
        "sinonimos": ["PAN AJO QUESO"], 
        "categoria": "panaderia", 
        "unidad_base": "unidad", 
        "precio": 550 # (1.100 / 2)
    },
    {
        "nombre": "Jabón Polvo FAB", 
        "sinonimos": ["JABON POLVO FAB 5 LBR", "Detergente Polvo"], 
        "categoria": "aseo", 
        "unidad_base": "bolsa_5lb", 
        "precio": 20070
    },
    {
        "nombre": "Jabón Barra Rey", 
        "sinonimos": ["JABON BARRA REY", "Jabón Azul"], 
        "categoria": "aseo", 
        "unidad_base": "barra", 
        "precio": 2388 # (14.330 / 6) Aprox
    },
    {
        "nombre": "Wolite Ropa Negra", 
        "sinonimos": ["WOLITE ROPA NEG X2", "Detergente Ropa Oscura"], 
        "categoria": "aseo", 
        "unidad_base": "botella", 
        "precio": 24950 # (49.900 / 2)
    },

    # ==========================================
    # 🧾 FACTURA 1 (Pequeña - Huevos y Lácteos)
    # ==========================================
    {
        "nombre": "Mantequilla Alpina", 
        "sinonimos": ["Mantequilla sin sal", "MANTEUILLA ALPINA S/SAL", "MANTEQUILLA ALPINA"], 
        "categoria": "lacteos", 
        "unidad_base": "barra", 
        "precio": 4350 # Promedio entre Factura 1 (4280) y Factura 2 (4460) para tolerar ambas
    },
    {
        "nombre": "Queso Mozzarella Alpina", 
        "sinonimos": ["MOZRE/DBCR ALPINA", "Queso Especial"], 
        "categoria": "lacteos", 
        "unidad_base": "bloque_grande", 
        "precio": 10630 # Precio Factura 1 (Distinto al de Exito)
    },
    {
        "nombre": "Leche Alquería", 
        "sinonimos": ["LEC.LIC.UH ALQUERI (2)", "LEC.LIC.UH", "Leche Larga Vida"], 
        "categoria": "lacteos", 
        "unidad_base": "bolsa", 
        "precio": 3310 # (6.620 / 2)
    },
    {
        "nombre": "Huevos Rojos x12", 
        "sinonimos": ["ROJOS SM CX12", "Caja Huevos 12", "Huevos Docena"], 
        "categoria": "huevos", 
        "unidad_base": "caja_12", 
        "precio": 4500
    },
    {
        "nombre": "Pan Tajado Comapan", 
        "sinonimos": ["PAN TAJADO COMAPAN", "Pan Molde"], 
        "categoria": "panaderia", 
        "unidad_base": "paquete", 
        "precio": 3370
    }
]

async def seed_products_catalog():
    print("📚 Generando Catálogo Maestro (con PRECIOS CALIBRADOS)...")
    texts_to_embed = []
    
    # Creamos el "texto rico" para la IA
    for p in ALL_PRODUCTS_DATA:
        rich_text = f"{p['nombre']} {' '.join(p.get('sinonimos', []))}"
        texts_to_embed.append(rich_text)
    
    embeddings = await matching_service.get_embeddings(texts_to_embed)
    
    if not embeddings:
        print("❌ Error: Fallo al generar embeddings (Revisar API Key).")
        return

    for i, product in enumerate(ALL_PRODUCTS_DATA):
        product_copy = product.copy()
        product_copy["embedding"] = embeddings[i]
        db.products.insert_one(product_copy)
    
    print(f"   ✅ {len(ALL_PRODUCTS_DATA)} productos insertados correctamente.")

async def seed_inventory():
    print("\n📦 Llenando Bodega Inicial...")
    stock_items = []
    
    # Creamos stock basado en el catálogo
    for prod in ALL_PRODUCTS_DATA:
        stock_items.append({
            "producto": prod["nombre"],
            "stock_actual": 100,  
            "precio_referencia": prod["precio"], 
            "unidad": prod["unidad_base"],
            "ubicacion": "Bodega General",
            "fecha": datetime.now(timezone.utc)
        })

    # Embeddings simples para el inventario (para búsquedas internas)
    names = [i["producto"] for i in stock_items]
    embeddings = await matching_service.get_embeddings(names)
    
    for i, item in enumerate(stock_items):
        if i < len(embeddings):
            item["embedding"] = embeddings[i]
            db.inventory.insert_one(item)

    print(f"   ✅ Inventario inicializado.")

async def main():
    print("\n🚀 REINICIANDO BASE DE DATOS PARA DEMO...")
    try:
        # Limpiar todo para empezar limpio
        db.products.delete_many({})
        db.inventory.delete_many({})
        db.validations.delete_many({})
        
        await seed_products_catalog()
        await seed_inventory()
        
        print("\n✨ SEED COMPLETADO: Base de datos lista para pruebas.")
        print("   -> Factura 1 y 3 deberían dar VERDE (o Amarillo leve).")
        print("   -> Factura 2 debería dar ROJO en Lentejas (Protección de precio).")
    except Exception as e:
        print(f"❌ Error Crítico: {e}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())