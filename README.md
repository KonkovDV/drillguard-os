# DrillGuard OS

Локальная рекомендательная система скрининга **кандидатов** на осложнения при бурении  
(направление INDUSTRIX: **Бурение и внутрискважинные работы**).

| | |
|---|---|
| **Версия** | **0.2.2** |
| **Направление** | Бурение и внутрискважинные работы |
| **Статус доказательной базы** | `synthetic_only` · `requires_field_validation` |
| **Уровень готовности (самооценка)** | **УТГ 4 / TRL 4** — программный прототип и воспроизводимый расчётный контур (**не** полевая валидация) |
| **Соответствие заявке** | Сопроводительное письмо INDUSTRIX 2026 ↔ код/docs ([`docs/INDUSTRIX_APPLICATION_SYNC.md`](docs/INDUSTRIX_APPLICATION_SYNC.md)) |
| **Лицензия** | Apache-2.0 |
| **Репозиторий** | [KonkovDV/drillguard-os](https://github.com/KonkovDV/drillguard-os) |

Проект относится к цифровизации процессов строительства и ремонта скважин: выявлению возможных осложнений при бурении и снижению времени первичной инженерной проверки.

DrillGuard OS анализирует временные ряды буровых параметров и формирует для инженера понятную **карточку события**: какой сигнал отклоняется, в каком режиме это происходит, какие данные подтверждают вывод, что необходимо проверить (`explanation`, `optional_context`).

### Жёсткие ограничения (обязательно читать)

Система:

- **не** управляет буровой;
- **не** передаёт команды в АСУ ТП / SCADA / системы диспетчерского управления;
- **не** является системой противоаварийной защиты (ПАЗ / SIL);
- **не** заменяет инженера;
- **не** подтверждает наличие аварии, проявления, поглощения или прихвата.

Текущая версия проверена **только на синтетических данных**. Результаты demo/benchmark **не** являются полевой валидацией и **не** подтверждают промышленную точность, экономический эффект или готовность к автономной эксплуатации.

`heuristic_score` / `rule_score` / `screening_score` отражают силу срабатывания правил и **не являются вероятностью события**.

---

## Производственная задача

При бурении инженер одновременно работает с давлением на стояке, расходом бурового раствора, нагрузкой на крюке, крутящим моментом, скоростью проходки, глубиной, режимом насосов и текущей операцией.

Изменение этих параметров может быть связано с:

- возможным осложнением;
- сменой режима работы;
- коротким переходным процессом;
- шумом;
- пропуском или неисправностью измерительного канала.

Разрозненные или противоречивые сигналы увеличивают время ручного сопоставления. DrillGuard OS **не заменяет** технологическое решение, а помогает определить, какое отклонение требует внимания и какие данные необходимо проверить.

### Пользователи решения

- инженер по бурению;
- буровой мастер;
- специалист по сопровождению строительства скважины;
- диспетчер бурения;
- специалист по буровым растворам;
- руководитель программы бурения.

---

## Входные данные

### Минимальный набор (`REQUIRED_COLUMNS`)

| Канал | Колонка |
|---|---|
| время измерения | `timestamp` |
| глубина | `depth_m` |
| давление на стояке | `standpipe_pressure_kpa` |
| расход бурового раствора (вход) | `pump_flow_lpm` |
| нагрузка на крюке | `hookload_kn` |
| крутящий момент | `torque_knm` |
| скорость проходки | `rate_of_penetration_m_h` |
| обороты насосов | `pump_rpm` |
| текущая операция | `operation` |
| признаки качества данных | `data_quality` |

### Дополнительно при наличии (`OPTIONAL_COLUMNS`)

| Канал (письмо) | Колонка |
|---|---|
| расход на выходе | `flow_out_lpm` |
| объём в ёмкости | `pit_volume_m3` |
| плотность раствора | `mud_density_sg` |
| реология | `plastic_viscosity_cp`, `yield_point_pa` |
| температура | `temperature_c` |
| содержание шлама | `cuttings_load_pct` |
| сведения о работе оборудования | `equipment_status` |
| суточный рапорт (ссылка) | `daily_report_ref` |
| действующие тревоги | `active_alarms` |
| комментарий инженера | `engineer_comment` |

Текстовые опциональные поля попадают в `optional_context` карточки для разбора; они **не** подтверждают осложнение сами по себе.  
Словарь: [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md).

---

## Принцип работы

```text
схема и качество → время → режим → причинная базовая линия
  → отклонения и согласованность → persistence / гистерезис
  → класс кандидата → карточка (explanation + optional_context)
  → архив → read-only shadow mode
```

1. Проверяются схема данных, временная шкала, единицы, пропуски и качество каналов.
2. Определяется текущий режим операции.
3. Строится **причинная** базовая линия только по уже полученным данным (без future leakage; freeze на кандидате).
4. Рассчитываются отклонения давления, расхода, нагрузки, момента и скорости проходки.
5. Проверяется согласованность сигналов; gap/desync блокируют качество (sticky desync).
6. Учитываются длительность и устойчивость (persistence, `min_points`, гистерезис); кандидаты **не** склеиваются через quality holes.
7. Смена операции, короткий выброс и недостаток истории отделяются от возможного осложнения.
8. Формируется карточка: сигнал, режим, ограничения, рекомендуемая проверка, `explanation`.

Пакет: `schema` → `ingestion` → `timebase` → `quality` → `regimes` → `baseline` → `features` → `persistence` → `detector` → `events` / `explain` → `report` (+ `cli`, `api`, `dashboard`, `synthetic`).

### Классы результатов (письмо ↔ код)

| `EventClass` | Формулировка письма / display |
|---|---|
| `possible_packoff` | кандидат на ухудшение очистки ствола или ограничение циркуляции |
| `possible_lost_circulation` | кандидат на поглощение (**не** подтверждение объёма) |
| `possible_influx_candidate` | сигнал, похожий на проявление (**не** диагностика) |
| `torque_drag_anomaly` | аномалия крутящего момента и нагрузки |
| `sensor_quality_issue` | проблема качества измерений |
| `operation_change` | смена операции |
| `short_transient` | короткий выброс |
| `insufficient_history` | недостаток истории для базовой линии |
| `signal_conflict` | конфликт режима и сигналов |
| `normal_noise` / `none` | отклонение в зоне шума / нет события |

Без pit volume, flow-out и экспертной проверки influx-like остаётся только кандидатом. Карта `event_class_letter_ru` — в `schema_manifest()`.

---

## Версия 0.2.2 — что реализовано

- проверка входа и качества каналов (в т.ч. опциональные numeric ranges);
- временная шкала, режимы, **причинная** базовая линия + freeze на кандидате;
- persistence / гистерезис / `min_points`; защита от bridging через quality holes;
- sticky desync (не эскалирует в packoff после latch);
- Level A / B / C метрики; demotion appearance-rate;
- объяснимые карточки: `explanation`, `optional_context`, `well_control_overclaim`;
- CLI: `demo` · `screen` · `dashboard` · `benchmark` · `schema`;
- локальный API read-only (`python -m drillguard.api`) + origin allowlist;
- синтетический генератор, pytest + CI, JSON/HTML отчёты;
- выравнивание под сопроводительное письмо INDUSTRIX 2026;
- red-team hardening (см. [`docs/AUDIT_REDTEAM_2026_07_24.md`](docs/AUDIT_REDTEAM_2026_07_24.md)).

### Доказательная база (SSOT)

Источник чисел: [`artifacts/CLAIMS_MANIFEST.json`](artifacts/CLAIMS_MANIFEST.json) · сверка: [`docs/EVIDENCE_SYNC.md`](docs/EVIDENCE_SYNC.md).

| Показатель | Значение |
|---|---|
| Автотесты (pytest) | **53** |
| Синтетические случаи | **50** (10 сценариев × 5 seeds) |
| Red-team probes | **12** (из них **11** hard gates) |
| Claim level | `synthetic_only` |
| Полевая валидация | **не выполнена** |
| УТГ / TRL (самооценка) | **4** — только прототип / синтетический контур |

Отдельно проверены: причинность baseline; `normal` FA gate; short_transient без эскалации; ballooning / influx без well-control overclaim; согласованность артефактов.

### Метрики (важно)

**Не** используйте appearance rate / `compat_*` как KPI готовности.

**Первичны:** Level A F1 / precision / recall / delay / FA/h; Level B interval-hit / no-escalation; Level C поток и качество.  
`false_alarms_per_hour` = **строки** Level-A FA в час (см. `false_alarms_per_hour_definition` в артефактах).

---

## Практическая ценность

Целевой эффект — **гипотеза** относительно базы заказчика: быстрее разбор сигналов, раньше фиксация устойчивого отклонения, воспроизводимость оценки, отделение quality от осложнений, единая карточка, локальная обработка **без** управляющего воздействия.

Конкретное сокращение НПВ, число осложнений и денежный эффект **заранее не заявляются**.

---

## Сотрудничество и пилот

Последовательность: архив → каналы/единицы → разметка операций → экспертная разметка → сравнение с тревогами → пороги на history → temporal holdout → read-only → журнал карточек → решение stop/go.

**Первый этап — архивная проверка**, не подключение к управлению. Затем возможен локальный **shadow mode** (`data_origin=shadow_mode`): без записи в АСУ, без команд, с оценкой карточек инженером.

План: [`docs/PILOT_PLAN.md`](docs/PILOT_PLAN.md) · валидация: [`docs/VALIDATION_PROTOCOL.md`](docs/VALIDATION_PROTOCOL.md).

---

## Быстрый старт

```bash
pip install -e ".[dev]"
pytest -q
python -m drillguard.cli demo --scenario packoff --html artifacts/demo_report.html
python -m drillguard.cli benchmark --output artifacts/benchmark_results.json
python -m benchmark.run_redteam
python -m drillguard.cli schema   # манифест схемы + УТГ4 + letter map
```

```bash
# API (read-only, localhost)
pip install -e ".[api]"
python -m drillguard.api
# → http://127.0.0.1:8000/health  ·  POST /screen

# Dashboard
pip install -e ".[dashboard]"
python -m drillguard.cli dashboard --scenario packoff --html artifacts/dashboard.html
python -m drillguard.cli dashboard --csv path/to/series.csv --html artifacts/dashboard.html
```

### Проверка опубликованных артефактов

При кэше браузера — hard-refresh или raw:

- [commits/main](https://github.com/KonkovDV/drillguard-os/commits/main)
- [CLAIMS_MANIFEST.json](https://raw.githubusercontent.com/KonkovDV/drillguard-os/main/artifacts/CLAIMS_MANIFEST.json)
- [benchmark_results.json](https://raw.githubusercontent.com/KonkovDV/drillguard-os/main/artifacts/benchmark_results.json)
- [redteam_results.json](https://raw.githubusercontent.com/KonkovDV/drillguard-os/main/artifacts/redteam_results.json)

---

## Документация

| Документ | Содержание |
|---|---|
| [`docs/INDUSTRIX_APPLICATION_SYNC.md`](docs/INDUSTRIX_APPLICATION_SYNC.md) | письмо INDUSTRIX ↔ репозиторий |
| [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) | ограничения и запрещённые заявления |
| [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md) | словарь каналов |
| [`docs/PHYSICS_AND_ASSUMPTIONS.md`](docs/PHYSICS_AND_ASSUMPTIONS.md) | физические допущения |
| [`docs/VALIDATION_PROTOCOL.md`](docs/VALIDATION_PROTOCOL.md) | протокол архивной/полевой проверки |
| [`docs/PILOT_PLAN.md`](docs/PILOT_PLAN.md) | пилот / shadow mode |
| [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md) | модель угроз |
| [`docs/EVIDENCE_SYNC.md`](docs/EVIDENCE_SYNC.md) | claims ↔ артефакты |
| [`docs/AUDIT_REDTEAM_2026_07_24.md`](docs/AUDIT_REDTEAM_2026_07_24.md) | red-team аудит |
| [`docs/CHANGELOG.md`](docs/CHANGELOG.md) · [`RELEASE_NOTES_v0.2.2.md`](RELEASE_NOTES_v0.2.2.md) | изменения |
| [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md) | чеклист релиза |
| [`docs/REFERENCES.md`](docs/REFERENCES.md) | ссылки |

---

## Цель участия в INDUSTRIX

Проверить инженерную гипотезу **на данных владельца объекта**: сохраняется ли полезность объяснимой карточки при реальных режимах, качестве измерений и переходных процессах. Решение о доработке или контролируемом испытании — только после архивной проверки и теневого режима.

---

## Лицензия

Apache-2.0 — полный текст в [`LICENSE`](LICENSE).
