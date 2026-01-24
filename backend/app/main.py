from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv

# Importar servicios
from app.services.gemini_service import gemini_service
from app.services.matching_service import matching_service
from app.services.validation_service import validation_service
from app.services.email_service import email_service
from app.database.mongodb import db

load_dotenv()

app = FastAPI(title="Validador de Mercancía API", version="1.0.0")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== MODELOS PYDANTIC ==========

class InvoiceItem(BaseModel):
    producto: str
    cantidad: float
    unidad: str = "unidades"
    precio_unitario: float
    total: float

class InvoiceData(BaseModel):
    proveedor: str
    fecha: str
    numero_factura: Optional[str] = None
    items: List[InvoiceItem]
    subtotal: Optional[float] = 0
    iva: Optional[float] = 0
    total_factura: float

class ValidationRequest(BaseModel):
    invoice_data: InvoiceData
    purchase_order_id: Optional[str] = None

# ========== ENDPOINTS ==========

@app.get("/")
async def root():
    return {
        "app": "Validador de Mercancía",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "ocr": "/upload-invoice",
            "validation": "/validate",
            "visual": "/inspect-visual",
            "purchase_orders": "/purchase-orders",
            "stats": "/stats"
        }
    }

@app.post("/upload-invoice")
async def upload_invoice(file: UploadFile = File(...)):
    """
    Endpoint 1: OCR de factura con Gemini
    Recibe imagen, extrae datos estructurados
    """
    try:
        # Validar tipo de archivo
        if not file.content_type.startswith("image/"):
            raise HTTPException(400, "Solo se permiten imágenes")
        
        # Leer imagen
        image_data = await file.read()
        
        # Extraer datos con Gemini OCR
        result = await gemini_service.extract_invoice_data(image_data)
        
        if not result["success"]:
            raise HTTPException(500, f"Error en OCR: {result.get('error')}")
        
        invoice_data = result["data"]
        
        # Buscar orden de compra del proveedor
        purchase_order = db.get_purchase_order_by_supplier(invoice_data["proveedor"])
        
        return {
            "success": True,
            "invoice_data": invoice_data,
            "purchase_order_found": purchase_order is not None,
            "purchase_order_id": str(purchase_order["_id"]) if purchase_order else None,
            "message": "Factura procesada exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error procesando factura: {str(e)}")

@app.post("/validate")
async def validate_invoice(request: ValidationRequest):
    """
    Endpoint 2: Validación completa
    Fuzzy matching + validación financiera + semáforo
    """
    try:
        invoice_data = request.invoice_data.dict()
        
        # 1. Buscar orden de compra
        if request.purchase_order_id:
            from bson import ObjectId
            purchase_order = db.purchase_orders.find_one({"_id": ObjectId(request.purchase_order_id)})
        else:
            purchase_order = db.get_purchase_order_by_supplier(invoice_data["proveedor"])
        
        if not purchase_order:
            raise HTTPException(404, f"No hay orden de compra para el proveedor '{invoice_data['proveedor']}'")
        
        # 2. Fuzzy matching de productos
        invoice_items = [item for item in invoice_data["items"]]
        po_items = purchase_order.get("items", [])
        
        match_results = await matching_service.match_all_items(invoice_items, po_items)
        
        # 3. Validación financiera completa
        validation_result = validation_service.validate_invoice_complete(
            invoice_data,
            purchase_order,
            match_results
        )
        
        # 4. Guardar validación en BD
        validation_id = db.save_validation(validation_result)
        
        # 5. Guardar factura
        invoice_data["validacion"] = {
            "validation_id": validation_id,
            "status": validation_result["status"],
            "aprobado": validation_result["aprobado"]
        }
        invoice_id = db.create_invoice(invoice_data)
        
        # 6. Enviar notificaciones si es necesario
        if validation_result.get("requiere_notificacion"):
            email_service.send_alert(validation_result)
        elif validation_result["aprobado"]:
            # Actualizar estado de orden de compra
            db.update_purchase_order_status(str(purchase_order["_id"]), "completada")
        
        return {
            "success": True,
            "validation": validation_result,
            "invoice_id": invoice_id,
            "match_results": match_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error en validación: {str(e)}")

@app.post("/inspect-visual")
async def inspect_visual(
    file: UploadFile = File(...),
    product_type: str = "general"
):
    """
    Endpoint 3: Inspector Visual con Gemini Vision
    Analiza calidad del producto
    """
    try:
        if not file.content_type.startswith("image/"):
            raise HTTPException(400, "Solo se permiten imágenes")
        
        image_data = await file.read()
        
        # Analizar calidad visual
        result = await gemini_service.analyze_product_quality(image_data, product_type)
        
        if not result["success"]:
            raise HTTPException(500, f"Error en análisis: {result.get('error')}")
        
        quality_data = result["data"]
        
        return {
            "success": True,
            "quality": quality_data,
            "recommendation": "APROBAR" if quality_data["apto_venta"] else "RECHAZAR"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error inspeccionando producto: {str(e)}")

# ========== ENDPOINTS DE GESTIÓN ==========

@app.get("/purchase-orders")
async def get_purchase_orders():
    """Obtiene todas las órdenes de compra"""
    try:
        orders = db.get_all_purchase_orders()
        # Convertir ObjectId a string
        for order in orders:
            order["_id"] = str(order["_id"])
        return {"success": True, "orders": orders}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/purchase-orders")
async def create_purchase_order(order_data: dict):
    """Crea una nueva orden de compra"""
    try:
        order_id = db.create_purchase_order(order_data)
        return {"success": True, "order_id": order_id}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/stats")
async def get_stats():
    """Obtiene estadísticas de validaciones"""
    try:
        stats = db.get_validation_stats(days=30)
        return {"success": True, "stats": stats}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/invoices/{proveedor}")
async def get_invoices_by_supplier(proveedor: str):
    """Obtiene facturas de un proveedor"""
    try:
        invoices = db.get_invoices_by_supplier(proveedor)
        for inv in invoices:
            inv["_id"] = str(inv["_id"])
        return {"success": True, "invoices": invoices}
    except Exception as e:
        raise HTTPException(500, str(e))

# ========== EVENTO DE CIERRE ==========

@app.on_event("shutdown")
def shutdown_event():
    db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)