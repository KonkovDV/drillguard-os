# DrillGuard OS

Локальная **рекомендательная** система скрининга **кандидатов** на осложнения при бурении.

**Версия:** 0.2.1 · **Статус:** воспроизводимый **синтетический** демонстратор.  
**Не является** ПАЗ / well-control системой, не управляет буровой, не пишет в АСУ ТП/SCADA, не заменяет инженера и **не заявляет полевую точность**.

Результаты demo/benchmark: `synthetic_only` + `requires_field_validation`.

## Главный принцип

сигналы → качество → время → режим → **причинная** базовая линия → признаки → persistence → класс кандидата → карточка → архив → read-only shadow mode.

## Метрики (важно)

**Не используйте** rate появления класса / `compat_appearance_rate` как главный KPI.  
Первичны: **Level A** F1 / precision / recall / detection delay / FA/h для осложнений; **Level B** interval-hit для `operation_change` и no-escalation для `short_transient`; **Level C** поток и quality.

`heuristic_score` / `rule_score` / `screening_score` — **не вероятность**.

`possible_influx_candidate` — **не** диагностика проявления без pit volume / flow-out.

## Быстрый старт

```bash
pip install -e ".[dev]"
pytest -q
python -m drillguard.cli demo --scenario packoff --html artifacts/demo_report.html
python -m drillguard.cli benchmark --output artifacts/benchmark_results.json
python -m benchmark.run_redteam
```

## Документы

`docs/AUDIT_2026_07_23.md` · `DATA_DICTIONARY` · `PHYSICS_AND_ASSUMPTIONS` · `LIMITATIONS` · `VALIDATION_PROTOCOL` · `PILOT_PLAN` · `INDUSTRIX_APPLICATION_SYNC` · `THREAT_MODEL` · `REFERENCES` · `CHANGELOG` · `RELEASE_CHECKLIST`

## Лицензия

Apache-2.0 (полный текст в `LICENSE`)
