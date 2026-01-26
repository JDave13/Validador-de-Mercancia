import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

# Importamos tus servicios actuales
from app.services.matching_service import matching_service
from app.database.mongodb import db

async def run_diagnostico():
    print("--- 🩺 INICIANDO DIAGNÓSTICO ---")

    # 1. VERIFICAR API KEY
    api_key = os.getenv("GEMINI_API_KEY")
    print(f"\n1️⃣  API KEY: {'✅ Detectada' if api_key else '❌ NO DETECTADA'}")
    
    # 2. PRUEBA DE GENERACIÓN (Ver si la IA responde de verdad)
    print("\n2️⃣  Probando generación de embedding con Google...")
    try:
        # Probamos generar el vector de una palabra simple
        test_vector = await matching_service.get_embeddings(["Prueba de conexión"])
        vector = test_vector[0]
        
        dim = len(vector)
        es_todo_ceros = sum(vector) == 0

        print(f"   ➡️  Dimensión obtenida: {dim}")
        
        if dim == 768 and not es_todo_ceros:
            print("   ✅ IA FUNCIONANDO: Generó un vector válido.")
        elif es_todo_ceros:
            print("   ⚠️ ERROR SILENCIOSO: La IA devolvió ceros (hubo error y el try/except lo ocultó).")
        else:
            print(f"   ⚠️ DIMENSIÓN EXTRAÑA: Se esperaban 768, se recibieron {dim}.")
            
    except Exception as e:
        print(f"   ❌ ERROR CRÍTICO LLAMANDO A GOOGLE: {e}")

    # 3. VERIFICAR BASE DE DATOS
    print("\n3️⃣  Inspeccionando Base de Datos (Mongo)...")
    producto = db.products.find_one({"nombre": "Cebolla Cabezona"})
    
    if not producto:
        print("   ❌ NO SE ENCONTRÓ 'Cebolla Cabezona' en la DB. (Ejecuta seed_data.py)")
    else:
        emb_db = producto.get("embedding", [])
        if not emb_db:
            print("   ❌ El producto existe pero NO TIENE embedding.")
        else:
            dim_db = len(emb_db)
            db_es_ceros = sum(emb_db) == 0
            print(f"   ➡️  Producto en DB: {producto['nombre']}")
            print(f"   ➡️  Dimensión en DB: {dim_db}")
            
            if db_es_ceros:
                print("   ❌ ERROR IDENTIFICADO: El vector en la DB es pura basura (CEROS).")
                print("      Por eso el match da 0%. Debemos regenerar la data.")
            else:
                print("   ✅ El vector en DB parece correcto (tiene datos reales).")

if __name__ == "__main__":
    asyncio.run(run_diagnostico())