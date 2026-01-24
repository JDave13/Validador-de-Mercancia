import google.generativeai as genai
import os
import json
import base64
from PIL import Image
import io

class GeminiService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY no configurada")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    async def extract_invoice_data(self, image_data: bytes) -> dict:
        """
        Extrae datos estructurados de una factura usando Gemini OCR
        """
        try:
            # Convertir bytes a imagen PIL
            image = Image.open(io.BytesIO(image_data))
            
            # Prompt para extracción estructurada
            prompt = """
            Analiza esta imagen de factura y extrae la información en formato JSON EXACTO.
            
            Reglas importantes:
            1. Limpia los precios: "$50.000" debe ser 50000 (número sin símbolos)
            2. Las cantidades pueden ser decimales: "2.5 kg" → 2.5
            3. Si no encuentras un campo, usa null
            4. La fecha debe estar en formato YYYY-MM-DD
            
            Responde SOLO con este JSON (sin texto adicional):
            {
                "proveedor": "nombre del proveedor",
                "fecha": "YYYY-MM-DD",
                "numero_factura": "número si existe",
                "items": [
                    {
                        "producto": "nombre del producto",
                        "cantidad": 0,
                        "unidad": "kg/unidades/etc",
                        "precio_unitario": 0,
                        "total": 0
                    }
                ],
                "subtotal": 0,
                "iva": 0,
                "total_factura": 0
            }
            """
            
            # Generar contenido
            response = self.model.generate_content([prompt, image])
            
            # Limpiar respuesta (remover markdown si existe)
            text = response.text.strip()
            if text.startswith("```json"):
                text = text.replace("```json", "").replace("```", "").strip()
            
            # Parse JSON
            invoice_data = json.loads(text)
            
            return {
                "success": True,
                "data": invoice_data
            }
            
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Error parseando JSON: {str(e)}",
                "raw_response": response.text if 'response' in locals() else None
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error en OCR: {str(e)}"
            }
    
    async def analyze_product_quality(self, image_data: bytes, product_type: str = "general") -> dict:
        """
        Analiza la calidad visual de un producto
        """
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # Prompts específicos por tipo de producto
            prompts = {
                "frutas": """
                Eres un inspector de calidad de frutas y verduras. Analiza esta imagen y evalúa:
                1. Frescura (color, textura, firmeza aparente)
                2. Daños físicos (golpes, cortes, podredumbre)
                3. Madurez adecuada para venta
                4. Signos de plagas o enfermedades
                """,
                "carnes": """
                Eres un inspector de calidad de productos cárnicos. Analiza esta imagen y evalúa:
                1. Color de la carne (indicador de frescura)
                2. Presencia de mal aspecto (decoloración, mal olor aparente)
                3. Empaque en buen estado
                4. Textura aparente
                """,
                "abarrotes": """
                Eres un inspector de calidad de productos empacados. Analiza esta imagen y evalúa:
                1. Empaque intacto (sin roturas, abombamientos)
                2. Etiquetas legibles
                3. Signos de daño durante transporte
                4. Condición general del producto
                """,
                "general": """
                Eres un inspector de calidad de productos. Analiza esta imagen y evalúa la condición general del producto.
                """
            }
            
            base_prompt = prompts.get(product_type, prompts["general"])
            
            full_prompt = f"""
            {base_prompt}
            
            Responde SOLO en formato JSON (sin texto adicional):
            {{
                "estado": "excelente/bueno/regular/malo",
                "problemas": ["lista de problemas encontrados, vacía si no hay"],
                "apto_venta": true/false,
                "confianza": 0.0-1.0,
                "observaciones": "descripción breve del análisis"
            }}
            """
            
            response = self.model.generate_content([full_prompt, image])
            
            # Limpiar y parsear
            text = response.text.strip()
            if text.startswith("```json"):
                text = text.replace("```json", "").replace("```", "").strip()
            
            quality_data = json.loads(text)
            
            return {
                "success": True,
                "data": quality_data
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error en análisis visual: {str(e)}"
            }

# Singleton
gemini_service = GeminiService()