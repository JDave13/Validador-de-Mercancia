from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.services.ai_service import ai_service
from app.services.matching_service import matching_service
from app.services.email_service import email_service 
from app.database.mongodb import db
from datetime import datetime, timezone
import json
import uuid 
import re 

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def clean_price(price_str):
    if not price_str: return 0.0
    s = str(price_str).replace('$', '').replace(' ', '').strip()
    if re.match(r'^\d{1,3}(\.\d{3})+$', s):
        s = s.replace('.', '') 
    elif ',' in s:
        s = s.replace('.', '').replace(',', '.') 
    try:
        return float(s)
    except ValueError:
        return 0.0

def fix_mongo_id(document):
    if not document: return None
    if isinstance(document, list):
        return [fix_mongo_id(d) for d in document]
    if isinstance(document, dict):
        d = document.copy()
        if "_id" in d:
            d["_id"] = str(d["_id"])
        for k, v in d.items():
            if isinstance(v, (dict, list)):
                d[k] = fix_mongo_id(v)
        return d
    return document

@app.post("/process-invoice")
async def process_invoice(invoice: UploadFile = File(...)):
    print(f"📥 Procesando imagen: {invoice.filename}")
    
    # 1. OCR
    invoice_content = await invoice.read()
    ocr_result = await ai_service.extract_invoice_data(invoice_content)
    
    if not ocr_result["success"]:
        raise HTTPException(status_code=500, detail=ocr_result.get("error"))
    
    invoice_data = ocr_result["invoice_data"]
    items_factura = invoice_data.get("items", [])
    
    # ID & Duplicate Check
    ocr_id = invoice_data.get("invoice_number")
    if ocr_id and str(ocr_id).strip().upper() not in ["N/A", "NONE", ""]:
        invoice_id = str(ocr_id).strip()
        es_id_real = True
    else:
        timestamp = datetime.now().strftime("%Y%m%d")
        unique_suffix = str(uuid.uuid4())[:6].upper()
        invoice_id = f"AUTO-{timestamp}-{unique_suffix}"
        es_id_real = False

    if es_id_real:
        # Bloqueamos solo si ya existe y fue ROJA anteriormente
        prev = db.validations.find_one({"factura_id": invoice_id, "status": "ROJO"})
        if prev:
            raise HTTPException(status_code=409, detail=f"Factura {invoice_id} ya rechazada.")

    proveedor_detectado = invoice_data.get("proveedor") or "Proveedor Desconocido"
    total_facturado_ocr = clean_price(invoice_data.get("total_factura"))

    # 2. MATCHING
    catalog_products = list(db.products.find({}))
    matches = await matching_service.match_all_items(items_factura, catalog_products)

    # 3. CALCULOS
    items_procesados = []
    alertas = []
    items_validos_count = 0
    items_totales_relevantes = 0
    total_esperado_calculado = 0.0 

    for match in matches:
        item_factura = match.get("original", {})
        producto_catalogo = match.get("db_item")
        score = match.get("score", 0)
        
        nombre_factura = item_factura.get("producto") or item_factura.get("descripcion") or "Item"
        
        try:
            cant = float(item_factura.get("cantidad") or 0)
        except:
            cant = 0.0

        precio_factura = clean_price(item_factura.get("precio_unitario"))
        
        precio_db = 0.0
        if producto_catalogo:
            p_raw = producto_catalogo.get("precio") or producto_catalogo.get("costo")
            precio_db = clean_price(str(p_raw)) if p_raw else 0.0

        # Si hay precio DB, se usa para "Esperado". Si no, asumimos el de factura para no distorsionar.
        precio_ref = precio_db if precio_db > 0 else precio_factura
        total_esperado_calculado += (cant * precio_ref)

        es_irrelevante = "BOLSA" in nombre_factura.upper() or "IMPOCONSUMO" in nombre_factura.upper()

        detalles = {
            "product_name": nombre_factura,
            "matched_name": producto_catalogo["nombre"] if producto_catalogo else "No encontrado",
            "quantity": cant,
            "unit_price": precio_factura,
            "expected_price": precio_db,
            "score": score,
            "match_found": match.get("match_found", False),
            "status": "UNKNOWN"
        }

        if producto_catalogo:
            inv = db.inventory.find_one({"producto": producto_catalogo["nombre"]})
            if inv:
                detalles["status"] = "OK"
                if not es_irrelevante: items_validos_count += 1
            else:
                detalles["status"] = "NEW_ITEM"
                if not es_irrelevante: alertas.append(f"Nuevo item: {nombre_factura}")
        else:
            if not es_irrelevante: alertas.append(f"Desconocido: {nombre_factura}")

        if not es_irrelevante:
            items_totales_relevantes += 1
        items_procesados.append(detalles)

    # Totales Finales
    total_final = total_facturado_ocr if total_facturado_ocr > 0 else sum(i["quantity"] * i["unit_price"] for i in items_procesados)
    
    desviacion = 0.0
    if total_esperado_calculado > 0:
        desviacion = ((total_final - total_esperado_calculado) / total_esperado_calculado) * 100

    # 4. SEMÁFORO (LÓGICA ACTUALIZADA)
    if items_totales_relevantes > 0:
        ratio_exito = items_validos_count / items_totales_relevantes
    else:
        ratio_exito = 0.0 if len(items_factura) > 0 else 1.0

    # Definición estricta de estados
    # 🔴 ROJO: Desviación > 10% O mal reconocimiento (<50%)
    if abs(desviacion) > 10.0 or ratio_exito < 0.5:
        estado_validacion = "ROJO"
        mensaje_validacion = "Discrepancias críticas (>10%)"
    
    # 🟡 AMARILLO: Desviación entre 5% y 10% (inclusive 10, exclusivo 5)
    elif 5.0 < abs(desviacion) <= 10.0:
        estado_validacion = "AMARILLO"
        mensaje_validacion = "Revisión necesaria (5% - 10%)"
    
    # 🟢 VERDE: Desviación <= 5% (y buen ratio)
    else:
        estado_validacion = "VERDE"
        mensaje_validacion = "Validación Exitosa"

    # 5. GUARDAR Y NOTIFICAR
    resumen = {
        "factura_id": invoice_id,
        "es_id_generado": not es_id_real,
        "fecha": datetime.now(timezone.utc),
        "status": estado_validacion,
        "mensaje": mensaje_validacion,
        "proveedor": proveedor_detectado,
        "items": items_procesados,
        "alertas": alertas,
        "totales": {
            "facturado": total_final,
            "esperado": total_esperado_calculado,
            "diferencia": total_final - total_esperado_calculado
        },
        "desviacion_porcentual": desviacion,
        "matchResults": items_procesados
    }
    
    try:
        db.validations.insert_one(resumen)
    except Exception as e:
        print(f"⚠️ Error Mongo: {e}")

    # --- CORRECCIÓN DE EMAIL ---
    if estado_validacion in ["ROJO", "AMARILLO"]:
        print(f"📧 Enviando alerta por estado: {estado_validacion}")
        try:
            # AGREGADO AWAIT: Es probable que send_alert sea asíncrono
            # Si no es async, el await no estorba mucho en versiones modernas, 
            # pero si lo es y faltaba, era la causa del error.
            if hasattr(email_service.send_alert, '__await__') or  \
               (hasattr(email_service, 'send_alert') and hasattr(email_service.send_alert, '__code__') and \
                email_service.send_alert.__code__.co_flags & 0x80):
                 await email_service.send_alert(resumen)
            else:
                 email_service.send_alert(resumen)
                 
        except Exception as e:
            print(f"⚠️ Error enviando email: {e}")

    return {
        "success": True,
        "mensaje": mensaje_validacion,
        "status": estado_validacion,
        "factura_id": invoice_id,
        "data": fix_mongo_id(resumen)
    }

@app.get("/inventory")
async def get_inventory():
    stock = list(db.inventory.find({}))
    return {"inventory": fix_mongo_id(stock)}