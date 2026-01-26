import os
import re
import numpy as np
from difflib import SequenceMatcher
from dotenv import load_dotenv
from google import genai # <--- Importación nueva

load_dotenv()

class MatchingService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("❌ GEMINI_API_KEY no encontrada")
        
        # --- CAMBIO CLAVE: Usamos el Cliente nuevo ---
        self.client = genai.Client(api_key=self.api_key)
        self.model = "text-embedding-004"

    def normalize_text(self, text):
        """
        Limpia el 'ruido' común del OCR de facturas.
        Ej: '1,43FV. CEBOLLA CABEZONA' -> 'CEBOLLA CABEZONA'
        """
        if not text: return ""
        text = str(text).upper()
        # 1. Quitar patrones como '1,43FV.' o '01 ' al inicio
        text = re.sub(r'^[\d,\.]+[A-Z]*\.?\s*', '', text)
        # 2. Quitar caracteres no alfanuméricos (deja espacios)
        text = re.sub(r'[^\w\s]', '', text)
        return text.strip()

    def calculate_fuzzy_score(self, a, b):
        """Calcula similitud de texto puro (0 a 1)"""
        if not a or not b: return 0.0
        return SequenceMatcher(None, a, b).ratio()

    async def get_embeddings(self, texts):
        """Genera embeddings usando la NUEVA librería google-genai"""
        if not texts: return []
        
        # Sanitizar para evitar errores vacíos
        sanitized = [t if t and t.strip() else "unknown" for t in texts]
        
        try:
            # --- SINTAXIS NUEVA ---
            result = self.client.models.embed_content(
                model=self.model,
                contents=sanitized
            )
            # La nueva librería devuelve objetos, extraemos .values
            return [e.values for e in result.embeddings]
        except Exception as e:
            print(f"❌ Error generando embeddings: {e}")
            # Retornar vectores vacíos para no romper el flujo
            return [[0.0]*768 for _ in texts]

    def cosine_similarity(self, vec1, vec2):
        if not vec1 or not vec2: return 0.0
        # Asegurar que sean arrays de numpy y tipo float
        v1 = np.array(vec1, dtype=float)
        v2 = np.array(vec2, dtype=float)
        
        dot_product = np.dot(v1, v2)
        norm_a = np.linalg.norm(v1)
        norm_b = np.linalg.norm(v2)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot_product / (norm_a * norm_b))

    async def match_all_items(self, invoice_items: list, db_products: list) -> list:
        """
        LÓGICA HÍBRIDA:
        1. Intenta Fuzzy Match (Texto limpio vs Sinónimos). Si > 85%, es un match.
        2. Si falla, usa Embeddings (IA).
        """
        matches = []
        if not invoice_items: return []

        # Preparamos listas para IA (solo para los que no pasen el filtro fuzzy)
        items_needing_ai = []
        indices_needing_ai = []

        print(f"\n🔍 Iniciando Matching Híbrido para {len(invoice_items)} items...")

        # --- PASO 1: FUZZY MATCHING (TEXTO EXACTO) ---
        for idx, item in enumerate(invoice_items):
            # Obtener nombre sucio
            raw_name = (item.get("producto") or item.get("descripcion") or "").strip()
            # Limpiar nombre (Ej: "1,43FV. CEBOLLA" -> "CEBOLLA")
            clean_name = self.normalize_text(raw_name)
            
            best_fuzzy_score = 0.0
            best_fuzzy_product = None

            # Buscamos en DB (Nombre + Sinónimos)
            for db_prod in db_products:
                candidates = [db_prod['nombre']] + db_prod.get('sinonimos', [])
                for cand in candidates:
                    cand_clean = self.normalize_text(cand)
                    score = self.calculate_fuzzy_score(clean_name, cand_clean)
                    if score > best_fuzzy_score:
                        best_fuzzy_score = score
                        best_fuzzy_product = db_prod
            
            # DECISIÓN: Si el texto se parece más del 85%, NO usamos IA.
            if best_fuzzy_score > 0.85:
                print(f"   ✅ Fuzzy Match: '{clean_name}' == '{best_fuzzy_product['nombre']}' ({int(best_fuzzy_score*100)}%)")
                matches.append({
                    "original": item,
                    "db_item": best_fuzzy_product,
                    "score": round(best_fuzzy_score * 100, 2),
                    "match_found": True,
                    "method": "Fuzzy"
                })
            else:
                # Si no encontramos match claro, lo mandamos a la cola de IA
                items_needing_ai.append(clean_name if clean_name else raw_name)
                indices_needing_ai.append(idx)
                # Ponemos un placeholder en matches para rellenar luego
                matches.append(None) 

        # --- PASO 2: AI EMBEDDINGS (SOLO PARA LOS DIFÍCILES) ---
        if items_needing_ai:
            print(f"   ⚠️ Consultando IA para {len(items_needing_ai)} items difíciles...")
            inv_embeddings = await self.get_embeddings(items_needing_ai)

            for i, inv_emb in enumerate(inv_embeddings):
                original_idx = indices_needing_ai[i]
                original_item = invoice_items[original_idx]
                
                best_ai_score = -1.0
                best_ai_product = None

                for db_prod in db_products:
                    if "embedding" in db_prod:
                        score = self.cosine_similarity(inv_emb, db_prod["embedding"])
                        if score > best_ai_score:
                            best_ai_score = score
                            best_ai_product = db_prod
                
                # Umbral de IA 
                threshold = 0.60
                is_match = best_ai_score >= threshold
                
                matches[original_idx] = {
                    "original": original_item,
                    "db_item": best_ai_product if is_match else None,
                    "score": round(best_ai_score * 100, 2),
                    "match_found": is_match,
                    "method": "AI"
                }

        return matches

matching_service = MatchingService()