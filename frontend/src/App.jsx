import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";

import Login from "./components/Login";
import Register from "./components/Register";
import Chatbot from "./components/Chatbot";
import AdminPage from "./components/AdminPage";

import "./index.css";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/chat" element={<Chatbot />} />
        <Route path="/admin" element={<AdminPage />} />   {/* added route */}
      </Routes>
    </Router>
  );
}

export default App;