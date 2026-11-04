#!/usr/bin/env python3
"""
Flight pipeline — 5 steps (on demand):

  1 read + refresh links   2 search   3 filter   4 save   5 purge invalid rows
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from flight_policy import MAX_PRICE_USD, MAX_STOPS_PER_LEG
from playwright_common import flight_browser, new_flight_page
from pipeline.step1_read import (
    data_row_count,
    default_row_range,
    load_requests,
    request_to_json,
)
from pipeline.step2_search import search_offer
from pipeline.step3_filter import filter_offer, status_line
from pipeline.step4_save import (
    append_jsonl,
    offer_from_dict,
    offer_to_dict,
    save_payload,
    update_csv_row,
)
from pipeline.step5_purge_invalid import purge_csv, write_purge_manifest
from run_timestamp import TZ, format_actualizado

DEFAULT_CSV = ROOT / "sheet_live.csv"
DEFAULT_WORK = Path("/tmp/flight_work")
DEFAULT_WRITES = Path("/tmp/flight_writes.jsonl")
PROGRESS = ROOT / "scripts" / "scrape_progress.json"


def load_progress() -> dict:
    if PROGRESS.exists():
        return json.loads(PROGRESS.read_text(encoding="utf-8"))
    return {
        "next_row": 2,
        "end_row": 238,
        "verified_rows": [],
        "pending_rows": [],
        "rejected_rows": {},
        "failed_rows": [],
    }


def save_progress(p: dict) -> None:
    PROGRESS.write_text(json.dumps(p, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def work_paths(work_dir: Path, step: int) -> Path:
    return work_dir / f"step{step}.jsonl"


def clear_work_dir(work_dir: Path) -> None:
    if work_dir.exists():
        for p in work_dir.glob("step*.jsonl"):
            p.unlink()
    work_dir.mkdir(parents=True, exist_ok=True)


def resolve_row_range(args: argparse.Namespace) -> None:
    if args.all_rows or args.refresh_sheet:
        start, end = default_row_range(args.csv)
        args.start_row = start
        args.end_row = end
    elif args.end_row < args.start_row:
        args.end_row = args.start_row


def ensure_run_started(args: argparse.Namespace) -> str:
    if not getattr(args, "run_started_at", None):
        args.run_started_at = format_actualizado(datetime.now(TZ))
    return args.run_started_at


def cmd_step1(args: argparse.Namespace) -> int:
    reqs = load_requests(args.csv, args.start_row, args.end_row, refresh_links=True)
    out = Path(args.jsonl_out) if args.jsonl_out else work_paths(args.work_dir, 1)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for req in reqs:
            f.write(json.dumps(request_to_json(req), ensure_ascii=False) + "\n")
    progress = load_progress()
    progress["end_row"] = default_row_range(args.csv)[1]
    progress["data_rows"] = data_row_count(args.csv)
    save_progress(progress)
    print(f"step1: {len(reqs)} rows (links refreshed) -> {out}", file=sys.stderr)
    return 0


def _read_step1(work_dir: Path, csv: Path, start: int, end: int):
    p = work_paths(work_dir, 1)
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            row = int(rec["row_num"])
            if start <= row <= end:
                yield rec
        return
    for req in load_requests(csv, start, end, refresh_links=True):
        yield request_to_json(req)


def cmd_step2(args: argparse.Namespace) -> int:
    out = Path(args.jsonl_out) if args.jsonl_out else work_paths(args.work_dir, 2)
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    failed: list[dict] = []
    with flight_browser(headless=not args.headful) as (_p, browser):
        page = new_flight_page(browser)
        with out.open("w", encoding="utf-8") as f:
            for rec in _read_step1(args.work_dir, args.csv, args.start_row, args.end_row):
                row = int(rec["row_num"])
                if rec.get("link_error"):
                    entry = {
                        "row": row,
                        "status": "error",
                        "error": rec["link_error"],
                        "link": rec.get("link", ""),
                    }
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    failed.append({"row": row, "error": rec["link_error"]})
                    continue
                link = rec.get("link") or ""
                sys.stderr.write(f"step2 row {row} {link[:60]}...\n")
                entry: dict = {"row": row, "link": link, "raw": rec.get("raw", {})}
                try:
                    offer = search_offer(link, page=page)
                    entry["offer"] = offer_to_dict(offer)
                    entry["status"] = "ok"
                except Exception as e:
                    entry["status"] = "error"
                    entry["error"] = str(e)
                    failed.append({"row": row, "error": str(e)})
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                n += 1
                if args.pause_sec:
                    time.sleep(args.pause_sec)
    progress = load_progress()
    progress["failed_rows"] = failed
    save_progress(progress)
    print(f"step2: {n} rows scraped, {len(failed)} failed -> {out}", file=sys.stderr)
    return 0


def _read_step2(work_dir: Path) -> list[dict]:
    p = work_paths(work_dir, 2)
    if not p.exists():
        raise SystemExit(f"Missing {p}; run --step 2 first")
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def cmd_step3(args: argparse.Namespace) -> int:
    out = Path(args.jsonl_out) if args.jsonl_out else work_paths(args.work_dir, 3)
    out.parent.mkdir(parents=True, exist_ok=True)
    accepted = rejected = 0
    with out.open("w", encoding="utf-8") as f:
        for entry in _read_step2(args.work_dir):
            row = int(entry["row"])
            if entry.get("status") != "ok" or "offer" not in entry:
                line = status_line(row, "search_failed", error=entry.get("error"))
                f.write(json.dumps(line, ensure_ascii=False) + "\n")
                rejected += 1
                continue
            offer = offer_from_dict(entry["offer"])
            filtered, reason = filter_offer(offer)
            if filtered:
                f.write(
                    json.dumps(
                        {
                            "row": row,
                            "status": "accepted",
                            "offer": entry["offer"],
                            "raw": entry.get("raw", {}),
                            "link": entry.get("link", ""),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                accepted += 1
            else:
                f.write(
                    json.dumps(
                        status_line(row, reason or "rejected", precio=offer.precio),
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                rejected += 1
    print(
        f"step3: accepted={accepted} rejected={rejected} (max {MAX_PRICE_USD} USD, max {MAX_STOPS_PER_LEG} escalas/pierna) -> {out}",
        file=sys.stderr,
    )
    return 0


def _read_step3(work_dir: Path) -> list[dict]:
    p = work_paths(work_dir, 3)
    if not p.exists():
        raise SystemExit(f"Missing {p}; run --step 3 first")
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def cmd_step4(args: argparse.Namespace) -> int:
    writes = Path(args.jsonl_out) if args.jsonl_out else DEFAULT_WRITES
    if args.fresh_writes:
        writes.write_text("", encoding="utf-8")
    actualizado = ensure_run_started(args)
    n = 0
    progress = load_progress()
    verified = set(progress.get("verified_rows") or [])
    rejected_map: dict = dict(progress.get("rejected_rows") or {})

    for entry in _read_step3(args.work_dir):
        row = int(entry["row"])
        if entry.get("status") == "accepted":
            raw = dict(entry.get("raw") or {})
            if not raw.get("Origen") and args.csv.exists():
                reqs = load_requests(args.csv, row, row)
                if reqs:
                    raw = reqs[0].raw
            offer = offer_from_dict(entry["offer"])
            link = entry.get("link") or raw.get("Link") or ""
            payload = save_payload(row, raw, offer, link, actualizado=actualizado)
            append_jsonl(writes, payload)
            if args.update_csv:
                update_csv_row(args.csv, row, payload["values"][0])
            verified.add(row)
            n += 1
            sys.stderr.write(f"step4 row {row} OK precio={offer.precio}\n")
        else:
            reason = entry.get("reason", "rejected")
            rejected_map[str(row)] = reason

    progress["verified_rows"] = sorted(verified)
    progress["rejected_rows"] = rejected_map
    progress["last_run_actualizado"] = actualizado
    progress["note"] = f"step4: {n} write_range payloads -> {writes}"
    save_progress(progress)
    print(f"step4: {n} payloads appended to {writes}", file=sys.stderr)
    return 0 if n else 1


def cmd_step5(args: argparse.Namespace) -> int:
    manifest = Path(args.work_dir) / "step5_purge.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    kept, removed, details = purge_csv(args.csv, dry_run=args.dry_run)
    if removed:
        write_purge_manifest(manifest, removed, details)
    if not args.dry_run:
        progress = load_progress()
        progress["purged_invalid_rows"] = removed
        progress["end_row"] = kept + 1
        progress["note"] = (
            f"step5: removed {len(removed)} rows from {args.csv}; manifest {manifest if removed else 'n/a'}"
        )
        save_progress(progress)
    print(
        f"step5: kept={kept} removed={len(removed)} dry_run={args.dry_run} -> {args.csv}",
        file=sys.stderr,
    )
    if removed:
        print(f"step5: MCP delete plan -> {manifest}", file=sys.stderr)
    return 0


def prepare_args(args: argparse.Namespace) -> None:
    resolve_row_range(args)
    if args.fresh:
        clear_work_dir(args.work_dir)


def cmd_all(args: argparse.Namespace) -> int:
    prepare_args(args)
    ensure_run_started(args)
    if cmd_step1(args) != 0:
        return 1
    if cmd_step2(args) != 0:
        return 1
    if cmd_step3(args) != 0:
        return 1
    rc = cmd_step4(args)
    if not args.no_purge:
        cmd_step5(args)
    else:
        print("step5: skipped (--no-purge)", file=sys.stderr)
    return rc


def main() -> None:
    ap = argparse.ArgumentParser(description="Flight pipeline (5 steps, on demand)")
    ap.add_argument("--step", type=int, choices=[1, 2, 3, 4, 5], help="Run single step")
    ap.add_argument("--all", action="store_true", help="Run steps 1→5")
    ap.add_argument(
        "--refresh-sheet",
        action="store_true",
        help="All data rows in CSV + steps 1→5 (same as --all --all-rows --fresh)",
    )
    ap.add_argument("--all-rows", action="store_true", help="Use full CSV row range")
    ap.add_argument("--fresh", action="store_true", help="Clear /tmp/flight_work/step*.jsonl")
    ap.add_argument(
        "--fresh-writes",
        action="store_true",
        help="Truncate /tmp/flight_writes.jsonl before step 4",
    )
    ap.add_argument(
        "--no-purge",
        action="store_true",
        help="With --all: skip step 5 (use for partial row ranges / test batches)",
    )
    ap.add_argument("--dry-run", action="store_true", help="Step 5: list removals without writing CSV")
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--start-row", type=int, default=2)
    ap.add_argument("--end-row", type=int, default=2)
    ap.add_argument("--work-dir", type=Path, default=DEFAULT_WORK)
    ap.add_argument("--jsonl-out", type=str, default="")
    ap.add_argument("--headful", action="store_true")
    ap.add_argument("--pause-sec", type=float, default=1.0)
    ap.add_argument("--update-csv", action="store_true", help="Step 4: mirror writes to local CSV")
    args = ap.parse_args()
    args.run_started_at = None

    if args.refresh_sheet:
        args.all = True
        args.all_rows = True
        args.fresh = True
        args.fresh_writes = True
        args.update_csv = True

    if args.all:
        sys.exit(cmd_all(args))

    prepare_args(args)
    if args.step == 1:
        sys.exit(cmd_step1(args))
    if args.step == 2:
        sys.exit(cmd_step2(args))
    if args.step == 3:
        sys.exit(cmd_step3(args))
    if args.step == 4:
        sys.exit(cmd_step4(args))
    if args.step == 5:
        sys.exit(cmd_step5(args))
    ap.print_help()
    sys.exit(2)


if __name__ == "__main__":
    main()
