# Vuelos Argentina → China (sheet helper)

Scripts y criterios para mantener la hoja [Vuelos](https://docs.google.com/spreadsheets/d/1x0uFv5uXDMSGTcMcxFyJDJyxlRunb2_ScLy5snc3pfE/edit) en Google Drive.

## Columnas de la hoja

Orden actual: **Precio**, **Origen**, **Destino**, **Fecha**, **Escala IDA**, **Escala VUELTA**, **Total Horas**, **Ida**, **Vuelta**, **Cantidad de dias de viaje**, **Link**, **Actualizado** (columna **L**).

**Fecha** unifica ida y vuelta en una celda con formato **DD-MON a DD-MON**, con el mes en tres letras en español y mayúsculas (por ejemplo `20-MAY a 14-JUN`, `15-FEB a 10-MAR`). El año sigue implícito en los links y en el parser de `trip_days.py` cuando hace falta recalcular días.

**Escala IDA** y **Escala VUELTA** cuentan las ciudades entre paréntesis en el tramo Ida o Vuelta respectivamente (`+` separa escalas). Si falta el tramo o no hay paréntesis, queda `sin dato`. Formato condicional en **E** y **F** (escalas, filas 2–238): **1** verde (`#d9ead3`), **2** amarillo (`#fff2cc`), **3** rojo (`#f4cccc`).

**Precio** (columna **A**, filas 2–238): verde **1500–1800** USD, amarillo **1800–2000**, rojo **> 2000** (mismos tonos). Tras scrape, no se escribe fila con precio **> USD 2.300**.

Rellenar celdas `sin dato` desde la fila más completa por ruta (Origen + Destino), con alias Mendoza→Tokio ← Buenos Aires→Tokio:

```bash
python3 scripts/backfill_sheet.py < sheet_export.csv > backfill_payload.json
```

Regenerar **Fecha** desde ida/vuelta separadas:

```bash
python3 scripts/merge_fecha_column.py < sheet_export.csv > payload.json
```

Regenerar columnas de escala desde un CSV exportado de la hoja:

```bash
python3 scripts/split_escalas_columns.py < sheet_current.csv > payload.json
```

## Columna **Días viaje** (ahora «Cantidad de dias de viaje»)

- Días **inclusivos** entre ida y vuelta, parseados desde la columna **Fechas** (español, año explícito).
- No confundir con **Total**, que sigue siendo la suma de horas de vuelo ida + vuelta.

Recalcular localmente:

```bash
python3 scripts/trip_days.py
```

Desde Python:

```python
from scripts.trip_days import inclusive_days, candidate_windows

inclusive_days("2 - 27 mar 2027")  # 26
candidate_windows(2027)[:5]       # mejores ventanas 25–30 días (score marzo / evitar febrero)
```

## Criterios de búsqueda de vuelos nuevos

- **Origen:** Argentina (Buenos Aires, Mendoza).
- **Destino:** China (Shanghái, Pekín).
- **Duración:** 25–30 días inclusivos (todas las combinaciones en ese rango).
- **Calendario 2027:** ida desde **01-MAR**; vuelta hasta **05-ABR** (primeros 5 días de abril). **Febrero no se considera** (eliminar de la hoja con `purge_february_from_sheet.py`; el scrape también omite esas filas).
- **Tope de precio:** no se escribe en la hoja un scrape cuyo precio ida y vuelta supere **USD 2.300** (`scripts/price_policy.py`; salida temprana en Google si el mínimo visible ya supera el tope).
- **Prioridad:** maximizar días en **marzo** (`score_window` en `trip_days.py`; ventanas nuevas solo en marzo).

Generar ventanas y filas faltantes (4 rutas × cada ventana):

```bash
python3 scripts/search_windows.py          # lista 69 ventanas de fechas
python3 scripts/append_argentina_china.py < sheet_export.csv > append.json
```

## Edición del sheet

El Cloud Agent usa los plugins MCP **Google-sheets** y **Google-drive** (OAuth en Cursor → Customize → Cloud). Sin MCP, el export CSV público del sheet solo permite lectura.

## Fuentes de precios

Los precios agregados en filas nuevas pueden provenir de agregadores (p. ej. AirHint, RatePunk) y deben confirmarse en Google Flights / Kayak antes de reservar. El backfill copia precio e itinerario de referencia por ruta cuando faltaba scraping por fecha; no sustituye una cotización en el link de esa fila.

### Pipeline de vuelos (5 pasos, bajo demanda)

Las filas de la planilla (origen, destino, fechas, link) se cargan **manualmente**. El agente **no** debe ejecutar scrape en background salvo que lo pidas.

| Paso | Módulo | Qué hace |
|------|--------|----------|
| **1** | `step1_read.py` + [`route_links.py`](scripts/route_links.py) | Lee CSV; **regenera Link** desde origen, destino y **Fecha** |
| **2** | `step2_search.py` | Scrape Playwright con URL nueva |
| **3** | `step3_filter.py` + `flight_policy.py` | Precio **≤ 2.300 USD**, **< 3 escalas** por pierna, ida/vuelta completos |
| **4** | `step4_save.py` | Actualiza variables: **Precio, escalas, Total Horas, Ida, Vuelta, Link, días, Actualizado** → JSONL `A:L` |
| **5** | `step5_purge_invalid.py` | Quita filas del CSV que sigan violando precio/escalas (+ manifiesto MCP) |

**Refresh completo** (todas las filas del CSV, links nuevos, sin estado intermedio viejo):

```cmd
run_flights.cmd --refresh-sheet
```

Equivalente: `--all --all-rows --fresh --fresh-writes --update-csv`.

**Rango acotado** (scrape + guardar; **no** purga todo el CSV — el paso 5 escanea la planilla entera):

```cmd
run_flights.cmd --all --start-row 82 --end-row 91 --fresh --no-purge
```

**Prueba / un lote de 10 desde fila 20:**

```cmd
run_flights.cmd --all --start-row 20 --end-row 29 --fresh --fresh-writes --update-csv --no-purge
```

**Refresh completo por lotes de 20** (toda la planilla, sin paso 5 en cada lote; MCP tras cada lote):

```cmd
python3 scripts/pipeline_lotes.py --batch-size 20 --start-row 2 --apply-mcp
```

- Primer lote: `--fresh --fresh-writes --update-csv`; siguientes: `--update-csv` y writes acumulados en `/tmp/flight_writes.jsonl`.
- Tras cada lote, el agente aplica MCP con `mcp_apply_pending.py --dump` → Google-sheets `write_range` → `--mark-done`.
- Al terminar todos los lotes, purga opcional: `run_flights.cmd --step 5 --dry-run` y luego `--step 5` + MCP deletes del manifiesto.

`pipeline_lotes.py` siempre pasa `--no-purge` en cada lote. Tras un refresh completo monolítico, el paso 5 corre con `--refresh-sheet`; para purgar a mano: `--step 5`.

**Solo limpiar inválidos:** `run_flights.cmd --step 5` (opcional `--dry-run`).

Salidas: `/tmp/flight_work/step*.jsonl`, `/tmp/flight_writes.jsonl` (MCP `write_range` **A:L**). Progreso: `scrape_progress.json` (`verified_rows`, `rejected_rows`, `failed_rows`).

**Actualizado:** fecha/hora de la corrida (Argentina) en cada fila guardada en paso 4.

Pedir al agente (solo si lo indicás): **P-refresh**, **P1–P5**, **P-all**, **D1**, **D2**. No scrape en background. Lotes: `pipeline_lotes.py --one-batch`.

Legacy: `pipeline/run.py scrape` → `run_flights.py --all`.
