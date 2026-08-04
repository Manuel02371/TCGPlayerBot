import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd

from src.scraper import card_from_anchor, catalog_url, wait_for_catalog_change
from src.storage import append_history, find_new_or_lower, observation_key
from src.telegram import job_finished_message, job_started_message, price_drop_messages, send_price_drop_alerts


class StorageTest(unittest.TestCase):
    def test_telegram_job_messages_show_start_and_final_summary(self) -> None:
        variations = pd.DataFrame([
            {"status": "Bajo precio"},
            {"status": "Bajo precio"},
            {"status": "Nueva carta"},
        ])

        start = job_started_message(7)
        finish = job_finished_message(variations)
        empty_finish = job_finished_message(pd.DataFrame(columns=["status"]))

        self.assertIn("Iniciando consulta MasterSet", start)
        self.assertIn("Revisando 7 expansiones", start)
        self.assertIn("Consulta finalizada", finish)
        self.assertIn("2 bajas", finish)
        self.assertIn("1 carta nueva", finish)
        self.assertIn("sin cambios esta vez", empty_finish)

    def test_telegram_alerts_group_price_drops_by_expansion(self) -> None:
        variations = pd.DataFrame([
            {"status": "Bajo precio", "card_name": "Mew ex", "expansion": "Destined Rivals", "card_number": "231/182", "previous_market_price": 20.0, "market_price": 18.99, "change_amount": -1.01, "change_percent": -0.0505, "card_url": "https://masterset.pe/card/1"},
            {"status": "Bajo precio", "card_name": "Charizard ex", "expansion": "Destined Rivals", "card_number": "125/182", "previous_market_price": 20.0, "market_price": 18.50, "change_amount": -1.5, "change_percent": -0.075, "card_url": "https://masterset.pe/card/2"},
            {"status": "Bajo precio", "card_name": "Pikachu ex", "expansion": "Mega Evolution", "card_number": "101/132", "previous_market_price": 15.0, "market_price": 13.0, "change_amount": -2.0, "change_percent": -0.1333, "card_url": "https://masterset.pe/card/3"},
            {"status": "Nueva carta", "card_name": "Pikachu", "market_price": 10.0},
        ])
        with patch("src.telegram.send_message") as send:
            sent = send_price_drop_alerts(variations, "token", "123")

        self.assertEqual((sent, send.call_count), (2, 2))
        self.assertIn("S/ 20.00", send.call_args_list[0].args[2])
        self.assertIn("━━━━━━━━", send.call_args.args[2])
        self.assertIn("https://masterset.pe/card/1", send.call_args_list[0].args[2])
        self.assertIn("Charizard ex 125/182", send.call_args_list[0].args[2])
        self.assertIn("Mega Evolution", send.call_args_list[1].args[2])

    def test_telegram_group_messages_split_before_telegram_limit(self) -> None:
        rows = [{"card_name": f"Carta {index}", "expansion": "Destined Rivals", "card_number": str(index), "previous_market_price": 20.0, "market_price": 18.0, "change_amount": -2.0, "card_url": "https://masterset.pe/card/1"} for index in range(100)]

        messages = price_drop_messages(rows)

        self.assertGreater(len(messages), 1)
        self.assertTrue(all(len(message) <= 4096 for message in messages))

    def test_page_change_retries_after_2_5_and_10_seconds(self) -> None:
        class Page:
            def __init__(self) -> None:
                self.attempts, self.waits, self.clicks = 0, [], 0

            def wait_for_function(self, *_args, **_kwargs) -> None:
                self.attempts += 1
                if self.attempts < 4:
                    raise RuntimeError("La página aún no cambió")

            def wait_for_timeout(self, milliseconds: int) -> None:
                self.waits.append(milliseconds)

            def click_next(self) -> None:
                self.clicks += 1

        page = Page()
        wait_for_catalog_change(page, ("/card/1",), 30_000, page.click_next)

        self.assertEqual((page.attempts, page.waits, page.clicks), (4, [2_000, 5_000, 10_000], 3))

    def test_catalog_url_and_same_day_deduplication_key(self) -> None:
        self.assertIn("Destined%20Rivals", catalog_url("Destined Rivals"))
        row = {"expansion": "Destined Rivals", "card_name": "Mew", "card_number": "1/2", "language": "English", "card_url": "https://masterset.pe/card/1", "execution_date": "2026-07-30", "seller_count": 1, "price_from": 3.5, "market_price": 4.0}
        repeated_run = row | {"execution_id": "otra-ejecucion"}
        row["execution_id"] = "primera-ejecucion"
        self.assertNotEqual(observation_key(row), observation_key(repeated_run))

    def test_visible_catalog_card_is_normalized(self) -> None:
        anchor = {"href": "/card/1", "alt": "Mew ex 231/182", "text": "sv10 \u00b7 Destined Rivals\nMew ex 231/182\nEnglish\n2 desde\nS/ 2,150.00\nMercado: S/ 2,625.00"}
        result = card_from_anchor(anchor, "Destined Rivals", "https://masterset.pe/catalog")
        self.assertEqual((result["expansion_code"], result["card_number"], result["seller_count"]), ("SV10", "231/182", 2))

    def test_history_keeps_the_same_card_from_two_executions(self) -> None:
        base = {"expansion": "Destined Rivals", "card_name": "Skuntank", "card_number": "1/2", "language": "English", "card_url": "https://masterset.pe/card/1", "execution_date": "2026-07-30", "seller_count": 1, "price_from": 3.5, "market_price": 4.0}
        with TemporaryDirectory() as directory:
            path = Path(directory) / "history.parquet"
            append_history([base | {"execution_id": "run-1", "extracted_at": "2026-07-30T10:00:00-05:00"}], path)
            result = append_history([base | {"execution_id": "run-2", "extracted_at": "2026-07-30T11:00:00-05:00"}], path)
        self.assertEqual(len(result), 2)

    def test_variations_include_new_cards_and_price_drops(self) -> None:
        old = {"expansion": "Set", "card_name": "Old", "card_number": "1", "language": "English", "card_url": "https://card/1", "market_price": 10, "execution_id": "old", "extracted_at": "2026-07-30T10:00:00-05:00"}
        current = [old | {"market_price": 8, "execution_id": "now", "extracted_at": "2026-07-30T11:00:00-05:00"},
                   {"expansion": "Set", "card_name": "New", "card_number": "2", "language": "English", "card_url": "https://card/2", "market_price": 5}]
        result = find_new_or_lower(current, __import__("pandas").DataFrame([old]))
        self.assertEqual(set(result["status"]), {"Bajo precio", "Nueva carta"})
