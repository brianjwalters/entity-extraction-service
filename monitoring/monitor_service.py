#!/usr/bin/env python3
"""
vLLM Monitoring Service

Lightweight monitoring service for production deployment.
Runs as a systemd service to continuously monitor vLLM performance.
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitoring.vllm_monitor import VLLMMonitor, AlertLevel

# Configure logging
LOG_DIR = Path("/srv/luris/be/monitoring/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "monitor_service.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class MonitoringService:
    """
    Production monitoring service for vLLM.

    Provides continuous monitoring with alert escalation,
    automatic recovery actions, and performance reporting.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize monitoring service.

        Args:
            config_path: Path to configuration file
        """
        self.config = self.load_config(config_path)
        self.monitor = None
        self.shutdown_event = asyncio.Event()
        self.alert_history = []
        self.last_critical_alert = None
        self.consecutive_failures = 0

        logger.info("Monitoring service initialized")

    def load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load monitoring configuration."""
        default_config = {
            "vllm_service_url": os.getenv("VLLM_SERVICE_URL", "http://localhost:8080"),
            "entity_extraction_url": os.getenv("ENTITY_EXTRACTION_URL", "http://localhost:8007"),
            "document_upload_url": os.getenv("DOCUMENT_UPLOAD_URL", "http://localhost:8008"),
            "monitoring_interval": int(os.getenv("MONITORING_INTERVAL", "30")),
            "gpu_check_interval": int(os.getenv("GPU_CHECK_INTERVAL", "10")),
            "alert_webhook": os.getenv("ALERT_WEBHOOK_URL"),
            "alert_email": os.getenv("ALERT_EMAIL"),
            "enable_auto_recovery": os.getenv("ENABLE_AUTO_RECOVERY", "false").lower() == "true",
            "max_consecutive_failures": int(os.getenv("MAX_CONSECUTIVE_FAILURES", "5")),
            "dashboard_interval": int(os.getenv("DASHBOARD_INTERVAL", "300")),  # 5 minutes
        }

        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    file_config = json.load(f)
                    default_config.update(file_config)
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")

        return default_config

    async def start(self):
        """Start monitoring service."""
        logger.info("Starting monitoring service...")

        # Initialize monitor
        self.monitor = VLLMMonitor(
            vllm_service_url=self.config["vllm_service_url"],
            entity_extraction_url=self.config["entity_extraction_url"],
            document_upload_url=self.config["document_upload_url"],
            monitoring_interval=self.config["monitoring_interval"],
            gpu_check_interval=self.config["gpu_check_interval"]
        )

        # Start monitor
        await self.monitor.start()

        # Start service loops
        tasks = [
            asyncio.create_task(self._alert_handler_loop()),
            asyncio.create_task(self._dashboard_generation_loop()),
            asyncio.create_task(self._health_check_loop()),
        ]

        if self.config["enable_auto_recovery"]:
            tasks.append(asyncio.create_task(self._auto_recovery_loop()))

        logger.info("Monitoring service started successfully")

        # Wait for shutdown
        await self.shutdown_event.wait()

        # Cancel tasks
        for task in tasks:
            task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)

        # Stop monitor
        await self.monitor.stop()

        logger.info("Monitoring service stopped")

    async def _alert_handler_loop(self):
        """Handle alerts and escalations."""
        while not self.shutdown_event.is_set():
            try:
                # Check for critical alerts
                recent_alerts = [
                    alert for alert in list(self.monitor.alerts)[-50:]
                    if alert.level in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY]
                ]

                for alert in recent_alerts:
                    if alert not in self.alert_history:
                        await self.handle_alert(alert)
                        self.alert_history.append(alert)

                # Cleanup old alert history
                if len(self.alert_history) > 1000:
                    self.alert_history = self.alert_history[-500:]

                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"Alert handler error: {e}")
                await asyncio.sleep(30)

    async def handle_alert(self, alert):
        """Handle individual alert with escalation."""
        try:
            logger.warning(f"Alert: [{alert.level.value}] {alert.service}: {alert.message}")

            # Track consecutive failures
            if alert.level == AlertLevel.CRITICAL:
                self.consecutive_failures += 1
                self.last_critical_alert = alert
            else:
                self.consecutive_failures = max(0, self.consecutive_failures - 1)

            # Escalate if needed
            if self.consecutive_failures >= self.config["max_consecutive_failures"]:
                await self.escalate_alert(alert)

            # Send notifications
            await self.send_alert_notification(alert)

            # Log to alert file
            alert_log = LOG_DIR / "alerts.jsonl"
            with open(alert_log, 'a') as f:
                alert_data = {
                    "timestamp": alert.timestamp.isoformat(),
                    "level": alert.level.value,
                    "service": alert.service,
                    "message": alert.message,
                    "metrics": alert.metrics
                }
                f.write(json.dumps(alert_data) + "\n")

        except Exception as e:
            logger.error(f"Failed to handle alert: {e}")

    async def escalate_alert(self, alert):
        """Escalate critical alert."""
        logger.critical(f"ESCALATION: Multiple critical failures detected!")

        escalation_message = (
            f"CRITICAL ESCALATION\n"
            f"Service: {alert.service}\n"
            f"Consecutive Failures: {self.consecutive_failures}\n"
            f"Last Alert: {alert.message}\n"
            f"Timestamp: {alert.timestamp.isoformat()}\n"
        )

        # Log escalation
        with open(LOG_DIR / "escalations.log", 'a') as f:
            f.write(f"{datetime.now().isoformat()} - {escalation_message}\n")

        # Trigger auto-recovery if enabled
        if self.config["enable_auto_recovery"]:
            await self.trigger_auto_recovery(alert)

    async def trigger_auto_recovery(self, alert):
        """Trigger automatic recovery actions."""
        logger.info(f"Triggering auto-recovery for {alert.service}")

        try:
            # Restart affected service
            if "vllm" in alert.service.lower():
                logger.info("Attempting to restart vLLM service...")
                os.system("sudo systemctl restart luris-vllm")
                await asyncio.sleep(30)  # Wait for restart

            elif "entity" in alert.service.lower():
                logger.info("Attempting to restart Entity Extraction service...")
                os.system("sudo systemctl restart luris-entity-extraction")
                await asyncio.sleep(10)

            # Reset failure counter after recovery attempt
            self.consecutive_failures = 0

        except Exception as e:
            logger.error(f"Auto-recovery failed: {e}")

    async def send_alert_notification(self, alert):
        """Send alert notifications (webhook, email, etc.)."""
        if alert.level not in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY]:
            return

        try:
            # Webhook notification
            if self.config.get("alert_webhook"):
                import httpx
                async with httpx.AsyncClient() as client:
                    await client.post(
                        self.config["alert_webhook"],
                        json={
                            "text": f"🚨 {alert.level.value.upper()}: {alert.message}",
                            "service": alert.service,
                            "timestamp": alert.timestamp.isoformat()
                        },
                        timeout=5.0
                    )

            # Email notification (simplified - would need proper SMTP config)
            if self.config.get("alert_email"):
                logger.info(f"Would send email to {self.config['alert_email']}: {alert.message}")

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    async def _dashboard_generation_loop(self):
        """Generate performance dashboards periodically."""
        while not self.shutdown_event.is_set():
            try:
                # Generate dashboard
                dashboard = await self.monitor.generate_dashboard()

                # Save to file
                dashboard_file = LOG_DIR / f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(dashboard_file, 'w') as f:
                    f.write(dashboard)

                # Keep only recent dashboards
                dashboards = sorted(LOG_DIR.glob("dashboard_*.txt"))
                if len(dashboards) > 48:  # Keep 48 files (4 days at 5-minute intervals)
                    for old_dashboard in dashboards[:-48]:
                        old_dashboard.unlink()

                logger.info(f"Dashboard generated: {dashboard_file}")

                await asyncio.sleep(self.config["dashboard_interval"])

            except Exception as e:
                logger.error(f"Dashboard generation error: {e}")
                await asyncio.sleep(self.config["dashboard_interval"])

    async def _health_check_loop(self):
        """Perform regular health checks."""
        while not self.shutdown_event.is_set():
            try:
                # Get monitoring status
                gpu_summary = self.monitor.get_gpu_summary()
                service_summary = self.monitor.get_service_summary()

                # Check GPU health
                for gpu_name, stats in gpu_summary.items():
                    if isinstance(stats, dict):
                        if stats.get("max_memory_percent", 0) > 95:
                            logger.warning(f"{gpu_name}: Memory critically high ({stats['max_memory_percent']:.1f}%)")

                # Check service health
                for service, stats in service_summary.items():
                    if isinstance(stats, dict):
                        if stats.get("error_rate", 0) > 10:
                            logger.warning(f"{service}: High error rate ({stats['error_rate']:.1f}%)")

                        if stats.get("max_timeout_percentage", 0) > 80:
                            logger.warning(f"{service}: Approaching timeout ({stats['max_timeout_percentage']:.1f}%)")

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(60)

    async def _auto_recovery_loop(self):
        """Automatic recovery actions."""
        while not self.shutdown_event.is_set():
            try:
                # Check if recovery is needed
                if self.consecutive_failures >= 3:
                    logger.info("Auto-recovery check triggered")

                    # Get GPU metrics
                    gpu_metrics = await self.monitor.collect_gpu_metrics()

                    for metric in gpu_metrics:
                        memory_percent = (metric.memory_used_mb / metric.memory_total_mb) * 100

                        # Clear GPU cache if memory is critical
                        if memory_percent > 95:
                            logger.warning(f"GPU {metric.gpu_id} memory critical, clearing cache...")
                            try:
                                import torch
                                if torch.cuda.is_available():
                                    torch.cuda.empty_cache()
                                    logger.info("GPU cache cleared")
                            except ImportError:
                                logger.warning("PyTorch not available for cache clearing")

                await asyncio.sleep(300)  # Check every 5 minutes

            except Exception as e:
                logger.error(f"Auto-recovery loop error: {e}")
                await asyncio.sleep(300)

    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown_event.set()


async def main():
    """Main service entry point."""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="vLLM Monitoring Service")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    args = parser.parse_args()

    # Create service
    service = MonitoringService(config_path=args.config)

    # Setup signal handlers
    signal.signal(signal.SIGTERM, service.handle_shutdown)
    signal.signal(signal.SIGINT, service.handle_shutdown)

    # Run service
    try:
        await service.start()
    except Exception as e:
        logger.error(f"Service failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())