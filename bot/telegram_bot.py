from dotenv import load_dotenv
import os

load_dotenv()

import logging
from pathlib import Path
from typing import Any

import httpx

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# Системный proxy часто ломает доступ к api.telegram.org (403 и т.п.)
for _key in (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
):
    os.environ.pop(_key, None)

from telegram import Update  # noqa: E402
from telegram.ext import Application, CommandHandler, ContextTypes  # noqa: E402

if __package__:
    from .aiohttp_request import AiohttpRequest  # noqa: E402
else:
    from aiohttp_request import AiohttpRequest  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
API_KEY = os.getenv("HEALTHOS_API_KEY", "")
logger.info("BACKEND_URL=%s", BACKEND_URL)

# Запросы к своему backend не должны ходить через корпоративный proxy из env
_HTTPX_BACKEND = {"trust_env": False}


def _api_headers() -> dict[str, str]:
    return {"X-API-Key": API_KEY}


async def _post_event(client: httpx.AsyncClient, payload: dict[str, Any]) -> dict[str, Any]:
    r = await client.post(
        f"{BACKEND_URL}/events", json=payload, headers=_api_headers(), timeout=30.0
    )
    r.raise_for_status()
    return r.json()


async def _analyze(client: httpx.AsyncClient, user_id: str) -> dict[str, Any]:
    r = await client.get(
        f"{BACKEND_URL}/analyze",
        params={"user_id": user_id},
        headers=_api_headers(),
        timeout=30.0,
    )
    r.raise_for_status()
    return r.json()


async def _put_profile(
    client: httpx.AsyncClient, user_id: str, goal_hours: float, timezone_name: str
) -> dict[str, Any]:
    response = await client.put(
        f"{BACKEND_URL}/profile",
        headers=_api_headers(),
        json={
            "user_id": user_id,
            "timezone": timezone_name,
            "sleep_goal_minutes": round(goal_hours * 60),
            "reminders_enabled": False,
        },
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()


async def _put_sleep_checkin(
    client: httpx.AsyncClient, payload: dict[str, Any]
) -> dict[str, Any]:
    response = await client.put(
        f"{BACKEND_URL}/sleep/checkin",
        headers=_api_headers(),
        json=payload,
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()


async def _get_sleep_weekly(
    client: httpx.AsyncClient, user_id: str
) -> dict[str, Any]:
    response = await client.get(
        f"{BACKEND_URL}/sleep/weekly",
        headers=_api_headers(),
        params={"user_id": user_id},
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()


def _format_digest(data: dict[str, Any]) -> str:
    mode = data.get("mode_ru") or data.get("mode")
    risks = data.get("risks") or []
    effects = data.get("system_effect") or []
    pred = data.get("prediction") or {}
    cmds = data.get("commands") or []
    disclaimer = data.get("disclaimer")

    lines: list[str] = []
    lines.append(f"РЕЖИМ: {mode}")
    lines.append("РИСК:")
    if risks:
        lines.extend(f"- {r}" for r in risks)
    else:
        lines.append("- нет активных флагов")

    lines.append("СИСТЕМНЫЙ ЭФФЕКТ:")
    if effects:
        lines.extend(f"- {e}" for e in effects)
    else:
        lines.append("- нейтральный фон")

    lines.append("ПРОГНОЗ:")
    lines.append(f"- через 2–4 часа: {pred.get('through_2_4h', '')}")
    lines.append(f"- к вечеру: {pred.get('by_evening', '')}")
    lines.append(f"- завтра утром: {pred.get('tomorrow_morning', '')}")

    lines.append("NOW DO:")
    for i, c in enumerate(cmds[:6], start=1):
        lines.append(f"{i}. {c}")

    lines.append("")
    lines.append(
        "Не меняйте дозы назначенных препаратов и не отменяйте их без врача. "
        "Сервис не ставит диагнозы."
    )
    if disclaimer:
        lines.append("")
        lines.append(disclaimer)

    return "\n".join(lines)


def _user_id(update: Update) -> str:
    chat = update.effective_chat
    assert chat is not None
    return str(chat.id)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "HealthOS — журнал событий и мягкие операционные подсказки.\n\n"
        "Команды журнала: /water, /glucose, /uric, /coffee, /food, /workout, "
        "/sauna, /symptom, /status\n"
        "Сон: /profile, /morning, /sleepweek\n\n"
        "Это не медицинская консультация. Не игнорируйте назначения врача. "
        "При ухудшении состояния обратитесь к специалисту."
    )
    await update.message.reply_text(text)  # type: ignore[union-attr]


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = _user_id(update)
    try:
        async with httpx.AsyncClient(trust_env=False) as client:
            r = await client.get(
                f"{BACKEND_URL}/analyze",
                params={"user_id": str(user_id)},
                headers=_api_headers(),
                timeout=30.0,
            )
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        logger.warning("status analyze failed: %s", repr(e))
        await update.message.reply_text(f"Ошибка status: {type(e).__name__}: {e}")  # type: ignore[union-attr]
        return
    await update.message.reply_text(_format_digest(data))  # type: ignore[union-attr]


async def _log_and_reply(update: Update, payload: dict[str, Any]) -> None:
    uid = _user_id(update)
    payload["user_id"] = uid
    try:
        async with httpx.AsyncClient(**_HTTPX_BACKEND) as client:
            await _post_event(client, payload)
            data = await _analyze(client, uid)
    except httpx.HTTPError:
        await update.message.reply_text(  # type: ignore[union-attr]
            "Не удалось связаться с backend. Проверьте BACKEND_URL и что API запущен."
        )
        return
    await update.message.reply_text(_format_digest(data))  # type: ignore[union-attr]


async def _parse_float(update: Update, context: ContextTypes.DEFAULT_TYPE, example: str) -> float | None:
    if not context.args:
        await update.message.reply_text(f"Укажите число, например {example}")  # type: ignore[union-attr]
        return None
    try:
        return float(context.args[0].replace(",", "."))
    except ValueError:
        await update.message.reply_text("Неверное число.")  # type: ignore[union-attr]
        return None


async def cmd_water(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    v = await _parse_float(update, context, "/water 300")
    if v is None:
        return
    await _log_and_reply(
        update,
        {"event_type": "water", "value": v, "unit": "ml"},
    )


async def cmd_glucose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    v = await _parse_float(update, context, "/glucose 6.5")
    if v is None:
        return
    await _log_and_reply(
        update,
        {"event_type": "glucose", "value": v, "unit": "mmol/L"},
    )


async def cmd_uric(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    v = await _parse_float(update, context, "/uric 434")
    if v is None:
        return
    await _log_and_reply(
        update,
        {"event_type": "uric_acid", "value": v, "unit": "µmol/L"},
    )


async def cmd_coffee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    volume: float | None = None
    if context.args:
        try:
            volume = float(context.args[0].replace(",", "."))
        except ValueError:
            await update.message.reply_text("Неверное число объёма.")  # type: ignore[union-attr]
            return
    payload: dict[str, Any] = {"event_type": "coffee"}
    if volume is not None:
        payload["value"] = volume
        payload["unit"] = "ml"
    await _log_and_reply(update, payload)


async def cmd_food(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    note = " ".join(context.args).strip() if context.args else ""
    if not note:
        await update.message.reply_text("Добавьте текст: /food овсянка")  # type: ignore[union-attr]
        return
    await _log_and_reply(update, {"event_type": "food", "note": note})


async def cmd_workout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    note = " ".join(context.args).strip() if context.args else ""
    payload: dict[str, Any] = {"event_type": "workout"}
    if note:
        payload["note"] = note
    await _log_and_reply(update, payload)


async def cmd_sauna(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    v = await _parse_float(update, context, "/sauna 10")
    if v is None:
        return
    await _log_and_reply(
        update,
        {"event_type": "sauna", "value": v, "unit": "min"},
    )


async def cmd_symptom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    note = " ".join(context.args).strip() if context.args else ""
    if not note:
        await update.message.reply_text("Опишите симптом: /symptom насморк")  # type: ignore[union-attr]
        return
    await _log_and_reply(update, {"event_type": "symptom", "note": note})


async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(  # type: ignore[union-attr]
            "Формат: /profile 8 Asia/Yekaterinburg"
        )
        return
    try:
        goal_hours = float(context.args[0].replace(",", "."))
    except ValueError:
        await update.message.reply_text("Цель сна должна быть числом часов.")  # type: ignore[union-attr]
        return
    timezone_name = context.args[1] if len(context.args) > 1 else "Asia/Yekaterinburg"
    try:
        async with httpx.AsyncClient(**_HTTPX_BACKEND) as client:
            profile = await _put_profile(client, _user_id(update), goal_hours, timezone_name)
    except httpx.HTTPStatusError as exc:
        logger.warning("profile rejected: status=%s", exc.response.status_code)
        await update.message.reply_text(  # type: ignore[union-attr]
            "Не удалось сохранить профиль. Проверьте цель сна и название часового пояса."
        )
        return
    except httpx.HTTPError:
        await update.message.reply_text("Backend временно недоступен.")  # type: ignore[union-attr]
        return
    await update.message.reply_text(  # type: ignore[union-attr]
        f"Профиль сохранён. Цель сна: {profile['sleep_goal_minutes'] / 60:g} ч. "
        f"Часовой пояс: {profile['timezone']}."
    )


async def cmd_morning(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 4:
        await update.message.reply_text(  # type: ignore[union-attr]
            "Формат: /morning 7.5 4 1 3 [комментарий]\n"
            "Поля: часы сна, качество 1–5, пробуждения, энергия 1–5."
        )
        return
    try:
        duration_hours = float(context.args[0].replace(",", "."))
        quality = int(context.args[1])
        awakenings = int(context.args[2])
        energy = int(context.args[3])
    except ValueError:
        await update.message.reply_text("Проверьте числовые значения чекина.")  # type: ignore[union-attr]
        return

    payload: dict[str, Any] = {
        "user_id": _user_id(update),
        "duration_hours": duration_hours,
        "quality": quality,
        "awakenings": awakenings,
        "energy": energy,
    }
    note = " ".join(context.args[4:]).strip()
    if note:
        payload["note"] = note

    try:
        async with httpx.AsyncClient(**_HTTPX_BACKEND) as client:
            checkin = await _put_sleep_checkin(client, payload)
            weekly = await _get_sleep_weekly(client, payload["user_id"])
    except httpx.HTTPStatusError as exc:
        logger.warning("morning checkin rejected: status=%s", exc.response.status_code)
        await update.message.reply_text(  # type: ignore[union-attr]
            "Чекин отклонён. Проверьте: часы 0–24, качество и энергия 1–5, "
            "пробуждения 0–20."
        )
        return
    except httpx.HTTPError:
        await update.message.reply_text("Backend временно недоступен.")  # type: ignore[union-attr]
        return

    await update.message.reply_text(  # type: ignore[union-attr]
        "Утренний чекин сохранён.\n"
        f"Сон: {checkin['duration_hours']:g} ч; качество: {checkin['quality']}/5; "
        f"пробуждения: {checkin['awakenings']}; энергия: {checkin['energy']}/5.\n"
        f"NEXT BEST ACTION: {weekly['next_best_action']}"
    )


async def cmd_sleepweek(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        async with httpx.AsyncClient(**_HTTPX_BACKEND) as client:
            weekly = await _get_sleep_weekly(client, _user_id(update))
    except httpx.HTTPError:
        await update.message.reply_text("Backend временно недоступен.")  # type: ignore[union-attr]
        return

    def display(value: Any, suffix: str = "") -> str:
        return "нет данных" if value is None else f"{value:g}{suffix}"

    await update.message.reply_text(  # type: ignore[union-attr]
        f"СОН ЗА 7 ДНЕЙ ({weekly['period_start']} — {weekly['period_end']})\n"
        f"Заполнено: {weekly['days_logged']}/7\n"
        f"Средняя длительность: {display(weekly['average_duration_hours'], ' ч')}\n"
        f"Среднее качество: {display(weekly['average_quality'], '/5')}\n"
        f"Средняя энергия: {display(weekly['average_energy'], '/5')}\n"
        f"Дней с выполненной целью: {weekly['goal_met_days']}\n"
        f"NEXT BEST ACTION: {weekly['next_best_action']}"
    )


def main() -> None:
    if not TOKEN:
        raise SystemExit("Задайте TELEGRAM_BOT_TOKEN в .env или окружении.")
    if not API_KEY:
        raise SystemExit("Задайте HEALTHOS_API_KEY в .env или окружении.")
    # In sandbox, httpx TLS handshake hangs with anyio backend.
    # PTB uses TWO request objects: one for getUpdates (polling) and one for all other calls.
    # Both must be replaced with the aiohttp adapter.
    tg_request = AiohttpRequest()
    tg_updates_request = AiohttpRequest()
    app = (
        Application.builder()
        .token(TOKEN)
        .request(tg_request)
        .get_updates_request(tg_updates_request)
        .build()
    )
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("water", cmd_water))
    app.add_handler(CommandHandler("glucose", cmd_glucose))
    app.add_handler(CommandHandler("uric", cmd_uric))
    app.add_handler(CommandHandler("coffee", cmd_coffee))
    app.add_handler(CommandHandler("food", cmd_food))
    app.add_handler(CommandHandler("workout", cmd_workout))
    app.add_handler(CommandHandler("sauna", cmd_sauna))
    app.add_handler(CommandHandler("symptom", cmd_symptom))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("morning", cmd_morning))
    app.add_handler(CommandHandler("sleepweek", cmd_sleepweek))
    logger.info("Bot polling… backend=%s", BACKEND_URL)
    app.run_polling()


if __name__ == "__main__":
    main()
