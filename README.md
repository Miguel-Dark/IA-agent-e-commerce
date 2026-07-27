# Challenge Alura Agente: Service Desk & E-commerce AI

Agente de Inteligencia Artificial conversacional especializado en triaje inteligente, atención al cliente y recuperación automatizada de información (RAG) para la plataforma de comercio electrónico **Nexus Store**.

---

## 🚀 Arquitectura y Tecnologías
El proyecto está desarrollado en **Python** utilizando una arquitectura modular de backend:
* **Framework Web:** FastAPI & Uvicorn (Exposición de endpoints REST asíncronos para la interacción fluida con el frontend).
* **Orquestación del Agente:** LangGraph (Gestión de estados basada en grafos con nodos de triaje, saludos contextuales, auto-resolución y gestión de tickets).
* **Modelo de Lenguaje:** ChatGroq (`llama-3.3-70b-versatile` para procesamiento veloz y de alta precisión).
* **RAG & Procesamiento de Datos:** LangChain, FAISS (Base de datos vectorial local), HuggingFace Embeddings (`all-MiniLM-L6-v2`), PyMuPDF (Carga de guías y políticas en PDF) y Pandas (Procesamiento estructurado de FAQs y catálogo de productos en CSV).
* **Validación de Esquemas:** Pydantic (Validación estricta de entradas, salidas y clasificación estructurada del triaje).

### Flujo Operativo del Sistema
1. **Petición HTTP (`api.py`):** El cliente envía su consulta a través del endpoint `/chat`. FastAPI la procesa de forma concurrente mediante hilos.
2. **Triaje Inteligente (`graph.py`):** Un prompt estructurado con Pydantic clasifica la intención del mensaje en: `SALUDO`, `AUTO_RESOLVER`, `PEDIR_INFO` o `ABRIR_TICKET`.
3. **Recuperación Vectorial RAG (`rag.py`):** Si la consulta es del tipo `AUTO_RESOLVER`, el retriever de FAISS busca en la base de conocimiento local (políticas de reembolso, guías de envío, inventario y preguntas frecuentes).
4. **Síntesis del Agente (Ayesha):** El LLM redacta una respuesta empática, profesional y totalmente apegada a los datos oficiales de la tienda, entregando citaciones y controlando el historial de la conversación.

---

## 💡 Ejemplos de Preguntas y Respuestas del Agente

* **Pregunta (Precios y Stock):** 
  > *"¿Tienen disponible la Laptop Gamer 15.6" RTX 4090 y cuánto cuesta?"*
  * **Respuesta del Agente (Ayesha):** 
    > *"¡Hola! Sí, tenemos disponible la Laptop Gamer 15.6" RTX 4090 perteneciente a la categoría de Tecnología. Su precio en Nexus Store es de \$21,999.00 MXN y cuenta con un stock de 18 unidades listas para ti. 😊✨"*

* **Pregunta (Envíos y Costos):** 
  > *"¿Cuánto cuesta el envío si mi compra es menor a 500 pesos?"*
  * **Respuesta del Agente (Ayesha):** 
    > *"De acuerdo con nuestra guía de envíos, en compras cuyo monto sea menor o igual a \$500 MXN se aplica un costo de envío estándar único de \$99 MXN. ¡Recuerda que tus envíos son totalmente gratuitos en compras superiores a \$500 MXN! ✨"*

* **Pregunta (Políticas de Devolución):** 
  > *"¿Cuál es el plazo límite para devolver un producto si no me gustó?"*
  * **Respuesta del Agente (Ayesha):** 
    > *"Cuentas con un plazo máximo e improrrogable de 30 días naturales a partir de la fecha en que recibiste tu producto para iniciar una solicitud de devolución, siempre y cuando conserve su empaque original y sin señales de uso. 😊"*

---

## 📂 Estructura del Proyecto
* `config.py`: Módulo centralizado para la configuración de credenciales y la inicialización del LLM de Groq.
* `rag.py`: Lógica de carga de documentos de la carpeta `content/`, fragmentación y construcción del Vectorstore FAISS con su retriever.
* `graph.py`: Definición de los nodos del agente, triaje estructurado con Pydantic y las aristas condicionales de LangGraph.
* `main.py` / `api.py`: Punto de entrada principal con configuración de logging, FastAPI y ejecución del servidor.
* `requirements.txt`: Dependencias del proyecto.

---

## ⚙️ Instrucciones de Ejecución Local

Sigue estos pasos para clonar y poner en marcha el proyecto en tu entorno local:

### 1. Clonar el Repositorio
```bash
git clone https://github.com/tu-usuario/ia-agent-ecommerce.git
cd ia-agent-ecommerce
```

2. Crear y Activar un Entorno Virtual
En Windows (CMD / PowerShell):

python -m venv .venv
.venv\Scripts\activate

En Mac / Linux:

python3 -m venv .venv
source .venv/bin/activate

3. Instalar Dependencias

pip install -r requirements.txt

4. Configurar las Variables de Entorno
Crea un archivo .env en la raíz del proyecto y añade tu llave secreta de Groq:

GROQ_API_KEY=tu_clave_de_groq_aqui

5. Ejecutar el Servidor con Uvicorn

uvicorn api:app --reload --host 0.0.0.0 --port 8000

La API estará corriendo localmente en http://localhost:8000 y puedes probar la documentación interactiva en http://localhost:8000/docs.

☁️ Despliegue en la Nube (Deploy)
El agente se encuentra desplegado y accesible mediante API pública, permitiendo su integración con interfaces de chat para la atención automatizada de usuarios en la nube.

Desarrollado como parte del desafío final de la especialización de Backend e Inteligencia Artificial de Alura.