import { useState } from "react";
import "./StudyAssistant.css";

function StudyAssistant() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);

  const sendQuestion = async () => {
    if (!question) return;

    const userMessage = {
      type: "user",
      text: question,
    };

    setMessages((prev) => [...prev, userMessage]);

    try {
      const response = await fetch("http://127.0.0.1:8000/ask-question", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: question,
        }),
      });

      const data = await response.json();

      const botMessage = {
        type: "bot",
        text: JSON.stringify(data),
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      console.log(error);
    }

    setQuestion("");
  };

  return (
    <div className="container">
      <h1>AI Study Assistant</h1>

      <div className="upload-box">
        <input type="file" />
      </div>

      <div className="chat-box">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={msg.type === "user" ? "user-msg" : "bot-msg"}
          >
            {msg.text}
          </div>
        ))}
      </div>

      <div className="input-box">
        <input
          type="text"
          placeholder="Ask from your PDF..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />

        <button onClick={sendQuestion}>Send</button>
      </div>
    </div>
  );
}

export default StudyAssistant;