# -*- coding: utf-8 -*-
import os
import logging
from dotenv import load_dotenv
from langchain_groq import ChatGroq

logger = logging.getLogger(__name__)
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    logger.critical("No se encontró la GROQ_API_KEY en las variables de entorno.")
    raise ValueError("No se encontró la GROQ_API_KEY en las variables de entorno.")

try:
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0
    )
    logger.info("Modelo ChatGroq inicializado correctamente en config.py.")
except Exception as e:
    logger.critical(f"Error al inicializar ChatGroq: {e}")
    raise e