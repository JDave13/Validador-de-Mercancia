from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import os
from typing import Optional, List, Dict
from datetime import datetime

class MongoDB:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDB, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.uri = os.getenv("MONGODB_URI")
        self.db_name = os.getenv("MONGODB_DB_NAME", "validador_mercancia")
        
        if not self.uri:
            raise ValueError("MONGODB_URI no está configurada en .env")
        
        try:
            self.client = MongoClient(self.uri)
            # Verificar conexión
            self.client.admin.command('ping')
            print("✅ Conexión a MongoDB exitosa")
            
            self.db = self.client[self.db_name]
            
            # Referencias a colecciones
            self.purchase_orders = self.db.purchase_orders
            self.invoices = self.db.invoices
            self.products = self.db.products
            self.validations = self.db.validations
            
            self._initialized = True
            
        except ConnectionFailure as e:
            print(f"❌ Error conectando a MongoDB: {e}")
            raise
    
    # ========== PURCHASE ORDERS ==========
    
    def create_purchase_order(self, order_data: dict) -> str:
        """Crea una nueva orden de compra"""
        order_data["fecha_creacion"] = datetime.utcnow()
        order_data["estado"] = "pendiente"
        result = self.purchase_orders.insert_one(order_data)
        return str(result.inserted_id)
    
    def get_purchase_order_by_supplier(self, proveedor: str, estado: str = "pendiente") -> Optional[dict]:
        """Busca órdenes de compra pendientes de un proveedor"""
        return self.purchase_orders.find_one({
            "proveedor": proveedor,
            "estado": estado
        })
    
    def get_all_purchase_orders(self, limit: int = 100) -> List[dict]:
        """Obtiene todas las órdenes de compra"""
        return list(self.purchase_orders.find().limit(limit))
    
    def update_purchase_order_status(self, order_id: str, estado: str):
        """Actualiza el estado de una orden de compra"""
        from bson import ObjectId
        self.purchase_orders.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"estado": estado, "fecha_actualizacion": datetime.utcnow()}}
        )
    
    # ========== INVOICES ==========
    
    def create_invoice(self, invoice_data: dict) -> str:
        """Guarda una factura procesada"""
        invoice_data["fecha_procesamiento"] = datetime.utcnow()
        result = self.invoices.insert_one(invoice_data)
        return str(result.inserted_id)
    
    def get_invoice(self, invoice_id: str) -> Optional[dict]:
        """Obtiene una factura por ID"""
        from bson import ObjectId
        return self.invoices.find_one({"_id": ObjectId(invoice_id)})
    
    def get_invoices_by_supplier(self, proveedor: str) -> List[dict]:
        """Obtiene todas las facturas de un proveedor"""
        return list(self.invoices.find({"proveedor": proveedor}))
    
    # ========== PRODUCTS (CATÁLOGO) ==========
    
    def create_product(self, product_data: dict) -> str:
        """Crea un producto en el catálogo maestro"""
        result = self.products.insert_one(product_data)
        return str(result.inserted_id)
    
    def search_products_by_embedding(self, embedding: List[float], limit: int = 5) -> List[dict]:
        """
        Búsqueda vectorial de productos similares
        Requiere índice de búsqueda vectorial configurado en Atlas
        """
        pipeline = [
            {
                "$search": {
                    "index": "product_vector_index",
                    "knnBeta": {
                        "vector": embedding,
                        "path": "embedding",
                        "k": limit
                    }
                }
            },
            {
                "$project": {
                    "nombre": 1,
                    "categoria": 1,
                    "sinonimos": 1,
                    "score": {"$meta": "searchScore"}
                }
            }
        ]
        
        return list(self.products.aggregate(pipeline))
    
    def get_all_products(self) -> List[dict]:
        """Obtiene todos los productos del catálogo"""
        return list(self.products.find())
    
    # ========== VALIDATIONS ==========
    
    def save_validation(self, validation_data: dict) -> str:
        """Guarda el resultado de una validación"""
        validation_data["timestamp"] = datetime.utcnow()
        result = self.validations.insert_one(validation_data)
        return str(result.inserted_id)
    
    def get_validation_stats(self, days: int = 30) -> dict:
        """Obtiene estadísticas de validaciones"""
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff_date}}},
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1},
                    "avg_desviacion": {"$avg": "$desviacion_porcentual"}
                }
            }
        ]
        
        results = list(self.validations.aggregate(pipeline))
        
        stats = {
            "total": sum(r["count"] for r in results),
            "verde": 0,
            "amarillo": 0,
            "rojo": 0
        }
        
        for r in results:
            if r["_id"] == "VERDE":
                stats["verde"] = r["count"]
            elif r["_id"] == "AMARILLO":
                stats["amarillo"] = r["count"]
            elif r["_id"] == "ROJO":
                stats["rojo"] = r["count"]
        
        return stats
    
    # ========== UTILIDADES ==========
    
    def close(self):
        """Cierra la conexión"""
        if self.client:
            self.client.close()
            print("Conexión a MongoDB cerrada")

# Singleton global
db = MongoDB()