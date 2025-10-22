#!/usr/bin/env python3
"""
Entity Extraction Service - Standalone Runner

This script provides a simple way to run the Entity Extraction Service
for development and testing purposes.

Usage:
    python run.py [--port PORT] [--debug] [--host HOST]

Example:
    python run.py --port 8007 --debug
"""

import argparse
import logging
import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Add shared path setup
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'shared'))

# Note: shared.python_path doesn't exist, skipping that import

import uvicorn
from src.core.config import get_settings


def setup_logging(debug: bool = False):
    """Set up logging configuration."""
    log_level = logging.DEBUG if debug else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/entity_service.log", mode="a")
        ]
    )
    
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)


def main():
    """Main entry point for the service."""
    parser = argparse.ArgumentParser(
        description="Entity Extraction Service - Legal entity extraction with hybrid REGEX + AI"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8007,
        help="Port to run the service on (default: 8007)"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0", 
        help="Host to bind the service to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with auto-reload"
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Logging level (default: info)"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(debug=args.debug)
    logger = logging.getLogger(__name__)
    
    # Get settings and override with command line arguments
    settings = get_settings()
    
    logger.info(f"Starting Entity Extraction Service...")
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {args.port}")
    logger.info(f"Debug: {args.debug}")
    logger.info(f"Log Level: {args.log_level}")
    
    try:
        # Run the service with proper timeout settings for entity extraction
        uvicorn.run(
            "src.api.main:app",
            host=args.host,
            port=args.port,
            reload=args.debug,
            log_level=args.log_level,
            access_log=True,
            # Extended timeouts for long-running entity extraction operations (45 minutes)
            timeout_keep_alive=settings.extraction.uvicorn_timeout_keep_alive,  # 600 seconds
            timeout_graceful_shutdown=60,  # 60 seconds for graceful shutdown
            limit_concurrency=settings.extraction.max_concurrent_extractions,
            limit_max_requests=1000,  # Restart worker after 1000 requests to prevent memory leaks
            use_colors=True,  # Colored output for debugging
            workers=1,  # Single worker for development
            # Additional settings
            server_header=False,  # Reduce header overhead
            date_header=True     # Keep date header for debugging
        )
    except KeyboardInterrupt:
        logger.info("Service stopped by user")
    except Exception as e:
        logger.error(f"Service failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()