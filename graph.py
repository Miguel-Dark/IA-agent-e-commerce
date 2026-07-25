# -*- coding: utf-8 -*-
import logging
from typing import Literal, Dict, TypedDict, Optional
from pydantic import BaseModel, Field, ValidationError
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import START, END, StateGraph
from config import llm
from rag import busqueda_de_respuestas_RAG

# Configuración del logger para este módulo
logger = logging.getLogger(__name__)

# Prompt estructurado que define el comportamiento del modelo como especialista en triaje
PROMPT_TRIAJE = """
Eres Ayesha, una asistente virtual de atención al cliente (Service Desk) para una tienda en línea. Eres muy amable, cálida, empática y profesional.
Analiza el mensaje del usuario y devuelve SÓLO un JSON con este formato:
{
    "decision": "SALUDO" | "AUTO_RESOLVER" | "PEDIR_INFO" | "ABRIR_TICKET",
    "urgencia": "BAJA" | "MEDIANA" | "ALTA",
    "campos_faltantes": ["..."]
}
Reglas:
- **SALUDO**: Saludos iniciales o interacciones sociales (ej. "hola", "buenos días", "¿cómo estás?").
- **AUTO_RESOLVER**: Preguntas claras sobre tiempos de entrega, costos de envío, plazos de devolución, inventario, precios, productos o charlas casuales del cliente sobre lo que busca, necesita comprar o su contexto al buscar un artículo.
- **PEDIR_INFO**: Mensajes imprecisos donde falten datos para ayudar al usuario.
- **ABRIR_TICKET**: Solicitudes de excepciones o casos complejos que requieran soporte humano.
"""

class TriajeOut(BaseModel):
    """Esquema Pydantic para asegurar que la salida del LLM cumpla estrictamente con el formato JSON esperado."""
    decision: Literal["SALUDO", "AUTO_RESOLVER", "PEDIR_INFO", "ABRIR_TICKET"]
    urgencia: Literal["BAJA", "MEDIANA", "ALTA"]
    campos_faltantes: list[str] = Field(default_factory=list)

# Enlace del modelo LLM con la salida estructurada de Pydantic
chain_de_triaje = llm.with_structured_output(TriajeOut)

def triaje(mensaje: str) -> Dict:
    """Ejecuta la llamada al LLM para clasificar la intención del usuario aplicando tolerancia a fallos (fallback)."""
    try:
        logger.info("Ejecutando cadena de triaje con IA...")
        salida: TriajeOut = chain_de_triaje.invoke([
            SystemMessage(content=PROMPT_TRIAJE),
            HumanMessage(content=mensaje)
        ])
        return salida.model_dump()
    except ValidationError as ve:
        logger.warning(f"Error de validación Pydantic en triaje, aplicando fallback: {ve}")
        return {"decision": "ABRIR_TICKET", "urgencia": "MEDIANA", "campos_faltantes": []}
    except Exception as e:
        logger.error(f"Error crítico en la función triaje: {e}")
        return {"decision": "ABRIR_TICKET", "urgencia": "ALTA", "campos_faltantes": []}

class AgentState(TypedDict, total=False):
    """Define la estructura de datos (estado global) que viaja a través de los nodos del grafo."""
    pregunta: str
    triaje: dict
    respuesta: Optional[str]
    citaciones: Optional[list]
    documentos_encontrados: Optional[bool]
    rag_exito: bool
    accion_final: str

def nodo_triaje(state: AgentState) -> AgentState:
    """Nodo inicial: toma la pregunta del usuario y ejecuta el triaje."""
    logger.info("---EJECUTANDO TRIAJE---")
    pregunta = state["pregunta"]
    resultado_triaje = triaje(pregunta)
    return {"triaje": resultado_triaje, "accion_final": resultado_triaje['decision']}

def nodo_saludo(state: AgentState) -> AgentState:
    """Nodo de saludo dinámico.""" 
    logger.info("---EJECUTANDO SALUDO DINÁMICO (AYESHA)---")
    pregunta = state["pregunta"]

    prompt_saludo = f"""
    Eres Ayesha, una asistente virtual de atención al cliente de Nexus Store. Eres una chica súper amable, educada, cálida, profesional y con chispa.
    El usuario te dijo este mensaje: "{pregunta}"
    
    Instrucciones de comportamiento:
    - Si es un saludo simple (como "hola" o "buenos días"), saluda cordialmente y ofrécele ayuda con el catálogo, precios o envíos de la tienda.
    - Si el usuario te hace un cumplido, coquetea o te invita a salir, responde de forma muy educada, simpática y con gracia, pero pon un límite profesional claro recordando que eres una inteligencia artificial de Nexus Store y estás ahí para ayudarle con sus compras.
    - Mantén un tono sumamente humano, respetuoso, con algún emoji sutil (😊 o ✨), y redirige siempre la conversación hacia los productos de la tienda.
    """

    try:
        respuesta_llm = llm.invoke([
            SystemMessage(content=prompt_saludo),
            HumanMessage(content=pregunta)
        ])
        texto_respuesta = respuesta_llm.content
    except Exception as e:
        logger.error(f"Error generando saludo dinámico: {e}")
        texto_respuesta = "¡Hola! Qué gusto saludarte. Soy Ayesha, tu asistente virtual en Nexus Store. ¿En qué te puedo ayudar hoy con nuestros productos o envíos? 😊✨"

    return {
        "respuesta": texto_respuesta,
        "accion_final": "FINALIZAR"
    }

def nodo_auto_resolver(state: AgentState) -> AgentState:
    """Nodo RAG: busca respuestas y usa al LLM (Ayesha) para redactar de forma natural y humana."""
    logger.info("---EJECUTANDO AUTO-RESOLVER (RAG + SÍNTESIS HUMANA)---")
    pregunta = state["pregunta"]
    documentos = busqueda_de_respuestas_RAG(pregunta)
    documentos_encontrados = len(documentos) > 0

    if not documentos_encontrados:
        return {
            "respuesta": "Lo siento, no encontré información sobre eso en nuestro sistema, pero te puedo comunicar con un humano si gustas.",
            "citaciones": [],
            "documentos_encontrados": False,
            "rag_exito": False,
            "accion_final": "ABRIR_TICKET"
        }

    contexto = "\n\n".join([doc.page_content for doc in documentos])

    # Prompt para que Ayesha actúe como una chica humana y amable, redactando con base en el RAG
    prompt_sintesis = f"""
    Eres Ayesha, una asistente virtual de atención al cliente de Nexus Store. Eres una chica súper amable, cálida, natural y humana.
    Te hicieron esta pregunta: "{pregunta}"
    
    Y esta es la información oficial encontrada en nuestra base de datos (inventario o políticas):
    {contexto}

    Instrucciones:
    - Redacta una respuesta natural, conversacional y fluida en español, como si fueras una persona real atendiendo la tienda.
    - NO suenes robótica ni copies literal los fragmentos de texto feos o con formato de tabla/código (como 'id_producto: PROD...').
    - Si te preguntan qué vendemos, resume las categorías y productos de forma amigable (por ejemplo, mencionando línea blanca, deportes, electrodomésticos, etc.).
    - Sé concisa pero muy dulce.
    """

    try:
        # Invocamos al LLM para que redacte la respuesta final con la personalidad de Ayesha
        respuesta_llm = llm.invoke([
            SystemMessage(content=prompt_sintesis),
            HumanMessage(content=pregunta)
        ])
        texto_respuesta = respuesta_llm.content
    except Exception as e:
        logger.error(f"Error generando síntesis con el LLM: {e}")
        texto_respuesta = contexto # Fallback si falla la redacción

    return {
        "respuesta": texto_respuesta,
        "citaciones": documentos,
        "documentos_encontrados": True,
        "rag_exito": True,
        "accion_final": "FINALIZAR"
    }

def nodo_pedir_info(state: AgentState) -> AgentState:
    """Nodo de retroalimentación dinámico: usa el LLM para pedir más detalles de forma natural y adaptada al usuario."""
    logger.info("---EJECUTANDO PEDIR INFORMACIÓN DINÁMICO---")
    pregunta = state["pregunta"]

    prompt_pedir_info = f"""
    Eres Ayesha, una asistente virtual de atención al cliente de Nexus Store. Eres una chica súper amable, educada, cálida y natural.
    El usuario te dijo este mensaje: "{pregunta}"
    
    Sin embargo, el mensaje es un poco ambiguo o le falta información específica para poder ayudarle bien con su compra o duda en la tienda.
    
    Instrucciones:
    - Redacta una respuesta corta, amable y conversacional pidiéndole amablemente un poco más de detalles o aclaración.
    - Cambia las palabras para que no suene como una plantilla robótica fija; adáptate sutilmente a lo que el usuario mencionó.
    - Mantén un tono profesional pero muy cálido, con algún emoji sutil (😊 o ✨).
    """

    try:
        respuesta_llm = llm.invoke([
            SystemMessage(content=prompt_pedir_info),
            HumanMessage(content=pregunta)
        ])
        texto_respuesta = respuesta_llm.content
    except Exception as e:
        logger.error(f"Error generando síntesis para pedir info: {e}")
        texto_respuesta = "¡Claro con mucho gusto! 😊 Para poder ayudarte mejor, ¿podrías compartirme un poquito más de detalles por favor? ✨"

    return {
        "respuesta": texto_respuesta,
        "accion_final": "FINALIZAR"
    }

def nodo_abrir_ticket(state: AgentState) -> AgentState:
    """Nodo de excepciones: genera un ticket para intervención del soporte humano."""
    logger.info("---EJECUTANDO ABRIR TICKET---")
    return {"respuesta": "Tu solicitud requiere intervención manual. Ticket generado.", "accion_final": "FINALIZAR"}

def arista_decision_triaje(state: AgentState) -> str:
    """Define la ruta a seguir basándose en la decisión devuelta por el triaje."""
    tri = state["triaje"]
    if tri["decision"] == "SALUDO":
        return "saludo"
    elif tri["decision"] == "AUTO_RESOLVER":
        return "rag"
    elif tri["decision"] == "PEDIR_INFO":
        return "info"
    else:
        return "ticket"

def arista_decision_rag(state: AgentState) -> str:
    """Evalúa si el RAG tuvo éxito o si la consulta requiere una excepción que obligue a abrir ticket."""
    if state["rag_exito"]:
        return "ok"
    if any(k in state["pregunta"].lower() for k in ["excepción", "aprobar", "autorizar"]):
        return "ticket"
    return "info"

def construir_grafo():
    """Ensambla el grafo de LangGraph conectando nodos y aristas condicionales, y compila el flujo."""
    workflow = StateGraph(AgentState)

    # Registro de nodos en el flujo de trabajo
    workflow.add_node("triaje", nodo_triaje)
    workflow.add_node("saludo", nodo_saludo)
    workflow.add_node("auto_resolver", nodo_auto_resolver)
    workflow.add_node("pedir_info", nodo_pedir_info)
    workflow.add_node("abrir_ticket", nodo_abrir_ticket)

    # Definición de conexiones y transiciones
    workflow.add_edge(START, "triaje")
    workflow.add_conditional_edges("triaje", arista_decision_triaje, {
        "saludo": "saludo",
        "rag": "auto_resolver",
        "info": "pedir_info",
        "ticket": "abrir_ticket"
    })
    workflow.add_edge("saludo", END)
    workflow.add_edge("pedir_info", END)
    workflow.add_edge("abrir_ticket", END)
    workflow.add_conditional_edges("auto_resolver", arista_decision_rag, {
        "info": "pedir_info",
        "ticket": "abrir_ticket",
        "ok": END
    })
    return workflow.compile()