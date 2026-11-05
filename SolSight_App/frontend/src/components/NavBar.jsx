import React from "react";
import { useNavigate } from "react-router-dom";

export default function NavBar({ user, onLogout, right }) {
  const navigate = useNavigate();
  return (
    <div className="topbar">
      <div className="topbar-inner">
        <div
          onClick={() => navigate("/")}
          role="button"
          tabIndex={0}
          style={{ display: "inline-flex", alignItems: "center", gap: 10, cursor: "pointer" }}
        >
          <Mark />
          <span className="h-mono" style={{ fontSize: 15 }}>
            SolSight
          </span>
        </div>
        <div className="topbar-actions">
          {right}
          {user && <span className="topbar-user">{user.name}</span>}
          {onLogout && (
            <button className="btn btn-ghost" onClick={onLogout}>
              Log out
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function Mark() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
      <circle cx="11" cy="11" r="5" fill="var(--amber)" style={{ filter: "drop-shadow(0 0 5px var(--amber))" }} />
      <g stroke="var(--amber)" strokeWidth="1.6" strokeLinecap="round" opacity="0.6">
        <line x1="11" y1="1" x2="11" y2="4" />
        <line x1="11" y1="18" x2="11" y2="21" />
        <line x1="1" y1="11" x2="4" y2="11" />
        <line x1="18" y1="11" x2="21" y2="11" />
      </g>
    </svg>
  );
}
