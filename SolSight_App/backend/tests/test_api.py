import io

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.db import mongo
from app.main import app


@pytest.fixture
async def client():
    for c in (mongo.users_collection, mongo.panels_collection, mongo.inspections_collection):
        await c.delete_many({})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def auth_headers(client, email="ops@example.com"):
    r = await client.post("/auth/register", json={"name": "Ops", "email": email, "password": "secret123"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def make_panel(client, headers, panel_id="PNL-001"):
    r = await client.post("/panels", headers=headers, json={
        "panel_id": panel_id, "location": "Rooftop A",
        "installation_date": "2024-01-15", "rated_power": 400,
    })
    assert r.status_code == 201, r.text
    return r.json()


async def inspect(client, headers, panel_id="PNL-001", v=33.0, i=10.8, t=45.0, files=None):
    return await client.post("/predict-defect", headers=headers, files=files,
                             data={"panel_id": panel_id, "voltage": v, "current": i, "temperature": t})


async def test_register_login_me(client):
    await auth_headers(client)
    r = await client.post("/auth/login", json={"email": "OPS@example.com", "password": "secret123"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    r = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.json()["email"] == "ops@example.com"


async def test_wrong_password_rejected(client):
    await auth_headers(client)
    r = await client.post("/auth/login", json={"email": "ops@example.com", "password": "nope-nope"})
    assert r.status_code == 401


async def test_short_password_rejected(client):
    r = await client.post("/auth/register", json={"name": "x", "email": "a@b.co", "password": "123"})
    assert r.status_code == 422


async def test_full_inspection_flow(client):
    h = await auth_headers(client)
    await make_panel(client, h)

    r = await inspect(client, h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "Healthy"
    assert body["analysis_mode"]["defect"] in ("cnn", "rule-based")
    assert [p["day"] for p in body["degradation_forecast"]] == [30, 60, 90]

    r = await inspect(client, h, v=24.0, i=8.0, t=72.0)
    assert r.json()["status"] != "Healthy"

    panels = (await client.get("/panels", headers=h)).json()
    assert panels[0]["latest_status"] == r.json()["status"]

    history = (await client.get("/panels/PNL-001/history", headers=h)).json()
    assert len(history) == 2

    pred = (await client.get("/panels/PNL-001/prediction", headers=h)).json()
    assert pred["recommendation"]


async def test_unanalyzed_upload_does_not_break_reads(client):
    h = await auth_headers(client)
    await make_panel(client, h)
    r = await client.post("/upload-inspection", headers=h,
                          data={"panel_id": "PNL-001", "voltage": 30, "current": 8, "temperature": 40})
    assert r.status_code == 200
    assert (await client.get("/panels", headers=h)).status_code == 200
    assert (await client.get("/panels/PNL-001", headers=h)).status_code == 200
    assert (await client.get("/panels/PNL-001/history", headers=h)).json() == []
    assert (await client.get("/panels/PNL-001/prediction", headers=h)).status_code == 404


async def test_image_upload(client):
    h = await auth_headers(client)
    await make_panel(client, h)
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (40, 60, 120)).save(buf, format="PNG")
    files = {"image": ("panel.png", buf.getvalue(), "image/png")}
    r = await inspect(client, h, files=files)
    assert r.status_code == 200, r.text
    assert r.json()["has_image"] is True


async def test_bad_image_is_a_400_not_a_500(client):
    h = await auth_headers(client)
    await make_panel(client, h)
    files = {"image": ("panel.png", b"definitely not a png", "image/png")}
    r = await inspect(client, h, files=files)
    assert r.status_code == 400


async def test_out_of_range_reading_rejected(client):
    h = await auth_headers(client)
    await make_panel(client, h)
    r = await inspect(client, h, v=500)
    assert r.status_code == 422


async def test_panels_are_private_to_owner(client):
    a = await auth_headers(client, "a@example.com")
    b = await auth_headers(client, "b@example.com")
    await make_panel(client, a)
    assert (await client.get("/panels/PNL-001", headers=b)).status_code == 404
    assert (await client.get("/panels", headers=b)).json() == []


async def test_delete_panel_removes_inspections(client):
    h = await auth_headers(client)
    await make_panel(client, h)
    await inspect(client, h)
    r = await client.delete("/panels/PNL-001", headers=h)
    assert r.status_code == 204
    assert (await client.get("/panels/PNL-001", headers=h)).status_code == 404
    assert await mongo.inspections_collection.count_documents({"panel_id": "PNL-001"}) == 0


async def test_future_install_date_rejected(client):
    h = await auth_headers(client)
    r = await client.post("/panels", headers=h, json={
        "panel_id": "PNL-9", "location": "X", "installation_date": "2999-01-01", "rated_power": 400,
    })
    assert r.status_code == 422
