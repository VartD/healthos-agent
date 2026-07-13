"""Short Russian action nudges (not prescriptions)."""

from app.schemas import Mode


def build_commands(mode: Mode, risk_codes: list[str]) -> list[str]:
    codes = set(risk_codes)

    risk_cmds: list[str] = []
    if "blood_pressure_critical" in codes:
        risk_cmds.append("подождите 1 минуту и повторно измерьте давление")
        risk_cmds.append("при тревожных симптомах звоните 112")
    if "кофе + недостаточная компенсация водой" in codes:
        risk_cmds.append("вода 400–600 мл в течение 30–60 мин")
    if "кофе поздно вечером" in codes:
        risk_cmds.append("исключить кофеин до сна")
        risk_cmds.append("магний вечером")
    if risk_cmds:
        return risk_cmds[:6]

    cmds: list[str] = []

    if codes & {"coffee_low_water", "poor_sleep_coffee"}:
        cmds.append("стоп кофе")

    if codes & {"coffee_low_water", "salt_low_water", "workout_sauna_low_water"}:
        cmds.append("вода")

    if codes & {"glucose_high", "uric_high", "uric_high_protein"}:
        cmds.append("чистый приём пищи")

    if codes & {"glucose_high", "uric_high"}:
        cmds.append("контроль через 30–60 минут")

    if mode == Mode.RECOVERY or codes & {"poor_sleep_coffee"}:
        cmds.append("сон")

    if mode == Mode.TRAINING or codes & {"workout_sauna_low_water"}:
        cmds.append("движение")

    if mode == Mode.STABILIZATION and "контроль через 30–60 минут" not in cmds:
        cmds.append("контроль через 30–60 минут")

    if mode == Mode.DRY_MODE and "чистый приём пищи" not in cmds:
        cmds.append("чистый приём пищи")

    # de-dupe preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for c in cmds:
        if c not in seen:
            seen.add(c)
            ordered.append(c)

    if not ordered:
        ordered = ["вода", "движение"]

    return ordered[:6]
