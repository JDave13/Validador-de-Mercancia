import { useState } from 'react';
import CameraCapture from './components/CameraCapture';
import ValidationResults from './components/ValidationResults';
import { Loader2 } from 'lucide-react';

function App() {
  const [step, setStep] = useState('capture'); // capture | processing | results
  const [invoiceData, setInvoiceData] = useState(null);
  const [validationResult, setValidationResult] = useState(null);
  const [matchResults, setMatchResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Callback cuando se captura la imagen y se procesa OCR
  const handleImageCapture = async (ocrResult) => {
    setInvoiceData(ocrResult);
    setStep('processing');
    setLoading(true);
    setError(null);

    try {
      // Llamar al endpoint de validación
      const response = await fetch('http://localhost:8000/validate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          invoice_data: ocrResult
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error en validación');
      }

      const result = await response.json();

      if (result.success) {
        setValidationResult(result.validation);
        setMatchResults(result.match_results);
        setStep('results');
      } else {
        throw new Error('Validación falló');
      }
    } catch (err) {
      console.error('Error:', err);
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
    setMatchResults(null);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
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
        {/* Indicador de pasos */}
        <div className="mb-8 flex justify-center">
          <div className="flex items-center gap-4">
            <div className={`flex items-center gap-2 ${step === 'capture' ? 'text-blue-600 font-bold' : 'text-gray-400'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step === 'capture' ? 'bg-blue-600 text-white' : 'bg-gray-300'}`}>
                1
              </div>
              <span>Capturar</span>
            </div>
            
            <div className="w-12 h-1 bg-gray-300"></div>
            
            <div className={`flex items-center gap-2 ${step === 'processing' ? 'text-blue-600 font-bold' : 'text-gray-400'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step === 'processing' ? 'bg-blue-600 text-white' : 'bg-gray-300'}`}>
                2
              </div>
              <span>Validando</span>
            </div>
            
            <div className="w-12 h-1 bg-gray-300"></div>
            
            <div className={`flex items-center gap-2 ${step === 'results' ? 'text-blue-600 font-bold' : 'text-gray-400'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step === 'results' ? 'bg-blue-600 text-white' : 'bg-gray-300'}`}>
                3
              </div>
              <span>Resultados</span>
            </div>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 bg-red-100 border-l-4 border-red-500 text-red-700 p-4 rounded">
            <p className="font-bold">Error</p>
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
            <Loader2 className="animate-spin text-blue-600 mb-4" size={64} />
            <h2 className="text-2xl font-bold text-gray-800 mb-2">
              Validando factura...
            </h2>
            <p className="text-gray-600">
              Esto puede tomar unos segundos
            </p>
            
            {invoiceData && (
              <div className="mt-8 bg-white p-6 rounded-lg shadow max-w-md">
                <h3 className="font-bold mb-2">Datos extraídos:</h3>
                <div className="text-sm space-y-1">
                  <p><span className="font-medium">Proveedor:</span> {invoiceData.proveedor}</p>
                  <p><span className="font-medium">Fecha:</span> {invoiceData.fecha}</p>
                  <p><span className="font-medium">Total:</span> ${invoiceData.total_factura?.toLocaleString('es-CO')}</p>
                  <p><span className="font-medium">Items:</span> {invoiceData.items?.length}</p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Step: Results */}
        {step === 'results' && (
          <div>
            <ValidationResults 
              validation={validationResult} 
              matchResults={matchResults}
            />
            
            <div className="flex justify-center mt-8">
              <button
                onClick={handleNewInvoice}
                className="bg-blue-600 text-white px-8 py-3 rounded-lg hover:bg-blue-700 transition font-medium"
              >
                📸 Validar Nueva Factura
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-12">
        <div className="max-w-7xl mx-auto px-4 py-6 text-center text-gray-600 text-sm">
          <p>Validador de Mercancía v1.0 | Powered by Gemini AI & FastAPI</p>
        </div>
      </footer>
    </div>
  );
}

export default App;