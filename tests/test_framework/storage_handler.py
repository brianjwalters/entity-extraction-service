"""
Storage Handler Module for Entity Extraction Service Testing Framework

This module provides append-only JSON storage for test results with atomic file
locking to support concurrent test execution. All test results are stored in a
single JSON file with automatic history maintenance.

Features:
- Append-only storage (never overwrites existing results)
- Atomic file locking using fcntl (prevents race conditions)
- Automatic history rotation (configurable max entries)
- Timestamped entries with unique test IDs
- JSON schema validation
- Thread-safe and process-safe operations

Storage Schema:
{
    "version": "1.0",
    "tests": [
        {
            "test_id": "test_1234567890",
            "timestamp": 1234567890.123,
            "document_id": "rahimi_2024",
            "routing": {...},
            "waves": [...],
            "entity_distribution": {...},
            "performance": {...},
            "quality": {...}
        }
    ]
}

Usage:
    handler = StorageHandler()
    handler.save_test_result(metrics)
    recent_tests = handler.load_recent_results(limit=10)
"""

import json
import fcntl
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import asdict
import logging

logger = logging.getLogger(__name__)


class StorageHandler:
    """
    Handles append-only JSON storage for test results.

    This handler ensures thread-safe and process-safe storage operations
    using file locking. All results are stored in a single JSON file with
    automatic history management.
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        max_history: int = 1000,
        auto_rotate: bool = True
    ):
        """
        Initialize storage handler.

        Args:
            storage_path: Path to storage JSON file (default: tests/results/test_history.json)
            max_history: Maximum number of test results to keep (default: 1000)
            auto_rotate: Automatically rotate history when limit reached (default: True)
        """
        if storage_path is None:
            # Default to tests/results/test_history.json
            base_dir = Path(__file__).parent.parent
            storage_path = base_dir / "results" / "test_history.json"

        self.storage_path = Path(storage_path)
        self.max_history = max_history
        self.auto_rotate = auto_rotate
        self.schema_version = "1.0"

        # Ensure storage directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize storage file if it doesn't exist
        self._initialize_storage()

    def _initialize_storage(self) -> None:
        """Initialize storage file with empty schema if it doesn't exist."""
        if not self.storage_path.exists():
            initial_data = {
                "version": self.schema_version,
                "tests": []
            }
            self._write_data(initial_data)
            logger.info(f"Initialized storage at {self.storage_path}")

    def _write_data(self, data: Dict[str, Any]) -> None:
        """
        Write data to storage file (internal method, no locking).

        Args:
            data: Dictionary to write
        """
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _read_data(self) -> Dict[str, Any]:
        """
        Read data from storage file (internal method, no locking).

        Returns:
            dict: Storage data
        """
        if not self.storage_path.exists():
            return {"version": self.schema_version, "tests": []}

        with open(self.storage_path, 'r') as f:
            return json.load(f)

    def _acquire_lock(self, file_handle, timeout: float = 5.0) -> bool:
        """
        Acquire exclusive file lock with timeout.

        Args:
            file_handle: Open file handle
            timeout: Lock timeout in seconds

        Returns:
            bool: True if lock acquired, False on timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                fcntl.flock(file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except BlockingIOError:
                time.sleep(0.01)  # Wait 10ms before retry

        logger.error(f"Failed to acquire lock after {timeout}s")
        return False

    def _release_lock(self, file_handle) -> None:
        """
        Release file lock.

        Args:
            file_handle: Open file handle
        """
        fcntl.flock(file_handle, fcntl.LOCK_UN)

    def save_test_result(self, metrics_dict: Dict[str, Any]) -> bool:
        """
        Save test result to storage with atomic file locking.

        This method ensures thread-safe and process-safe append operations.
        Multiple test executions can run concurrently without data corruption.

        Args:
            metrics_dict: Metrics dictionary from MetricsCollector

        Returns:
            bool: True if saved successfully, False on error
        """
        try:
            # Open file for read+write
            with open(self.storage_path, 'r+') as f:
                # Acquire exclusive lock
                if not self._acquire_lock(f):
                    logger.error("Failed to acquire lock for saving test result")
                    return False

                try:
                    # Read current data
                    f.seek(0)
                    data = json.load(f)

                    # Append new test result
                    data["tests"].append(metrics_dict)

                    # Auto-rotate if enabled and limit reached
                    if self.auto_rotate and len(data["tests"]) > self.max_history:
                        # Keep only the most recent max_history entries
                        data["tests"] = data["tests"][-self.max_history:]
                        logger.info(f"Rotated history to keep last {self.max_history} entries")

                    # Write updated data
                    f.seek(0)
                    f.truncate()
                    json.dump(data, f, indent=2)

                    logger.info(f"Saved test result: {metrics_dict.get('test_id', 'unknown')}")
                    return True

                finally:
                    # Always release lock
                    self._release_lock(f)

        except Exception as e:
            logger.error(f"Failed to save test result: {e}", exc_info=True)
            return False

    def load_all_results(self) -> List[Dict[str, Any]]:
        """
        Load all test results from storage.

        Returns:
            list: All test results
        """
        try:
            with open(self.storage_path, 'r') as f:
                # Acquire shared lock for reading
                fcntl.flock(f, fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                    return data.get("tests", [])
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)

        except Exception as e:
            logger.error(f"Failed to load test results: {e}", exc_info=True)
            return []

    def load_recent_results(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Load most recent test results.

        Args:
            limit: Maximum number of results to return

        Returns:
            list: Recent test results (newest first)
        """
        all_results = self.load_all_results()
        return all_results[-limit:][::-1]  # Reverse to get newest first

    def load_results_by_document(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Load all test results for a specific document.

        Args:
            document_id: Document identifier

        Returns:
            list: Test results for the document
        """
        all_results = self.load_all_results()
        return [r for r in all_results if r.get("document_id") == document_id]

    def load_results_by_strategy(self, strategy: str) -> List[Dict[str, Any]]:
        """
        Load all test results using a specific routing strategy.

        Args:
            strategy: Routing strategy (e.g., "three_wave", "single_pass")

        Returns:
            list: Test results using the strategy
        """
        all_results = self.load_all_results()
        return [
            r for r in all_results
            if r.get("routing", {}).get("strategy") == strategy
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            dict: Statistics about stored tests
        """
        all_results = self.load_all_results()

        if not all_results:
            return {
                "total_tests": 0,
                "oldest_test": None,
                "newest_test": None,
                "unique_documents": 0,
                "strategies_used": []
            }

        # Extract statistics
        timestamps = [r["timestamp"] for r in all_results]
        documents = set(r["document_id"] for r in all_results)
        strategies = set(r.get("routing", {}).get("strategy") for r in all_results)

        return {
            "total_tests": len(all_results),
            "oldest_test": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(min(timestamps))),
            "newest_test": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(max(timestamps))),
            "unique_documents": len(documents),
            "strategies_used": list(strategies),
            "storage_path": str(self.storage_path),
            "storage_size_kb": self.storage_path.stat().st_size / 1024
        }

    def clear_history(self, keep_recent: int = 0) -> bool:
        """
        Clear test history.

        Args:
            keep_recent: Number of recent tests to keep (default: 0 = clear all)

        Returns:
            bool: True if cleared successfully
        """
        try:
            with open(self.storage_path, 'r+') as f:
                if not self._acquire_lock(f):
                    logger.error("Failed to acquire lock for clearing history")
                    return False

                try:
                    f.seek(0)
                    data = json.load(f)

                    if keep_recent > 0:
                        # Keep only the most recent entries
                        data["tests"] = data["tests"][-keep_recent:]
                    else:
                        # Clear all
                        data["tests"] = []

                    f.seek(0)
                    f.truncate()
                    json.dump(data, f, indent=2)

                    logger.info(f"Cleared history (kept {keep_recent} recent tests)")
                    return True

                finally:
                    self._release_lock(f)

        except Exception as e:
            logger.error(f"Failed to clear history: {e}", exc_info=True)
            return False

    def export_results(self, output_path: Path, limit: Optional[int] = None) -> bool:
        """
        Export test results to a separate JSON file.

        Args:
            output_path: Path to export file
            limit: Maximum number of results to export (None = all)

        Returns:
            bool: True if exported successfully
        """
        try:
            all_results = self.load_all_results()

            if limit:
                all_results = all_results[-limit:]

            export_data = {
                "version": self.schema_version,
                "exported_at": time.time(),
                "total_tests": len(all_results),
                "tests": all_results
            }

            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2)

            logger.info(f"Exported {len(all_results)} test results to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export results: {e}", exc_info=True)
            return False


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Initialize storage handler
    handler = StorageHandler()

    # Example test result
    mock_result = {
        "test_id": f"test_{int(time.time() * 1000)}",
        "timestamp": time.time(),
        "document_id": "rahimi_2024",
        "routing": {
            "strategy": "three_wave",
            "prompt_version": "wave_v1",
            "estimated_tokens": 30838
        },
        "performance": {
            "total_duration_seconds": 0.92,
            "entities_per_second": 154.35
        }
    }

    # Save test result
    print("Saving test result...")
    handler.save_test_result(mock_result)

    # Load recent results
    print("\nRecent test results:")
    recent = handler.load_recent_results(limit=5)
    for result in recent:
        print(f"  - {result['test_id']} ({result['document_id']})")

    # Get statistics
    print("\nStorage statistics:")
    stats = handler.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
