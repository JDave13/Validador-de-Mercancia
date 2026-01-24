import { CheckCircle, AlertTriangle, XCircle, TrendingUp, Package } from 'lucide-react';

export default function ValidationResults({ validation, matchResults }) {
  if (!validation) {
    return null;
  }

  const { status, mensaje, desviacion_porcentual, totales, discrepancias, detalle_items } = validation;

  // Determinar color y emoji según status
  const statusConfig = {
    VERDE: {
      color: 'bg-green-100 border-green-500 text-green-900',
      icon: <CheckCircle className="text-green-600" size={48} />,
      emoji: '✅',
      title: 'Factura Aprobada'
    },
    AMARILLO: {
      color: 'bg-yellow-100 border-yellow-500 text-yellow-900',
      icon: <AlertTriangle className="text-yellow-600" size={48} />,
      emoji: '⚠️',
      title: 'Requiere Revisión'
    },
    ROJO: {
      color: 'bg-red-100 border-red-500 text-red-900',
      icon: <XCircle className="text-red-600" size={48} />,
      emoji: '🔴',
      title: 'Factura Rechazada'
    }
  };

  const config = statusConfig[status] || statusConfig.AMARILLO;

  return (
    <div className="w-full max-w-4xl mx-auto p-6 space-y-6">
      {/* Header con status */}
      <div className={`border-l-4 p-6 rounded-lg ${config.color}`}>
        <div className="flex items-center gap-4">
          {config.icon}
          <div>
            <h2 className="text-2xl font-bold">{config.emoji} {config.title}</h2>
            <p className="text-sm mt-1">{mensaje}</p>
          </div>
        </div>
      </div>

      {/* Métricas principales */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-lg shadow border">
          <div className="flex items-center gap-2 text-gray-600 mb-2">
            <TrendingUp size={20} />
            <span className="text-sm font-medium">Desviación</span>
          </div>
          <p className="text-3xl font-bold text-gray-900">
            {desviacion_porcentual.toFixed(2)}%
          </p>
        </div>

        <div className="bg-white p-4 rounded-lg shadow border">
          <div className="flex items-center gap-2 text-gray-600 mb-2">
            <Package size={20} />
            <span className="text-sm font-medium">Total Esperado</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">
            ${totales.esperado.toLocaleString('es-CO')}
          </p>
        </div>

        <div className="bg-white p-4 rounded-lg shadow border">
          <div className="flex items-center gap-2 text-gray-600 mb-2">
            <Package size={20} />
            <span className="text-sm font-medium">Total Facturado</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">
            ${totales.facturado.toLocaleString('es-CO')}
          </p>
        </div>
      </div>

      {/* Discrepancias */}
      {discrepancias && discrepancias.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow border">
          <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
            <AlertTriangle className="text-yellow-600" size={24} />
            Discrepancias Encontradas ({discrepancias.length})
          </h3>
          
          <div className="space-y-3">
            {discrepancias.map((disc, idx) => {
              const severityColors = {
                ALTA: 'border-red-500 bg-red-50',
                MEDIA: 'border-yellow-500 bg-yellow-50',
                BAJA: 'border-blue-500 bg-blue-50'
              };
              
              return (
                <div 
                  key={idx}
                  className={`border-l-4 p-3 rounded ${severityColors[disc.severidad] || 'border-gray-500 bg-gray-50'}`}
                >
                  <div className="flex items-start gap-2">
                    <span className="font-bold text-sm">{disc.tipo}:</span>
                    <span className="text-sm">{disc.mensaje}</span>
                  </div>
                  {disc.porcentaje && (
                    <span className="text-xs text-gray-600 ml-2">
                      ({disc.porcentaje.toFixed(1)}% de diferencia)
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Detalle de items */}
      {detalle_items && detalle_items.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow border">
          <h3 className="text-xl font-bold mb-4">Detalle de Productos</h3>
          
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-100">
                <tr>
                  <th className="p-2 text-left">Producto Factura</th>
                  <th className="p-2 text-left">Producto Pedido</th>
                  <th className="p-2 text-center">Match %</th>
                  <th className="p-2 text-center">Estado</th>
                </tr>
              </thead>
              <tbody>
                {detalle_items.map((item, idx) => (
                  <tr key={idx} className="border-b hover:bg-gray-50">
                    <td className="p-2">{item.producto_factura}</td>
                    <td className="p-2">{item.producto_pedido}</td>
                    <td className="p-2 text-center">
                      <span className={`px-2 py-1 rounded text-xs font-bold ${
                        item.similarity >= 0.9 ? 'bg-green-200 text-green-800' :
                        item.similarity >= 0.8 ? 'bg-yellow-200 text-yellow-800' :
                        'bg-red-200 text-red-800'
                      }`}>
                        {(item.similarity * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="p-2 text-center">
                      {item.validado ? (
                        <span className="text-green-600 font-bold">✓</span>
                      ) : (
                        <span className="text-red-600 font-bold">✗</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Match Results (debug) */}
      {matchResults && (
        <details className="bg-gray-50 p-4 rounded-lg border">
          <summary className="cursor-pointer font-bold text-gray-700">
            Ver resultados de matching (debug)
          </summary>
          <pre className="mt-4 text-xs overflow-auto bg-white p-4 rounded border">
            {JSON.stringify(matchResults, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}