"""CLI. Рабочий режим:  python main.py run [--ai]
Проверочный режим:     python main.py check --input data/sample_api_response.json --output reports/sample_report.json [--ai]"""
import argparse
import json
import os
import sys

from transparent_vacancy.fetch import FetchError, fetch_vacancies
from transparent_vacancy.report import build_report, save_atomic


def load_cfg(path):
    cfg = json.load(open(path, encoding="utf-8"))
    cfg["source_url"] = os.environ.get("SOURCE_URL", cfg["source_url"])
    cfg["max_vacancies"] = int(os.environ.get("MAX_VACANCIES", cfg["max_vacancies"]))
    return cfg


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["run", "check"])
    p.add_argument("--config", default="config.json")
    p.add_argument("--input")
    p.add_argument("--output")
    p.add_argument("--ai", action="store_true", help="включить ИИ-анализ (нужна LLM, см. .env.example)")
    a = p.parse_args()
    cfg = load_cfg(a.config)
    if a.mode == "check":
        if not a.input:
            p.error("--input обязателен в режиме check")
        data = json.load(open(a.input, encoding="utf-8"))
        items = (data.get("results") or {}).get("vacancies") or []
        out = a.output or os.path.join(cfg["output_dir"], "check_report.json")
        save_atomic(build_report(items, cfg, a.ai, source=a.input), out)
    else:
        out = a.output or os.path.join(cfg["output_dir"], "latest.json")
        try:
            items = fetch_vacancies(cfg)
        except FetchError as e:
            print(f"ОШИБКА источника: {e}", file=sys.stderr)
            print("Последний успешный отчёт сохранён." if os.path.exists(out) else "Предыдущего отчёта нет.", file=sys.stderr)
            sys.exit(2)
        save_atomic(build_report(items, cfg, a.ai, source=cfg["source_url"]), out)
    print("Отчёт сохранён:", out)


if __name__ == "__main__":
    main()
