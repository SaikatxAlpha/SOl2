const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const TOKEN_KEY = "solsight_token";

// ---------- DEMO MODE ----------
// VITE_DEMO_MODE=true serves canned data with no backend at all (useful for
// a UI walkthrough offline). Leave it unset to talk to the real API.
const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === "true";

const DEMO_USER = { name: "Demo Admin", email: "demo@solsight.com" };

const DEMO_PANELS = [
  {
    id: "demo-1",
    panel_id: "PNL-001",
    location: "Rooftop A",
    installation_date: "2024-01-15",
    rated_power: 400,
    latest_health_score: 92,
    latest_status: "Healthy",
  },
  {
    id: "demo-2",
    panel_id: "PNL-002",
    location: "Rooftop B",
    installation_date: "2023-11-02",
    rated_power: 380,
    latest_health_score: 61,
    latest_status: "Warning",
  },
  {
    id: "demo-3",
    panel_id: "PNL-003",
    location: "Field Array C",
    installation_date: "2022-06-20",
    rated_power: 410,
    latest_health_score: 28,
    latest_status: "Critical",
  },
];

const DEMO_HISTORY = [
  { date: "2024-05-01T00:00:00Z", health_score: 95, status: "Healthy", detected_defect: "Normal", confidence: 97.2 },
  { date: "2024-06-01T00:00:00Z", health_score: 90, status: "Healthy", detected_defect: "Normal", confidence: 95.1 },
  { date: "2024-07-01T00:00:00Z", health_score: 78, status: "Warning", detected_defect: "Soiling", confidence: 88.4 },
  { date: "2024-08-01T00:00:00Z", health_score: 65, status: "Warning", detected_defect: "Hotspot", confidence: 91.0 },
];

const DEMO_PREDICTION = {
  current_health: 65,
  status: "Warning",
  degradation_forecast: [
    { day: 30, predicted_health: 60.5 },
    { day: 60, predicted_health: 55.2 },
    { day: 90, predicted_health: 49.8 },
  ],
  recommendation:
    "Panel shows early warning signs. Monitor closely and plan a routine inspection.",
};

function delay(ms = 350) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
// ---------- END DEMO MODE DATA ----------

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request(path, { method = "GET", body, form, auth = true } = {}) {
  const headers = {};
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  let payload = body;
  if (form) {
    payload = form; // FormData sets its own content-type boundary
  } else if (body) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const res = await fetch(`${BASE_URL}${path}`, { method, headers, body: payload });

  if (res.status === 401 && auth) {
    // Token expired or the user was removed: start over at the login screen.
    clearToken();
    window.location.assign("/login");
    throw new Error("Session expired, please sign in again.");
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const err = await res.json();
      // FastAPI validation errors come back as a list of {loc, msg}
      detail = Array.isArray(err.detail) ? err.detail.map((d) => d.msg).join("; ") : err.detail || detail;
    } catch (_) {
      /* no-op */
    }
    throw new Error(detail);
  }

  if (res.status === 204) return null;
  return res.json();
}

// ---------- auth ----------
export const login = async (email, password) => {
  if (DEMO_MODE) {
    await delay();
    return { access_token: "demo-token", token_type: "bearer" };
  }
  return request("/auth/login", { method: "POST", body: { email, password }, auth: false });
};

export const register = async (name, email, password) => {
  if (DEMO_MODE) {
    await delay();
    return { access_token: "demo-token", token_type: "bearer" };
  }
  return request("/auth/register", { method: "POST", body: { name, email, password }, auth: false });
};

export const me = async () => {
  if (DEMO_MODE) {
    await delay(150);
    return DEMO_USER;
  }
  return request("/auth/me");
};

// ---------- panels ----------
export const listPanels = async () => {
  if (DEMO_MODE) {
    await delay();
    return DEMO_PANELS;
  }
  return request("/panels");
};

export const createPanel = async (panel) => {
  if (DEMO_MODE) {
    await delay();
    const newPanel = {
      id: `demo-${Date.now()}`,
      ...panel,
      latest_health_score: null,
      latest_status: null,
    };
    DEMO_PANELS.push(newPanel);
    return newPanel;
  }
  return request("/panels", { method: "POST", body: panel });
};

export const getPanel = async (panelId) => {
  if (DEMO_MODE) {
    await delay();
    return (
      DEMO_PANELS.find((p) => p.panel_id === panelId) || {
        id: "demo-unknown",
        panel_id: panelId,
        location: "Unknown",
        installation_date: "2024-01-01",
        rated_power: 400,
        latest_health_score: 80,
        latest_status: "Healthy",
      }
    );
  }
  return request(`/panels/${panelId}`);
};

export const deletePanel = async (panelId) => {
  if (DEMO_MODE) {
    await delay();
    const i = DEMO_PANELS.findIndex((p) => p.panel_id === panelId);
    if (i >= 0) DEMO_PANELS.splice(i, 1);
    return null;
  }
  return request(`/panels/${panelId}`, { method: "DELETE" });
};

export const getPanelHistory = async (panelId) => {
  if (DEMO_MODE) {
    await delay();
    return DEMO_HISTORY;
  }
  return request(`/panels/${panelId}/history`);
};

export const getPanelPrediction = async (panelId) => {
  if (DEMO_MODE) {
    await delay();
    return DEMO_PREDICTION;
  }
  return request(`/panels/${panelId}/prediction`);
};

// ---------- inspections ----------
export async function uploadInspection({ panelId, voltage, current, temperature, image }) {
  if (DEMO_MODE) {
    await delay();
    return { inspection_id: `demo-${Date.now()}`, status: "uploaded" };
  }
  const form = new FormData();
  form.append("panel_id", panelId);
  form.append("voltage", voltage);
  form.append("current", current);
  form.append("temperature", temperature);
  if (image) form.append("image", image);
  return request("/upload-inspection", { method: "POST", form });
}

export async function predictDefect({ panelId, voltage, current, temperature, image }) {
  if (DEMO_MODE) {
    await delay(700);
    const power = voltage * current;
    return {
      panel_id: panelId,
      detected_defect: "Soiling",
      confidence: 87.3,
      defect_probabilities: { Normal: 8.1, Crack: 2.4, Hotspot: 2.2, Soiling: 87.3 },
      status: "Warning",
      health_score: 71.5,
      health_probabilities: { Healthy: 22.0, Warning: 71.5, Critical: 6.5 },
      power_output: Math.round(power * 100) / 100,
      expected_power: 368.0,
      performance_ratio: 0.938,
      power_loss_pct: 6.2,
      degradation_forecast: DEMO_PREDICTION.degradation_forecast,
      recommendation: "Panel shows early warning signs. Monitor closely and plan a routine inspection.",
      analysis_mode: { defect: "rule-based", health: "rule-based", forecast: "trend" },
    };
  }
  const form = new FormData();
  form.append("panel_id", panelId);
  form.append("voltage", voltage);
  form.append("current", current);
  form.append("temperature", temperature);
  if (image) form.append("image", image);
  return request("/predict-defect", { method: "POST", form });
}
