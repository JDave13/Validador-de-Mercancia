import { useState } from 'react';
import CameraCapture from './components/CameraCapture';
import QualityInspection from './components/QualityInspection';
import ValidationResults from './components/ValidationResults';
import { 
  Loader2, 
  Home, 
  ArrowLeft, 
  CheckCircle, 
  AlertTriangle, 
  AlertOctagon, 
  XCircle,
  Camera
} from 'lucide-react';

function App() {
  const [step, setStep] = useState('capture');
  const [capturedInvoice, setCapturedInvoice] = useState(null);
  const [validationResult, setValidationResult] = useState(null);
  const [matchResults, setMatchResults] = useState([]);
  const [qualityResult, setQualityResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const goToStep = (newStep) => {
    setError(null);
    setStep(newStep);
  };

  const resetApp = () => {
    setStep('capture');
    setCapturedInvoice(null);
    setValidationResult(null);
    setMatchResults([]);
    setQualityResult(null);
    setError(null);
    setLoading(false);
  };

  const handleInvoiceCapture = async (imageFile) => {
    console.log("📸 Factura capturada, procesando...");
    setCapturedInvoice(imageFile);
    processInvoice(imageFile);
  };

  const processInvoice = async (imageFile) => {
    setStep('processing');
    setLoading(true);
    setError(null);

    try {
      console.log("📦 Enviando factura al backend para validación...");

      const formData = new FormData();
      formData.append('invoice', imageFile || capturedInvoice);

      const response = await fetch('http://localhost:8000/process-invoice', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error en validación');
      }

      const result = await response.json();
      console.log("📊 Resultado de validación:", result);

      if (result.success) {
        const datosSeguros = result.validation || result.invoice || result.data || result;

        setValidationResult(datosSeguros);
        setMatchResults(result.match_results || datosSeguros.items || []);

        // --- CORRECCIÓN DE FLUJO IMPLEMENTADA ---
        // Si la factura ya es ROJA (financieramente), no perdemos tiempo con calidad.
        // Saltamos directo al final para mostrar el error y evitar doble correo.
        if (datosSeguros.status === 'ROJO') {
            console.log("🛑 Factura rechazada financieramente. Saltando inspección de calidad.");
            // Seteamos un estado dummy para que la UI final no se rompa
            setQualityResult({ quality_status: 'N/A', skipped: true }); 
            setStep('final');
        } else {
            // Si es VERDE o AMARILLO, permitimos decidir si inspeccionar calidad
            setStep('results');
        }

      } else {
        throw new Error(result.mensaje || 'Error desconocido');
      }

    } catch (err) {
      console.error('❌ Error en validación:', err);
      setError(err.message);
      setStep('capture');
    } finally {
      setLoading(false);
    }
  };

  const handleStartQualityInspection = () => {
    console.log("🔍 Iniciando inspección de calidad física...");
    setStep('quality');
  };

  const handleQualityComplete = async (result) => {
    console.log("✅ Inspección de calidad completada:", result);
    setQualityResult(result);
    await finalizeValidation(result.quality_status, result);
  };

  const handleQualitySkip = async () => {
    console.log("⏭️ Inspección de calidad omitida");
    const skippedResult = { quality_status: 'OMITIDO', skipped: true };
    setQualityResult(skippedResult);
    await finalizeValidation('OMITIDO', skippedResult);
  };

  const finalizeValidation = async (qualityStatus, qualityData) => {
    setLoading(true);
    
    try {
      const formData = new FormData();
      formData.append('factura_id', validationResult.factura_id);
      formData.append('quality_status', qualityStatus);
      formData.append('quality_data', JSON.stringify(qualityData));

      const response = await fetch('http://localhost:8000/finalize-validation', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error finalizando validación');
      }

      const finalResult = await response.json();
      console.log("✅ Validación finalizada:", finalResult);

      if (finalResult.rechazo_total) {
        setValidationResult(prev => ({
          ...prev,
          status: 'ROJO',
          mensaje: finalResult.mensaje,
          rechazo_total: true
        }));
      }

      setStep('final');
      
    } catch (err) {
      console.error('❌ Error finalizando validación:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // --- Lógica Visual del Estado Final ---
  const getFinalStatusConfig = () => {
    // Prioridad 1: Rechazo Total (Físico o Financiero Crítico)
    if (validationResult?.rechazo_total || qualityResult?.quality_status === 'RECHAZADO') {
      return {
        theme: 'bg-red-50 border-red-200 text-red-900',
        iconBg: 'bg-red-100',
        icon: <XCircle size={64} className="text-red-600" />,
        title: 'Mercancía rechazada',
        desc: 'La inspección ha determinado que la mercancía no es aceptable.'
      };
    }
    
    // Prioridad 2: Validación Factura ROJA (Financiera)
    if (validationResult?.status === 'ROJO') {
      return {
        theme: 'bg-red-50 border-red-200 text-red-900',
        iconBg: 'bg-red-100',
        icon: <AlertOctagon size={64} className="text-red-600" />,
        title: 'Error Crítico en Factura',
        desc: 'Hay discrepancias graves en precios o totales respecto a la orden.'
      };
    }

    // Prioridad 3: Advertencia AMARILLA
    if (validationResult?.status === 'AMARILLO' || qualityResult?.quality_status === 'ADVERTENCIA') {
      return {
        theme: 'bg-yellow-50 border-yellow-200 text-yellow-900',
        iconBg: 'bg-yellow-100',
        icon: <AlertTriangle size={64} className="text-yellow-600" />,
        title: 'Revisión necesaria',
        desc: 'El proceso se completó, pero se detectaron desviaciones que requieren supervisión.'
      };
    }

    // Prioridad 4: Éxito VERDE
    return {
      theme: 'bg-green-50 border-green-200 text-green-900',
      iconBg: 'bg-green-100',
      icon: <CheckCircle size={64} className="text-green-600" />,
      title: 'Proceso exitoso',
      desc: 'La factura coincide y la calidad es aceptable. Mercancía recibida en sistema.'
    };
  };

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-blue-50 to-indigo-100">
      
      {/* HEADER */}
      <header className="bg-white shadow-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                📦 Validador de Mercancía
              </h1>
              <p className="text-gray-600 text-sm mt-1">
                Sistema de validación automática de facturas con ayuda de Inteligencia Artificial
              </p>
            </div>
            
            {step !== 'capture' && (
              <div className="flex gap-2">
                {step === 'results' && (
                  <button
                    onClick={() => goToStep('capture')}
                    className="flex items-center gap-2 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
                  >
                    <ArrowLeft size={18} /> <span className="hidden sm:inline">Volver</span>
                  </button>
                )}
                {step === 'quality' && (
                  <button
                    onClick={() => goToStep('results')}
                    className="flex items-center gap-2 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
                  >
                    <ArrowLeft size={18} /> <span className="hidden sm:inline">Volver</span>
                  </button>
                )}
                <button
                  onClick={resetApp}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                >
                  <Home size={18} /> <span className="hidden sm:inline">Inicio</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* MAIN CONTENT */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-8">
        
        {/* STEPPER */}
        <div className="mb-8 flex justify-center overflow-x-auto">
          <div className="flex items-center gap-2">
            {[
              { id: 'capture', label: 'Capturar', num: 1 },
              { id: 'processing', label: 'Validando', num: 2 },
              { id: 'results', label: 'Resultados', num: 3 },
              { id: 'quality', label: 'Calidad', num: 4 },
              { id: 'final', label: 'Final', num: '✓' }
            ].map((s, idx, arr) => (
              <div key={s.id} className="flex items-center gap-2">
                 <div className={`flex items-center gap-2 ${step === s.id ? 'text-blue-600 font-bold' : 'text-gray-400'}`}>
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm ${
                      step === s.id ? (s.id === 'final' ? 'bg-green-600 text-white' : 'bg-blue-600 text-white') : 'bg-gray-300 text-gray-600'
                    }`}>
                      {s.num}
                    </div>
                    <span className="hidden sm:inline text-sm">{s.label}</span>
                 </div>
                 {idx < arr.length - 1 && <div className="w-8 h-1 bg-gray-300"></div>}
              </div>
            ))}
          </div>
        </div>

        {/* ERROR MESSAGE */}
        {error && (
          <div className="mb-6 bg-red-100 border-l-4 border-red-500 text-red-700 p-4 rounded shadow-sm animate-fade-in">
            <p className="font-bold flex items-center gap-2"><AlertTriangle size={20}/> Error</p>
            <p>{error}</p>
            <button onClick={() => setError(null)} className="mt-2 text-sm underline hover:no-underline">Cerrar</button>
          </div>
        )}

        {/* --- STEP 1: CAPTURE --- */}
        {step === 'capture' && (
          <CameraCapture onImageCapture={handleInvoiceCapture} />
        )}

        {/* --- STEP 2: PROCESSING --- */}
        {step === 'processing' && (
          <div className="flex flex-col items-center justify-center py-12 animate-fade-in">
            <Loader2 className="animate-spin text-blue-600 mb-6" size={80} />
            <h2 className="text-2xl font-bold text-gray-800 mb-2">Analizando Factura...</h2>
            <p className="text-gray-600 text-center max-w-md">
              Se está leyendo la imagen con ayuda de Inteligencia Artificial y cruzando los datos con el inventario actual.
            </p>
          </div>
        )}

        {/* --- STEP 3: RESULTS & DECISION --- */}
        {step === 'results' && validationResult && (
          <div className="animate-fade-in-up">
            <ValidationResults 
              validation={validationResult} 
              matchResults={matchResults}
            />
            
            <div className="mt-8 max-w-5xl mx-auto bg-white rounded-xl shadow-lg border-2 border-blue-200 p-8">
              <div className="text-center mb-6">
                <h3 className="text-2xl font-bold text-gray-800 mb-2">¿Deseas validar la calidad física?</h3>
                <p className="text-gray-600">Puedes inspeccionar visualmente los productos con IA o marcar como recibida directamente.</p>
              </div>
              
              <div className="grid md:grid-cols-2 gap-4">
                <button
                  onClick={handleStartQualityInspection}
                  disabled={loading}
                  className="bg-blue-600 text-white px-8 py-4 rounded-lg hover:bg-blue-700 transition font-bold shadow-lg flex items-center justify-center gap-2"
                >
                  <span className="text-2xl">🔍</span> Sí, validar calidad
                </button>
                
                <button
                  onClick={handleQualitySkip}
                  disabled={loading}
                  className="bg-green-600 text-white px-8 py-4 rounded-lg hover:bg-green-700 transition font-bold shadow-lg flex items-center justify-center gap-2"
                >
                  <span className="text-2xl">✅</span> No, marcar como recibida
                </button>
              </div>
            </div>
          </div>
        )}

        {/* --- STEP 4: QUALITY --- */}
        {step === 'quality' && validationResult && (
          <QualityInspection 
            onComplete={handleQualityComplete}
            onSkip={handleQualitySkip}
            invoiceData={validationResult}
            loading={loading}
          />
        )}

        {/* --- STEP 5: FINAL SUMMARY --- */}
        {step === 'final' && validationResult && (
          <div className="animate-fade-in-up space-y-6">
            
            {/* 1. Componente de Resultados (Tabla siempre visible) */}
            <ValidationResults 
              validation={validationResult} 
              matchResults={matchResults}
            />
            
            {/* 2. Tarjeta de Estado Final Dinámica */}
            {(() => {
              const config = getFinalStatusConfig();
              return (
                <div className={`max-w-5xl mx-auto rounded-xl shadow-lg border-2 p-8 text-center transition-all ${config.theme}`}>
                  
                  <div className={`inline-flex p-4 rounded-full mb-4 shadow-sm ${config.iconBg}`}>
                    {config.icon}
                  </div>
                  
                  <h2 className="text-3xl font-bold mb-2">{config.title}</h2>
                  <p className="opacity-80 mb-8 max-w-2xl mx-auto text-lg">{config.desc}</p>
                  
                  {/* Grid de Resumen de Estados */}
                  <div className="grid grid-cols-2 gap-4 max-w-md mx-auto mb-8">
                    <div className="bg-white/60 rounded-lg p-3 backdrop-blur-sm border border-black/5">
                      <p className="text-xs uppercase font-bold opacity-60">Validación Factura</p>
                      <p className={`font-bold text-lg ${
                        validationResult.status === 'VERDE' ? 'text-green-700' :
                        validationResult.status === 'AMARILLO' ? 'text-yellow-700' : 'text-red-700'
                      }`}>
                        {validationResult.status}
                      </p>
                    </div>
                    <div className="bg-white/60 rounded-lg p-3 backdrop-blur-sm border border-black/5">
                      <p className="text-xs uppercase font-bold opacity-60">Control Calidad</p>
                      <p className={`font-bold text-lg ${
                          qualityResult?.quality_status === 'APROBADO' ? 'text-green-700' :
                          qualityResult?.quality_status === 'RECHAZADO' ? 'text-red-700' : 
                          (qualityResult?.skipped || qualityResult?.quality_status === 'N/A') ? 'text-gray-600' : 'text-yellow-700'
                      }`}>
                        {qualityResult?.skipped || qualityResult?.quality_status === 'N/A' ? 'OMITIDO' : qualityResult?.quality_status}
                      </p>
                    </div>
                  </div>

                  {/* Mensaje de Acción si hay rechazo */}
                  {(validationResult.rechazo_total || validationResult.status === 'ROJO') && (
                    <div className="bg-white p-4 rounded-lg text-left shadow-sm border border-red-100 max-w-2xl mx-auto">
                      <p className="font-bold text-red-800 flex items-center gap-2">
                        <AlertOctagon size={18}/> Acción requerida:
                      </p>
                      <ul className="mt-2 text-sm text-red-700 list-disc list-inside space-y-1">
                        <li>No ingresar la mercancía al inventario.</li>
                        <li>Contactar al proveedor para gestionar la devolución o nota crédito.</li>
                        <li>Se ha generado un reporte de incidencia automático.</li>
                      </ul>
                    </div>
                  )}

                  <div className="flex justify-center mt-8">
                    <button
                      onClick={resetApp}
                      className="bg-blue-600 text-white px-8 py-3 rounded-lg hover:bg-blue-700 transition font-bold shadow-lg hover:shadow-xl transform hover:-translate-y-1 flex items-center gap-2"
                    >
                      <Camera size={20} /> Validar Nueva Factura
                    </button>
                  </div>
                </div>
              );
            })()}

          </div>
        )}

      </main>

      <footer className="bg-white border-t mt-auto">
        <div className="max-w-7xl mx-auto px-4 py-6 text-center text-gray-500 text-sm">
          <p>Validador de Mercancía v1.0 | Powered by Gemini 2.5 Flash</p>
          <p>Participante: Juan David Cortés Amador</p>
        </div>
      </footer>
    </div>
  );
}

export default App;