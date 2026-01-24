import os
from typing import List, Dict, Tuple
from datetime import datetime

class ValidationService:
    def __init__(self):
        # Umbrales de desviación desde .env
        self.yellow_threshold = float(os.getenv("YELLOW_ALERT_THRESHOLD", 5))
        self.red_threshold = float(os.getenv("RED_ALERT_THRESHOLD", 10))
    
    def validate_quantity(self, factura_qty: float, pedido_qty: float) -> Dict:
        """
        Valida si la cantidad facturada coincide con la pedida
        """
        diferencia = factura_qty - pedido_qty
        porcentaje_diferencia = abs((diferencia / pedido_qty) * 100) if pedido_qty > 0 else 100
        
        if diferencia > 0:
            tipo = "SOBRECARGO"
            mensaje = f"Se facturó {diferencia} unidades más de lo pedido"
        elif diferencia < 0:
            tipo = "FALTANTE"
            mensaje = f"Faltan {abs(diferencia)} unidades"
        else:
            tipo = "OK"
            mensaje = "Cantidad correcta"
        
        return {
            "tipo": tipo,
            "diferencia": diferencia,
            "porcentaje": round(porcentaje_diferencia, 2),
            "mensaje": mensaje,
            "es_valido": tipo == "OK"
        }
    
    def validate_price(self, factura_price: float, pedido_price: float) -> Dict:
        """
        Valida si el precio unitario coincide con el pactado
        """
        diferencia = factura_price - pedido_price
        porcentaje_diferencia = abs((diferencia / pedido_price) * 100) if pedido_price > 0 else 100
        
        if diferencia > 0:
            tipo = "PRECIO_ALTO"
            mensaje = f"Precio ${diferencia:,.0f} más alto que lo pactado"
        elif diferencia < 0:
            tipo = "PRECIO_BAJO"
            mensaje = f"Precio ${abs(diferencia):,.0f} más bajo (revisar calidad)"
        else:
            tipo = "OK"
            mensaje = "Precio correcto"
        
        return {
            "tipo": tipo,
            "diferencia": diferencia,
            "porcentaje": round(porcentaje_diferencia, 2),
            "mensaje": mensaje,
            "es_valido": abs(porcentaje_diferencia) <= self.yellow_threshold
        }
    
    def validate_item(
        self, 
        invoice_item: Dict, 
        matched_item: Dict, 
        similarity: float
    ) -> Dict:
        """
        Valida un item individual de la factura contra su match en la orden
        """
        discrepancias = []
        
        # 1. Validar similitud del producto
        if similarity < 0.85:
            discrepancias.append({
                "tipo": "MATCH_BAJO",
                "severidad": "ALTA",
                "mensaje": f"Producto '{invoice_item['producto']}' no matchea claramente con '{matched_item['producto']}' (similitud: {similarity:.2%})"
            })
        
        # 2. Validar cantidad
        qty_validation = self.validate_quantity(
            invoice_item["cantidad"],
            matched_item["cantidad"]
        )
        
        if not qty_validation["es_valido"]:
            severidad = "ALTA" if qty_validation["porcentaje"] > self.red_threshold else "MEDIA"
            discrepancias.append({
                "tipo": qty_validation["tipo"],
                "severidad": severidad,
                "mensaje": qty_validation["mensaje"],
                "porcentaje": qty_validation["porcentaje"]
            })
        
        # 3. Validar precio
        price_validation = self.validate_price(
            invoice_item["precio_unitario"],
            matched_item["precio_unitario"]
        )
        
        if not price_validation["es_valido"]:
            severidad = "ALTA" if price_validation["porcentaje"] > self.red_threshold else "MEDIA"
            discrepancias.append({
                "tipo": price_validation["tipo"],
                "severidad": severidad,
                "mensaje": price_validation["mensaje"],
                "porcentaje": price_validation["porcentaje"]
            })
        
        # 4. Validar total del item
        expected_total = invoice_item["cantidad"] * invoice_item["precio_unitario"]
        actual_total = invoice_item["total"]
        
        if abs(expected_total - actual_total) > 0.01:  # Tolerancia de centavos
            discrepancias.append({
                "tipo": "ERROR_CALCULO",
                "severidad": "MEDIA",
                "mensaje": f"Total del item incorrecto: esperado ${expected_total:,.0f}, facturado ${actual_total:,.0f}"
            })
        
        return {
            "producto_factura": invoice_item["producto"],
            "producto_pedido": matched_item["producto"],
            "similarity": round(similarity, 3),
            "discrepancias": discrepancias,
            "validado": len(discrepancias) == 0
        }
    
    def calculate_global_deviation(
        self,
        invoice_total: float,
        expected_total: float
    ) -> float:
        """
        Calcula la desviación porcentual global de la factura
        """
        if expected_total == 0:
            return 100.0
        
        diferencia = invoice_total - expected_total
        porcentaje = abs((diferencia / expected_total) * 100)
        return round(porcentaje, 2)
    
    def determine_status(
        self,
        desviacion_global: float,
        discrepancias: List[Dict]
    ) -> Tuple[str, str, bool]:
        """
        Determina el status final (VERDE/AMARILLO/ROJO) y si se aprueba
        
        Returns:
            Tuple de (status, mensaje, aprobado)
        """
        # Contar discrepancias por severidad
        altas = sum(1 for d in discrepancias if d.get("severidad") == "ALTA")
        medias = sum(1 for d in discrepancias if d.get("severidad") == "MEDIA")
        
        # Lógica de semáforo
        if desviacion_global > self.red_threshold or altas > 0:
            return (
                "ROJO",
                f"Rechazado: Desviación {desviacion_global}% supera el límite ({self.red_threshold}%). {altas} discrepancias críticas.",
                False
            )
        
        elif desviacion_global > self.yellow_threshold or medias > 0:
            return (
                "AMARILLO",
                f"Requiere revisión: Desviación {desviacion_global}%. {medias} discrepancias menores.",
                False  # Requiere aprobación manual
            )
        
        else:
            return (
                "VERDE",
                f"Aprobado automáticamente: Desviación {desviacion_global}% dentro del rango aceptable.",
                True
            )
    
    def validate_invoice_complete(
        self,
        invoice_data: Dict,
        purchase_order: Dict,
        match_results: List[Dict]
    ) -> Dict:
        """
        Validación completa de una factura
        
        Args:
            invoice_data: Datos de la factura procesada
            purchase_order: Orden de compra correspondiente
            match_results: Resultados del fuzzy matching
        
        Returns:
            Resultado completo de la validación
        """
        all_discrepancias = []
        items_validados = []
        
        # 1. Validar cada item
        for match in match_results:
            if match["status"] == "MATCHED":
                item_validation = self.validate_item(
                    match["invoice_item"],
                    match["matched_item"],
                    match["similarity"]
                )
                items_validados.append(item_validation)
                all_discrepancias.extend(item_validation["discrepancias"])
            
            elif match["status"] == "UNMATCHED":
                # Producto en factura que NO está en orden de compra
                all_discrepancias.append({
                    "tipo": "PRODUCTO_NO_PEDIDO",
                    "severidad": "ALTA",
                    "mensaje": f"Producto '{match['invoice_item']['producto']}' no fue pedido",
                    "producto": match['invoice_item']['producto']
                })
        
        # 2. Verificar si hay items en la orden que NO están en la factura
        factura_productos = [m["invoice_item"]["producto"] for m in match_results]
        for po_item in purchase_order.get("items", []):
            # Buscar si este item de la orden tiene match en la factura
            encontrado = any(
                m.get("matched_item", {}).get("producto") == po_item["producto"]
                for m in match_results
                if m["status"] == "MATCHED"
            )
            
            if not encontrado:
                all_discrepancias.append({
                    "tipo": "PRODUCTO_FALTANTE",
                    "severidad": "MEDIA",
                    "mensaje": f"Producto '{po_item['producto']}' pedido pero no facturado",
                    "producto": po_item["producto"],
                    "cantidad_pedida": po_item["cantidad"]
                })
        
        # 3. Calcular totales esperados vs reales
        expected_total = sum(
            m["matched_item"]["cantidad"] * m["matched_item"]["precio_unitario"]
            for m in match_results
            if m["status"] == "MATCHED"
        )
        
        actual_total = invoice_data.get("total_factura", 0)
        
        # 4. Calcular desviación global
        desviacion_global = self.calculate_global_deviation(actual_total, expected_total)
        
        # 5. Determinar status final
        status, mensaje, aprobado = self.determine_status(desviacion_global, all_discrepancias)
        
        # 6. Compilar resultado completo
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "invoice_id": invoice_data.get("numero_factura"),
            "proveedor": invoice_data.get("proveedor"),
            "status": status,
            "aprobado": aprobado,
            "mensaje": mensaje,
            "desviacion_porcentual": desviacion_global,
            "totales": {
                "esperado": round(expected_total, 2),
                "facturado": round(actual_total, 2),
                "diferencia": round(actual_total - expected_total, 2)
            },
            "items_validados": len(items_validados),
            "items_con_errores": sum(1 for i in items_validados if not i["validado"]),
            "discrepancias": all_discrepancias,
            "detalle_items": items_validados,
            "requiere_notificacion": status in ["AMARILLO", "ROJO"]
        }

# Singleton
validation_service = ValidationService()