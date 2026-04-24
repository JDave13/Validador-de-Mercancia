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

# --- UTILS MEJORADOS (Lógica Definitiva) ---

def parse_number(num_str, is_price=False):
    """
    Parsea números con reglas estrictas para Colombia/Latam.
    """
    if not num_str: return 0.0
    
    # 1. Limpieza inicial: Quitar simbolos de moneda y espacios
    # Convertimos a string y quitamos espacios internos (ej: "1 500" -> "1500")
    s = str(num_str).replace('$', '').replace(' ', '').strip()
    
    # 2. Manejo de negativos (paréntesis o signo menos)
    is_negative = False
    if s.startswith('-') or (s.startswith('(') and s.endswith(')')):
        is_negative = True
        s = s.replace('-', '').replace('(', '').replace(')', '')
    
    # 3. Limpieza de caracteres basura (dejar solo dígitos, puntos y comas)
    s = re.sub(r'[^\d.,]', '', s)
    
    if not s: return 0.0

    try:
        val = 0.0
        
        # CASO 1: Formato con múltiples separadores (ej: 1.234.567)
        # Si hay más de un punto, definitivamente son miles.
        if s.count('.') > 1:
            # Formato: 1.200.000 -> Quitamos puntos
            val = float(s.replace('.', '').replace(',', '.'))
            
        elif s.count(',') > 1:
            # Formato raro (USA millones): 1,200,000 -> Quitamos comas
            val = float(s.replace(',', ''))
            
        # CASO 2: Separadores mixtos (ej: 1.200,50 o 1,200.50)
        elif '.' in s and ',' in s:
            last_dot = s.rfind('.')
            last_comma = s.rfind(',')
            
            if last_comma > last_dot: # Formato COL: 1.200,50
                val = float(s.replace('.', '').replace(',', '.'))
            else: # Formato USA: 1,200.50
                val = float(s.replace(',', ''))
        
        # CASO 3: Solo Puntos (El caso más conflictivo: 1.500 vs 1.5)
        elif '.' in s:
            # Regla de Oro para Precios en Colombia:
            # Si es precio Y tiene exactamente 3 decimales al final (ej: 1.500), es MILES.
            # Si tiene 1 o 2 (ej: 1.5 o 1.50), es DECIMAL.
            if is_price:
                if re.search(r'\.\d{3}$', s): # Termina en .XXX (ej: 1.200)
                    val = float(s.replace('.', ''))
                else:
                    val = float(s) # Ej: 5.5 (cinco punto cinco)
            else:
                # Si es cantidad (Kg/Lb), el punto suele ser decimal (1.5 kg)
                # A MENOS que sea un número enorme, pero asumimos decimal por defecto en cantidades
                val = float(s)

        # CASO 4: Solo Comas (ej: 1,5 o 1200,50)
        elif ',' in s:
            # En Latam la coma es decimal casi siempre
            val = float(s.replace(',', '.'))
            
        # CASO 5: Solo dígitos
        else:
            val = float(s)

        return -val if is_negative else val

    except Exception as e:
        print(f"⚠️ Error crítico parseando número '{num_str}': {e}")
        return 0.0

def extract_hidden_quantity(name: str, current_qty: float):
    if not name: return current_qty
    name = name.upper()
    # Busca patrones como (x12), x 24, etc.
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
    try:
        f_id = data.get('factura_id', 'Desconocido')
        print(f"📧 Enviando alerta background: {f_id}")
        
        if inspect.iscoroutinefunction(email_service.send_alert):
            await email_service.send_alert(data)
        else:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, email_service.send_alert, data)
    except Exception as e:
        print(f"❌ Error enviando email: {e}")

# --- ENDPOINTS ---

@app.post("/inspect-quality")
async def inspect_quality(
    product_image: UploadFile = File(...),
    product_name: str = Form(None),
    factura_id: str = Form(None),
    proveedor: str = Form(None)
):
    try:
        await product_image.seek(0)
        image_bytes = await product_image.read()
        print(f"🔍 Inspeccionando imagen: {len(image_bytes)} bytes")
        
        if factura_id:
            temp_path = os.path.join(TEMP_DIR, f"{factura_id}.jpg")
            with open(temp_path, "wb") as f:
                f.write(image_bytes)

        result = await quality_service.inspect_product_quality(image_bytes)
        
        if not result.get("success"): 
            raise HTTPException(status_code=500, detail="Error IA Calidad")
        
        if result.get("quality_status") == "RECHAZADO" and not factura_id:
            email_data = {
                "factura_id": f"RECHAZO-{datetime.now().strftime('%Y%m%d%H%M')}",
                "status": "RECHAZO-CALIDAD", 
                "rechazo_total": True,
                "proveedor": proveedor or "Desconocido",
                "fecha": datetime.now(timezone.utc),
                "product_name": product_name,
                "product_image_bytes": image_bytes, 
                "product_image_filename": product_image.filename,
                "quality_inspection": result, 
                "items": [], "totales": {}
            }
            asyncio.create_task(enviar_alerta_async(email_data))
            
        return result
    except Exception as e:
        print(f"❌ Error inspect-quality: {e}")
        raise HTTPException(500, str(e))

@app.post("/finalize-validation")
async def finalize_validation(
    factura_id: str = Form(...),
    quality_status: str = Form(...),
    quality_data: Optional[str] = Form(None),
    product_image: UploadFile = File(None)
):
    try:
        doc = db.validations.find_one({"factura_id": factura_id})
        if not doc: raise HTTPException(404, "Factura no encontrada")
        
        parsed_q = json.loads(quality_data) if quality_data else {}
        
        img_bytes = None
        img_name = "evidencia.jpg"
        
        if product_image:
            await product_image.seek(0)
            img_bytes = await product_image.read()
            img_name = product_image.filename
        else:
            temp_path = os.path.join(TEMP_DIR, f"{factura_id}.jpg")
            if os.path.exists(temp_path):
                with open(temp_path, "rb") as f: img_bytes = f.read()
                try: os.remove(temp_path) 
                except: pass

        estado_previo = doc.get("status", "VERDE")
        
        if quality_status == "RECHAZADO":
            update = {
                "status": "ROJO", 
                "mensaje": "🚨 RECHAZADO POR CALIDAD",
                "quality_inspection": parsed_q, 
                "quality_status": "RECHAZADO",
                "rechazo_total": True
            }
            db.validations.update_one({"factura_id": factura_id}, {"$set": update})
            
            email_data = {**doc, **update, "product_image_bytes": img_bytes, "product_image_filename": img_name}
            asyncio.create_task(enviar_alerta_async(email_data))
            return {"success": True, "estado_final": "ROJO"}
        else:
            db.validations.update_one(
                {"factura_id": factura_id},
                {"$set": {"quality_status": quality_status, "quality_inspection": parsed_q}}
            )
            return {"success": True, "estado_final": estado_previo}

    except Exception as e:
        print(f"❌ Error finalize-validation: {e}")
        raise HTTPException(500, str(e))

@app.post("/process-invoice")
async def process_invoice(invoice: UploadFile = File(...)):
    print(f"📥 Procesando: {invoice.filename}")
    try:
        await invoice.seek(0)
        content = await invoice.read()
        ocr_res = await ai_service.extract_invoice_data(content)
        if not ocr_res["success"]: raise HTTPException(500, "Error OCR")
        
        data = ocr_res["invoice_data"]
        items = data.get("items", [])
        
        ocr_id = data.get("invoice_number")
        # Generar ID robusto
        clean_id = str(ocr_id).strip().upper()
        if not ocr_id or clean_id in ["N/A", "NONE", ""]:
            invoice_id = f"AUTO-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6]}"
            es_id_real = False
        else:
            invoice_id = clean_id
            es_id_real = True

        if es_id_real and db.validations.find_one({"factura_id": invoice_id, "status": "ROJO"}):
            raise HTTPException(409, "Factura rechazada previamente.")

        # PARSEO CRÍTICO: Precios y Totales
        total_ocr = parse_number(data.get("total_factura"), is_price=True)
        
        catalog = list(db.products.find({}))
        matches = await matching_service.match_all_items(items, catalog)

        sum_as_totals = 0
        sum_as_units = 0
        temp_items = []
        
        for m in matches:
            orig = m.get("original", {})
            
            # Cantidad: is_price=False (permite 1.5 como 1.5, no 1500)
            cant = parse_number(orig.get("cantidad"), is_price=False)
            
            nombre = orig.get("producto", "")
            if cant <= 1.0: 
                extracted = extract_hidden_quantity(nombre, cant)
                if extracted > cant: cant = extracted
            
            if cant == 0: cant = 1.0
            
            # Precio: is_price=True (1.500 se convierte en 1500)
            p_leido = parse_number(orig.get("precio_unitario"), is_price=True)
            
            sum_as_totals += p_leido
            sum_as_units += (p_leido * cant)
            temp_items.append({"match": m, "cant": cant, "p_leido": p_leido})

        # Determinación de modo de precios (Unitario vs Total)
        modo_precios = "UNITARIO"
        
        if total_ocr > 0:
            diff_totals = abs(total_ocr - sum_as_totals)
            diff_units = abs(total_ocr - sum_as_units)
            # Si la suma de los leídos como "totales de linea" se acerca más al total factura
            if diff_totals < diff_units: 
                modo_precios = "TOTAL_LINEA"
            else:
                modo_precios = "UNITARIO"
        else:
            # Heurística si no hay total factura: comparar con precio DB
            if temp_items and temp_items[0]["match"].get("db_item"):
                item0 = temp_items[0]
                db_p = parse_number(item0["match"]["db_item"].get("precio"), is_price=True)
                if item0["cant"] > 1 and abs(item0["p_leido"] - (db_p * item0["cant"])) < abs(item0["p_leido"] - db_p):
                    modo_precios = "TOTAL_LINEA"

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
                p_esp = parse_number(db_item.get("precio") or db_item.get("costo"), is_price=True)
            
            # Usamos precio esperado para calcular "lo que debió costar"
            total_esperado += (cant * (p_esp if p_esp > 0 else unit_real))
            
            ignore = any(x in nombre.upper() for x in ["BOLSA", "IMPOCONSUMO", "PROPINA", "SERVICIO"])
            status_item = "UNKNOWN"
            if db_item:
                status_item = "OK"
                if not ignore: validos += 1
            elif not ignore: alertas.append(nombre)
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
            msg = f"Discrepancia {diff:.1f}% o ítems desconocidos"
        elif abs(diff) > 5.0:
            status = "AMARILLO"
            msg = "Revisar precios unitarios"

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
        print(f"❌ Error Fatal Process Invoice: {e}")
        raise HTTPException(500, str(e))

@app.get("/inventory")
async def get_inventory():
    return {"inventory": fix_mongo_id(list(db.inventory.find({})))}

@app.get("/")
async def root():
    return {"system": "Validador v3.7 (Regex Strict Parsing)", "status": "online"}