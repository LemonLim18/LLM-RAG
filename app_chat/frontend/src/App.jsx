import { useState } from "react";

function App() {
  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!message.trim()) return;

    setAnswer("");
    setLoading(true);

    try {
      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: message,
        }),
      });

      if (!response.ok) {
        throw new Error("Request failed");
      }

      // Get the streaming response body
      const reader = response.body.getReader();

      // Decode binary chunks into text
      const decoder = new TextDecoder();

      while (true) {
        const { value, done } = await reader.read();

        if (done) {
          break;
        }

        // Convert chunk to text
        const chunk = decoder.decode(value, {
          stream: true,
        });

        // Immediately append the chunk
        setAnswer((previous) => previous + chunk);
      }
    } catch (error) {
      console.error(error);
      setAnswer("Error communicating with backend.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "40px", maxWidth: "800px", margin: "auto" }}>
      <h1>Ollama Streaming Demo</h1>

      <textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Ask something..."
        rows={5}
        style={{
          width: "100%",
          padding: "10px",
          fontSize: "16px",
        }}
      />

      <button
        onClick={sendMessage}
        disabled={loading}
        style={{
          marginTop: "10px",
          padding: "10px 20px",
        }}
      >
        {loading ? "Generating..." : "Send"}
      </button>

      <div
        style={{
          marginTop: "30px",
          padding: "20px",
          background: "#f5f5f5",
          whiteSpace: "pre-wrap",
          minHeight: "100px",
        }}
      >
        {answer}
        {loading && <span>▌</span>}
      </div>
    </div>
  );
}

export default App;