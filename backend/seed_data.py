"""
Script para poblar la base de datos con datos de prueba
Ejecutar: python seed_data.py
"""

import asyncio
from datetime import datetime, timedelta
from app.database.mongodb import db
from app.services.matching_service import matching_service

async def seed_purchase_orders():
    """Crea órdenes de compra de ejemplo"""
    
    orders = [
        {
            "numero_orden": "OC-2026-001",
            "proveedor": "Frutas del Valle",
            "fecha_creacion": datetime.utcnow() - timedelta(days=2),
            "estado": "pendiente",
            "items": [
                {
                    "producto": "Tomate Chonto",
                    "cantidad": 50,
                    "unidad": "kg",
                    "precio_unitario": 2500,
                    "total": 125000
                },
                {
                    "producto": "Papa Pastusa",
                    "cantidad": 100,
                    "unidad": "kg",
                    "precio_unitario": 1800,
                    "total": 180000
                },
                {
                    "producto": "Cebolla Cabezona",
                    "cantidad": 30,
                    "unidad": "kg",
                    "precio_unitario": 2200,
                    "total": 66000
                }
            ],
            "total_orden": 371000
        },
        {
            "numero_orden": "OC-2026-002",
            "proveedor": "Lácteos La Hacienda",
            "fecha_creacion": datetime.utcnow() - timedelta(days=1),
            "estado": "pendiente",
            "items": [
                {
                    "producto": "Leche Entera",
                    "cantidad": 20,
                    "unidad": "litros",
                    "precio_unitario": 3500,
                    "total": 70000
                },
                {
                    "producto": "Queso Campesino",
                    "cantidad": 10,
                    "unidad": "kg",
                    "precio_unitario": 18000,
                    "total": 180000
                },
                {
                    "producto": "Mantequilla",
                    "cantidad": 5,
                    "unidad": "kg",
                    "precio_unitario": 12000,
                    "total": 60000
                }
            ],
            "total_orden": 310000
        },
        {
            "numero_orden": "OC-2026-003",
            "proveedor": "Carnes Premium",
            "fecha_creacion": datetime.utcnow(),
            "estado": "pendiente",
            "items": [
                {
                    "producto": "Carne de Res",
                    "cantidad": 25,
                    "unidad": "kg",
                    "precio_unitario": 22000,
                    "total": 550000
                },
                {
                    "producto": "Pollo Entero",
                    "cantidad": 15,
                    "unidad": "unidades",
                    "precio_unitario": 15000,
                    "total": 225000
                },
                {
                    "producto": "Cerdo Lomo",
                    "cantidad": 10,
                    "unidad": "kg",
                    "precio_unitario": 18000,
                    "total": 180000
                }
            ],
            "total_orden": 955000
        }
    ]
    
    print("🌱 Creando órdenes de compra...")
    
    # Generar embeddings para los productos
    for order in orders:
        product_names = [item["producto"] for item in order["items"]]
        embeddings = await matching_service.get_embeddings(product_names)
        
        # Asignar embeddings a cada item
        for i, item in enumerate(order["items"]):
            item["embedding"] = embeddings[i]
    
    # Insertar en BD
    for order in orders:
        order_id = db.create_purchase_order(order)
        print(f"   ✅ Creada: {order['numero_orden']} - {order['proveedor']} (ID: {order_id})")
    
    print(f"\n✅ {len(orders)} órdenes de compra creadas\n")

async def seed_products_catalog():
    """Crea catálogo de productos con sinónimos"""
    
    products = [
        {
            "nombre": "Tomate Chonto",
            "sinonimos": ["Tomate Larga Vida", "Tomate Rojo", "Tomate Milano"],
            "categoria": "frutas_verduras",
            "unidad_base": "kg"
        },
        {
            "nombre": "Papa Pastusa",
            "sinonimos": ["Papa Blanca", "Papa Criolla"],
            "categoria": "frutas_verduras",
            "unidad_base": "kg"
        },
        {
            "nombre": "Cebolla Cabezona",
            "sinonimos": ["Cebolla Blanca", "Cebolla de Bulbo"],
            "categoria": "frutas_verduras",
            "unidad_base": "kg"
        },
        {
            "nombre": "Leche Entera",
            "sinonimos": ["Leche Fresca", "Leche Completa"],
            "categoria": "lacteos",
            "unidad_base": "litros"
        },
        {
            "nombre": "Queso Campesino",
            "sinonimos": ["Queso Fresco", "Queso Blanco"],
            "categoria": "lacteos",
            "unidad_base": "kg"
        }
    ]
    
    print("🌱 Creando catálogo de productos...")
    
    # Generar embeddings
    product_names = [p["nombre"] for p in products]
    embeddings = await matching_service.get_embeddings(product_names)
    
    for i, product in enumerate(products):
        product["embedding"] = embeddings[i]
        product_id = db.create_product(product)
        print(f"   ✅ Producto: {product['nombre']} (ID: {product_id})")
    
    print(f"\n✅ {len(products)} productos creados\n")

async def main():
    print("\n" + "="*60)
    print("🚀 SEED DATA - Validador de Mercancía")
    print("="*60 + "\n")
    
    try:
        # Limpiar colecciones existentes (opcional)
        print("⚠️  Limpiando datos anteriores...")
        db.purchase_orders.delete_many({})
        db.products.delete_many({})
        db.invoices.delete_many({})
        db.validations.delete_many({})
        print("   ✅ Datos limpios\n")
        
        # Crear datos de prueba
        await seed_products_catalog()
        await seed_purchase_orders()
        
        # Mostrar resumen
        print("="*60)
        print("📊 RESUMEN")
        print("="*60)
        print(f"   Órdenes de Compra: {db.purchase_orders.count_documents({})}")
        print(f"   Productos: {db.products.count_documents({})}")
        print(f"   Facturas: {db.invoices.count_documents({})}")
        print(f"   Validaciones: {db.validations.count_documents({})}")
        print("="*60)
        print("\n✅ Seed completado exitosamente!\n")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}\n")
        raise

if __name__ == "__main__":
    asyncio.run(main())