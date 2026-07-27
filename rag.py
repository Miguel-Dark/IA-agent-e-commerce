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
    cargando PDFs con chunking y manteniendo los CSVs completos por fila.
    """
    docs_pdf = []
    docs_csv = []
    carpeta = Path(data_dir)

    # Verificación defensiva: si el directorio no existe, lo crea automáticamente
    if not carpeta.exists():
        logger.warning(f"La carpeta de documentos '{data_dir}' no existe. Se intentará crear.")
        carpeta.mkdir(parents=True, exist_ok=True)

    # Carga masiva de archivos PDF usando PyMuPDF
    for n in carpeta.glob("*.pdf"):
        try:
            loader = PyMuPDFLoader(str(n))
            docs_pdf.extend(loader.load())
            logger.info(f"PDF cargado con éxito: {n.name}")
        except Exception as e:
            logger.error(f"Error cargando PDF {n.name}: {e}")

    # Dividimos únicamente los PDFs
    splitter_pdf = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    docs_pdf_splits = splitter_pdf.split_documents(docs_pdf)

    # Carga y estructuración de archivos CSV como texto plano con metadatos
    for n in carpeta.glob("*.csv"):
        try:
            df = pd.read_csv(str(n), encoding="utf-8")
            # Limpieza defensiva para borrar columnas vacías tipo "Unnamed"
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

            logger.info(f"Procesando CSV: {n.name} con columnas: {list(df.columns)}")

            for index, row in df.iterrows():
                cols_map = {str(c).strip().lower(): c for c in df.columns}

                pregunta_key = next((cols_map[c] for c in cols_map if 'pregunta' in c or 'question' in c), None)
                respuesta_key = next((cols_map[c] for c in cols_map if 'respuesta' in c or 'answer' in c), None)

                if pregunta_key and respuesta_key:
                    contenido_doc = f"Información sobre {row[pregunta_key]} en Nexus Store: {row[respuesta_key]}"
                else:
                    # Formato optimizado para que el RAG entienda perfectamente cada producto de tu tienda
                    prod_id = row.get('id_producto', 'N/A')
                    nombre = row.get('nombre', 'Producto')
                    cat = row.get('categoria', 'General')
                    precio = row.get(' precio_mxn ' if ' precio_mxn ' in row else 'precio_mxn', 'Consultar')
                    stock = row.get('stock_disponible', 'Disponible')
                    desc = row.get('descripcion', '')

                    contenido_doc = f"Producto en Nexus Store: El {nombre}, perteneciente a la categoría {cat}, tiene un precio de {precio}, cuenta con un stock de {stock} unidades y su descripción es: {desc} (ID: {prod_id})." 
                doc_csv = Document(
                    page_content=contenido_doc,
                    metadata={"file_path": str(n)}
                )
                docs_csv.append(doc_csv)
            logger.info(f"CSV cargado con éxito: {n.name} ({len(df)} filas procesadas)")
        except Exception as e:
            logger.error(f"Error procesando el CSV {n.name}: {e}")

    # Unimos los splits de PDFs con los CSVs, aplicando un splitter suave a los CSVs también para que el retriever los encuentre fácil
    splitter_csv = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs_csv_splits = splitter_csv.split_documents(docs_csv)
    docs_totales = docs_pdf_splits + docs_csv_splits

    # Fallback por si la carpeta está completamente vacía
    if not docs_totales:
        logger.warning("No se encontraron documentos en la carpeta content. Agregando documento por defecto.")
        docs_totales = [Document(page_content="Información no disponible en la base de conocimiento.")]

    return docs_totales

# Bloque principal de construcción del RAG con manejo de excepciones críticas
try:
    docs_splits = cargar_documentos()
    # Instanciación del modelo de HuggingFace para la vectorización
    modelo_embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    # Construcción de la base de datos vectorial local con FAISS
    vectorstore = FAISS.from_documents(docs_splits, modelo_embeddings)
    # Configuración del retriever en modo similitud recuperando los 4 mejores chunks
    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 8})
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