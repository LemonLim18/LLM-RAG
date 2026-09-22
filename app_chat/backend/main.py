from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import ollama

app = FastAPI()

# Allow React development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


@app.post("/api/chat")
def chat(request: ChatRequest):

    def generate():
        # stream=True means Ollama returns chunks
        stream = ollama.chat(
            model="qwen2.5:1.5b",
            messages=[
                {
                    "role": "user",
                    "content": request.message,
                }
            ],
            stream=True,
        )

        for chunk in stream:
            text = chunk["message"]["content"]

            if text:
                yield text

    return StreamingResponse(
        generate(),
        media_type="text/plain",
    )