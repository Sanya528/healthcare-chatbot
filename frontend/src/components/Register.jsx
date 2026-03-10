import React, { useState } from "react";
import axios from "axios";
import { useNavigate, Link } from "react-router-dom";
import "../index.css";

export default function Register() {

  const nav = useNavigate();

  const [user, setUser] = useState({
    name: "", email: "", password: "", age: "", gender: ""
  });
  const [msg, setMsg] = useState("");

  const submit = async () => {
    try {
      await axios.post("http://127.0.0.1:5000/register", user);
      nav("/login");
    } catch (err) {
      const detail = err.response?.data?.error;
      setMsg(detail || "Registration failed. Please try again.");
    }
  };

  return (
    <div className="center-page">
      <div className="card">

        <h2>Create Account</h2>
        <p className="subtitle">Join your personal health assistant</p>

        <div className="input-group">
          <input
            placeholder="Full Name"
            value={user.name}
            onChange={(e) => setUser({ ...user, name: e.target.value })}
          />
        </div>

        <div className="input-group">
          <input
            placeholder="Email"
            type="email"
            value={user.email}
            onChange={(e) => setUser({ ...user, email: e.target.value })}
          />
        </div>

        <div className="input-group">
          <input
            type="password"
            placeholder="Password"
            value={user.password}
            onChange={(e) => setUser({ ...user, password: e.target.value })}
          />
        </div>

        <div className="input-group">
          <input
            type="number"
            placeholder="Age"
            min="1"
            max="120"
            value={user.age}
            onChange={(e) => setUser({ ...user, age: e.target.value })}
          />
        </div>

        <div className="select-wrapper">
          <select
            value={user.gender}
            onChange={(e) => setUser({ ...user, gender: e.target.value })}
          >
            <option value="">Select Gender</option>
            <option value="male">Male</option>
            <option value="female">Female</option>
            <option value="other">Other</option>
          </select>
        </div>

        <button
          onClick={submit}
          disabled={!user.name || !user.password || !user.email || !user.age || !user.gender}
        >
          Create Account
        </button>

        {msg && <p className="error-msg">{msg}</p>}

        <hr className="card-divider" />

        <p className="switch-link">
          Already registered? <Link to="/login">Login</Link>
        </p>

      </div>
    </div>
  );
}
