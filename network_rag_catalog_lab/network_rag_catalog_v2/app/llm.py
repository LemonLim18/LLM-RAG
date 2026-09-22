from langchain_ollama import ChatOllama
from .config import OLLAMA_LLM_MODEL
llm=ChatOllama(model=OLLAMA_LLM_MODEL,temperature=0)
