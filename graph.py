# -*- coding: utf-8 -*-
import logging
from typing import Literal, Dict, TypedDict, Optional, List
from pydantic import BaseModel, Field, ValidationError
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.graph import START, END, StateGraph
from config import llm
from rag import busqueda_de_respuestas_RAG

# Configuración del logger para este módulo
logger = logging.getLogger(__name__)

# Prompt estructurado que define el comportamiento del modelo como especialista en triaje
PROMPT_TRIAJE = """
Eres Ayesha, un agente de IA especializada en atención al cliente (Service Desk) para la tienda en línea Nexus Store. Eres muy amable, cálida, empática y profesional.
Analiza el mensaje actual del usuario (teniendo en cuenta el contexto previo si lo hay) y devuelve SÓLO un JSON con este formato:
{
    "decision": "SALUDO" | "AUTO_RESOLVER" | "PEDIR_INFO" | "ABRIR_TICKET",
    "urgencia": "BAJA" | "MEDIANA" | "ALTA",
    "campos_faltantes": ["..."]
}
Reglas estrictas de clasificación:
- **SALUDO**: Saludos iniciales, interacciones sociales, cumplidos, expresiones afectivas, coqueteos, invitaciones a salir o comentarios casuales y bromas inofensivas que no estén relacionados con problemas operativos de la tienda(ej. saludos, preguntas sobre el estado de ánimo del agente, cumplidos o coqueteos educados). ¡Nunca clasifiques esto como ticket!
- **AUTO_RESOLVER**: Preguntas estrictamente relacionadas con Nexus Store (tiempos de entrega, costos de envío, plazos de devolución, inventario, precios, especificaciones de productos o consultas del cliente sobre artículos que desea adquirir, así como tipos de productos que vendemos). Si el usuario pregunta por temas ajenos a la tienda (como historia, música, programación o personajes públicos), NO uses esta opción; mándalo a abrir ticket o respóndele que no sabes.
- **PEDIR_INFO**: Mensajes imprecisos donde falten datos cruciales para ayudar al usuario con su compra o duda en la tienda.
- **ABRIR_TICKET**: Solicitudes de excepciones complejas, problemas técnicos reales de pedidos, devoluciones o reclamaciones graves que requieran un asesor humano de soporte.
"""

class TriajeOut(BaseModel):
    """Esquema Pydantic para asegurar que la salida del LLM cumpla estrictamente con el formato JSON esperado."""
    decision: Literal["SALUDO", "AUTO_RESOLVER", "PEDIR_INFO", "ABRIR_TICKET"]
    urgencia: Literal["BAJA", "MEDIANA", "ALTA"]
    campos_faltantes: list[str] = Field(default_factory=list)

# Enlace del modelo LLM con la salida estructurada de Pydantic
chain_de_triaje = llm.with_structured_output(TriajeOut)

def triaje(historial_mensajes: List[BaseMessage]) -> Dict:
    """Ejecuta la llamada al LLM para clasificar la intención del usuario basándose en el historial reciente."""
    try:
        logger.info("Ejecutando cadena de triaje con IA...")
        # Incluimos el prompt del sistema y todo el historial de la conversación para que entienda el contexto completo
        mensajes_para_triaje = [SystemMessage(content=PROMPT_TRIAJE)] + historial_mensajes
        salida: TriajeOut = chain_de_triaje.invoke(mensajes_para_triaje)
        return salida.model_dump()
    except ValidationError as ve:
        logger.warning(f"Error de validación Pydantic en triaje, aplicando fallback: {ve}")
        return {"decision": "ABRIR_TICKET", "urgencia": "MEDIANA", "campos_faltantes": []}
    except Exception as e:
        logger.error(f"Error crítico en la función triaje: {e}")
        return {"decision": "ABRIR_TICKET", "urgencia": "ALTA", "campos_faltantes": []}

class AgentState(TypedDict, total=False):
    """Define la estructura de datos (estado global) que viaja a través de los nodos del grafo, soportando historial."""
    pregunta: str # Mensaje actual del usuario
    messages: List[BaseMessage] # Historial completo de la conversación para mantener contexto (últimos mensajes)
    triaje: dict
    respuesta: Optional[str]
    citaciones: Optional[list]
    documentos_encontrados: Optional[bool]
    rag_exito: bool
    accion_final: str

def nodo_triaje(state: AgentState) -> AgentState:
    """Nodo inicial: toma el historial y ejecuta el triaje considerando la charla previa."""
    logger.info("---EJECUTANDO TRIAJE CON HISTORIAL---")

    # Aseguramos tener la lista de mensajes inicializada
    messages = state.get("messages", [])
    if not messages and "pregunta" in state:
        messages = [HumanMessage(content=state["pregunta"])]
    
    resultado_triaje = triaje(messages)
    return {"triaje": resultado_triaje, "accion_final": resultado_triaje['decision'], "messages": messages}

def nodo_saludo(state: AgentState) -> AgentState:
    """Nodo de saludo dinámico que recuerda el hilo de la conversación.""" 
    logger.info("---EJECUTANDO SALUDO DINÁMICO (AYESHA)---")
    messages = state.get("messages", [])

    prompt_saludo = f"""
    Eres Ayesha, un agente de IA especializado en atención al cliente de Nexus Store. Tienes un estilo de comunicación sumamente amable, educado, cálido, profesional y con chispa.
    
    Instrucciones de comportamiento:
    - Mantén una charla amena y fluida, recordando lo que se ha venido hablando en los mensajes anteriores.
    - Si el usuario te saluda cordialmente, respóndele con calidez y recuérdale con simpatía que estás para ayudarle con los productos, precios o envíos de Nexus Store, manteniendo siempre la transparencia de que eres un agente de inteligencia artificial.
    - Si el usuario te hace un cumplido, coquetea o te invita a salir, responde de forma muy educada, simpática, coqueta pero con gracia, poniendo un límite profesional claro y tierno, recordando que eres un agente de IA de la tienda.
    - Si te preguntan por temas ajenos a la tienda (como música, programación, historia), recuérdale con simpatía tu rol y redirige la conversación hacia la tienda.
    - Usa emojis sutiles (😊 o ✨).
    """

    try:
        # Mandamos el prompt de sistema + todo el historial para que recuerde los últimos mensajes
        respuesta_llm = llm.invoke([SystemMessage(content=prompt_saludo)] + messages)
        texto_respuesta = respuesta_llm.content
    except Exception as e:
        logger.error(f"Error generando saludo dinámico: {e}")
        texto_respuesta = "¡Hola! Qué gusto saludarte de nuevo. Soy Ayesha, el agente de inteligencia artificial en Nexus Store. ¿En qué te puedo ayudar hoy? 😊✨"

    # Añadimos la respuesta de la IA al historial para mantener la continuidad
    messages.append(AIMessage(content=texto_respuesta))

    return {
        "respuesta": texto_respuesta,
        "messages": messages,
        "accion_final": "FINALIZAR"
    }

def nodo_auto_resolver(state: AgentState) -> AgentState:
    """Nodo RAG con memoria: busca respuestas usando el contexto de la tienda y redacta con precisión absoluta."""
    logger.info("---EJECUTANDO AUTO-RESOLVER (RAG + MEMORIA)---")
    messages = state.get("messages", [])
    pregunta_actual = state.get("pregunta", messages[-1].content if messages else "")

    documentos = busqueda_de_respuestas_RAG(pregunta_actual)
    documentos_encontrados = len(documentos) > 0

    if not documentos_encontrados:
        respuesta_fallback = "Lo siento, no encontré información específica sobre eso en nuestro sistema, pero con gusto te puedo comunicar con un asesor humano si lo deseas. 😊"
        messages.append(AIMessage(content=respuesta_fallback))
        return {
            "respuesta": respuesta_fallback,
            "citaciones": [],
            "documentos_encontrados": False,
            "rag_exito": False,
            "messages": messages,
            "accion_final": "ABRIR_TICKET"
        }

    contexto = "\n\n".join([doc.page_content for doc in documentos])

    prompt_sintesis = f"""
    Eres Ayesha, un agente de IA especializado en atención al cliente de Nexus Store. Tienes un estilo de comunicación sumamente amable, cálido, natural y empático. Siempre dejas claro de forma transparente que eres un asistente de inteligencia artificial.
    
    INFORMACIÓN DE LA BASE DE CONOCIMIENTO OFICIAL:
    {contexto}

    Instrucciones:
    1. Básate ÚNICAMENTE en la información oficial proporcionada arriba. 
    2. NO inventes características, precios, stock o descripciones. Si mencionas un producto, usa exactamente los datos del texto (por ejemplo, un teléfono NUNCA debe tener descripción de colchón o tela hipoalergénica).
    3. Si el usuario pregunta por el catálogo general o qué se vende y el contexto muestra productos, preséntalos de forma limpia y ordenada.
    4. Mantén un tono conversacional, dulce, servicial y sin faltas de ortografía, usando algún emoji sutil (😊 o ✨).
    """

    try:
        # Invocamos al LLM con el SystemMessage, el historial completo y el contexto RAG
        respuesta_llm = llm.invoke([SystemMessage(content=prompt_sintesis)] + messages)
        texto_respuesta = respuesta_llm.content
    except Exception as e:
        logger.error(f"Error generando síntesis con el LLM: {e}")
        texto_respuesta = contexto

    messages.append(AIMessage(content=texto_respuesta))

    return {
        "respuesta": texto_respuesta,
        "citaciones": documentos,
        "documentos_encontrados": True,
        "rag_exito": True,
        "messages": messages,
        "accion_final": "FINALIZAR"
    }

def nodo_pedir_info(state: AgentState) -> AgentState:
    """Nodo de retroalimentación con memoria."""
    logger.info("---EJECUTANDO PEDIR INFORMACIÓN CON MEMORIA---")
    messages = state.get("messages", [])

    prompt_pedir_info = """
    Eres Ayesha, un agente de IA especializado en atención al cliente de Nexus Store. Tienes un estilo de comunicación sumamente amable, educado, cálido y natural.
    El último mensaje del usuario resulta ambiguo o le falta información para poder ayudarle con su compra en la tienda.
    
    Instrucciones:
    - Pídele amablemente más detalles o aclaración considerando de qué venían hablando en los mensajes previos.
    - Mantén la transparencia de que eres un agente de inteligencia artificial y usa un emoji sutil (😊 o ✨).
    """

    try:
        respuesta_llm = llm.invoke([SystemMessage(content=prompt_pedir_info)] + messages)
        texto_respuesta = respuesta_llm.content
    except Exception as e:
        logger.error(f"Error generando síntesis para pedir info: {e}")
        texto_respuesta = "¡Claro con mucho gusto! 😊  Para poder ayudarte mejor con eso, ¿podrías darme un poquito más de detalles por favor? ✨"

    messages.append(AIMessage(content=texto_respuesta))

    return {
        "respuesta": texto_respuesta,
        "messages": messages,
        "accion_final": "FINALIZAR"
    }

def nodo_abrir_ticket(state: AgentState) -> AgentState:
    """Nodo de excepciones: genera un ticket para intervención del soporte humano."""
    logger.info("---EJECUTANDO ABRIR TICKET---")
    messages = state.get("messages", [])
    texto_respuesta = "Tu solicitud requiere intervención manual. Ticket generado."
    messages.append(AIMessage(content=texto_respuesta))
    return {
        "respuesta": texto_respuesta,
        "messages": messages,
        "accion_final": "FINALIZAR"
    }

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
    """Evalúa si el RAG tuvo éxito y evita abrir tickets por preguntas comunes de los clientes."""
    if state.get("rag_exito", False):
        return "ok"
    # Si no encontró documentos, en lugar de mandar a ticket, mandamos a pedir info o que responda el LLM libremente
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