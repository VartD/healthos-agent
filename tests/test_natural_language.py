from bot.natural_language import (
    parse_event,
    parse_sleep_checkin,
    parse_uncertain_event,
)


def test_parses_water_in_natural_russian() -> None:
    event = parse_event("Вода 0,5 л")
    assert event is not None
    assert event.payload == {"event_type": "water", "value": 500.0, "unit": "ml"}


def test_parses_blood_pressure_and_pulse() -> None:
    event = parse_event("Давление 128/82, пульс 64")
    assert event is not None
    assert event.payload["event_type"] == "blood_pressure"
    assert event.payload["value"] == 128.0
    assert event.payload["note"] == "Давление 128/82, пульс 64"
    assert event.payload["metadata"] == {
        "systolic": 128,
        "diastolic": 82,
        "pulse": 64,
    }


def test_parses_glucose_food_workout_and_symptom() -> None:
    assert parse_event("Сахар 6,4").payload["event_type"] == "glucose"  # type: ignore[union-attr]
    assert parse_event("Съел овсянку и два яйца").payload["event_type"] == "food"  # type: ignore[union-attr]
    assert parse_event("Тренировка в зале 45 минут").payload["event_type"] == "workout"  # type: ignore[union-attr]
    assert parse_event("Болит голова").payload["event_type"] == "symptom"  # type: ignore[union-attr]


def test_does_not_guess_ambiguous_or_implausible_input() -> None:
    assert parse_event("кофе") is None
    assert parse_event("как у меня дела?") is None
    assert parse_event("давление 999/20") is None


def test_missing_volume_unit_requires_confirmation() -> None:
    assert parse_event("Вода 300") is None
    pending = parse_uncertain_event("Вода 300")
    assert pending is not None
    assert pending.payload == {"event_type": "water", "value": 300.0, "unit": "ml"}
    assert parse_uncertain_event("Вода 2") is None


def test_parses_complete_natural_sleep_checkin() -> None:
    checkin = parse_sleep_checkin(
        "Спал 7,5 часов, качество 4, просыпался 1 раз, энергия 3"
    )
    assert checkin is not None
    assert checkin.payload["duration_hours"] == 7.5
    assert checkin.payload["quality"] == 4
    assert checkin.payload["awakenings"] == 1
    assert checkin.payload["energy"] == 3


def test_incomplete_natural_sleep_checkin_is_not_parsed() -> None:
    assert parse_sleep_checkin("Спал 7 часов, энергия 3") is None
