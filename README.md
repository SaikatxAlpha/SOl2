# SOl2 — Solar Panel Health Monitoring (ML modules)

## Current status

Only the health-classification piece of the pipeline is built so far:

```
SOl2/
├── requirements.txt
├── Module1/
│   └── Model/
│       └── health_mlp.py        # Module 1: HealthMLP architecture
├── Module2/
│   └── Training/
│       └── train_health_mlp.py  # Module 2: training (backprop + Adam, dropout/batchnorm)
└── saved_models/                # trained .pt checkpoints land here
```

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run it

From the repo root:

```bash
python Module2/Training/train_health_mlp.py --epochs 50
```

No dataset is required to try it — the script auto-generates a synthetic
dataset that matches the real feature schema, trains the MLP, and saves
the best checkpoint to `saved_models/mlp_best.pt`.

Once you have a real dataset, pass it in:

```bash
python Module2/Training/train_health_mlp.py --csv data/mlp_features.csv --epochs 50
```

Expected CSV columns:
`cnn_feat_0 ... cnn_feat_127, voltage, current, power, temperature, efficiency, defect_confidence, historical_health_avg, label`
(`label` ∈ {Healthy, Warning, Critical})

## What's still missing (per the module list in your sheet)

- **CNN defect detection** (Normal / Crack / Hotspot / Soiling) — feeds the
  128-d `cnn_feat_*` features that Module 1's MLP expects as input. Right
  now training the MLP only works with synthetic stand-in features.
- **Bi-LSTM degradation forecasting** — takes a panel's health-score history
  and predicts 30/60/90-day health.
- **VAE for synthetic defect images** — used offline to generate more
  Crack/Hotspot images so the CNN doesn't overfit to the majority classes.
- **A real dataset** — panel images labeled by defect type, and/or a CSV of
  operational readings + health labels, to replace the synthetic data.
- **requirements.txt is now added, but there's no `.py` entry point tying
  all modules into a single inference pipeline yet** (that's what
  `prediction_service`-style orchestration would do once CNN/Bi-LSTM exist).
- No frontend/backend — intentionally out of scope per your request.
