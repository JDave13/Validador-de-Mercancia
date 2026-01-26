"""
app/services/quality_service.py
Servicio de Inspección Visual de Calidad usando Gemini 2.0 Flash (GRATIS)
Actualizado con google.genai (nueva API)
"""

import os
from google import genai
from google.genai import types
import json

class QualityService:
    def __init__(self):
        # Configurar Gemini API con nueva librería
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("❌ GEMINI_API_KEY no configurada en .env")
        
        # Crear cliente con nueva API
        self.client = genai.Client(api_key=api_key)
        
        print("✅ QualityService inicializado con Gemini API")
        
    async def inspect_product_quality(self, image_bytes: bytes) -> dict:
        """
        Analiza la calidad visual de un producto usando Gemini Vision
        
        Args:
            image_bytes: Imagen del producto en bytes
            
        Returns:
            dict con:
                - quality_status: APROBADO | RECHAZADO | REVISAR
                - confidence: 0.0 - 1.0
                - issues: Lista de problemas detectados
                - recommendation: Texto de recomendación
        """
        
        try:
            # Prompt especializado para inspección de calidad
            prompt = """
Eres un inspector de calidad experto en productos de supermercado y restaurantes.

Analiza la imagen del producto y determina su estado de calidad visual.

**CRITERIOS DE INSPECCIÓN:**

🍎 FRUTAS Y VERDURAS:
- Color uniforme y fresco (no manchas marrones/negras)
- Sin magulladuras evidentes
- Sin moho visible (puntos blancos, verdes o negros)
- Apariencia firme (no excesivamente blanda o arrugada)
- Sin podredumbre

🥩 CARNES Y PESCADOS:
- Color característico (rojo brillante para carne, rosado para pescado)
- Sin decoloración grisácea o verdosa
- Sin signos de descomposición visual
- Empaque intacto sin roturas
- Sin líquidos extraños o turbios

🥛 LÁCTEOS Y EMPAQUES:
- Empaque sin roturas, abolladuras severas o deformaciones
- Sin fugas o derrames visibles
- Sello intacto
- Sin hinchazón del envase (signo de fermentación)

📦 PRODUCTOS SECOS:
- Empaque sellado correctamente
- Sin signos de humedad
- Sin infestación visible (agujeros, polvo extraño)
- Etiquetas legibles

**RESPONDE ÚNICAMENTE CON ESTE JSON VÁLIDO (SIN TEXTO ADICIONAL):**

{"quality_status":"APROBADO","confidence":0.95,"issues":[],"product_type":"Fruta","recommendation":"Producto en excelente estado"}

**REGLAS:**
- quality_status: solo "APROBADO", "RECHAZADO" o "REVISAR"
- confidence: número entre 0 y 1
- issues: lista de strings (vacía [] si no hay problemas)
- product_type: tipo de producto identificado
- recommendation: texto breve y claro
- NO agregues markdown, NO agregues explicaciones, SOLO el JSON
- Si el producto está en mal estado usa "RECHAZADO"
"""

            # Generar análisis con nueva API
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    prompt,
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type='image/jpeg'
                    )
                ],
                config=types.GenerateContentConfig(
                    temperature=0.1,  # Muy baja para respuestas consistentes
                    max_output_tokens=1024,  # Aumentado para evitar truncamiento
                    response_mime_type="application/json"  # Forzar JSON
                )
            )
            
            # Parsear respuesta
            content = response.text.strip()
            
            # Limpiar markdown y espacios
            content = content.replace('```json', '').replace('```', '').strip()
            
            # Intentar reparar JSON incompleto
            if not content.endswith('}'):
                # Si el JSON está truncado, intentar completarlo
                print(f"⚠️ JSON truncado detectado, intentando reparar...")
                content = content.rsplit(',', 1)[0]  # Quitar última coma incompleta
                
                # Contar llaves para cerrar
                open_braces = content.count('{')
                close_braces = content.count('}')
                content += '}' * (open_braces - close_braces)
            
            # Parsear JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                print(f"⚠️ Error parseando JSON de Gemini: {e}")
                print(f"Respuesta recibida (primeros 200 chars): {content[:200]}")
                
                # Intentar extraer info básica con regex si el JSON falló
                import re
                
                fallback_result = {
                    "quality_status": "REVISAR",
                    "confidence": 0.5,
                    "issues": ["Error al analizar respuesta de IA"],
                    "product_type": "Desconocido",
                    "recommendation": "Revisar manualmente el producto por seguridad."
                }
                
                # Intentar extraer status si está visible
                status_match = re.search(r'"quality_status"\s*:\s*"(\w+)"', content)
                if status_match:
                    fallback_result["quality_status"] = status_match.group(1)
                
                # Intentar extraer confidence
                conf_match = re.search(r'"confidence"\s*:\s*([\d.]+)', content)
                if conf_match:
                    fallback_result["confidence"] = float(conf_match.group(1))
                
                result = fallback_result
            
            # Validar estructura
            required_keys = ["quality_status", "confidence", "issues", "recommendation"]
            for key in required_keys:
                if key not in result:
                    if key == "issues":
                        result[key] = []
                    elif key == "confidence":
                        result[key] = 0.5
                    else:
                        result[key] = "N/A"
            
            # Normalizar status
            status = str(result.get("quality_status", "REVISAR")).upper()
            if status not in ["APROBADO", "RECHAZADO", "REVISAR"]:
                result["quality_status"] = "REVISAR"
            else:
                result["quality_status"] = status
            
            # Asegurar que confidence es float entre 0 y 1
            try:
                conf = float(result["confidence"])
                result["confidence"] = max(0.0, min(1.0, conf))
            except:
                result["confidence"] = 0.5
            
            # Asegurar que issues es lista
            if not isinstance(result.get("issues"), list):
                result["issues"] = []
            
            print(f"✅ Inspección completada: {result['quality_status']} (confidence: {result['confidence']})")
            
            return {
                "success": True,
                **result
            }
            
        except Exception as e:
            print(f"❌ Error en inspección de calidad: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "quality_status": "REVISAR",
                "confidence": 0.0,
                "issues": [f"Error técnico: {str(e)}"],
                "product_type": "Error",
                "recommendation": "No se pudo completar la inspección automática. Revisar manualmente."
            }

# Singleton
quality_service = QualityService()