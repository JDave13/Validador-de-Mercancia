import cohere
import os
import numpy as np
from typing import List, Dict, Tuple

class MatchingService:
    def __init__(self):
        api_key = os.getenv("COHERE_API_KEY")
        if not api_key:
            raise ValueError("COHERE_API_KEY no configurada")
        
        self.co = cohere.Client(api_key)
        self.threshold = float(os.getenv("SIMILARITY_THRESHOLD", 0.85))
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calcula similitud coseno entre dos vectores
        """
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm_a = np.linalg.norm(vec1)
        norm_b = np.linalg.norm(vec2)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Obtiene embeddings de una lista de textos usando Cohere
        """
        try:
            response = self.co.embed(
                texts=texts,
                model="embed-multilingual-v3.0",  # Soporta español
                input_type="search_document"
            )
            return response.embeddings
        except Exception as e:
            raise Exception(f"Error obteniendo embeddings: {str(e)}")
    
    async def find_best_match(
        self, 
        invoice_item: str, 
        purchase_order_items: List[Dict]
    ) -> Tuple[Dict, float]:
        """
        Encuentra el mejor match de un producto de factura en la orden de compra
        
        Args:
            invoice_item: Nombre del producto en la factura
            purchase_order_items: Lista de items de la orden de compra
                Formato: [{"producto": "...", "cantidad": ..., "precio": ...}, ...]
        
        Returns:
            Tuple con (mejor_match, similitud)
        """
        try:
            # Preparar textos para embeddings
            invoice_text = [invoice_item]
            po_texts = [item["producto"] for item in purchase_order_items]
            
            # Obtener embeddings
            all_texts = invoice_text + po_texts
            embeddings = await self.get_embeddings(all_texts)
            
            # Primer embedding es del item de factura
            invoice_embedding = embeddings[0]
            po_embeddings = embeddings[1:]
            
            # Calcular similitudes
            similarities = []
            for i, po_embedding in enumerate(po_embeddings):
                similarity = self.cosine_similarity(invoice_embedding, po_embedding)
                similarities.append({
                    "item": purchase_order_items[i],
                    "similarity": similarity
                })
            
            # Ordenar por similitud descendente
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            
            # Mejor match
            best_match = similarities[0]
            
            return best_match["item"], best_match["similarity"]
            
        except Exception as e:
            raise Exception(f"Error en matching: {str(e)}")
    
    async def match_all_items(
        self,
        invoice_items: List[Dict],
        purchase_order_items: List[Dict]
    ) -> List[Dict]:
        """
        Matchea todos los items de una factura con la orden de compra
        
        Returns:
            Lista de matches con formato:
            [{
                "invoice_item": {...},
                "matched_item": {...} o None,
                "similarity": 0.0-1.0,
                "status": "MATCHED/UNMATCHED/LOW_CONFIDENCE"
            }]
        """
        results = []
        
        for invoice_item in invoice_items:
            try:
                best_match, similarity = await self.find_best_match(
                    invoice_item["producto"],
                    purchase_order_items
                )
                
                # Determinar status
                if similarity >= self.threshold:
                    status = "MATCHED"
                elif similarity >= 0.70:
                    status = "LOW_CONFIDENCE"
                else:
                    status = "UNMATCHED"
                
                results.append({
                    "invoice_item": invoice_item,
                    "matched_item": best_match if status != "UNMATCHED" else None,
                    "similarity": round(similarity, 3),
                    "status": status
                })
                
            except Exception as e:
                results.append({
                    "invoice_item": invoice_item,
                    "matched_item": None,
                    "similarity": 0.0,
                    "status": "ERROR",
                    "error": str(e)
                })
        
        return results

# Singleton
matching_service = MatchingService()