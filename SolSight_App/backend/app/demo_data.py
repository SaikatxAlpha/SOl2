"""
Demo fleet for in-memory mode: four panels with ~10 weeks of inspections
each, every reading pushed through the real prediction pipeline so the
stored scores are exactly what the API would have produced.

  PNL-001  steady and healthy
  PNL-002  dust building up (soiling), output sliding slowly
  PNL-003  hotspot developing, cell temperature climbing
  PNL-004  cracked cell after a hail event in week 6
"""
import random
from datetime import datetime, timedelta

from app.services.prediction_service import prediction_service

WEEKS = 10

PANELS = [
    ("PNL-001", "Rooftop A", "2023-03-14", 400),
    ("PNL-002", "Rooftop B", "2022-11-02", 380),
    ("PNL-003", "Field Array C", "2021-06-20", 410),
    ("PNL-004", "Carport East", "2024-02-08", 400),
]


def _readings(panel_id: str, week: int, rated: float, rng: random.Random):
    """(voltage, current, temperature) for a given week of a scenario."""
    j = lambda s: rng.uniform(-s, s)  # noqa: E731
    temp = 42 + j(4)
    ratio = 0.98 + j(0.015)
    if panel_id == "PNL-002":
        ratio = 0.97 - week * 0.016 + j(0.01)
    elif panel_id == "PNL-003":
        temp = 46 + week * 3.2 + j(1.5)
        ratio = 0.96 - max(0, week - 3) * 0.035 + j(0.01)
    elif panel_id == "PNL-004":
        ratio = (0.97 if week < 6 else 0.66 - (week - 6) * 0.02) + j(0.01)
    expected = rated * (1 - 0.004 * (temp - 25))
    voltage = 33.2 + j(0.4)
    current = expected * ratio / voltage
    return round(voltage, 2), round(current, 2), round(temp, 1)


async def seed_demo_fleet(panels_col, inspections_col, owner_email: str):
    if await panels_col.count_documents({"owner_email": owner_email}) > 0:
        return
    rng = random.Random(7)
    now = datetime.utcnow()
    for panel_id, location, installed, rated in PANELS:
        await panels_col.insert_one({
            "panel_id": panel_id, "location": location, "installation_date": installed,
            "rated_power": rated, "owner_email": owner_email,
            "created_at": now - timedelta(weeks=WEEKS + 1),
        })
        history = []
        for week in range(WEEKS):
            at = now - timedelta(weeks=WEEKS - 1 - week, hours=rng.randint(0, 6))
            v, i, t = _readings(panel_id, week, rated, rng)
            result = prediction_service.run_inspection(
                image_bytes=None, voltage=v, current=i, temperature=t,
                rated_power=rated, history=list(history),
            )
            history.append((at, result["health_score"]))
            await inspections_col.insert_one({
                "panel_id": panel_id, "owner_email": owner_email, "created_at": at,
                "voltage": v, "current": i, "temperature": t, "has_image": False,
                **result, "analyzed": True,
            })
