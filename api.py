# -*- coding: utf-8 -*-
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from graph import construir_grafo

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

# Configuración de CORS (permite que cualquier frontend web se conecte, ideal para desarrollo y despliegue inicial)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compilación única del grafo al arrancar el servidor (optimización de rendimiento)
logger.info("Compilando grafo de LangGraph para la API...")
grafo_app = construir_grafo()
logger.info("¡Grafo listo para recibir peticiones HTTP!")

# Esquemas Pydantic para validación estricta de Entradas y Salidas JSON
class ConsultaRequest(BaseModel):
    pregunta: str = Field(..., min_length=1, description="Pregunta enviada por el cliente en el chat.")

class ConsultaResponse(BaseModel):
    respuesta: str
    accion_final: str
    citaciones_count: int

@app.get("/")
def read_root():
    """Endpoint de salud para verificar que el backend está vivo."""
    return {"status": "online", "mensaje": "¡Bienvenido al backend de Ayesha Service Desk! 🚀"}

@app.post("/chat", response_model=ConsultaResponse)
def chatear_con_ayesha(request: ConsultaRequest):
    """
    Endpoint principal de chat: recibe el JSON del frontend, invoca el grafo de LangGraph
    y devuelve la respuesta generada por Ayesha en formato JSON.
    """
    try:
        logger.info(f"Petición recibida en /chat -> Pregunta: '{request.pregunta}'")
        
        # Invocación del grafo compilado
        resultado = grafo_app.invoke({"pregunta": request.pregunta})
        
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
        raise HTTPException(status_code=500, error=str(e), detail="Error interno procesando la consulta con el agente.")