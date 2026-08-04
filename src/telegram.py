from __future__ import annotations

import json
import time
from datetime import datetime
from html import escape
from urllib.request import Request, urlopen

import pandas as pd

RETRY_DELAYS_SECONDS = (0, 2, 5, 10)
MINIMUM_PRICE_DROP = 1.0
SEPARATOR = "\u2501" * 28


def send_message(token: str, chat_id: str, text: str) -> None:
    request = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=30) as response:
        response.read()


def send_job_message(token: str | None, chat_id: str | None, text: str) -> bool:
    if not token or not chat_id:
        return False
    try:
        send_message(token, chat_id, text)
        return True
    except Exception:
        print("No se pudo enviar el mensaje de estado a Telegram.")
        return False


def job_started_message(expansion_count: int) -> str:
    time_text = datetime.now().strftime("%H:%M")
    return f"\U0001f50d <b>Iniciando consulta MasterSet</b> \u2014 {time_text}\nRevisando {expansion_count} expansiones..."


def job_finished_message(variations: pd.DataFrame) -> str:
    time_text = datetime.now().strftime("%H:%M")
    status = variations["status"] if "status" in variations else pd.Series(dtype=str)
    drops, new_cards = int(status.eq("Bajo precio").sum()), int(status.eq("Nueva carta").sum())
    details = []
    if drops:
        details.append(f"\U0001f4c9 {drops} baja{'s' if drops != 1 else ''}")
    if new_cards:
        details.append(f"\U0001f195 {new_cards} carta{'s' if new_cards != 1 else ''} nueva{'s' if new_cards != 1 else ''}")
    return f"\u2705 <b>Consulta finalizada</b> \u2014 {time_text}\n{' \u00b7 '.join(details) if details else 'sin cambios esta vez'}"


def send_job_started(expansion_count: int, token: str | None, chat_id: str | None) -> bool:
    return send_job_message(token, chat_id, job_started_message(expansion_count))


def send_job_finished(variations: pd.DataFrame, token: str | None, chat_id: str | None) -> bool:
    return send_job_message(token, chat_id, job_finished_message(variations))


def price_drop_card(row: dict) -> str:
    percent = abs(row["change_percent"]) * 100 if pd.notna(row.get("change_percent")) else None
    percent_text = f" ({percent:.1f}%)" if percent is not None else ""
    return (
        f"\u2022 <b>{escape(str(row['card_name']))} {escape(str(row['card_number']))}</b>\n"
        f"S/ {row['previous_market_price']:.2f} \u2192 S/ {row['market_price']:.2f} (-{abs(row['change_amount']):.2f}){percent_text}\n"
        f"<a href=\"{escape(str(row['card_url']), quote=True)}\">Ver carta</a>"
    )


def price_drop_messages(rows: list[dict]) -> list[str]:
    messages = []
    groups: dict[str, list[dict]] = {}
    for row in rows:
        groups.setdefault(str(row["expansion"]), []).append(row)

    for expansion, cards in groups.items():
        header = f"\U0001f4c9 <b>Bajaron de precio \u2014 {escape(expansion)}</b>\n{SEPARATOR}"
        message = header
        for card in cards:
            candidate = f"{message}\n{price_drop_card(card)}"
            if len(candidate) > 4096 and message != header:
                messages.append(message)
                message = f"{header}\n{price_drop_card(card)}"
            else:
                message = candidate
        messages.append(message)
    return messages


def price_drop_message(row: dict) -> str:
    return price_drop_messages([row])[0]


def send_price_drop_alerts(variations: pd.DataFrame, token: str | None, chat_id: str | None) -> int:
    if not token or not chat_id:
        print("Alertas Telegram omitidas: falta TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID.")
        return 0

    sent = 0
    drops = variations.loc[(variations["status"] == "Bajo precio") & (variations["change_amount"] < -MINIMUM_PRICE_DROP)]
    for message in price_drop_messages(drops.to_dict("records")):
        last_error = None
        for delay in RETRY_DELAYS_SECONDS:
            if delay:
                time.sleep(delay)
            try:
                send_message(token, chat_id, message)
                sent += 1
                time.sleep(0.05)
                break
            except Exception as error:
                last_error = error
        else:
            raise RuntimeError("No se pudo enviar la alerta de Telegram.") from last_error
    return sent
