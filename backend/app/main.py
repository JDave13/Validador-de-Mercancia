from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from app.services.ai_service import ai_service
from app.services.matching_service import matching_service
from app.services.email_service import email_service 
from app.services.quality_service import quality_service
from app.database.mongodb import db
from datetime import datetime, timezone
from typing import Optional
import json
import uuid 
import re 
import asyncio
import inspect
import os 

app = FastAPI()

# Crear carpeta temporal al iniciar si no existe
TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- UTILS ---
def clean_price(price_str):
    if not price_str: return 0.0
    s = str(price_str).replace('$', '').replace(' ', '').strip()
    s = s.rstrip('.,')
    try:
        if re.match(r'^-?\d{1,3}(\.\d{3})+$', s): return float(s.replace('.', '')) 
        if re.match(r'^-?\d{1,3}(,\d{3})+$', s): return float(s.replace(',', ''))
        if ',' in s and '.' in s:
            if s.rfind(',') > s.rfind('.'): s = s.replace('.', '').replace(',', '.') 
            else: s = s.replace(',', '') 
            return float(s)
        if ',' in s:
            parts = s.split(',')
            if len(parts) > 1 and len(parts[-1]) == 3: s = s.replace(',', '') 
            else: s = s.replace(',', '.') 
        return float(s)
    except: return 0.0

def extract_hidden_quantity(name: str, current_qty: float):
    if not name: return current_qty
    name = name.upper()
    match = re.search(r'\(\s*[xX]?\s*(\d+)\s*\)', name)
    if match: return float(match.group(1))
    match = re.search(r'\s+[xX]\s*(\d+)$', name)
    if match: return float(match.group(1))
    return current_qty

def fix_mongo_id(document):
    if not document: return None
    if isinstance(document, list): return [fix_mongo_id(d) for d in document]
    if isinstance(document, dict):
        d = document.copy()
        if "_id" in d: d["_id"] = str(d["_id"])
        for k, v in d.items():
            if isinstance(v, (dict, list)): d[k] = fix_mongo_id(v)
        return d
    return document

async def enviar_alerta_async(data: dict):
    """Wrapper seguro para enviar correos sin bloquear el hilo principal"""
    try:
        f_id = data.get('factura_id', 'Desconocido')
        print(f"📧 Iniciando envío de alerta para: {f_id}")
        
        # Verificar imagen
        img_bytes = data.get('product_image_bytes')
        if img_bytes:
            print(f"   📸 Imagen adjunta detectada: {len(img_bytes) / 1024:.2f} KB")
        else:
            print("   ⚠️ No se detectó imagen en el payload del correo.")

        if inspect.iscoroutinefunction(email_service.send_alert):
            await email_service.send_alert(data)
        else:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, email_service.send_alert, data)
            
    except Exception as e:
        print(f"❌ Error crítico enviando email: {e}")

# --- ENDPOINTS ---

@app.post("/inspect-quality")
async def inspect_quality(
    product_image: UploadFile = File(...),
    product_name: str = Form(None),
    factura_id: str = Form(None),
    proveedor: str = Form(None)
):
    try:
        # 1. Leer imagen
        await product_image.seek(0)
        image_bytes = await product_image.read()
        print(f"🔍 Inspeccionando imagen: {len(image_bytes)} bytes")
        
        # 2. GUARDADO TEMPORAL: Si tenemos ID, guardamos la foto para usarla luego en finalize
        if factura_id:
            temp_path = os.path.join(TEMP_DIR, f"{factura_id}.jpg")
            with open(temp_path, "wb") as f:
                f.write(image_bytes)
            print(f"   💾 Imagen guardada temporalmente en: {temp_path}")

        # 3. Procesar con IA
        result = await quality_service.inspect_product_quality(image_bytes)
        
        if not result.get("success"): 
            raise HTTPException(status_code=500, detail="Error en servicio de IA de Calidad")
        
        # 4. Si es RECHAZADO y NO hay ID (flujo directo), enviar correo ya.
        if result.get("quality_status") == "RECHAZADO" and not factura_id:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            email_data = {
                "factura_id": f"RECHAZO-{timestamp}",
                "status": "RECHAZO-CALIDAD", 
                "rechazo_total": True,
                "proveedor": proveedor or "Desconocido",
                "fecha": datetime.now(timezone.utc),
                "product_name": product_name or result.get("product_type"),
                "product_image_bytes": image_bytes, 
                "product_image_filename": product_image.filename,
                "quality_inspection": result, 
                "items": [], 
                "totales": {}
            }
            asyncio.create_task(enviar_alerta_async(email_data))
            
        return result
    except Exception as e:
        print(f"❌ Error en inspect-quality: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/finalize-validation")
async def finalize_validation(
    factura_id: str = Form(...),
    quality_status: str = Form(...),
    quality_data: Optional[str] = Form(None),
    product_image: UploadFile = File(None)
):
    try:
        doc = db.validations.find_one({"factura_id": factura_id})
        if not doc: raise HTTPException(status_code=404, detail="Factura no encontrada")
        
        parsed_q = {}
        if quality_data:
            try: parsed_q = json.loads(quality_data)
            except: pass
            
        # --- LÓGICA DE RECUPERACIÓN DE IMAGEN ---
        img_bytes = None
        img_name = "evidencia.jpg"
        
        # 1. Intentar leer del request actual (si el frontend la envió)
        if product_image:
            print(f"📥 Recibiendo imagen desde request para {factura_id}")
            await product_image.seek(0)
            img_bytes = await product_image.read()
            img_name = product_image.filename
        
        # 2. Si no llegó, buscar en la carpeta temporal (del paso inspect-quality)
        else:
            temp_path = os.path.join(TEMP_DIR, f"{factura_id}.jpg")
            if os.path.exists(temp_path):
                print(f"🔄 Recuperando imagen desde caché temporal: {temp_path}")
                with open(temp_path, "rb") as f:
                    img_bytes = f.read()
                
                # --- BORRADO AUTOMÁTICO ---
                try:
                    os.remove(temp_path)
                    print(f"🗑️ Archivo temporal eliminado: {temp_path}")
                except Exception as e:
                    print(f"⚠️ Error intentando borrar temporal: {e}")
            else:
                print("⚠️ Finalize-validation: No hay imagen en request ni en caché.")

        estado_previo = doc.get("status", "VERDE")
        
        # CASO 1: RECHAZO
        if quality_status == "RECHAZADO":
            update = {
                "status": "ROJO", 
                "mensaje": "🚨 RECHAZADO POR CALIDAD FÍSICA",
                "quality_inspection": parsed_q, 
                "quality_status": "RECHAZADO",
                "rechazo_total": True, 
                "fecha_actualizacion": datetime.now(timezone.utc)
            }
            db.validations.update_one({"factura_id": factura_id}, {"$set": update})
            
            email_data = {
                **doc, 
                **update, 
                "product_image_bytes": img_bytes, 
                "product_image_filename": img_name
            }
            asyncio.create_task(enviar_alerta_async(email_data))
            return {"success": True, "estado_final": "ROJO", "rechazo_total": True}
        
        # CASO 2: APROBADO / OMITIDO
        else:
            db.validations.update_one(
                {"factura_id": factura_id},
                {"$set": {"quality_status": quality_status, "quality_inspection": parsed_q}}
            )
            return {"success": True, "estado_final": estado_previo, "rechazo_total": False}

    except Exception as e:
        print(f"❌ Error en finalize-validation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process-invoice")
async def process_invoice(invoice: UploadFile = File(...)):
    print(f"📥 Procesando Factura PDF/Img: {invoice.filename}")
    try:
        await invoice.seek(0)
        content = await invoice.read()
        ocr_res = await ai_service.extract_invoice_data(content)
        if not ocr_res["success"]: raise HTTPException(500, "Error OCR")
        
        data = ocr_res["invoice_data"]
        items = data.get("items", [])
        
        # Generación de ID
        ocr_id = data.get("invoice_number")
        invoice_id = str(ocr_id).strip() if ocr_id and str(ocr_id).strip().upper() not in ["N/A", ""] else f"AUTO-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6]}"
        es_id_real = "AUTO-" not in invoice_id

        if es_id_real and db.validations.find_one({"factura_id": invoice_id, "status": "ROJO"}):
            raise HTTPException(409, "Factura ya rechazada previamente.")

        total_ocr = clean_price(data.get("total_factura"))
        catalog = list(db.products.find({}))
        matches = await matching_service.match_all_items(items, catalog)

        # Precios
        sum_as_totals = 0
        sum_as_units = 0
        temp_items = []
        
        for m in matches:
            orig = m.get("original", {})
            try: cant = float(orig.get("cantidad", 0))
            except: cant = 0.0
            
            nombre = orig.get("producto", "")
            if cant <= 1.0: cant = extract_hidden_quantity(nombre, cant)
            if cant == 0: cant = 1.0
            
            p_leido = clean_price(orig.get("precio_unitario"))
            
            sum_as_totals += p_leido
            sum_as_units += (p_leido * cant)
            temp_items.append({"match": m, "cant": cant, "p_leido": p_leido})

        modo_precios = "UNITARIO"
        if total_ocr > 0:
            diff_totals = abs(total_ocr - sum_as_totals)
            diff_units = abs(total_ocr - sum_as_units)
            if diff_units < diff_totals:
                modo_precios = "UNITARIO"
            else:
                modo_precios = "TOTAL_LINEA"
        elif temp_items and temp_items[0]["match"].get("db_item"):
            db_p = clean_price(temp_items[0]["match"]["db_item"].get("precio"))
            p_l = temp_items[0]["p_leido"]
            c = temp_items[0]["cant"]
            if c > 1 and abs(p_l - (db_p * c)) < abs(p_l - db_p):
                modo_precios = "TOTAL_LINEA"

        # Reporte
        items_processed = []
        alertas = []
        total_esperado = 0.0
        validos = 0
        relevantes = 0

        for item in temp_items:
            m = item["match"]
            cant = item["cant"]
            p_leido = item["p_leido"]
            db_item = m.get("db_item")
            nombre = m.get("original", {}).get("producto", "Item")

            if modo_precios == "TOTAL_LINEA":
                line_total = p_leido
                unit_real = p_leido / cant if cant > 0 else 0
            else:
                unit_real = p_leido
                line_total = p_leido * cant

            p_esp = 0.0
            if db_item:
                p_esp = clean_price(db_item.get("precio") or db_item.get("costo"))
            
            total_esperado += (cant * (p_esp if p_esp > 0 else unit_real))
            
            ignore = any(x in nombre.upper() for x in ["BOLSA", "IMPOCONSUMO", "PROPINA"])
            status_item = "UNKNOWN"
            if db_item:
                status_item = "OK"
                if not ignore: validos += 1
            elif not ignore: alertas.append(f"Nuevo: {nombre}")
            if not ignore: relevantes += 1

            items_processed.append({
                "product_name": nombre,
                "matched_name": db_item["nombre"] if db_item else "No encontrado",
                "quantity": cant,
                "unit_price": unit_real,
                "line_total": line_total,
                "expected_price": p_esp,
                "status": status_item,
                "score": m.get("score", 0)
            })

        total_final = total_ocr if total_ocr > 0 else sum(i["line_total"] for i in items_processed)
        diff = ((total_final - total_esperado) / total_esperado * 100) if total_esperado > 0 else 0.0
        
        ratio = validos / relevantes if relevantes > 0 else 1.0
        status = "VERDE"
        msg = "Validación Exitosa"
        
        if abs(diff) > 10.0 or ratio < 0.5:
            status = "ROJO"
            msg = "Discrepancia Crítica (>10%)"
        elif abs(diff) > 5.0:
            status = "AMARILLO"
            msg = "Revisión necesaria"

        resumen = {
            "factura_id": invoice_id,
            "es_id_generado": not es_id_real,
            "fecha": datetime.now(timezone.utc),
            "status": status,
            "mensaje": msg,
            "proveedor": data.get("proveedor", "Desconocido"),
            "items": items_processed,
            "totales": { "facturado": total_final, "esperado": total_esperado, "diferencia": total_final - total_esperado },
            "desviacion_porcentual": diff,
            "quality_status": "PENDIENTE",
            "rechazo_total": False
        }
        
        db.validations.insert_one(resumen)
        if status != "VERDE": asyncio.create_task(enviar_alerta_async(resumen))

        return {"success": True, "status": status, "data": fix_mongo_id(resumen)}

    except Exception as e:
        print(f"❌ Error Process Invoice: {e}")
        raise HTTPException(500, str(e))

@app.get("/inventory")
async def get_inventory():
    return {"inventory": fix_mongo_id(list(db.inventory.find({})))}

@app.get("/")
async def root():
    return {"system": "Validador v3.3 (Image Cache & Clean)", "status": "online"}