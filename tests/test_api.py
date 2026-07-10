def test_health_endpoint_is_public(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "HealthOS running"}


def test_health_data_endpoints_require_api_key(client):
    assert client.get("/events", params={"user_id": "u1"}).status_code == 401
    assert client.get("/analyze", params={"user_id": "u1"}).status_code == 401
    assert client.post(
        "/events",
        json={"user_id": "u1", "event_type": "water", "value": 300, "unit": "ml"},
    ).status_code == 401


def test_invalid_api_key_is_rejected(client):
    response = client.get(
        "/events",
        params={"user_id": "u1"},
        headers={"X-API-Key": "wrong"},
    )
    assert response.status_code == 401


def test_event_list_requires_user_id(client, auth_headers):
    response = client.get("/events", headers=auth_headers)
    assert response.status_code == 422


def test_events_are_filtered_by_user_id(client, auth_headers):
    for user_id in ("u1", "u2"):
        response = client.post(
            "/events",
            headers=auth_headers,
            json={
                "user_id": user_id,
                "event_type": "water",
                "value": 300,
                "unit": "ml",
            },
        )
        assert response.status_code == 200

    response = client.get(
        "/events", params={"user_id": "u1"}, headers=auth_headers
    )
    assert response.status_code == 200
    assert [item["user_id"] for item in response.json()] == ["u1"]


def test_negative_water_is_rejected(client, auth_headers):
    response = client.post(
        "/events",
        headers=auth_headers,
        json={"user_id": "u1", "event_type": "water", "value": -500, "unit": "ml"},
    )
    assert response.status_code == 422


def test_numeric_observation_requires_canonical_unit(client, auth_headers):
    response = client.post(
        "/events",
        headers=auth_headers,
        json={"user_id": "u1", "event_type": "water", "value": 500},
    )
    assert response.status_code == 422


def test_water_in_liters_uses_liter_bounds(client, auth_headers):
    response = client.post(
        "/events",
        headers=auth_headers,
        json={"user_id": "u1", "event_type": "water", "value": 11, "unit": "l"},
    )
    assert response.status_code == 422


def test_implausible_glucose_is_rejected(client, auth_headers):
    response = client.post(
        "/events",
        headers=auth_headers,
        json={
            "user_id": "u1",
            "event_type": "glucose",
            "value": 9999,
            "unit": "mmol/L",
        },
    )
    assert response.status_code == 422


def test_food_requires_description(client, auth_headers):
    response = client.post(
        "/events",
        headers=auth_headers,
        json={"user_id": "u1", "event_type": "food"},
    )
    assert response.status_code == 422


def test_valid_glucose_event_can_be_analyzed(client, auth_headers):
    created = client.post(
        "/events",
        headers=auth_headers,
        json={
            "user_id": "u1",
            "event_type": "glucose",
            "value": 9.2,
            "unit": "mmol/L",
        },
    )
    assert created.status_code == 200

    response = client.get(
        "/analyze", params={"user_id": "u1"}, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "STABILIZATION"
    assert "Глюкоза выше 8" in data["risks"]


def test_latest_glucose_measurement_drives_current_mode(client, auth_headers):
    now = datetime.now(ZoneInfo("Asia/Yekaterinburg"))
    for timestamp, value in (
        ((now - timedelta(hours=1)).isoformat(), 9.2),
        (now.isoformat(), 5.4),
    ):
        response = client.post(
            "/events",
            headers=auth_headers,
            json={
                "user_id": "u1",
                "timestamp": timestamp,
                "event_type": "glucose",
                "value": value,
                "unit": "mmol/L",
            },
        )
        assert response.status_code == 200

    response = client.get(
        "/analyze", params={"user_id": "u1"}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["mode"] == "NORMAL"


def test_old_severe_symptom_does_not_trigger_permanent_alert(client, auth_headers):
    old_timestamp = datetime.now(ZoneInfo("Asia/Yekaterinburg")) - timedelta(days=3)
    response = client.post(
        "/events",
        headers=auth_headers,
        json={
            "user_id": "u1",
            "timestamp": old_timestamp.isoformat(),
            "event_type": "symptom",
            "note": "боль в груди",
        },
    )
    assert response.status_code == 200

    response = client.get(
        "/analyze", params={"user_id": "u1"}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["disclaimer"] is None
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
