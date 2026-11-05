# SolSight

Solar panel inspection and health monitoring. Log a panel's electrical readings (and optionally a thermal or visual image), and SolSight works out whether something is wrong with it, how healthy it is, and where its health is heading over the next 90 days.

```
readings + image ──► defect detection ──► health score ──► 30/60/90-day forecast ──► recommendation
                     (CNN / rules)        (MLP / rules)    (Bi-LSTM / trend)
```

## How the analysis works

Every inspection goes through three stages. Each stage uses its neural network **only if trained weights exist in `backend/saved_models/`**; otherwise it falls back to a physics-based method. The API response says which path was used (`analysis_mode`), so an estimate is never presented as a model output.

| Stage | Model | Fallback when no trained weights |
|---|---|---|
| Defect (Normal / Crack / Hotspot / Soiling) | ResNet18-based CNN | Performance ratio + cell temperature + thermal-contrast check on the image |
| Health (Healthy / Warning / Critical, 0–100 score) | MLP on CNN features + readings | Temperature-corrected performance ratio, minus thermal and defect penalties |
| Forecast (30 / 60 / 90 days) | Bi-LSTM on health history | Least-squares trend over real inspection dates; sudden drops treated as events, not trends |

The physics side assumes readings near peak sun, a temperature coefficient of −0.40 %/°C above 25 °C, and ~0.7 %/year normal ageing. Status bands: Healthy ≥ 75, Warning 50–75, Critical < 50.

## Stack

- **Backend:** FastAPI, Motor (MongoDB), PyTorch, JWT auth with bcrypt
- **Frontend:** React 18, Vite, React Router, Recharts
- **Database:** MongoDB (Atlas or local), or an in-memory mock for demos

## Running it locally

You need Python 3.11, Node 18+, and either a MongoDB connection string or nothing at all (in-memory mode).

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env`:

```env
MONGO_URI=memory               # or mongodb+srv://user:pass@cluster/
MONGO_DB=solsight
JWT_SECRET=some-long-random-string
```

With `MONGO_URI=memory`, the API starts with a demo account (`admin@solsight.com` / `admin123`) and four sample panels with ten weeks of history. Nothing is saved between restarts.

With a real MongoDB, create the admin account once:

```bash
python seed_admin.py
```

Start the API:

```bash
uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000
- Interactive docs: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health (shows DB status and which models are trained)

### Frontend

From the **project root** (that's where `package.json` lives):

```bash
npm install
npm run dev
```

Open http://localhost:5173. To click through the UI with no backend at all, put `VITE_DEMO_MODE=true` in a root `.env`.

### Docker

Starts MongoDB and the API together:

```bash
docker compose up --build
```

Then run the frontend with `npm run dev` as above.

## API

| Method | Path | What it does |
|---|---|---|
| POST | `/auth/register` | Create an account, returns a JWT |
| POST | `/auth/login` | Log in, returns a JWT |
| GET | `/auth/me` | Current user |
| GET | `/panels` | Your panels with their latest status |
| POST | `/panels` | Add a panel |
| GET | `/panels/{id}` | One panel |
| DELETE | `/panels/{id}` | Remove a panel and its inspections |
| GET | `/panels/{id}/history` | All analyzed inspections, oldest first |
| GET | `/panels/{id}/prediction` | Latest forecast and recommendation |
| POST | `/predict-defect` | Upload readings (+ optional image), run the full analysis, save it |
| POST | `/upload-inspection` | Save raw readings without analysis |

## Training the models

The training scripts are in `backend/ml_training/`. Each one writes its best checkpoint to `backend/saved_models/`, and the API picks it up on the next restart.

```bash
cd backend/ml_training
python train_cnn.py --data-dir data --epochs 20        # data/train/<Class>/*.jpg, data/val/<Class>/*.jpg
python train_mlp.py --csv data/mlp_features.csv
python train_bilstm.py --csv data/health_history.csv   # columns: panel_id, date, health_score
```

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

The tests run against the in-memory database. They cover auth, panel ownership, the full inspection flow, upload validation, and the diagnostics logic.

## Project layout

```
backend/
  app/
    main.py                  FastAPI app, CORS, startup
    db/                      Mongo connection + Pydantic schemas
    routers/                 auth, panels, inspections
    services/
      prediction_service.py  runs the 3-stage pipeline
      diagnostics.py         physics/rule-based fallback + recommendations
    models/                  CNN, MLP, Bi-LSTM, VAE definitions
    demo_data.py             sample fleet for in-memory mode
  ml_training/               training scripts
  saved_models/              trained weights (.pt)
  tests/
frontend/
  api/client.js              API calls (+ offline demo mode)
  src/pages/                 Login, Dashboard, PanelDetail
  src/components/            gauge, chart, upload form, cards
```
