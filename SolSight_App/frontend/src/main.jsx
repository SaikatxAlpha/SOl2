import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "../styles/global.css";

import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import PanelDetail from "./pages/PanelDetail.jsx";
import { getToken } from "../api/client.js";

function Protected({ children }) {
  return getToken() ? children : <Navigate to="/login" replace />;
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <Protected>
              <Dashboard />
            </Protected>
          }
        />
        <Route
          path="/panels/:panelId"
          element={
            <Protected>
              <PanelDetail />
            </Protected>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
