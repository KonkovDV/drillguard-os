# DrillGuard OS

Локальная **рекомендательная** система скрининга **кандидатов** на осложнения при бурении по гидравлическим и механическим сигналам.

**Версия:** 0.2.0 · **Статус:** воспроизводимый синтетический демонстратор (GitHub-ready).  
**Не является** системой противоаварийной защиты, не управляет буровой, не пишет в АСУ ТП/SCADA, не заменяет инженера и **не заявляет полевую точность**.

Результаты demo/benchmark помечены как `synthetic` / `requires_field_validation`, пока нет архива заказчика и разметки эксперта.

## Что делает

1. Проверяет схему и качество входных данных  
2. Строит временную базу (сортировка, дубликаты, частота, пропуски)  
3. Определяет режим операции и окно адаптации  
4. Считает **причинную** режимную базовую линию (только прошлое; freeze при кандидате)  
5. Формирует наблюдаемые и физически мотивированные признаки  
6. Подтверждает устойчивые отклонения (persistence / hysteresis / cooldown)  
7. Выдаёт объяснимую карточку события с `heuristic_score` (**не вероятность**)

### Классы v0.2

| Класс | Смысл |
|-------|--------|
| `possible_packoff` | Кандидат на ухудшение очистки / закупорку |
| `possible_lost_circulation` | Кандидат на поглощение |
| `possible_influx` | Кандидат на проявление (**неполон без pit/flow-out**) |
| `torque_drag_anomaly` | Аномалия момента/нагрузки (упрощённый индекс, не 4DOF T&D) |
| `sensor_quality_issue` | Проблема качества измерений |
| `operation_change` | Смена операции (не осложнение) |
| `short_transient` | Короткий выброс |
| `normal_noise` / `insufficient_history` / `none` | Наблюдение / прогрев / нет события |
| `signal_conflict` | Конфликт режима и сигналов |

## Быстрый старт

```bash
pip install -e ".[dev]"
python -m drillguard.cli demo --scenario packoff --output artifacts/demo_report.json --html artifacts/demo_report.html
python -m drillguard.cli benchmark --output artifacts/benchmark_results.json
python -m benchmark.run_redteam
pytest -q
```

API (локально, read-only):

```bash
pip install -e ".[api]"
uvicorn drillguard.api:create_app --factory --port 8000
```

Dashboard HTML:

```bash
pip install -e ".[dashboard]"
python -c "from drillguard.dashboard import run_demo; print(run_demo())"
```

## Документация

- [DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md)
- [PHYSICS_AND_ASSUMPTIONS.md](docs/PHYSICS_AND_ASSUMPTIONS.md)
- [INDUSTRIX_APPLICATION_SYNC.md](docs/INDUSTRIX_APPLICATION_SYNC.md)
- [PILOT_PLAN.md](docs/PILOT_PLAN.md)
- [LIMITATIONS.md](docs/LIMITATIONS.md)
- [VALIDATION_PROTOCOL.md](docs/VALIDATION_PROTOCOL.md)
- [THREAT_MODEL.md](docs/THREAT_MODEL.md)
- [REFERENCES.md](docs/REFERENCES.md)
- [CHANGELOG.md](docs/CHANGELOG.md)

## INDUSTRIX

Рекомендуемое направление: бурение и внутрискважинные работы → цифровизация строительства/ремонта скважин.  
Пилот: архив → shadow mode → memo. KPI согласуются **до** работ. Эффект — **гипотеза** до проверки.

## Лицензия

Apache-2.0
