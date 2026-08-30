import torch
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "Module1", "Model"))

from health_mlp import HealthMLP


MODEL_PATH = "saved_models/mlp_best.pt"


def predict():
    print("=" * 50)
    print("       SOLSIGHT HEALTH PREDICTION")
    print("=" * 50)

    # Operational inputs
    voltage = float(input("Voltage (V): "))
    current = float(input("Current (A): "))
    temperature = float(input("Temperature (°C): "))
    efficiency = float(input("Efficiency (0-1): "))
    defect_confidence = float(input("Defect confidence (0-1): "))
    historical_health_avg = float(input("Historical health average (0-100): "))

    power = voltage * current

    # Demo CNN features.
    # In the real system these would come from the CNN image model.
    cnn_features = torch.zeros(128)

    numeric_features = torch.tensor([
        voltage,
        current,
        power,
        temperature,
        efficiency,
        defect_confidence,
        historical_health_avg
    ], dtype=torch.float32)

    model = HealthMLP()

    checkpoint = torch.load(
        MODEL_PATH,
        map_location="cpu",
        weights_only=True
    )

    model.load_state_dict(checkpoint)
    model.eval()

    status, health_score, probabilities = model.predict(
        cnn_features,
        numeric_features
    )

    print()
    print("=" * 50)
    print("             PREDICTION RESULT")
    print("=" * 50)

    print(f"Status         : {status}")
    print(f"Health Score   : {health_score}/100")

    print()
    print("Class Probabilities:")
    for name, probability in probabilities.items():
        print(f"  {name:<10}: {probability * 100:.2f}%")

    print("=" * 50)


if __name__ == "__main__":
    predict()
