from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path


class RecoveryError(RuntimeError):
    pass


class SyntheticInterruption(RecoveryError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
        candidate = Path(tmp.name)
    os.replace(candidate, path)


@dataclass(frozen=True)
class WorkUnit:
    unit_id: str
    start: int
    stop: int


def payload(unit: WorkUnit, source_hash: str, config_hash: str) -> bytes:
    rows = [
        {"id": i, "unit": unit.unit_id, "value": (i * 19 + 7) % 997,
         "source_hash": source_hash, "config_hash": config_hash}
        for i in range(unit.start, unit.stop)
    ]
    return (json.dumps(rows, sort_keys=True, separators=(",", ":")) + "\n").encode()


def run_units(run_dir: Path, units: list[WorkUnit], source_hash: str, config_hash: str,
              interrupt_after: int | None = None) -> dict:
    written = 0
    reused = 0
    run_dir.mkdir(parents=True, exist_ok=True)
    for unit in units:
        out = run_dir / "units" / f"{unit.unit_id}.json"
        receipt = run_dir / "receipts" / f"{unit.unit_id}.json"
        expected = payload(unit, source_hash, config_hash)
        expected_hash = sha256_bytes(expected)
        if out.exists() and receipt.exists():
            rec = json.loads(receipt.read_text())
            if (sha256_file(out) == expected_hash and rec.get("sha256") == expected_hash
                    and rec.get("source_hash") == source_hash
                    and rec.get("config_hash") == config_hash
                    and rec.get("status") == "PASS"):
                reused += 1
                continue
            raise RecoveryError(f"invalid existing unit: {unit.unit_id}")

        atomic_write(out, expected)
        atomic_write(receipt, (json.dumps({
            **asdict(unit), "sha256": expected_hash,
            "source_hash": source_hash, "config_hash": config_hash, "status": "PASS"
        }, sort_keys=True) + "\n").encode())
        written += 1
        if interrupt_after is not None and written >= interrupt_after:
            raise SyntheticInterruption("intentional public-demo interruption")
    return {"status": "PASS", "written": written, "reused": reused}


def merge_units(run_dir: Path, units: list[WorkUnit], accepted: Path) -> dict:
    merged = []
    for unit in units:
        p = run_dir / "units" / f"{unit.unit_id}.json"
        if not p.exists():
            raise RecoveryError("incomplete unit set")
        merged.extend(json.loads(p.read_text()))
    data = (json.dumps(merged, sort_keys=True, separators=(",", ":")) + "\n").encode()
    new_hash = sha256_bytes(data)
    if accepted.exists() and sha256_file(accepted) != new_hash:
        raise RecoveryError("accepted artifact differs")
    atomic_write(accepted, data)
    return {"status": "ACCEPTED", "rows": len(merged), "sha256": new_hash}
