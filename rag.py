# -*- coding: utf-8 -*-
import logging
from pathlib import Path
import pandas as pd
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# Configuración del logger para este módulo específico
logger = logging.getLogger(__name__)

# Definición de ruta absoluta para asegurar estabilidad en producción/nube
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = BASE_DIR / "content"

def cargar_documentos(data_dir: Path = DEFAULT_DATA_DIR):
    """
    Función encargada de escanear la carpeta de conocimiento usando rutas absolutas,
    cargar archivos PDF y CSV, y prepararlos como documentos de LangChain.
    """
    docs = []
    carpeta = Path(data_dir)

    # Verificación defensiva: si el directorio no existe, lo crea automáticamente
    if not carpeta.exists():
        logger.warning(f"La carpeta de documentos '{data_dir}' no existe. Se intentará crear.")
        carpeta.mkdir(parents=True, exist_ok=True)

    # Carga masiva de archivos PDF usando PyMuPDF
    for n in carpeta.glob("*.pdf"):
        try:
            loader = PyMuPDFLoader(str(n))
            docs.extend(loader.load())
            logger.info(f"PDF cargado con éxito: {n.name}")
        except Exception as e:
            logger.error(f"Error cargando PDF {n.name}: {e}")

    # Carga y estructuración de archivos CSV como texto plano con metadatos
    for n in carpeta.glob("*.csv"):
        try:
            df = pd.read_csv(str(n), encoding="utf-8")
            # Limpieza defensiva para borrar columnas vacías tipo "Unnamed"
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

            for index, row in df.iterrows():
                texto_fila = " | ".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
                doc_csv = Document(
                    page_content=f"Datos del producto de Nexus Store ({n.name}): {texto_fila}",
                    metadata={"file_path": str(n)}
                )
                docs.append(doc_csv)
            logger.info(f"CSV cargado con éxito: {n.name}")
        except Exception as e:
            logger.error(f"Error cargando CSV {n.name}: {e}")

    # Fallback por si la carpeta está completamente vacía
    if not docs:
        logger.warning("No se encontraron documentos en la carpeta content. Agregando documento por defecto.")
        docs = [Document(page_content="Información no disponible en la base de conocimiento.")]

    # División de textos en chunks optimizados para el modelo de embeddings
    splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=30)
    return splitter.split_documents(docs)

# Bloque principal de construcción del RAG con manejo de excepciones críticas
try:
    docs_splits = cargar_documentos()
    # Instanciación del modelo de HuggingFace para la vectorización
    modelo_embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    # Construcción de la base de datos vectorial local con FAISS
    vectorstore = FAISS.from_documents(docs_splits, modelo_embeddings)
    # Configuración del retriever en modo similitud recuperando los 4 mejores chunks
    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 4})
    logger.info("Vectorstore FAISS y retriever inicializados exitosamente en rag.py.")
except Exception as e:
    logger.critical(f"Error crítico al construir el RAG: {e}")
    raise e

def busqueda_de_respuestas_RAG(pregunta: str):
    """
    Ejecuta la consulta contra el retriever de FAISS utilizando la pregunta del usuario.
    """
    try:
        logger.info(f"Ejecutando retriever para la pregunta: '{pregunta}'")
        documentos_encontrados = retriever.invoke(pregunta)
        return documentos_encontrados
    except Exception as e:
        logger.error(f"Error en busqueda_de_respuestas_RAG: {e}")
        return []