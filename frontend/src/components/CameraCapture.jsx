import { useState, useRef } from 'react';
import Webcam from 'react-webcam';
import { Camera, Upload, X } from 'lucide-react';

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

  // Enviar imagen al backend
  const sendToBackend = async () => {
    if (!capturedImage) return;

    setUploading(true);
    try {
      // Convertir base64 a blob
      const blob = await fetch(capturedImage).then(r => r.blob());
      
      // Crear FormData
      const formData = new FormData();
      formData.append('file', blob, 'invoice.jpg');

      // Llamar al backend
      const response = await fetch('http://localhost:8000/upload-invoice', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();
      
      if (result.success) {
        onImageCapture(result.data);
      } else {
        alert('Error procesando la imagen');
      }
    } catch (error) {
      console.error('Error:', error);
      alert('Error conectando con el servidor');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-6">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">
        📸 Capturar Factura
      </h2>

      {/* Botones de acción */}
      {!capturedImage && !showCamera && (
        <div className="grid grid-cols-2 gap-4 mb-6">
          <button
            onClick={() => setShowCamera(true)}
            className="flex items-center justify-center gap-2 bg-blue-600 text-white px-6 py-4 rounded-lg hover:bg-blue-700 transition"
          >
            <Camera size={24} />
            Abrir Cámara
          </button>

          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center justify-center gap-2 bg-green-600 text-white px-6 py-4 rounded-lg hover:bg-green-700 transition"
          >
            <Upload size={24} />
            Subir Archivo
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
        <div className="relative">
          <Webcam
            ref={webcamRef}
            screenshotFormat="image/jpeg"
            className="w-full rounded-lg"
            videoConstraints={{
              facingMode: { ideal: "environment" } // Cámara trasera en móviles
            }}
          />
          
          <div className="flex gap-4 mt-4">
            <button
              onClick={capturePhoto}
              className="flex-1 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700"
            >
              📸 Capturar
            </button>
            <button
              onClick={() => setShowCamera(false)}
              className="bg-gray-600 text-white px-6 py-3 rounded-lg hover:bg-gray-700"
            >
              <X size={20} />
            </button>
          </div>
        </div>
      )}

      {/* Vista previa de imagen capturada */}
      {capturedImage && (
        <div className="space-y-4">
          <div className="relative">
            <img 
              src={capturedImage} 
              alt="Factura capturada" 
              className="w-full rounded-lg border-2 border-gray-300"
            />
            
            <button
              onClick={() => setCapturedImage(null)}
              className="absolute top-2 right-2 bg-red-600 text-white p-2 rounded-full hover:bg-red-700"
            >
              <X size={20} />
            </button>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={() => setCapturedImage(null)}
              className="bg-gray-600 text-white px-6 py-3 rounded-lg hover:bg-gray-700"
            >
              Tomar Otra
            </button>
            
            <button
              onClick={sendToBackend}
              disabled={uploading}
              className="bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 disabled:bg-gray-400"
            >
              {uploading ? '⏳ Procesando...' : '✅ Procesar Factura'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}