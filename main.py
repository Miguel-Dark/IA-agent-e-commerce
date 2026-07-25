# -*- coding: utf-8 -*-
import logging
from graph import construir_grafo

# Configuración global del logging para toda la aplicación
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Instanciación del logger principal
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Iniciando aplicación principal...")
    
    # Compilación inicial del grafo de LangGraph
    app = construir_grafo()
    logger.info("¡Grafo compilado con éxito!")

    # Banner de presentación
    print("\n" + "="*70)
    print("🤖 AYESHA - ASISTENTE VIRTUAL DE NEXUS STORE (Powered by LangGraph)")
    print("Escribe tus dudas sobre productos, inventario, precios, envíos o políticas.")
    print("Escribe 'salir', 'exit' o 'quit' para terminar la sesión.")
    print("="*70 + "\n")

    # Batería de mensajes de prueba para evaluar el comportamiento del agente
    """ mensajes_de_prueba = [
        "¿Cuál es el costo de envío si mi compra es de 400 pesos?",
        "¿Cuánto tiempo tengo para solicitar una devolución?",
        "Quiero devolver un producto, pero ya pasaron 40 días.",
        "¿Hacen envíos internacionales?"
    ]

    # Iteración sobre cada caso de prueba para invocar el flujo del grafo
    for prueba in mensajes_de_prueba:
        print("\n" + "="*50) """

    # Bucle interactivo para la terminal
    while True:
        pregunta_usuario = input("\nTú: ")
        if pregunta_usuario.lower() in ["salir", "exit", "quit"]:
            print("¡Hasta luego! Que tengas un excelente día.")
            break
        
        if not pregunta_usuario.strip():
            continue

        print("-" * 50)
        logger.info(f"PROCESANDO: {pregunta_usuario}")
        
        # Invocación del grafo pasando el estado inicial con la pregunta
        respuesta = app.invoke({"pregunta": pregunta_usuario})
        
        # Impresión limpia de la respuesta obtenida por el agente
        print(f"RESPUESTA: {respuesta.get('respuesta', 'N/D')}")