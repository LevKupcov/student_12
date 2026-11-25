# Прозрачная вакансия (КАНТКОД)

Прототип: забирает вакансии Калининградской области (регион 39) с портала «Работа в России» и строит JSON-отчёт о том, насколько понятно описаны условия работы. План работ — в [PLAN.md](PLAN.md).

## Быстрый старт (Python 3.11+, зависимостей нет)
```bash
python -m unittest discover -s tests -v                     # тесты
python main.py check --input data/sample_api_response.json \
       --output reports/sample_report.json                  # проверочный режим, без сети
python main.py run                                          # рабочий режим: API региона 39
python main.py run --ai                                     # с ИИ-анализом
```
Точка входа обработки: `main.py` (workflow: `.github/workflows/report.yml`).

## Настройки
`config.json`: `source_url`, `schedule_cron` (расписание зашито в workflow), `max_vacancies`, `page_size`, `timeout_sec`. Переопределяются переменными `SOURCE_URL`, `MAX_VACANCIES`.

## ИИ
Шаг ИИ: `transparent_vacancy/ai.py` — модель ищет неоднозначности и противоречия в тексте обязанностей, требований, графика, оплаты; результат добавляется в массив замечаний с `detected_by: "ai"`. Цитаты, которых нет дословно в исходном поле, отбрасываются (антигаллюцинационная проверка).
Любой OpenAI-совместимый endpoint. Без аккаунта — локально через [Ollama](https://ollama.com):
```bash
ollama pull qwen2.5:3b
cp .env.example .env   # затем: export $(grep -v '^#' .env | xargs)   (Linux/macOS; в Windows задайте переменные через set)
python main.py check --input data/sample_api_response.json --ai
```
> TODO: зафиксировать выбранную модель/провайдера после прогона (этап 3 плана).

## Источник данных
`offset` в API региона 39 — номер страницы (проверено на живом API: страницы не пересекаются). Портал нестабилен и периодически отдаёт HTTP 500 — `fetch.py` делает до 3 попыток с паузой. Минимум `min_pages` страниц обрабатывается, если объём данных позволяет; вакансии дедуплицируются по ID в том числе между страницами. В реальных данных ~30% вакансий приходят без поля `employment` — это подлинные пропуски источника, они попадают в отчёт как замечания.

## Формат отчёта
```json
{"generated_at": "...", "source": "...", "ai_enabled": true, "ai_errors": 0,
 "stats": {"vacancies": 5, "with_issues": 3, "issues_total": 11, "by_topic": {}},
 "vacancies": [{"id": "...", "url": "...", "title": "...",
   "issues": [{"topic": "schedule|title|duties|requirements|salary|workplace|employment",
               "field": "поле источника", "quote": "цитата или пусто для пропуска",
               "type": "missing|ambiguous|contradiction", "quote_2": "второе значение (противоречие)",
               "problem": "суть", "recommendation": "что уточнить", "detected_by": "rules|ai"}]}]}
```
Нет замечаний — `"issues": []`. Один объект на ID вакансии.

## Ошибки источника
Если API недоступен, процесс завершается с кодом 2 и сообщением; файл последнего успешного отчёта не перезаписывается (запись атомарная).

## Команда

**Live.Long.ClaudeCode**

Участники:
- Ховаев Георгий Евгеньевич
- Купцов Лев Андреевич
- Силинский Матвей Андреевич
- Вершинина Елизавета Сергеевна
- Камчиев Даниэль Алтынбекович
