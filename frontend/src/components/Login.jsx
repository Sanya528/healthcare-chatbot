import React, { useState } from "react";
import axios from "axios";
import { useNavigate, Link } from "react-router-dom";
import "../index.css";

export default function Login() {

  const nav = useNavigate();

  const [user, setUser] = useState({ name: "", password: "" });
  const [msg, setMsg] = useState("");

  const submit = async () => {
    try {
      const res = await axios.post("http://127.0.0.1:5000/login", user);

      localStorage.setItem("user_id", res.data.user_id);
      localStorage.setItem("name", user.name);

      if (user.name.toLowerCase() === "admin") {
        nav("/admin");
      } else {
        nav("/chat");
      }

    } catch {
      setMsg("Invalid name or password.");
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") { e.preventDefault(); submit(); }
  };

  return (
    <div className="center-page">
      <div className="card">

        <h2>Welcome Back</h2>
        <p className="subtitle">Sign in to your health assistant</p>

        <div className="input-group">
          <input
            placeholder="Username"
            value={user.name}
            onChange={(e) => setUser({ ...user, name: e.target.value })}
            onKeyDown={handleKeyDown}
          />
        </div>

        <div className="input-group">
          <input
            type="password"
            placeholder="Password"
            value={user.password}
            onChange={(e) => setUser({ ...user, password: e.target.value })}
            onKeyDown={handleKeyDown}
          />
        </div>

        <button onClick={submit} disabled={!user.name || !user.password}>
          Login
        </button>

        {msg && <p className="error-msg">{msg}</p>}

        <hr className="card-divider" />

        <p className="switch-link">
          Don't have an account? <Link to="/register">Register</Link>
        </p>

      </div>
    </div>
  );
}
