import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import "../index.css";

export default function Chatbot() {

  const [message, setMessage] = useState("");
  const [chat, setChat] = useState([
    { sender: "bot", text: "Hello, how can I help you?" }
  ]);
  const [conversationId, setConversationId] = useState(null);

  const bottomRef = useRef(null);
  const navigate = useNavigate();

  const user_id = localStorage.getItem("user_id");
  const name = localStorage.getItem("name");

  // Auto scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat]);

  const sendMessage = async () => {

    if (!message.trim()) return;

    const userMessage = message;

    const newChat = [
      ...chat,
      { sender: "user", text: userMessage }
    ];

    setChat(newChat);
    setMessage("");

    try {

      const res = await axios.post(
        "http://127.0.0.1:5000/chat",
        {
          message: userMessage,
          conversation_id: conversationId,
          user_id: user_id
        }
      );

      setConversationId(res.data.conversation_id);

      setChat([
        ...newChat,
        { sender: "bot", text: res.data.response }
      ]);

    } catch {

      setChat([
        ...newChat,
        { sender: "bot", text: "Server error." }
      ]);

    }

  };

  // Start new chat
  const newChat = () => {
    setChat([{ sender: "bot", text: "Hello, how can I help you?" }]);
    setConversationId(null);
  };

  // Logout
  const logout = () => {
    localStorage.clear();
    navigate("/login");
  };

  return (
    <div className="chat-container">

      <div className="chat-box">

        {/* HEADER */}
        <div className="chat-header">

          <div>
            Healthcare AI Chatbot
            <span className="user-tag">
              Welcome {name}
            </span>
          </div>

          <div className="header-buttons">

            <button
              className="reset-btn"
              onClick={newChat}
            >
              New Chat
            </button>

            <button
              className="logout-btn"
              onClick={logout}
            >
              Logout
            </button>

          </div>

        </div>

        {/* MESSAGES */}
        <div className="messages-container">

          {chat.map((msg, index) => (
            <div
              key={index}
              className={
                msg.sender === "user"
                  ? "message user-message"
                  : "message bot-message"
              }
            >
              {msg.text}
            </div>
          ))}

          <div ref={bottomRef}></div>

        </div>

        {/* INPUT */}
        <div className="input-container">

          <input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                sendMessage();
              }
            }}
            placeholder="Describe your symptoms..."
          />

          <button
            className="send-btn"
            onClick={sendMessage}
            disabled={!message.trim()}
          >
            Send
          </button>

        </div>

      </div>

    </div>
  );
}