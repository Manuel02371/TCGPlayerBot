from html import escape
from pathlib import Path

import pandas as pd

from src.config import DASHBOARD_DIR, DASHBOARD_HTML, REPORT_EXCEL


def _fmt_money(value) -> str:
    return "" if pd.isna(value) else f"${float(value):,.2f}"


def _fmt_pct(value) -> str:
    return "" if pd.isna(value) else f"{float(value) * 100:.1f}%"


def _table(df: pd.DataFrame, columns: list[str], limit: int = 15) -> str:
    if df.empty:
        return "<p class=\"empty\">Sin registros.</p>"

    rows = []
    for _, row in df.head(limit).iterrows():
        cells = []
        for col in columns:
            value = row.get(col, "")
            if col.startswith("precio") or col == "margen_estimado":
                value = _fmt_money(value)
            elif col.startswith("porcentaje"):
                value = _fmt_pct(value)
            cells.append(f"<td>{escape(str(value))}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")

    headers = "".join(f"<th>{escape(col)}</th>" for col in columns)
    return f"<table><thead><tr>{headers}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def generate_dashboard_html(
    detail_df: pd.DataFrame,
    summary: dict,
    output_path: Path = DASHBOARD_HTML,
    report_excel: Path = REPORT_EXCEL,
) -> Path:
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    oportunidades = detail_df[
        detail_df["clasificacion_oportunidad"].isin(["MUY_BUENA_OPORTUNIDAD", "BUENA_OPORTUNIDAD"])
    ].sort_values("porcentaje_margen", ascending=False)
    bajaron = detail_df[detail_df["estado_variacion"].eq("BAJO")].sort_values("diferencia_precio")
    subieron = detail_df[detail_df["estado_variacion"].eq("SUBIO")].sort_values("diferencia_precio", ascending=False)
    report_link = "../reports/" + report_excel.name

    cards = [
        ("Total", summary.get("total_items", 0)),
        ("Bajaron", summary.get("cantidad_bajaron", 0)),
        ("Subieron", summary.get("cantidad_subieron", 0)),
        ("Nuevos", summary.get("cantidad_nuevos", 0)),
        ("Errores", summary.get("cantidad_error", 0)),
        ("Oportunidades", summary.get("mejores_oportunidades", 0)),
    ]
    card_html = "".join(
        f"<section class=\"card\"><span>{escape(label)}</span><strong>{value}</strong></section>"
        for label, value in cards
    )

    table_cols = [
        "nombre_carta",
        "expansion",
        "rareza",
        "precio_anterior",
        "precio_actual",
        "diferencia_precio",
        "porcentaje_margen",
        "clasificacion_oportunidad",
    ]

    html = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dashboard TCGPlayerBot</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; color: #17202a; background: #f6f7f9; }}
    header {{ background: #19324a; color: white; padding: 24px 32px; }}
    main {{ padding: 24px 32px 40px; }}
    h1 {{ margin: 0 0 8px; font-size: 26px; }}
    h2 {{ margin-top: 28px; font-size: 18px; }}
    a {{ color: #0b63ce; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }}
    .card {{ background: white; border: 1px solid #d9e1e8; border-radius: 8px; padding: 16px; }}
    .card span {{ display: block; color: #5b6773; font-size: 13px; margin-bottom: 8px; }}
    .card strong {{ font-size: 28px; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #d9e1e8; }}
    th, td {{ padding: 8px 10px; border-bottom: 1px solid #edf0f3; text-align: left; font-size: 13px; }}
    th {{ background: #eaf1f7; font-weight: 700; }}
    .empty {{ background: white; border: 1px solid #d9e1e8; padding: 12px; }}
  </style>
</head>
<body>
  <header>
    <h1>TCGPlayerBot</h1>
    <div>Ultima ejecucion: {escape(str(summary.get("fecha_ejecucion", "")))}</div>
  </header>
  <main>
    <p>Reporte Excel: <a href="{escape(report_link)}">{escape(report_excel.name)}</a></p>
    <section class="cards">{card_html}</section>
    <h2>Mejores oportunidades</h2>
    {_table(oportunidades, table_cols)}
    <h2>Precios que bajaron</h2>
    {_table(bajaron, table_cols)}
    <h2>Precios que subieron</h2>
    {_table(subieron, table_cols)}
  </main>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")
    return output_path
