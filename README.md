# SOl2 — SolSight: Solar Panel Degradation Detection (module-wise)

The SolSight project split up by syllabus module. Each `ModuleN/` folder holds
the code for one topic, and `SolSight_App/` is the complete working system
that uses all of them together.

| Module | Syllabus topic | Code |
|---|---|---|
| **Module 1** | MLP classifies the panel condition as Healthy, Warning, or Critical using extracted features | `Module1/Model/health_mlp.py` |
| **Module 2** | Backpropagation and Adam optimizer train the model, with dropout/batch normalization to improve generalization | `Module2/Training/train_health_mlp.py` |
| **Module 3** | A pretrained CNN (ResNet/DenseNet) detects cracks, hotspots, soiling, and other panel defects | `Module3/Model/defect_cnn.py`, `Module3/Training/train_defect_cnn.py` |
| **Module 4** | Bi-LSTM analyzes repeated inspections to learn the panel's degradation trend over time | `Module4/Model/degradation_bilstm.py`, `Module4/Training/train_bilstm.py` |
| **Module 5** | VAE generates synthetic defect images to increase rare-defect samples and reduce class imbalance | `Module5/Model/defect_vae.py`, `Module5/Training/train_vae.py` |
| **Full project** | All modules wired into one app (FastAPI backend + React frontend) | `SolSight_App/` |

## How the modules fit together

```
            Module 5 (VAE) ── synthetic Crack/Hotspot images ──┐
                                                               ▼
panel image ──► Module 3 (CNN) ──► defect + 128-d features ──► Module 1 (MLP) ──► Healthy / Warning / Critical + score
readings  ─────────────────────────────────────────────────────┘      ▲
                                                Module 2 trains it ───┘
health scores over time ──► Module 4 (Bi-LSTM) ──► 30 / 60 / 90-day forecast
```

## Layout

```
SOl2/
├── requirements.txt               # deps for Modules 1–5
├── predict.py                     # quick CLI health prediction with the Module 1 MLP
├── Module1/Model/health_mlp.py
├── Module2/Training/train_health_mlp.py
├── Module3/
│   ├── Model/defect_cnn.py        # ResNet18 backbone + feature head, 4 defect classes
│   └── Training/train_defect_cnn.py
├── Module4/
│   ├── Model/degradation_bilstm.py
│   └── Training/train_bilstm.py
├── Module5/
│   ├── Model/defect_vae.py        # convolutional VAE + loss
│   └── Training/train_vae.py      # trains on one class folder, writes vae_*.png samples
├── SolSight_App/                  # complete project (backend, frontend, tests, Docker)
├── docs/                          # presentation (PDF + PPTX)
└── saved_models/                  # trained .pt checkpoints land here (git-ignored)
```

## Setup

```bash
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

## Running each module (from the repo root)

```bash
# Module 1 + 2: train the health MLP (synthetic data if no --csv is given)
python Module2/Training/train_health_mlp.py --epochs 50
python predict.py

# Module 3: CNN defect detection — data/train/<Class>/*.jpg and data/val/<Class>/*.jpg
python Module3/Training/train_defect_cnn.py --data-dir data --epochs 20

# Module 4: Bi-LSTM degradation trend — CSV columns: panel_id, date, health_score
python Module4/Training/train_bilstm.py --csv data/health_history.csv --epochs 100

# Module 5: VAE — grow a rare class before training the CNN
python Module5/Training/train_vae.py --class-dir data/train/Crack --epochs 50 --generate 200
```

Checkpoints are written to `saved_models/`.

## Running the full app

See [`SolSight_App/README.md`](SolSight_App/README.md). In short:

```bash
cd SolSight_App/backend
pip install -r requirements.txt
uvicorn app.main:app --reload          # with MONGO_URI=memory in backend/.env for a demo database

cd SolSight_App
npm install
npm run dev                            # http://localhost:5173
```
