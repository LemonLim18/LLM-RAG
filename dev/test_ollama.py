from langchain_ollama import ChatOllama

OLLAMA_URL = "http://192.168.1.8:11434"

llm = ChatOllama(
    model="qwen2.5:1.5b",
    base_url=OLLAMA_URL
)

while True:
    question = input("\nYou: ")

    if question.lower() == "exit":
        break

    response = llm.invoke(question)

    print("\nQwen:", response.content)