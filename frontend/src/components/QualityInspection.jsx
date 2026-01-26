import React, { useState } from 'react';
import { Camera, CheckCircle, XCircle, AlertTriangle, Scan, Loader2, ChevronRight } from 'lucide-react';

export default function QualityInspection({ onComplete, onSkip, invoiceData, loading: externalLoading }) {
  const [capturedImage, setCapturedImage] = useState(null);
  const [productName, setProductName] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  // ✅ Extraer info de la factura
  const facturaId = invoiceData?.factura_id || 'SIN-ID';
  const proveedor = invoiceData?.proveedor || 'Desconocido';
  const items = invoiceData?.items || [];

  const handleImageCapture = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setCapturedImage(file);
      const reader = new FileReader();
      reader.onload = (e) => {
        const preview = document.getElementById('quality-preview');
        if (preview) preview.src = e.target.result;
      };
      reader.readAsDataURL(file);
    }
  };

  const analyzeQuality = async () => {
    if (!capturedImage) return;

    setAnalyzing(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('product_image', capturedImage);
      
      // ✅ Agregar metadata de factura
      if (productName.trim()) {
        formData.append('product_name', productName.trim());
      }
      formData.append('factura_id', facturaId);
      formData.append('proveedor', proveedor);

      const response = await fetch('http://localhost:8000/inspect-quality', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error en inspección');
      }

      const data = await response.json();
      setResult(data);

    } catch (err) {
      console.error('Error en inspección:', err);
      setError(err.message);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleContinue = () => {
    onComplete(result);
  };

  const isLoading = analyzing || externalLoading;

  // Vista inicial: Captura
  if (!result) {
    return (
      <div className="max-w-3xl mx-auto">
        <div className="bg-white rounded-xl shadow-lg p-8 border-2 border-blue-200">
          
          {/* Header */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-4">
              <Scan size={32} className="text-blue-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-800 mb-2">
              Inspección de Calidad Visual
            </h2>
            <p className="text-gray-600 mb-4">
              Toma una foto del producto para validar su estado físico
            </p>
            
            {/* Info de la factura */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 max-w-md mx-auto">
              <p className="text-sm text-blue-800">
                <strong>Factura:</strong> {facturaId} | <strong>Proveedor:</strong> {proveedor}
              </p>
            </div>
          </div>

          {/* Preview */}
          {capturedImage && (
            <div className="mb-6 border-2 border-dashed border-gray-300 rounded-lg overflow-hidden">
              <img 
                id="quality-preview" 
                alt="Producto capturado"
                className="w-full h-64 object-cover"
              />
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="mb-4 bg-red-50 border-l-4 border-red-500 text-red-700 p-4 rounded">
              <p className="font-bold">⚠️ Error</p>
              <p>{error}</p>
            </div>
          )}

          {/* Botones de Acción */}
          <div className="space-y-4">
            
            {/* Input Nombre del Producto */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Nombre del Producto (Opcional)
              </label>
              <input
                type="text"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                placeholder="Ej: Tomate Chonto, Cebolla Cabezona..."
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                disabled={isLoading}
              />
              <p className="text-xs text-gray-500 mt-1">
                Ayuda a identificar mejor el producto en el reporte
              </p>
            </div>

            {/* Capturar Foto */}
            <label className={`
              block w-full text-center px-6 py-4 rounded-lg cursor-pointer transition-all
              ${capturedImage 
                ? 'bg-gray-100 text-gray-600 hover:bg-gray-200' 
                : 'bg-blue-600 text-white hover:bg-blue-700'
              }
              ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}
            `}>
              <Camera className="inline mr-2" size={20} />
              {capturedImage ? 'Cambiar Foto' : 'Capturar Foto del Producto'}
              <input 
                type="file" 
                accept="image/*" 
                capture="environment"
                className="hidden"
                onChange={handleImageCapture}
                disabled={isLoading}
              />
            </label>

            {/* Analizar */}
            {capturedImage && !analyzing && (
              <button
                onClick={analyzeQuality}
                disabled={isLoading}
                className="w-full bg-green-600 text-white px-6 py-4 rounded-lg hover:bg-green-700 transition font-bold flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Scan size={20} />
                Analizar Calidad con IA
              </button>
            )}

            {/* Loading */}
            {isLoading && (
              <div className="text-center py-8">
                <Loader2 className="animate-spin text-blue-600 mx-auto mb-4" size={48} />
                <p className="text-gray-600 font-medium">
                  {analyzing ? 'Analizando calidad del producto...' : 'Procesando...'}
                </p>
                <p className="text-sm text-gray-500 mt-2">Esto puede tomar unos segundos</p>
              </div>
            )}

            {/* Saltar */}
            <button
              onClick={onSkip}
              className="w-full bg-gray-200 text-gray-700 px-6 py-3 rounded-lg hover:bg-gray-300 transition flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={isLoading}
            >
              Omitir Inspección
              <ChevronRight size={18} />
            </button>
          </div>

          {/* Info */}
          <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-800">
              <strong>💡 Recuerda:</strong> La IA detectará productos en mal estado (podridos, dañados, vencidos) 
              y alertará si encuentra problemas visuales evidentes.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Vista de Resultados
  const { quality_status, confidence, issues, recommendation, product_type } = result;
  
  const statusConfig = {
    APROBADO: {
      icon: <CheckCircle size={48} className="text-green-600" />,
      color: 'green',
      bg: 'bg-green-50',
      border: 'border-green-500',
      title: 'Producto en Buen Estado'
    },
    RECHAZADO: {
      icon: <XCircle size={48} className="text-red-600" />,
      color: 'red',
      bg: 'bg-red-50',
      border: 'border-red-500',
      title: 'Producto Rechazado'
    },
    REVISAR: {
      icon: <AlertTriangle size={48} className="text-yellow-600" />,
      color: 'yellow',
      bg: 'bg-yellow-50',
      border: 'border-yellow-500',
      title: 'Requiere Revisión Manual'
    }
  };

  const config = statusConfig[quality_status] || statusConfig.REVISAR;

  return (
    <div className="max-w-3xl mx-auto animate-fade-in-up">
      <div className={`bg-white rounded-xl shadow-lg border-2 ${config.border} overflow-hidden`}>
        
        {/* Header */}
        <div className={`${config.bg} p-6 border-b-2 ${config.border}`}>
          <div className="flex items-center gap-4">
            {config.icon}
            <div>
              <h2 className="text-2xl font-bold text-gray-800">{config.title}</h2>
              <p className="text-gray-600 mt-1">
                Confianza del análisis: <strong>{(confidence * 100).toFixed(0)}%</strong>
              </p>
              {product_type && (
                <p className="text-sm text-gray-500 mt-1">
                  Tipo identificado: {product_type}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Imagen Analizada */}
        <div className="p-6 border-b">
          <img 
            id="quality-preview" 
            alt="Producto analizado"
            className="w-full h-64 object-cover rounded-lg border-2 border-gray-200"
          />
        </div>

        {/* Problemas Detectados */}
        {issues && issues.length > 0 && (
          <div className="p-6 border-b">
            <h3 className="font-bold text-gray-800 mb-3">⚠️ Problemas Detectados:</h3>
            <ul className="space-y-2">
              {issues.map((issue, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <XCircle size={18} className="text-red-500 mt-0.5 flex-shrink-0" />
                  <span className="text-gray-700">{issue}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Recomendación */}
        <div className="p-6 bg-gray-50">
          <h3 className="font-bold text-gray-800 mb-2">💡 Recomendación:</h3>
          <p className="text-gray-700">{recommendation}</p>
        </div>

        {/* Advertencia de Rechazo */}
        {quality_status === 'RECHAZADO' && (
          <div className="p-6 bg-red-50 border-t-2 border-red-200">
            <div className="flex items-start gap-3">
              <XCircle size={24} className="text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-red-800 mb-2">
                  🚨 ADVERTENCIA: Este producto será rechazado
                </p>
                <p className="text-sm text-red-700">
                  Al continuar, la factura completa será marcada como RECHAZADA y se enviará 
                  una alerta automática por email. No se aceptará la mercancía en bodega.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Botón Continuar */}
        <div className="p-6">
          <button
            onClick={handleContinue}
            disabled={externalLoading}
            className={`w-full px-6 py-4 rounded-lg transition font-bold flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed ${
              quality_status === 'RECHAZADO'
                ? 'bg-red-600 text-white hover:bg-red-700'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {externalLoading ? (
              <>
                <Loader2 className="animate-spin" size={20} />
                Procesando...
              </>
            ) : (
              <>
                {quality_status === 'RECHAZADO' ? 'Confirmar Rechazo' : 'Continuar con Validación'}
                <ChevronRight size={20} />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}