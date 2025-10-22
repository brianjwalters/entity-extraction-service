#!/usr/bin/env python3
"""
Simple Entity Extraction Service Runner (Single Worker)
For testing purposes without multiprocessing issues
"""

import os

import uvicorn
from src.api.main import app

if __name__ == "__main__":
    # Run with single worker to avoid multiprocessing issues
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8007,
        workers=1,
        log_level="info",
        access_log=True,
        timeout_keep_alive=2700
    )