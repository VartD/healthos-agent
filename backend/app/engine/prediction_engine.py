"""Fixed-horizon consequence hints (not medical prognosis)."""

from app.schemas import Mode


def build_prediction(risks: list[str]) -> dict[str, str] | None:
    """Risk-driven forecast; returns None → use fallback with mode."""
    if "кофе поздно вечером" in risks:
        return {
            "through_2_4h": "рост ЧСС, возбуждение, снижение способности к расслаблению",
            "by_evening": "высокий риск ухудшения засыпания и фрагментации сна",
            "tomorrow_morning": "ниже HRV, выше пульс покоя, ощущение недовосстановления",
        }
    if "кофе + недостаточная компенсация водой" in risks:
        return {
            "through_2_4h": "риск обезвоживания, повышение нагрузки на сосуды",
            "by_evening": "возможен рост давления и ухудшение восстановления",
            "tomorrow_morning": "возможен рост мочевой кислоты и ощущение усталости",
        }
    return None


def predict_consequences(
    mode: Mode,
    risks: list[str],
) -> dict[str, str]:
    """Fallback when build_prediction returns None."""

    risk_set = set(risks)

    parts_2_4: list[str] = []
    parts_evening: list[str] = []
    parts_tomorrow: list[str] = []

    if "glucose_high" in risk_set:
        parts_2_4.append("Нагрузка на обмен веществ может усилиться.")
        parts_evening.append("К вечеру возможна повышенная усталость.")
        parts_tomorrow.append("Утром стоит повторить контроль показателей.")
    elif mode.value == "STABILIZATION":
        parts_2_4.append("Фон может оставаться напряжённым без коррекции гидрации и нагрузки.")
        parts_evening.append("К вечеру субъективно может быть тяжелее, если режим не смягчить.")
        parts_tomorrow.append("Утром возможна большая инерция — полезен спокойный старт дня.")

    if "uric_high" in risk_set or "uric_high_protein" in risk_set:
        parts_2_4.append("Сочетание нагрузки на фильтрацию и рациона может давать дискомфорт.")
        parts_evening.append("К вечеру возможен рост субъективной тяжести в суставах/общего недомогания.")
        parts_tomorrow.append("Утром возможна «тяжесть» при недостаточном восстановлении.")

    if "coffee_low_water" in risk_set or "poor_sleep_coffee" in risk_set:
        parts_2_4.append("Стимуляция на фоне обезвоживания или недосыпа часто усиливает дрожь и раздражительность.")
        parts_evening.append("К вечеру возможен провал энергии или ухудшение концентрации.")
        parts_tomorrow.append("Утром возможен более жёсткий «откат» по самочувствию.")

    if "workout_sauna_low_water" in risk_set:
        parts_2_4.append("Комбо нагрузки и жары без воды повышает риск головокружения.")
        parts_evening.append("К вечеру возможна сильнее выраженная усталость.")
        parts_tomorrow.append("Утром восстановление может затянуться.")

    if mode.value == "TRAINING":
        parts_evening.append("К вечеру полезно заложить лёгкое восстановление и сон.")
    if mode.value == "RECOVERY":
        parts_tomorrow.append("Завтра утром самочувствие может зависеть от сна и гидрации сегодня.")

    if not parts_2_4:
        parts_2_4.append("При сохранении текущего паттерна фон останется близким к текущему.")
    if not parts_evening:
        parts_evening.append("К вечеру возможны обычные колебания энергии без резких скачков.")
    if not parts_tomorrow:
        parts_tomorrow.append("Завтра утром базовое самочувствие вероятно похоже на сегодняшнее.")

    return {
        "through_2_4h": " ".join(parts_2_4[:3]),
        "by_evening": " ".join(parts_evening[:3]),
        "tomorrow_morning": " ".join(parts_tomorrow[:3]),
    }


def system_effect_lines(mode: Mode, risks: list[str]) -> list[str]:
    lines: list[str] = []
    if mode == Mode.STABILIZATION:
        lines.append("Система в режиме приоритета стабилизации ключевых маркеров.")
    elif mode == Mode.TRAINING:
        lines.append("Нагрузка сегодня — акцент на восстановлении и ресурсе.")
    elif mode == Mode.RECOVERY:
        lines.append("Недостаток сна или симптомы снижают запас адаптации.")
    elif mode == Mode.DRY_MODE:
        lines.append("Цель снижения жира — упор на простые режимные якоря без экстремумов.")
    else:
        lines.append("Базовый режим: поддерживающие привычки без особых ограничений.")

    if risks:
        lines.append(f"Активных флагов риска: {len(risks)}.")
    return lines
