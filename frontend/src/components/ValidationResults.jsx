import React from 'react';
import { CheckCircle, AlertTriangle, AlertOctagon, FileText, Package, ArrowRight } from 'lucide-react';

export default function ValidationResults({ validation, matchResults }) {
  // 1. Protección inicial por si no llegan datos aún
  if (!validation) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-gray-500 bg-gray-50 rounded-lg border-2 border-dashed border-gray-200">
        <Package size={48} className="mb-4 text-gray-400" />
        <p className="text-lg font-medium">Esperando resultados de validación...</p>
      </div>
    );
  }

  // 2. Extracción de datos
  const { 
    proveedor = 'Desconocido', 
    desviacion_porcentual = 0,
    status = 'ROJO' 
  } = validation;

  const totales = validation.totales || validation.totals || { esperado: 0, facturado: 0, diferencia: 0 };
  
  // Usamos matchResults si existe (nuestro nuevo formato híbrido), o fallback a validation.items
  const items = matchResults?.length > 0 ? matchResults : (validation.items || []);

  // 3. Mapeo de Estados (Backend -> Frontend)
  let currentStatusKey = 'ALERTA'; 

  if (status === 'VERDE') {
      currentStatusKey = 'APROBADA';
  } else if (status === 'AMARILLO') {
      currentStatusKey = 'AMARILLO';
  } else {
      currentStatusKey = 'ALERTA'; // ROJO
  }

  // 4. Configuración visual según estado
  const statusConfig = {
    APROBADA: {
      theme: 'bg-green-600 border-green-600',
      icon: <CheckCircle size={32} className="text-white" />,
      text: 'Validación Exitosa',
      subtext: 'La factura coincide con la orden de compra (< 5%)'
    },
    AMARILLO: {
      theme: 'bg-yellow-500 border-yellow-500',
      icon: <AlertTriangle size={32} className="text-white" />,
      text: 'Revisión Necesaria',
      subtext: 'Desviación moderada detectada (5% - 10%)'
    },
    ALERTA: {
      theme: 'bg-red-600 border-red-600',
      icon: <AlertOctagon size={32} className="text-white" />,
      text: 'Discrepancia Crítica',
      subtext: 'Diferencias mayores al 10% o error de lectura'
    }
  };

  const config = statusConfig[currentStatusKey];

  // 5. Helpers de formato
  const formatMoney = (val) => {
    const num = Number(val);
    return isNaN(num) ? '$0' : `$ ${num.toLocaleString('es-CO')}`;
  };

  // --- CORRECCIÓN CRÍTICA ---
  const formatPercentage = (val) => {
    const num = Number(val);
    if (isNaN(num)) return "0.00%";
    
    // Si el backend envía 0.5, mostramos 0.50%.
    // No multiplicamos por 100 aquí porque el cálculo ya viene hecho o es un ratio directo.
    // Ajusta esto si tu backend envía 0.005 para representar 0.5%.
    // Asumiendo que backend envía el numero entero/decimal listo:
    return `${num.toFixed(2)}%`;
  };

  return (
    <div className="w-full max-w-5xl mx-auto space-y-6 animate-fade-in-up">
      
      {/* HEADER PRINCIPAL DINÁMICO */}
      <div className={`rounded-xl shadow-lg overflow-hidden border-2 ${config.theme} text-white transition-all duration-300`}>
        <div className="p-6 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <div className="bg-white/20 p-3 rounded-full backdrop-blur-sm">
              {config.icon}
            </div>
            <div>
              <h2 className="text-3xl font-bold uppercase tracking-wide">{config.text}</h2>
              <p className="opacity-90 flex items-center gap-2 text-lg">
                <FileText size={18} /> {proveedor}
              </p>
              <p className="text-sm opacity-75 mt-1">{config.subtext}</p>
            </div>
          </div>
          
          <div className="text-right bg-white/20 p-4 rounded-lg backdrop-blur-sm min-w-[150px]">
            <p className="text-xs uppercase tracking-widest opacity-80 mb-1">Desviación Total</p>
            <p className="text-3xl font-bold">{formatPercentage(desviacion_porcentual)}</p>
          </div>
        </div>

        {/* Totales - Siempre visibles en blanco */}
        <div className="bg-white text-gray-800 p-6 grid grid-cols-1 md:grid-cols-3 gap-4 divide-y md:divide-y-0 md:divide-x divide-gray-100">
          <div className="text-center p-2">
            <p className="text-gray-500 text-sm mb-1 uppercase tracking-wider">Esperado (Bodega)</p>
            <p className="text-2xl font-bold text-gray-700">{formatMoney(totales.esperado)}</p>
          </div>
          <div className="text-center p-2">
            <p className="text-gray-500 text-sm mb-1 uppercase tracking-wider">Facturado Real</p>
            <p className="text-2xl font-bold text-blue-900">{formatMoney(totales.facturado)}</p>
          </div>
          <div className="text-center p-2">
            <p className="text-gray-500 text-sm mb-1 uppercase tracking-wider">Diferencia</p>
            <p className={`text-2xl font-bold ${totales.diferencia > 0 ? 'text-red-600' : 'text-green-600'}`}>
              {totales.diferencia > 0 ? '+' : ''}{formatMoney(totales.diferencia)}
            </p>
          </div>
        </div>
      </div>

      {/* TABLA DE DETALLE */}
      <div className="bg-white rounded-xl shadow-md border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
          <h3 className="font-bold text-gray-700">Análisis Línea por Línea</h3>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-gray-100 text-gray-600 border-b border-gray-200 uppercase text-xs tracking-wider">
              <tr>
                <th className="px-6 py-4 font-semibold">Producto Detectado</th>
                <th className="px-6 py-4 font-semibold text-center">Cant.</th>
                <th className="px-6 py-4 font-semibold text-right">Precio Factura</th>
                <th className="px-6 py-4 font-semibold text-right text-gray-500">Precio Bodega</th>
                <th className="px-6 py-4 font-semibold text-center">Similitud</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((item, idx) => {
                const nombre = item.product_name || item.original_name || "Item Desconocido";
                const matchDB = item.matched_name || "";
                
                const precioFactura = Number(item.unit_price || 0);
                const precioEsperado = Number(item.expected_price || 0);
                const cantidad = item.quantity || 0;
                // Manejo seguro del score de similitud
                const similarity = item.similarity ?? item.score ?? 0;
                
                // Cálculo de alerta visual por fila
                let sobreprecioPercent = 0;
                let isPriceError = false;

                if (precioEsperado > 0) {
                  if (precioFactura > precioEsperado) {
                    sobreprecioPercent = ((precioFactura - precioEsperado) / precioEsperado) * 100;
                    if (sobreprecioPercent > 5) isPriceError = true; 
                  }
                }

                const rowClass = isPriceError 
                  ? 'bg-red-50 hover:bg-red-100' 
                  : 'hover:bg-gray-50';

                return (
                  <tr key={idx} className={`transition-colors ${rowClass}`}>
                    {/* 1. PRODUCTO */}
                    <td className="px-6 py-4">
                      <div className="font-bold text-gray-800 text-base">{nombre}</div>
                      {matchDB && matchDB !== "No encontrado" && (
                        <div className="text-xs text-gray-500 mt-1 flex items-center gap-1">
                           <ArrowRight size={12} /> Encontrado como: {matchDB}
                        </div>
                      )}
                      {isPriceError && (
                          <div className="mt-2 inline-flex items-center px-2 py-1 rounded text-xs font-bold bg-red-100 text-red-700 border border-red-200 animate-pulse">
                            ⚠️ Sobreprecio +{sobreprecioPercent.toFixed(0)}%
                          </div>
                      )}
                    </td>

                    {/* 2. CANTIDAD */}
                    <td className="px-6 py-4 text-center font-mono text-gray-600">
                      {cantidad}
                    </td>

                    {/* 3. PRECIO FACTURA */}
                    <td className={`px-6 py-4 text-right font-bold text-base ${isPriceError ? 'text-red-700' : 'text-gray-900'}`}>
                      {formatMoney(precioFactura)}
                    </td>

                    {/* 4. PRECIO BODEGA */}
                    <td className="px-6 py-4 text-right font-mono text-gray-500">
                      {precioEsperado > 0 ? formatMoney(precioEsperado) : <span className="text-gray-300 italic">--</span>}
                    </td>

                    {/* 5. SIMILITUD */}
                    <td className="px-6 py-4 text-center">
                      <div className="flex flex-col items-center">
                        <span className={`px-3 py-1 rounded-full text-xs font-bold shadow-sm ${
                          similarity >= 0.8 ? 'bg-green-100 text-green-800' : 
                          similarity >= 0.6 ? 'bg-yellow-100 text-yellow-800' : 
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {/* Visualización de score (0.98 -> 98.00%) */}
                          {similarity <= 1 
                            ? (similarity * 100).toFixed(2) + "%" 
                            : similarity.toFixed(2) + "%"}
                        </span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}