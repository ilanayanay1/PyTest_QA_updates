import json
import statistics
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from Ammeters.client import fetch_current_measurement
from ..utils.config import load_config


class AmmeterTestFramework:
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = load_config(config_path) or {}
        self.ammeters_cfg = self.config.get("ammeters", {})
        self.testing_cfg = self.config.get("testing", {})
        self.sampling_cfg = self.testing_cfg.get("sampling", {})
        self.results_dir = Path(self.config.get("result_management", {}).get("output_dir", "results"))
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_ammeter(self, ammeter_type: str):
        ammeterType = ammeter_type.strip().lower()
        cfg_entry = self.ammeters_cfg.get(ammeterType, {}) or {}
        port = int(cfg_entry.get("port"))# or ammetters_commands[ammeterType][0])
        raw_cmd = cfg_entry.get("command")
        command = raw_cmd.encode("utf-8") if isinstance(raw_cmd, str) and raw_cmd.strip() else  ValueError(f"Unsupported ammeter_type: '{ammeter_type}'")

        return ammeterType, port, command

    def _compute_interval(self, count: int) -> float:
        duration = self.sampling_cfg.get("total_duration_seconds")
        freq = self.sampling_cfg.get("sampling_frequency_hz")

        if isinstance(freq, (int, float)) and freq > 0:
            return 1.0 / float(freq)
        if isinstance(duration, (int, float)) and duration > 0 and count > 1:
            return float(duration) / (count - 1)
        return 0.1

    @staticmethod
    def _compute_stats(samples: List[float]) -> Dict[str, float]:
        return {
            "mean": statistics.mean(samples),
            "median": statistics.median(samples),
            "std_dev": statistics.stdev(samples) if len(samples) > 1 else 0.0,
            "min": min(samples),
            "max": max(samples),
            "count": len(samples),
        }

    def _save_result(self, report: Dict) -> str:
        file_path = self.results_dir / f"{report['test_id']}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        return str(file_path)

    def load_result(self, test_id: str) -> Dict:
        file_path = self.results_dir / f"{test_id}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Test result '{test_id}' not found at {file_path}.")
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def compare_results(self, test_ids: List[str]) -> Dict[str, Dict]:
        #result comparation betwwen ammeters
        comparison = {}
        for tid in test_ids:
            data = self.load_result(tid)
            comparison[tid] = {
                "ammeter_type": data.get("ammeter_type"),
                "stats": data.get("statistics", {}),
            }
        return comparison

    def run_test(self, ammeter_type: str, measurements_count: Optional[int] = None) -> Dict:
        ammeter_key, port, command = self._resolve_ammeter(ammeter_type)
        cfg_count = self.sampling_cfg.get("measurements_count")
        count = int(measurements_count or (cfg_count if isinstance(cfg_count, int) and cfg_count > 0 else 5))
        interval = self._compute_interval(count)
        timeout = float(self.testing_cfg.get("timeout_seconds") or 2.0)

        test_id = f"{ammeter_key}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        samples: List[float] = []
        errors: List[str] = []
        start_time = time.perf_counter()

        for i in range(count):
            sample_start = time.perf_counter()
            try:
                val = fetch_current_measurement(port=port, command=command, timeout_seconds=timeout)
                samples.append(val)
            except Exception as exc:
                errors.append(f"Sample {i + 1}: {exc}")

            if i < count - 1:
                elapsed = time.perf_counter() - sample_start
                sleep_for = max(0.0, interval - elapsed)
                if sleep_for > 0:
                    time.sleep(sleep_for)

        elapsed_total = time.perf_counter() - start_time
        stats = self._compute_stats(samples) if samples else {
            "mean": None, "median": None, "std_dev": None, "min": None, "max": None, "count": 0
        }

        report = {
            "test_id": test_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "ammeter_type": ammeter_key,
            "port": port,
            "command": command.decode("utf-8"),
            "duration_seconds": round(elapsed_total, 4),
            "samples": samples,
            "statistics": stats,
            "errors": errors,
            "status": "passed" if samples and not errors else ("partial" if samples else "failed"),
        }
        report["saved_path"] = self._save_result(report)
        return report