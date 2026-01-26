from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import os
from dotenv import load_dotenv

load_dotenv()

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
            raise ValueError("⚠️ MONGODB_URI no está configurada en .env")
        
        try:
            self.client = MongoClient(self.uri)
            print("✅ Conexión a MongoDB exitosa")
            
            self.db = self.client[self.db_name]
            
            # COLECCIONES REDEFINIDAS
            self.purchase_orders = self.db.purchase_orders  # Órdenes de compra PENDIENTES
            self.invoices = self.db.invoices                # Facturas procesadas
            self.inventory = self.db.inventory              # Stock ACTUAL en bodega
            self.products = self.db.products                # Catálogo maestro
            self.validations = self.db.validations          # Historial de validaciones
            
            self._initialized = True
            
        except ConnectionFailure as e:
            print(f"❌ Error conectando a MongoDB: {e}")
            raise

    def find_purchase_order_by_provider(self, proveedor: str):
        """
        Busca una ORDEN DE COMPRA pendiente (no recibida) del proveedor.
        """
        return self.purchase_orders.find_one({
            "proveedor": {"$regex": proveedor, "$options": "i"},
            "estado": "PENDIENTE"  # Solo órdenes que esperan entrega
        })
    
    def mark_order_as_received(self, order_id: str, validation_id: str):
        """
        Marca una orden como recibida después de validación exitosa.
        """
        self.purchase_orders.update_one(
            {"_id": order_id},
            {
                "$set": {
                    "estado": "RECIBIDA",
                    "validation_id": validation_id
                }
            }
        )
    
    def update_inventory(self, items: list):
        """
        Actualiza el stock en bodega sumando las cantidades recibidas.
        """
        for item in items:
            # Busca el producto en inventario
            existing = self.inventory.find_one({"producto": item["producto"]})
            
            if existing:
                # Incrementa stock existente
                self.inventory.update_one(
                    {"producto": item["producto"]},
                    {"$inc": {"stock_actual": item["cantidad"]}}
                )
            else:
                # Crea nuevo registro
                self.inventory.insert_one({
                    "producto": item["producto"],
                    "stock_actual": item["cantidad"],
                    "unidad": item.get("unidad", "unidad"),
                    "ubicacion": "Bodega Principal"
                })

db = MongoDB()