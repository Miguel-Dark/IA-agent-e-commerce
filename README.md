# Challenge Alura Agente: Service Desk & E-commerce AI

Agente de Inteligencia Artificial conversacional especializado en triaje, atención al cliente y recuperación inteligente de información (RAG) para una tienda en línea.

## 🚀 Arquitectura y Tecnologías
El proyecto está desarrollado en **Python** utilizando una arquitectura modular de backend:
* **Orquestación del Agente:** LangGraph (Gestión de estados y flujos condicionales).
* **Modelo de Lenguaje:** ChatGroq (`llama-3.3-70b-versatile`).
* **RAG & Procesamiento de Datos:** LangChain, FAISS (Base de datos vectorial), HuggingFace Embeddings, PyMuPDF (Carga de PDFs) y Pandas (Carga de CSVs).
* **Validación de Esquemas:** Pydantic.

## 📂 Estructura del Proyecto
* `config.py`: Módulo centralizado para la configuración de credenciales y la inicialización del LLM de Groq.
* `rag.py`: Lógica de carga de documentos de la carpeta `content/`, fragmentación y construcción del Vectorstore FAISS con su retriever.
* `graph.py`: Definición de los nodos del agente, triaje estructurado con Pydantic y las aristas condicionales de LangGraph.
* `main.py`: Punto de entrada principal con configuración centralizada de logging, compilación del grafo y ejecución de pruebas en consola.
* `requirements.txt`: Dependencias del proyecto.

## ⚙️ Flujo del Agente
1. **Triaje:** Analiza la consulta del usuario y la clasifica automáticamente (`AUTO_RESOLVER`, `PEDIR_INFO`, `ABRIR_TICKET`) con un nivel de urgencia.
2. **Auto-resolver (RAG):** Si la consulta es clara, busca en la base de conocimiento vectorial (guías y FAQs) para dar una respuesta precisa y con citaciones.
3. **Escalamiento:** Deriva a un ticket manual o solicita más información si la pregunta requiere una excepción o datos faltantes.

---
*Desarrollado como parte de las especializaciones de backend e IA.*