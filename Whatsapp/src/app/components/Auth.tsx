"use client";

import { useState } from "react";

type AuthProps = {
  onSelect: (userId: string) => void;
};

export default function Auth({ onSelect }: AuthProps) {
  const [selected, setSelected] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selected) onSelect(selected);
  };

  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: "#111b21",
    }}>
      <div style={{
        background: "#222e35",
        padding: "2rem",
        borderRadius: "8px",
        width: "100%",
        maxWidth: "400px",
        boxShadow: "0 4px 6px rgba(0, 0, 0, 0.3)",
      }}>
        <h2 style={{
          color: "#fff",
          textAlign: "center",
          marginBottom: "1.5rem",
          fontSize: "1.5rem",
        }}>
          Pick a User
        </h2>

        <form onSubmit={handleSubmit}>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginBottom: "1.5rem", maxHeight: "400px", overflowY: "auto" }}>
            {[
              { id: "user1", label: "User 1 (You)" },
              { id: "user2", label: "Ananya" },
              { id: "user3", label: "Arjun Mehta" },
              { id: "user4", label: "Priya Sharma" },
              { id: "user5", label: "Vikram Patel" },
              { id: "user6", label: "Neha Gupta" },
              { id: "user7", label: "Amit Kumar" },
              { id: "user8", label: "Rohan Singh" },
              { id: "user9", label: "Kavita Reddy" },
              { id: "user10", label: "Dev Team" },
              { id: "user11", label: "Sanjay Iyer" },
            ].map((u) => (
              <label
                key={u.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.75rem",
                  padding: "0.75rem 1rem",
                  borderRadius: "6px",
                  border: selected === u.id ? "2px solid #00a884" : "2px solid #3b4a54",
                  background: selected === u.id ? "#1a3a2a" : "#2a3942",
                  cursor: "pointer",
                  color: "#fff",
                  fontSize: "1rem",
                }}
              >
                <input
                  type="radio"
                  name="userId"
                  value={u.id}
                  checked={selected === u.id}
                  onChange={() => setSelected(u.id)}
                  style={{ accentColor: "#00a884" }}
                />
                {u.label}
              </label>
            ))}
          </div>

          <button
            type="submit"
            disabled={!selected}
            style={{
              width: "100%",
              padding: "0.75rem",
              borderRadius: "4px",
              border: "none",
              background: selected ? "#00a884" : "#555",
              color: "#fff",
              fontSize: "1rem",
              fontWeight: "bold",
              cursor: selected ? "pointer" : "not-allowed",
            }}
          >
            Enter Chat
          </button>
        </form>
      </div>
    </div>
  );
}
