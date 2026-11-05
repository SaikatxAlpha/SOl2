import React, { useEffect } from "react";

export default function Modal({ title, eyebrow, onClose, children }) {
  useEffect(() => {
    function onKey(e) {
      if (e.key === "Escape") onClose?.();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="modal-overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose?.()}>
      <div className="modal" role="dialog" aria-modal="true">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 18 }}>
          <div>
            {eyebrow && <div className="eyebrow">{eyebrow}</div>}
            <div className="h-display" style={{ fontSize: 22, marginTop: 6 }}>
              {title}
            </div>
          </div>
          <button type="button" className="btn btn-ghost" onClick={onClose} aria-label="Close" style={{ padding: "6px 10px" }}>
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
