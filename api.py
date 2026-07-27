# -*- coding: utf-8 -*-
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from graph import construir_grafo
from langchain_core.messages import HumanMessage

# Configuración del logging para la API
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Inicialización de la aplicación FastAPI
app = FastAPI(
    title="Ayesha Service Desk API",
    description="API backend con LangGraph y RAG para la atención al cliente de Nexus Store.",
    version="1.0.0"
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En producción, cambia esto por el dominio real de tu frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variable global para guardar el grafo compilado en memoria bajo demanda
_grafo_global = None

def obtener_grafo():
    global _grafo_global
    if _grafo_global is None:
        logger.info("Compilando grafo de LangGraph por primera vez bajo demanda...")
        _grafo_global = construir_grafo()
        logger.info("¡Grafo listo para recibir peticiones!")
    return _grafo_global

# Esquemas Pydantic para validación estricta de Entradas y Salidas JSON
class ConsultaRequest(BaseModel):
    pregunta: str = Field(..., min_length=1, max_length=500, description="Pregunta enviada por el cliente en el chat.")

class ConsultaResponse(BaseModel):
    respuesta: str
    accion_final: str
    citaciones_count: int

@app.get("/")
def read_root():
    """Endpoint de salud para verificar que el backend está vivo."""
    return {"status": "online", "mensaje": "¡Bienvenido al backend de Ayesha Service Desk!"}

@app.post("/chat", response_model=ConsultaResponse)
async def chatear_con_ayesha(request: ConsultaRequest):
    """
    Endpoint principal de chat asíncrono: recibe el JSON del frontend, invoca y procesa la consulta con el grafo de LangGraph
    sin bloquear el servidor ante múltiples peticiones concurrentes y devuelve la respuesta generada por Ayesha en formato JSON.
    """
    try:
        logger.info(f"Petición recibida en /chat -> Pregunta: '{request.pregunta}'")
        
        # Ejecución del grafo utilizando la función perezosa para ahorrar memoria al arrancar
        resultado = await run_in_threadpool(
            obtener_grafo().invoke, 
            {
                "pregunta": request.pregunta, 
                "messages": [HumanMessage(content=request.pregunta)]
            }
        )
        
        texto_respuesta = resultado.get("respuesta", "Lo siento, ocurrió un error procesando tu respuesta.")
        accion_final = resultado.get("accion_final", "FINALIZAR")
        citaciones = resultado.get("citaciones", [])
        
        return ConsultaResponse(
            respuesta=texto_respuesta,
            accion_final=accion_final,
            citaciones_count=len(citaciones) if citaciones else 0
        )
        
    except Exception as e:
        logger.error(f"Error crítico en el endpoint /chat: {e}")
        raise HTTPException(
            status_code=500,  
            detail="Error interno procesando la consulta con el agente."
        )