import os
import google.generativeai as genai
import numpy as np
from app.database.mongodb import db
from dotenv import load_dotenv
import re
from difflib import SequenceMatcher

load_dotenv()

class MatchingService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("❌ GEMINI_API_KEY no encontrada")
        genai.configure(api_key=self.api_key)
        self.model = "models/text-embedding-004"

    def normalize_text(self, text):
        """
        Limpia el 'ruido' común del OCR de facturas.
        Ej: '1,43FV. CEBOLLA CABEZONA' -> 'CEBOLLA CABEZONA'
        """
        if not text: return ""
        # 1. Convertir a mayúsculas
        text = text.upper()
        # 2. Quitar patrones como '1,43FV.' o '01 ' al inicio
        # Regex: Busca números, comas/puntos y letras raras al inicio seguidos de un punto o espacio
        text = re.sub(r'^[\d,\.]+[A-Z]*\.?\s*', '', text)
        # 3. Quitar caracteres especiales sobrantes
        text = re.sub(r'[^\w\s]', '', text)
        return text.strip()

    def calculate_fuzzy_score(self, a, b):
        """Calcula similitud de texto puro (0 a 1)"""
        return SequenceMatcher(None, a, b).ratio()

    async def get_embeddings(self, texts):
        try:
            # Generamos embeddings en lote
            result = genai.embed_content(
                model=self.model,
                content=texts,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            print(f"❌ Error generando embeddings: {e}")
            return []

    async def find_best_match(self, ocr_product_name):
        """
        Estrategia Híbrida:
        1. Fuzzy Match (Texto): Para coincidencias obvias y sinónimos exactos.
        2. Semantic Match (IA): Para conceptos relacionados.
        """
        ocr_clean = self.normalize_text(ocr_product_name)
        print(f"🔍 Buscando match para: '{ocr_product_name}' (Limpio: '{ocr_clean}')")

        products_cursor = db.products.find({})
        all_products = list(products_cursor)
        
        best_match = None
        highest_score = 0
        method = "None"

        # --- FASE 1: FUZZY MATCH (Texto vs Texto) ---
        # Revisamos todos los productos y sus sinónimos
        for product in all_products:
            candidates = [product['nombre']] + product.get('sinonimos', [])
            
            # Buscamos la mejor coincidencia de texto en este producto
            local_best_score = 0
            for candidate in candidates:
                candidate_clean = self.normalize_text(candidate)
                score = self.calculate_fuzzy_score(ocr_clean, candidate_clean)
                if score > local_best_score:
                    local_best_score = score
            
            # Si encontramos un match de texto muy alto, priorizamos esto
            if local_best_score > highest_score:
                highest_score = local_best_score
                best_match = product
                method = "Fuzzy"

        # Si el Fuzzy Match es excelente (> 0.85), nos quedamos con él y ahorramos IA
        if highest_score > 0.85:
            print(f"✅ Match Fuzzy encontrado: {best_match['nombre']} ({highest_score:.2f})")
            return {
                "matched_product": best_match,
                "score": highest_score,
                "method": "Fuzzy-Logic"
            }

        # --- FASE 2: SEMANTIC MATCH (IA Embeddings) ---
        print("⚠️ Fuzzy bajo, consultando IA (Embeddings)...")
        
        # Generar embedding del item de la factura
        try:
            query_embedding = genai.embed_content(
                model=self.model,
                content=ocr_product_name, # Enviamos el original para contexto
                task_type="retrieval_query"
            )['embedding']
        except:
            return None

        # Comparar vectores
        best_vector_score = -1
        best_vector_product = None

        for product in all_products:
            if "embedding" not in product: continue
            
            db_embedding = product["embedding"]
            # Similitud de Coseno
            score = np.dot(query_embedding, db_embedding)
            
            if score > best_vector_score:
                best_vector_score = score
                best_vector_product = product

        # Decisión Final: ¿Quién ganó?
        # A veces el fuzzy es 0.6 pero el vector es 0.8. Nos quedamos con el mejor.
        final_score = max(highest_score, best_vector_score)
        
        if best_vector_score > highest_score:
            return {
                "matched_product": best_vector_product,
                "score": float(best_vector_score),
                "method": "AI-Embedding"
            }
        else:
             return {
                "matched_product": best_match,
                "score": float(highest_score),
                "method": "Fuzzy-Logic"
            }

matching_service = MatchingService()