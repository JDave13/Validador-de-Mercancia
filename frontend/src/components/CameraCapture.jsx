import { useState, useRef } from 'react';
import Webcam from 'react-webcam';
import { Camera, Upload, X, Loader2 } from 'lucide-react';

export default function CameraCapture({ onImageCapture }) {
  const [showCamera, setShowCamera] = useState(false);
  const [capturedImage, setCapturedImage] = useState(null);
  const [uploading, setUploading] = useState(false);
  const webcamRef = useRef(null);
  const fileInputRef = useRef(null);

  // Capturar foto desde cámara
  const capturePhoto = () => {
    const imageSrc = webcamRef.current.getScreenshot();
    setCapturedImage(imageSrc);
    setShowCamera(false);
  };

  // Subir archivo desde dispositivo
  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setCapturedImage(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  // ✅ MODIFICADO: Solo prepara el archivo y lo envía al componente Padre (App.jsx)
  const sendToBackend = async () => {
    if (!capturedImage) return;

    setUploading(true);
    try {
      // 1. Convertimos la imagen (Base64) a un objeto File real
      const res = await fetch(capturedImage);
      const blob = await res.blob();
      const file = new File([blob], "invoice.jpg", { type: "image/jpeg" });
      
      // 2. Le pasamos el archivo a App.jsx para que él haga el POST a /process-invoice
      onImageCapture(file);

    } catch (error) {
      console.error('Error preparando imagen:', error);
      alert('Error al procesar la imagen.');
      setUploading(false);
    }
    // Nota: No ponemos setUploading(false) al final porque si todo sale bien,
    // App.jsx cambiará de pantalla y este componente desaparecerá.
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-6 animate-fade-in-up">
      <h2 className="text-2xl font-bold mb-6 text-gray-800 text-center">
        📸 Capturar Factura
      </h2>

      {/* Botones de acción */}
      {!capturedImage && !showCamera && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
          <button
            onClick={() => setShowCamera(true)}
            className="flex flex-col items-center justify-center gap-2 bg-blue-600 text-white px-6 py-8 rounded-xl hover:bg-blue-700 transition shadow-lg hover:shadow-xl"
          >
            <Camera size={32} />
            <span className="font-medium text-lg">Abrir Cámara</span>
          </button>

          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex flex-col items-center justify-center gap-2 bg-indigo-600 text-white px-6 py-8 rounded-xl hover:bg-indigo-700 transition shadow-lg hover:shadow-xl"
          >
            <Upload size={32} />
            <span className="font-medium text-lg">Subir Archivo</span>
          </button>
        </div>
      )}

      {/* Input oculto para subir archivos */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileUpload}
        className="hidden"
      />

      {/* Vista de cámara */}
      {showCamera && (
        <div className="relative bg-black rounded-lg overflow-hidden shadow-2xl">
          <Webcam
            ref={webcamRef}
            screenshotFormat="image/jpeg"
            className="w-full"
            videoConstraints={{
              facingMode: { ideal: "environment" }
            }}
          />
          
          <div className="absolute bottom-4 left-0 right-0 flex justify-center gap-4 px-4">
            <button
              onClick={() => setShowCamera(false)}
              className="bg-white/20 backdrop-blur-sm text-white p-4 rounded-full hover:bg-white/30"
            >
              <X size={24} />
            </button>
            <button
              onClick={capturePhoto}
              className="bg-white text-blue-600 p-4 rounded-full shadow-lg hover:scale-110 transition transform"
            >
              <Camera size={32} />
            </button>
          </div>
        </div>
      )}

      {/* Vista previa de imagen capturada */}
      {capturedImage && (
        <div className="space-y-6">
          <div className="relative group">
            <img 
              src={capturedImage} 
              alt="Factura capturada" 
              className="w-full rounded-xl shadow-lg border-2 border-white"
            />
            
            <button
              onClick={() => setCapturedImage(null)}
              className="absolute top-2 right-2 bg-red-600 text-white p-2 rounded-full hover:bg-red-700 opacity-0 group-hover:opacity-100 transition shadow-lg"
            >
              <X size={20} />
            </button>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={() => setCapturedImage(null)}
              disabled={uploading}
              className="bg-gray-100 text-gray-700 px-6 py-3 rounded-lg hover:bg-gray-200 transition font-medium border border-gray-300"
            >
              Tomar Otra
            </button>
            
            <button
              onClick={sendToBackend}
              disabled={uploading}
              className="flex items-center justify-center gap-2 bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 disabled:bg-green-400 transition font-bold shadow-md"
            >
              {uploading ? (
                <>
                  <Loader2 className="animate-spin" /> Procesando...
                </>
              ) : (
                '✅ Procesar Factura'
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}