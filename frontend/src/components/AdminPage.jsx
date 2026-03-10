import React, { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import "../index.css";

export default function AdminPage() {

  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    const name = localStorage.getItem("name");

    // Guard: only admin can access this page
    if (!name || name.toLowerCase() !== "admin") {
      navigate("/login");
      return;
    }

    axios.get("http://127.0.0.1:5000/admin/users")
      .then(res => {
        setUsers(res.data.users);
      })
      .catch(() => {
        setError("Failed to load users. Please try again.");
      });

  }, [navigate]);

  return (

    <div className="admin-container">

      <div className="admin-card">

        <h2 className="admin-title">Registered Users</h2>

        {error && (
          <p style={{ color: "red", textAlign: "center" }}>{error}</p>
        )}

        <table className="admin-table">

          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Email</th>
              <th>Age</th>
              <th>Gender</th>
            </tr>
          </thead>

          <tbody>

            {users.map((u) => (

              <tr key={u.id}>
                <td>{u.id}</td>
                <td>{u.name}</td>
                <td>{u.email}</td>
                <td>{u.age}</td>
                <td>{u.gender}</td>
              </tr>

            ))}

          </tbody>

        </table>

      </div>

    </div>

  );
}