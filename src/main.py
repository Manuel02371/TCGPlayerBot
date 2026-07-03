import sys
from datetime import datetime

from src.config import (
    DASHBOARD_DIR,
    DASHBOARD_HTML,
    GENERATE_DASHBOARD,
    GENERATE_REPORT,
    HEADLESS,
    INPUT_FILE,
    LOG_DIR,
    OUTPUT_DIR,
    OUTPUT_PARQUET,
    REPORTS_DIR,
)
from src.dashboard import generate_dashboard_html
from src.input_loader import load_input_excel
from src.logger import setup_logging
from src.parquet_store import append_to_parquet
from src.reporting import generate_latest_report
from src.scraper import run_scraping
from src.transformer import add_execution_metadata


def _rel(path) -> str:
    return str(path.relative_to(INPUT_FILE.parents[1]))


def _print_header(rows_read: int, rows_active: int) -> None:
    print("=" * 40)
    print("INICIO PROCESO SCRAPING")
    print("=" * 40)
    print(f"Modo navegador: {'HEADLESS' if HEADLESS else 'VISIBLE'}")
    print(f"Input: {_rel(INPUT_FILE)}")
    print(f"Output historico: {_rel(OUTPUT_PARQUET)}")
    print(f"Filas leidas: {rows_read}")
    print(f"Filas activas: {rows_active}")
    print()


def _print_summary(df_output, added_count: int) -> None:
    counts = df_output["estado_scraping"].value_counts()
    print()
    print("=" * 40)
    print("SCRAPING FINALIZADO")
    print("=" * 40)
    print(f"Registros OK: {int(counts.get('OK', 0))}")
    print(f"Sin resultado: {int(counts.get('SIN_RESULTADO', 0))}")
    print(f"Errores: {int(counts.get('ERROR', 0))}")
    print(f"Registros agregados al historico: {added_count}")
    print("Archivo Parquet actualizado correctamente.")


def _print_report_summary(summary: dict, excel_path, dashboard_path) -> None:
    print()
    print("=" * 40)
    print("REPORTE DE VARIACIONES")
    print("=" * 40)
    print(f"Bajaron: {summary.get('cantidad_bajaron', 0)}")
    print(f"Subieron: {summary.get('cantidad_subieron', 0)}")
    print(f"Igual: {summary.get('cantidad_igual', 0)}")
    print(f"Nuevos: {summary.get('cantidad_nuevos', 0)}")
    print(f"Errores: {summary.get('cantidad_error', 0)}")
    print(f"Buenas oportunidades: {summary.get('mejores_oportunidades', 0)}")
    print()
    print(f"Reporte Excel: {_rel(excel_path)}")
    if dashboard_path:
        print(f"Dashboard: {_rel(dashboard_path)}")
    print("=" * 40)


def main() -> int:
    logger = setup_logging()
    for folder in [OUTPUT_DIR, LOG_DIR, REPORTS_DIR, DASHBOARD_DIR]:
        folder.mkdir(parents=True, exist_ok=True)

    try:
        df_input = load_input_excel()
        rows_read = df_input.attrs.get("rows_read", len(df_input))
        rows_active = df_input.attrs.get("rows_active", len(df_input))
        _print_header(rows_read, rows_active)

        if df_input.empty:
            raise ValueError("No hay filas activas para procesar.")

        logger.info("Inicio scraping | filas_leidas=%s | filas_activas=%s", rows_read, rows_active)
        df_raw = run_scraping(df_input)
        if df_raw.empty:
            raise ValueError("El scraping no genero registros de salida.")

        df_output = add_execution_metadata(df_raw, datetime.now(), INPUT_FILE.name)
        added_count, total_count = append_to_parquet(df_output)
        logger.info("Parquet actualizado | nuevos=%s | total=%s", added_count, total_count)
        _print_summary(df_output, added_count)

        if GENERATE_REPORT:
            detail, summary, paths = generate_latest_report()
            dashboard_path = None
            if GENERATE_DASHBOARD:
                dashboard_path = generate_dashboard_html(detail, summary, DASHBOARD_HTML, paths[0])
            logger.info("Reporte generado | excel=%s | dashboard=%s", paths[0], dashboard_path)
            _print_report_summary(summary, paths[0], dashboard_path)

        return 0
    except Exception as exc:
        logger.exception("Proceso detenido: %s", exc)
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
