from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def test_sleep_endpoints_require_api_key(client):
    assert client.get("/profile", params={"user_id": "u1"}).status_code == 401
    assert client.get("/sleep/weekly", params={"user_id": "u1"}).status_code == 401
    assert client.put(
        "/sleep/checkin",
        json={
            "user_id": "u1",
            "duration_hours": 7.5,
            "quality": 4,
            "awakenings": 1,
            "energy": 3,
        },
    ).status_code == 401


def test_profile_rejects_unknown_timezone(client, auth_headers):
    response = client.put(
        "/profile",
        headers=auth_headers,
        json={
            "user_id": "u1",
            "timezone": "Mars/Olympus",
            "sleep_goal_minutes": 480,
        },
    )
    assert response.status_code == 422


def test_profile_round_trip(client, auth_headers):
    saved = client.put(
        "/profile",
        headers=auth_headers,
        json={
            "user_id": "u1",
            "timezone": "Asia/Yekaterinburg",
            "sleep_goal_minutes": 480,
            "reminders_enabled": False,
        },
    )
    assert saved.status_code == 200
    assert saved.json()["sleep_goal_minutes"] == 480

    loaded = client.get(
        "/profile", params={"user_id": "u1"}, headers=auth_headers
    )
    assert loaded.status_code == 200
    assert loaded.json()["timezone"] == "Asia/Yekaterinburg"


def test_sleep_checkin_upsert_keeps_single_linked_health_event(client, auth_headers):
    payload = {
        "user_id": "u1",
        "sleep_date": datetime.now(ZoneInfo("Asia/Yekaterinburg")).date().isoformat(),
        "duration_hours": 7.5,
        "quality": 4,
        "awakenings": 1,
        "energy": 3,
    }
    created = client.put("/sleep/checkin", headers=auth_headers, json=payload)
    assert created.status_code == 200
    assert created.json()["duration_hours"] == 7.5

    payload["duration_hours"] = 8
    updated = client.put("/sleep/checkin", headers=auth_headers, json=payload)
    assert updated.status_code == 200
    assert updated.json()["id"] == created.json()["id"]
    assert updated.json()["duration_hours"] == 8

    events = client.get(
        "/events", params={"user_id": "u1"}, headers=auth_headers
    )
    sleep_events = [row for row in events.json() if row["event_type"] == "sleep"]
    assert len(sleep_events) == 1
    assert sleep_events[0]["value"] == 8


def test_weekly_summary_prioritizes_logging_when_data_is_sparse(client, auth_headers):
    response = client.get(
        "/sleep/weekly", params={"user_id": "u1"}, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["days_logged"] == 0
    assert "минимум 4 раза" in data["next_best_action"]


def test_weekly_summary_returns_one_duration_action(client, auth_headers):
    client.put(
        "/profile",
        headers=auth_headers,
        json={
            "user_id": "u1",
            "timezone": "Asia/Yekaterinburg",
            "sleep_goal_minutes": 480,
        },
    )
    today = datetime.now(ZoneInfo("Asia/Yekaterinburg")).date()
    for offset in range(4):
        response = client.put(
            "/sleep/checkin",
            headers=auth_headers,
            json={
                "user_id": "u1",
                "sleep_date": (today - timedelta(days=offset)).isoformat(),
                "duration_hours": 6.5,
                "quality": 4,
                "awakenings": 1,
                "energy": 3,
            },
        )
        assert response.status_code == 200

    summary = client.get(
        "/sleep/weekly",
        params={"user_id": "u1", "period_end": today.isoformat()},
        headers=auth_headers,
    )
    assert summary.status_code == 200
    data = summary.json()
    assert data["days_logged"] == 4
    assert data["average_duration_hours"] == 6.5
    assert data["goal_met_days"] == 0
    assert data["next_best_action"] == (
        "Следующие 7 дней начинайте подготовку ко сну на 15 минут раньше."
    )
