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
from telegram.request import HTTPXRequest  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001").rstrip("/")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
logger.info("BACKEND_URL=%s", BACKEND_URL)

# Запросы к своему backend не должны ходить через корпоративный proxy из env
_HTTPX_BACKEND = {"trust_env": False}


async def _post_event(client: httpx.AsyncClient, payload: dict[str, Any]) -> dict[str, Any]:
    r = await client.post(f"{BACKEND_URL}/events", json=payload, timeout=30.0)
    r.raise_for_status()
    return r.json()


async def _analyze(client: httpx.AsyncClient, user_id: str) -> dict[str, Any]:
    r = await client.get(f"{BACKEND_URL}/analyze", params={"user_id": user_id}, timeout=30.0)
    r.raise_for_status()
    return r.json()


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
        "Команды: /water, /glucose, /uric, /coffee, /food, /workout, /sauna, /symptom, /status\n\n"
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


def main() -> None:
    if not TOKEN:
        raise SystemExit("Задайте TELEGRAM_BOT_TOKEN в .env или окружении.")
    tg_request = HTTPXRequest(httpx_kwargs={"trust_env": False})
    app = Application.builder().token(TOKEN).request(tg_request).build()
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
    logger.info("Bot polling… backend=%s", BACKEND_URL)
    app.run_polling()


if __name__ == "__main__":
    main()
