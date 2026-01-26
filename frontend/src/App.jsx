import { useState } from 'react';
import CameraCapture from './components/CameraCapture';
import ValidationResults from './components/ValidationResults';
import { Loader2 } from 'lucide-react';

function App() {
  const [step, setStep] = useState('capture'); // capture | processing | results
  const [invoiceData, setInvoiceData] = useState(null);
  const [validationResult, setValidationResult] = useState(null);
  const [matchResults, setMatchResults] = useState([]); 
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // ✅ LÓGICA CORREGIDA Y BLINDADA
  const handleImageCapture = async (imageFile) => {
    // 1. Cambiamos estado visual a "Procesando"
    setStep('processing');
    setLoading(true);
    setError(null);

    try {
      console.log("📸 Enviando imagen al backend...");

      // 2. Preparamos los datos como Archivo (Multipart)
      const formData = new FormData();
      formData.append('invoice', imageFile); 

      // 3. Petición al Backend
      const response = await fetch('http://localhost:8000/process-invoice', {
        method: 'POST',
        body: formData, 
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error en validación');
      }

      const result = await response.json();
      console.log("📦 Respuesta del Backend:", result);

      if (result.success) {
        // --- AQUÍ ESTABA EL ERROR, AHORA ESTÁ ARREGLADO ---
        // Definimos 'datosSeguros' buscando la info en cualquier lugar posible
        // Si no está en 'validation', busca en 'invoice', 'data' o en la raíz.
        const datosSeguros = result.validation || result.invoice || result.data || result;

        // 4. Guardamos los datos recibidos
        setValidationResult(datosSeguros); 
        
        // Buscamos los items/match_results con seguridad
        setMatchResults(result.match_results || datosSeguros.items || []);
        
        // Guardamos datos básicos de la factura usando ?. para que no explote si falta algo
        setInvoiceData({
            proveedor: datosSeguros?.proveedor_factura || datosSeguros?.proveedor || "Proveedor Desconocido",
            total_factura: datosSeguros?.total_factura || 0
        });

        setStep('results');
      } else {
        throw new Error(result.mensaje || 'Error desconocido');
      }

    } catch (err) {
      console.error('❌ Error en el flujo:', err);
      setError(err.message);
      setStep('capture');
    } finally {
      setLoading(false);
    }
  };

  // Reset para nueva factura
  const handleNewInvoice = () => {
    setStep('capture');
    setInvoiceData(null);
    setValidationResult(null);
    setMatchResults([]);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header Original */}
      <header className="bg-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-gray-900">
            📦 Validador de Mercancía
          </h1>
          <p className="text-gray-600 mt-1">
            Sistema de validación automática de facturas
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        
        {/* Indicador de pasos Original */}
        <div className="mb-8 flex justify-center">
          <div className="flex items-center gap-4">
            {/* Paso 1: Capturar */}
            <div className={`flex items-center gap-2 ${step === 'capture' ? 'text-blue-600 font-bold' : 'text-gray-400'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step === 'capture' ? 'bg-blue-600 text-white' : 'bg-gray-300'}`}>
                1
              </div>
              <span>Capturar</span>
            </div>
            
            <div className="w-12 h-1 bg-gray-300"></div>
            
            {/* Paso 2: Validando */}
            <div className={`flex items-center gap-2 ${step === 'processing' ? 'text-blue-600 font-bold' : 'text-gray-400'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step === 'processing' ? 'bg-blue-600 text-white' : 'bg-gray-300'}`}>
                2
              </div>
              <span>Validando</span>
            </div>
            
            <div className="w-12 h-1 bg-gray-300"></div>
            
            {/* Paso 3: Resultados */}
            <div className={`flex items-center gap-2 ${step === 'results' ? 'text-blue-600 font-bold' : 'text-gray-400'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step === 'results' ? 'bg-blue-600 text-white' : 'bg-gray-300'}`}>
                3
              </div>
              <span>Resultados</span>
            </div>
          </div>
        </div>

        {/* Mensaje de Error */}
        {error && (
          <div className="mb-6 bg-red-100 border-l-4 border-red-500 text-red-700 p-4 rounded shadow-sm">
            <p className="font-bold flex items-center gap-2">⚠️ Error</p>
            <p>{error}</p>
          </div>
        )}

        {/* Step: Capture */}
        {step === 'capture' && (
          <CameraCapture onImageCapture={handleImageCapture} />
        )}

        {/* Step: Processing */}
        {step === 'processing' && (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="animate-spin text-blue-600 mb-6" size={80} />
            <h2 className="text-2xl font-bold text-gray-800 mb-2">
              Analizando Factura...
            </h2>
            <p className="text-gray-600 text-center max-w-md">
              Estamos leyendo la imagen con IA y cruzando los datos con el inventario actual.
            </p>
          </div>
        )}

        {/* Step: Results */}
        {step === 'results' && validationResult && (
          <div className="animate-fade-in-up">
            <ValidationResults 
              validation={validationResult} 
              matchResults={matchResults}
            />
            
            <div className="flex justify-center mt-10 pb-12">
              <button
                onClick={handleNewInvoice}
                className="bg-blue-600 text-white px-8 py-3 rounded-lg hover:bg-blue-700 transition font-medium shadow-lg hover:shadow-xl transform hover:-translate-y-1 flex items-center gap-2"
              >
                📸 Validar Nueva Factura
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-auto">
        <div className="max-w-7xl mx-auto px-4 py-6 text-center text-gray-500 text-sm">
          <p>Validador de Mercancía v1.0 | Powered by Gemini 2.5 Flash Lite</p>
        </div>
      </footer>
    </div>
  );
}

export default App;