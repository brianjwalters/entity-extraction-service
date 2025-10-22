#!/usr/bin/env python3
"""
Monitoring Integration for Entity Extraction Service

Integrates vLLM monitoring with the Entity Extraction Service to track:
- Document processing performance
- Large document handling
- Timeout warnings
- Service health
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitoring.vllm_monitor import VLLMMonitor
from src.core.performance_monitor import PerformanceMonitor

logger = logging.getLogger(__name__)


class MonitoringIntegration:
    """
    Integration layer between vLLM Monitor and Entity Extraction Service.

    Provides hooks for request tracking, performance monitoring,
    and alert generation during document processing.
    """

    def __init__(
        self,
        vllm_monitor: Optional[VLLMMonitor] = None,
        performance_monitor: Optional[PerformanceMonitor] = None
    ):
        """
        Initialize monitoring integration.

        Args:
            vllm_monitor: vLLM monitoring instance
            performance_monitor: Entity extraction performance monitor
        """
        self.vllm_monitor = vllm_monitor or VLLMMonitor()
        self.performance_monitor = performance_monitor or PerformanceMonitor()

        # Request tracking
        self.active_operations = {}

        logger.info("Monitoring integration initialized")

    async def initialize(self):
        """Start monitoring systems."""
        try:
            # Start vLLM monitor
            await self.vllm_monitor.start()

            # Start performance monitor
            await self.performance_monitor.start_monitoring()

            logger.info("All monitoring systems started")

        except Exception as e:
            logger.error(f"Failed to initialize monitoring: {e}")
            raise

    async def shutdown(self):
        """Stop monitoring systems."""
        try:
            # Stop monitors
            await self.vllm_monitor.stop()
            await self.performance_monitor.stop_monitoring()

            logger.info("Monitoring systems stopped")

        except Exception as e:
            logger.error(f"Error during monitoring shutdown: {e}")

    def track_document_start(
        self,
        request_id: str,
        document_path: str,
        document_size_kb: Optional[int] = None,
        chunk_count: Optional[int] = None
    ) -> str:
        """
        Track the start of document processing.

        Args:
            request_id: Unique request identifier
            document_path: Path to document being processed
            document_size_kb: Document size in KB
            chunk_count: Number of chunks to process

        Returns:
            Operation ID for tracking
        """
        try:
            # Calculate document size if not provided
            if document_size_kb is None and Path(document_path).exists():
                document_size_kb = Path(document_path).stat().st_size // 1024

            # Track in vLLM monitor
            self.vllm_monitor.track_request_start(
                request_id=request_id,
                service_name="entity_extraction",
                document_size_kb=document_size_kb
            )

            # Track in performance monitor
            operation_id = self.performance_monitor.record_operation_start(
                operation_id=request_id,
                operation_type="document_processing"
            )

            # Store operation details
            self.active_operations[request_id] = {
                "document_path": document_path,
                "document_size_kb": document_size_kb,
                "chunk_count": chunk_count,
                "start_time": time.time(),
                "operation_id": operation_id
            }

            logger.info(
                f"Started tracking document: {request_id} "
                f"({document_size_kb}KB, {chunk_count} chunks)"
            )

            return operation_id

        except Exception as e:
            logger.error(f"Failed to track document start: {e}")
            return request_id

    def track_chunk_processing(
        self,
        request_id: str,
        chunk_index: int,
        chunk_size: int,
        processing_time_ms: float,
        success: bool = True,
        error_type: Optional[str] = None
    ):
        """
        Track individual chunk processing.

        Args:
            request_id: Request identifier
            chunk_index: Index of chunk being processed
            chunk_size: Size of chunk in tokens/characters
            processing_time_ms: Time taken to process chunk
            success: Whether processing succeeded
            error_type: Type of error if failed
        """
        try:
            if request_id in self.active_operations:
                op_data = self.active_operations[request_id]

                # Calculate progress
                progress = ((chunk_index + 1) / op_data.get("chunk_count", 1)) * 100 if op_data.get("chunk_count") else 0

                # Check for slow processing
                if processing_time_ms > 5000:  # 5 seconds per chunk
                    logger.warning(
                        f"Slow chunk processing: {request_id} chunk {chunk_index} "
                        f"took {processing_time_ms:.0f}ms"
                    )

                # Log progress at milestones
                if progress in [25, 50, 75, 90]:
                    elapsed_s = time.time() - op_data["start_time"]
                    estimated_total_s = (elapsed_s / progress) * 100 if progress > 0 else 0

                    logger.info(
                        f"Document {request_id} progress: {progress:.0f}% "
                        f"(elapsed: {elapsed_s:.0f}s, estimated: {estimated_total_s:.0f}s)"
                    )

        except Exception as e:
            logger.error(f"Failed to track chunk processing: {e}")

    def track_document_complete(
        self,
        request_id: str,
        success: bool = True,
        error_type: Optional[str] = None,
        total_chunks_processed: Optional[int] = None,
        total_entities_extracted: Optional[int] = None
    ):
        """
        Track document processing completion.

        Args:
            request_id: Request identifier
            success: Whether processing succeeded
            error_type: Type of error if failed
            total_chunks_processed: Total chunks processed
            total_entities_extracted: Total entities found
        """
        try:
            # Complete vLLM monitor tracking
            self.vllm_monitor.track_request_complete(
                request_id=request_id,
                success=success,
                error_type=error_type
            )

            # Complete performance monitor tracking
            if request_id in self.active_operations:
                op_data = self.active_operations.pop(request_id)

                from src.core.performance_monitor import ProcessingMode

                self.performance_monitor.record_operation_complete(
                    operation_id=op_data["operation_id"],
                    operation_type="document_processing",
                    processing_mode=ProcessingMode.LOCAL_WITH_REMOTE_FALLBACK,
                    tokens_processed=total_chunks_processed or 0,
                    success=success,
                    error_type=error_type,
                    metadata={
                        "document_size_kb": op_data.get("document_size_kb"),
                        "chunks_processed": total_chunks_processed,
                        "entities_extracted": total_entities_extracted
                    }
                )

                # Log completion
                elapsed_s = time.time() - op_data["start_time"]
                status = "SUCCESS" if success else f"FAILED ({error_type})"

                logger.info(
                    f"Document {request_id} completed: {status} "
                    f"(elapsed: {elapsed_s:.1f}s, chunks: {total_chunks_processed}, "
                    f"entities: {total_entities_extracted})"
                )

        except Exception as e:
            logger.error(f"Failed to track document completion: {e}")

    async def get_monitoring_status(self) -> Dict[str, Any]:
        """
        Get current monitoring status.

        Returns:
            Dictionary with monitoring status information
        """
        try:
            # Get GPU summary
            gpu_summary = self.vllm_monitor.get_gpu_summary()

            # Get service summary
            service_summary = self.vllm_monitor.get_service_summary()

            # Get performance health
            health_score = self.performance_monitor.get_health_score()

            # Get active operations
            active_ops = []
            for req_id, op_data in self.active_operations.items():
                elapsed_s = time.time() - op_data["start_time"]
                active_ops.append({
                    "request_id": req_id,
                    "document_size_kb": op_data.get("document_size_kb"),
                    "elapsed_seconds": elapsed_s,
                    "timeout_percentage": (elapsed_s * 1000 / 1800000) * 100  # 30 min timeout
                })

            return {
                "timestamp": datetime.now().isoformat(),
                "gpu_status": gpu_summary,
                "service_status": service_summary,
                "health_score": health_score,
                "active_operations": active_ops,
                "active_operation_count": len(active_ops)
            }

        except Exception as e:
            logger.error(f"Failed to get monitoring status: {e}")
            return {"error": str(e)}

    async def generate_performance_report(self) -> str:
        """
        Generate comprehensive performance report.

        Returns:
            Formatted performance report
        """
        try:
            # Get dashboard from vLLM monitor
            dashboard = await self.vllm_monitor.generate_dashboard()

            # Get optimization report from performance monitor
            optimization_report = self.performance_monitor.get_llama_optimization_report()

            # Combine reports
            report = []
            report.append(dashboard)
            report.append("\n### LLM Optimization Report ###")

            if optimization_report.get("current_configuration"):
                report.append(f"Current Profile: {optimization_report['current_configuration']}")

            if optimization_report.get("recent_performance"):
                perf = optimization_report["recent_performance"]
                if isinstance(perf, dict) and "breakthrough_rate" in perf:
                    report.append(f"Breakthrough Achievement: {perf['breakthrough_rate']:.1%}")
                    report.append(f"Average Response Time: {perf.get('avg_response_time_ms', 0):.0f}ms")

            if optimization_report.get("optimization_recommendations"):
                report.append("\nOptimization Recommendations:")
                for rec in optimization_report["optimization_recommendations"][:3]:
                    report.append(f"  - {rec}")

            return "\n".join(report)

        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            return f"Error generating report: {e}"


# FastAPI integration endpoints
def create_monitoring_router():
    """Create FastAPI router for monitoring endpoints."""
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel

    router = APIRouter(prefix="/monitoring", tags=["monitoring"])

    # Global monitoring instance
    monitor_integration = None

    class DocumentTrackingRequest(BaseModel):
        request_id: str
        document_path: str
        document_size_kb: Optional[int] = None
        chunk_count: Optional[int] = None

    class ChunkTrackingRequest(BaseModel):
        request_id: str
        chunk_index: int
        chunk_size: int
        processing_time_ms: float
        success: bool = True
        error_type: Optional[str] = None

    @router.on_event("startup")
    async def startup_monitoring():
        """Initialize monitoring on startup."""
        global monitor_integration
        monitor_integration = MonitoringIntegration()
        await monitor_integration.initialize()

    @router.on_event("shutdown")
    async def shutdown_monitoring():
        """Shutdown monitoring on exit."""
        global monitor_integration
        if monitor_integration:
            await monitor_integration.shutdown()

    @router.post("/track/document/start")
    async def track_document_start(request: DocumentTrackingRequest):
        """Track start of document processing."""
        if not monitor_integration:
            raise HTTPException(status_code=503, detail="Monitoring not initialized")

        operation_id = monitor_integration.track_document_start(
            request_id=request.request_id,
            document_path=request.document_path,
            document_size_kb=request.document_size_kb,
            chunk_count=request.chunk_count
        )

        return {"operation_id": operation_id}

    @router.post("/track/chunk")
    async def track_chunk(request: ChunkTrackingRequest):
        """Track chunk processing."""
        if not monitor_integration:
            raise HTTPException(status_code=503, detail="Monitoring not initialized")

        monitor_integration.track_chunk_processing(
            request_id=request.request_id,
            chunk_index=request.chunk_index,
            chunk_size=request.chunk_size,
            processing_time_ms=request.processing_time_ms,
            success=request.success,
            error_type=request.error_type
        )

        return {"status": "tracked"}

    @router.get("/status")
    async def get_monitoring_status():
        """Get current monitoring status."""
        if not monitor_integration:
            raise HTTPException(status_code=503, detail="Monitoring not initialized")

        status = await monitor_integration.get_monitoring_status()
        return status

    @router.get("/report")
    async def get_performance_report():
        """Get performance report."""
        if not monitor_integration:
            raise HTTPException(status_code=503, detail="Monitoring not initialized")

        report = await monitor_integration.generate_performance_report()
        return {"report": report}

    @router.get("/health")
    async def monitoring_health():
        """Check monitoring system health."""
        return {
            "status": "healthy" if monitor_integration else "not_initialized",
            "timestamp": datetime.now().isoformat()
        }

    return router


async def main():
    """Test monitoring integration."""
    integration = MonitoringIntegration()

    try:
        await integration.initialize()

        # Simulate document processing
        request_id = f"test_doc_{int(time.time())}"

        # Start tracking
        operation_id = integration.track_document_start(
            request_id=request_id,
            document_path="/srv/luris/be/tests/docs/Rahimi.pdf",
            document_size_kb=1024,
            chunk_count=10
        )

        print(f"Started tracking: {operation_id}")

        # Simulate chunk processing
        for i in range(10):
            await asyncio.sleep(1)
            integration.track_chunk_processing(
                request_id=request_id,
                chunk_index=i,
                chunk_size=100,
                processing_time_ms=850 + (i * 50),
                success=True
            )
            print(f"Processed chunk {i+1}/10")

        # Complete tracking
        integration.track_document_complete(
            request_id=request_id,
            success=True,
            total_chunks_processed=10,
            total_entities_extracted=25
        )

        # Get status
        status = await integration.get_monitoring_status()
        print(f"\nMonitoring Status:")
        print(f"  Health Score: {status.get('health_score', {}).get('overall_score', 'N/A')}")
        print(f"  Active Operations: {status.get('active_operation_count', 0)}")

        # Generate report
        report = await integration.generate_performance_report()
        print(f"\nPerformance Report:\n{report}")

        await asyncio.sleep(5)

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await integration.shutdown()


if __name__ == "__main__":
    asyncio.run(main())