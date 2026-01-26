# Prueba Técnica Country Club Ejecutivos

**Participante:** Juan David Cortés Amador

---

# 📦 Validador de Mercancía con IA

Sistema de auditoría automatizada diseñado para resolver el problema de la **recepción de pedidos "a ojo"**. Esta solución valida Facturas vs. Inventario/Orden de Compra en segundos, utilizando Inteligencia Artificial para OCR, emparejamiento difuso (Fuzzy Matching) e inspección visual de calidad física.

## 🚩 El Problema 

Recibir pedidos sin una validación estricta desangra el presupuesto. Facturas con precios inflados, cantidades incompletas o productos en mal estado entran a la bodega porque el proceso manual es lento y propenso al error humano.

## 🎯 La Misión

Un "auditor implacable" digital que valida **Factura vs. Pedido vs. Realidad** en tiempo real.

### Flujo de la Solución

1. **Digitalización (OCR Avanzado):** Transforma la foto de la factura en datos estructurados (limpieza de precios, cantidades y descripciones).
2. **Motor de Coincidencia (Fuzzy Logic):** El gran reto resuelto. Compara la factura contra la base de datos entendiendo que *"Tomate Larga Vida"* es igual a *"Tomate Chonto"*, usando algoritmos de similitud de texto y vectores.
3. **Validación Financiera (Semáforo):**

   * 🟢 **VERDE (<5%):** Aprobación automática.
   * 🟡 **AMARILLO (5-10%):** Alerta de revisión necesaria.
   * 🔴 **ROJO (>10%):** Rechazo crítico y bloqueo de entrada.
4. **Inspector Visual (Quality Check):** Análisis de la imagen del producto real para detectar calidad (madurez, estado del empaque) antes de aceptar el ingreso.

---

## 🛠️ Stack Tecnológico

La arquitectura fue seleccionada priorizando la velocidad de respuesta y la precisión en datos no estructurados.

### Backend (Python + FastAPI)

* **FastAPI:** Framework moderno y asíncrono de alto rendimiento.
* **Google Gemini (via `google-genai`):** Motor de IA multimodal seleccionado por su capacidad superior de contexto y visión a bajo costo.
* **Groq (Opcional):** Implementado para inferencia de texto ultra-rápida (LPU).
* **NumPy + TheFuzz:** Implementación híbrida matemática para el algoritmo de matching.
* **MongoDB:** Base de datos NoSQL para almacenar estructuras de facturas variables.
* **SMTP Service:** Sistema de notificaciones por correo para alertas críticas.

### Frontend (React + Vite)

* **React + Vite:** Para una experiencia de usuario (UX) fluida y cargas instantáneas.
* **TailwindCSS:** Diseño responsivo pensado para tablets y dispositivos móviles en bodega.
* **Camera API:** Integración nativa para captura de evidencias.

---

## 📂 Estructura del Proyecto

```text
/
├── backend/
│   ├── app/
│   │   ├── database/        # Conexión y modelos de MongoDB
│   │   ├── services/        # Lógica de Negocio
│   │   │   ├── ai_service.py       # OCR y extracción de datos
│   │   │   ├── matching_service.py # Algoritmo de comparación (Core Logic)
│   │   │   ├── quality_service.py  # Inspección visual de productos
│   │   │   └── email_service.py    # Notificaciones de alertas
│   │   └── main.py          # Endpoints API y orquestación
│   ├── temp_uploads/        # Caché temporal de imágenes (Auto-limpieza)
│   ├── .env                 # Variables de entorno (NO SUBIR A GIT)
│   └── requirements.txt     # Dependencias del sistema
│
└── frontend/
    ├── src/
    │   ├── components/      # Módulos: CameraCapture, ValidationResults, QualityInspection
    │   └── App.jsx          # Flujo principal de la aplicación
    └── vite.config.js       # Configuración del bundler
```

### 🧠 Decisiones de Diseño

**Algoritmo de Matching Híbrido**

Los sistemas tradicionales fallan con abreviaciones. Implementé una lógica que primero limpia el ruido (unidades, marcas irrelevantes) y luego aplica un score de similitud. Si la confianza es alta, se asocia automáticamente; si es baja, se alerta.

**Gestión de "Basura Digital"**

El sistema maneja archivos temporales para el procesamiento de imágenes, pero incluye una rutina de limpieza (`os.remove`) post-validación en `main.py` para mantener el servidor ligero y evitar costos de almacenamiento innecesarios.

**Normalización de Precios**

Se creó un parser robusto con Expresiones Regulares (Regex) para interpretar formatos de moneda colombiana complejos (ej: `$ 50.000`, `50.000,00`, `50000`), evitando errores matemáticos en la auditoría y asegurando la integridad de los datos financieros.

---

## ⚡ Guía de Instalación y Ejecución

Sigue estos pasos para desplegar el entorno de desarrollo localmente.

### 1. Configuración del Backend

```bash
# 1. Navegar a la carpeta backend
cd backend

# 2. Crear entorno virtual
python -m venv venv

# 3. Activar entorno
# En Windows:
.\venv\Scripts\activate
# En Mac/Linux:
source venv/bin/activate

# 4. Instalar dependencias
pip install -r requirements.txt
```

### 2. Configurar Variables de Entorno (.env)

Crea un archivo llamado `.env` dentro de la carpeta `/backend` con el siguiente contenido:

```text
# --- IA y Procesamiento (Gratuitas) ---
# Groq (Recomendado para velocidad de texto)
GROQ_API_KEY=gsk_tu_clave_de_groq_aqui

# Gemini (Requerido para visión y backup)
GEMINI_API_KEY=AIza_tu_clave_de_google_aqui

# Embeddings (Opcional - Cohere)
COHERE_API_KEY=tu_clave_cohere

# --- Base de Datos ---
MONGODB_URI=mongodb+srv://usuario:password@cluster.mongodb.net
MONGODB_DB_NAME=validador_mercancia

# --- Notificaciones (Gmail SMTP) ---
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_correo@gmail.com
# Generar contraseña de aplicación en: https://myaccount.google.com/apppasswords
SMTP_PASSWORD=tu_contraseña_de_aplicacion_aqui

# --- Destinatarios de Alertas ---
JEFE_COMPRAS_EMAIL=jefe@empresa.com
SUPERVISOR_EMAIL=supervisor@empresa.com

# --- Configuración de Negocio ---
SIMILARITY_THRESHOLD=0.85
YELLOW_ALERT_THRESHOLD=5
RED_ALERT_THRESHOLD=10
```

```bash
# 6. Iniciar Servidor
uvicorn app.main:app --reload
```

El backend estará disponible en: `http://localhost:8000`

### 2. Configuración del Frontend

```bash
# 1. Navegar a la carpeta frontend (en una nueva terminal)
cd frontend

# 2. Instalar dependencias
npm install

# 3. Iniciar aplicación
npm run dev
```

El frontend estará disponible en: `http://localhost:5173`

---

## 🔮 Mejoras Para el Proyecto

* Integración WhatsApp API: Para enviar las alertas rojas directamente al celular del Jefe de Compras y agilizar la toma de decisiones.
* Histórico de Proveedores: Dashboard para calificar proveedores según su tasa de error en facturas y optimizar la cadena de suministro.
* Login y Roles: Diferenciar entre vista de Operario (limitada a carga) y vista de Auditor (acceso a configuración y reportes).

---

Hecho por **Juan David Cortés Amador** para la Prueba Técnica Country Club Ejecutivos.
