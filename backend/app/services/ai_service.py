import os
from dotenv import load_dotenv
import json
import re
from google import genai
from google.genai import types

load_dotenv()

class SmartAIService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("⚠️ FALTA GEMINI_API_KEY")
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)

    def _clean_json_string(self, json_str: str) -> str:
        if "```" in json_str:
            json_str = re.sub(r"```json\s*", "", json_str)
            json_str = re.sub(r"```\s*", "", json_str)
        return json_str.strip()

    async def extract_invoice_data(self, image_data: bytes) -> dict:
        """
        Extrae datos estructurados de una factura física.
        """
        if not self.client:
            return {"success": False, "error": "API Key no configurada"}

        prompt = """
        Eres un sistema OCR contable experto. Analiza esta factura y extrae TODOS los datos.
        
        REGLAS CRÍTICAS:
        1. Números: Convierte formatos locales a flotantes: "1.200,00" → 1200.00
        2. Limpia símbolos: "$50.000=" → 50000
        3. Proveedor: Busca el nombre comercial principal (generalmente arriba en grande)
        4. Items: Extrae CADA producto de la factura, incluso si hay 20 líneas
        
        RESPONDE SOLO ESTE JSON (sin markdown):
        {
          "proveedor": "Nombre Empresa Proveedora",
          "fecha": "YYYY-MM-DD",
          "numero_factura": "String",
          "items": [
            { 
              "producto": "Descripción exacta tal como aparece", 
              "cantidad": 0.0, 
              "precio_unitario": 0.0,
              "total": 0.0
            }
          ],
          "total_factura": 0.0
        }
        """

        try:
            image_part = types.Part.from_bytes(data=image_data, mime_type="image/jpeg")
            
            # ✅ CAMBIO CLAVE: Usamos 'gemini-2.5-flash'
            # Tu captura muestra que tienes este modelo disponible y con el contador en 0.
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt, image_part],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            
            clean_json = self._clean_json_string(response.text)
            data = json.loads(clean_json)
            
            return {"success": True, "invoice_data": data}

        except Exception as e:
            print(f"❌ Error OCR: {e}")
            return {"success": False, "error": str(e)}

    async def inspect_product_quality(self, image_data: bytes, product_type: str) -> dict:
        """
        Inspección visual de calidad del producto.
        """
        if not self.client:
            return {"success": False, "error": "API Key no configurada"}

        quality_prompts = {
            "frutas": """
            Inspecciona esta fruta y evalúa:
            - Frescura (¿está podrida, magullada, con moho?)
            - Color (¿es uniforme o tiene manchas?)
            - Madurez (¿demasiado verde o pasada?)
            
            Responde SOLO:
            {"aprobado": true/false, "razon": "explicación corta", "puntuacion": 0-10}
            """,
            "carnes": """
            Inspecciona esta carne y evalúa:
            - Color (¿rojo brillante o gris/marrón?)
            - Textura visual (¿seca, viscosa?)
            - Empaque (¿sellado, roto, con líquidos?)
            
            Responde SOLO:
            {"aprobado": true/false, "razon": "explicación corta", "puntuacion": 0-10}
            """,
            "lacteos": """
            Inspecciona este producto lácteo:
            - Empaque (¿intacto, abombado, roto?)
            - Fecha visible de vencimiento
            - Aspecto general
            
            Responde SOLO:
            {"aprobado": true/false, "razon": "explicación corta", "puntuacion": 0-10}
            """,
            "abarrotes": """
            Inspecciona este producto:
            - Empaque (¿sellado correctamente?)
            - Etiquetas legibles
            - Daños visibles
            
            Responde SOLO:
            {"aprobado": true/false, "razon": "explicación corta", "puntuacion": 0-10}
            """
        }

        prompt = quality_prompts.get(product_type, quality_prompts["abarrotes"])

        try:
            image_part = types.Part.from_bytes(data=image_data, mime_type="image/jpeg")
            
            # ✅ CAMBIO CLAVE: Aquí también usamos 'gemini-2.5-flash'
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt, image_part],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2
                )
            )
            
            clean_json = self._clean_json_string(response.text)
            quality_data = json.loads(clean_json)
            
            return {"success": True, "quality": quality_data}

        except Exception as e:
            print(f"❌ Error inspección visual: {e}")
            return {"success": False, "error": str(e)}

ai_service = SmartAIService()