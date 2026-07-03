import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.input_loader import load_input_excel
from src.parquet_store import append_to_parquet, read_existing_parquet
from src.reporting import build_summary, compare_prices, generate_report_files
from src.transformer import add_execution_metadata, build_item_key


class BasicFlowTest(unittest.TestCase):
    def test_load_input_filters_active_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.xlsx"
            pd.DataFrame(
                [
                    {"Set Slug": "sv09-journey-together", "Set Name": "sv09-journey-together", "Activo": "SI"},
                    {"Set Slug": "me01-mega-evolution", "Set Name": "me01-mega-evolution", "Activo": "NO"},
                ]
            ).to_excel(path, index=False)

            df = load_input_excel(path)

            self.assertEqual(len(df), 1)
            self.assertEqual(df.attrs["rows_read"], 2)
            self.assertEqual(df.iloc[0]["set_slug"], "sv09-journey-together")

    def test_parquet_append_is_cumulative_and_dedupes_exact_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "historico.parquet"
            timestamp = datetime(2026, 7, 3, 12, 30, 0)
            raw = pd.DataFrame(
                [
                    {
                        "set_slug": "sv09-journey-together",
                        "set_name": "sv09-journey-together",
                        "estado_scraping": "OK",
                        "market_price_usd": "12.90",
                    }
                ]
            )
            output = add_execution_metadata(raw, timestamp, "input.xlsx")

            first_added, first_total = append_to_parquet(output, path)
            second_added, second_total = append_to_parquet(output, path)
            saved = read_existing_parquet(path)

            self.assertEqual((first_added, first_total), (1, 1))
            self.assertEqual((second_added, second_total), (0, 1))
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved.iloc[0]["timestamp_ejecucion"], "2026-07-03 12:30:00")

    def test_report_classifies_price_drop_and_opportunity(self):
        previous = pd.DataFrame(
            [
                {
                    "expansion": "SV09",
                    "rareza": "Double Rare",
                    "nombre_carta": "Pikachu ex",
                    "numero_carta": "001/100",
                    "market_price_usd": 10,
                    "precio_referencia": 15,
                    "estado_scraping": "OK",
                    "timestamp_ejecucion": "2026-07-03 10:00:00",
                }
            ]
        )
        latest = previous.copy()
        latest["market_price_usd"] = 8
        latest["timestamp_ejecucion"] = "2026-07-03 11:00:00"

        detail = compare_prices(latest, previous)
        summary = build_summary(detail)

        self.assertEqual(detail.iloc[0]["estado_variacion"], "BAJO")
        self.assertEqual(detail.iloc[0]["clasificacion_oportunidad"], "MUY_BUENA_OPORTUNIDAD")
        self.assertEqual(summary["cantidad_bajaron"], 1)
        self.assertEqual(summary["mejores_oportunidades"], 1)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            paths = generate_report_files(
                detail,
                summary,
                tmp_path / "reporte.xlsx",
                tmp_path / "reporte.csv",
                tmp_path / "resumen.json",
            )
            for path in paths:
                self.assertTrue(path.exists())

    def test_item_key_uses_input_fallback_for_error_rows(self):
        df = pd.DataFrame(
            [
                {"set_slug": "set-a", "set_name": "set-a", "estado_scraping": "ERROR"},
                {"set_slug": "set-b", "set_name": "set-b", "estado_scraping": "ERROR"},
            ]
        )

        keys = build_item_key(df).tolist()

        self.assertEqual(keys, ["input|set-a|set-a|", "input|set-b|set-b|"])


if __name__ == "__main__":
    unittest.main()
