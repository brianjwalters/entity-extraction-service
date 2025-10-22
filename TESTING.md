# Entity Extraction Service - Testing Guide

**Version**: 2.0.0
**Last Updated**: 2025-01-14 (Post P0/P1 Fixes)
**Status**: Production Ready

## 📋 Table of Contents

1. [Overview](#overview)
2. [Test Environment Setup](#test-environment-setup)
3. [Import Pattern Standards](#import-pattern-standards)
4. [Running Tests](#running-tests)
5. [Test Categories](#test-categories)
6. [Troubleshooting](#troubleshooting)
7. [Best Practices](#best-practices)
8. [Continuous Integration](#continuous-integration)

## Overview

This document provides comprehensive testing guidelines for the Entity Extraction Service, including mandatory requirements for virtual environment activation, import pattern standards, and test execution procedures.

### Key Testing Principles

1. **Virtual Environment Mandatory**: All tests MUST run within activated venv
2. **Absolute Imports Only**: No relative imports or sys.path manipulation
3. **Pytest Configuration**: Tests use pyproject.toml for configuration
4. **Zero Tolerance**: Import violations and venv issues cause immediate failures

### Recent Test Infrastructure Improvements (P0-1 Fix)

- ✅ Fixed 66 test files with import violations
- ✅ Corrected 108 total import errors across test suite
- ✅ Created pyproject.toml with proper pytest configuration
- ✅ ALL tests now use absolute imports exclusively
- ✅ Verified all tests work with venv-only activation

## Test Environment Setup

### Prerequisites

Before running any tests, ensure:

- ✅ Python 3.10+ installed
- ✅ Virtual environment exists (DO NOT create new one)
- ✅ All dependencies installed in venv
- ✅ Required services running (for integration tests)

### Initial Setup

```bash
# Navigate to service directory
cd /srv/luris/be/entity-extraction-service

# ⚠️ CRITICAL: Activate existing virtual environment
source venv/bin/activate

# ❌ NEVER create new venv (it already exists!)
# python3 -m venv venv  # DON'T DO THIS!

# Verify venv activation
which python
# Expected: /srv/luris/be/entity-extraction-service/venv/bin/python

which pytest
# Expected: /srv/luris/be/entity-extraction-service/venv/bin/pytest

# Install/update dependencies (if needed)
pip install -r requirements.txt

# Verify imports work
python -c "from src.api.main import app; print('✅ Imports working')"

# Verify pytest configuration
pytest --version
# Should show: pytest 7.x.x or higher
```

### Virtual Environment Verification Script

Create a verification script to ensure proper setup:

```bash
#!/bin/bash
# scripts/verify_test_env.sh

echo "🔍 Verifying test environment..."

# Check if in correct directory
if [[ ! -f "run.py" ]]; then
    echo "❌ Not in entity-extraction-service directory"
    exit 1
fi

# Check venv activation
PYTHON_PATH=$(which python)
if [[ $PYTHON_PATH != *"venv/bin/python"* ]]; then
    echo "❌ Virtual environment not activated"
    echo "Run: source venv/bin/activate"
    exit 1
fi

# Check pytest available
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found in venv"
    echo "Run: pip install -r requirements.txt"
    exit 1
fi

# Check imports work
python -c "from src.api.main import app" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Import test failed"
    exit 1
fi

# Check pyproject.toml exists
if [[ ! -f "pyproject.toml" ]]; then
    echo "❌ pyproject.toml not found"
    exit 1
fi

echo "✅ Test environment verified"
echo "✅ Python: $PYTHON_PATH"
echo "✅ Pytest: $(which pytest)"
echo "✅ Imports: Working"
echo "✅ Configuration: pyproject.toml present"
exit 0
```

## Import Pattern Standards

### 🚨 MANDATORY: Absolute Imports Only

**ALL test files MUST use absolute imports from project root.**

#### Correct Import Patterns

```python
# test_example.py

# Standard library imports
import os
import sys
from typing import List, Dict, Any
from datetime import datetime

# Third-party imports
import pytest
from fastapi.testclient import TestClient
import httpx

# ✅ CORRECT: Absolute imports from project root
from src.api.main import app
from src.core.extraction_service import ExtractionService
from src.core.regex_engine import RegexEngine
from src.models.entities import Entity, EntityType
from src.models.requests import ExtractionRequest
from src.models.responses import ExtractionResponse
from shared.clients.supabase_client import create_supabase_client
from shared.utils.logging_utils import log_info

# Test fixtures
@pytest.fixture
def client():
    return TestClient(app)

# Test implementation
def test_extraction(client):
    response = client.post("/api/v1/extract", json={
        "document_id": "test_001",
        "content": "Test content"
    })
    assert response.status_code == 200
```

#### Forbidden Import Patterns

```python
# ❌ FORBIDDEN: Relative imports
from ...src.api.main import app
from ..core.extraction_service import ExtractionService
from ....shared.clients.supabase_client import SupabaseClient

# ❌ FORBIDDEN: sys.path manipulation
import sys
import os
sys.path.append('../..')
sys.path.append(os.path.abspath('../..'))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ❌ FORBIDDEN: PYTHONPATH dependency in code
os.environ['PYTHONPATH'] = '/srv/luris/be/entity-extraction-service'

# ❌ FORBIDDEN: Relative imports beyond same directory
from .utils import helper_function  # OK in same package
from ..tests.utils import helper    # FORBIDDEN
```

### Import Organization

Organize imports in this order:

1. Standard library imports
2. Third-party library imports
3. Local application imports (using absolute paths)

```python
# 1. Standard library
import os
import sys
from typing import List, Dict

# 2. Third-party
import pytest
from fastapi.testclient import TestClient

# 3. Local application (absolute paths)
from src.api.main import app
from src.core.extraction_service import ExtractionService
from shared.clients.supabase_client import create_supabase_client
```

## Running Tests

### Pre-Test Checklist

**Complete this checklist BEFORE every test run:**

```bash
# 1. Navigate to service directory
cd /srv/luris/be/entity-extraction-service

# 2. MANDATORY: Activate venv
source venv/bin/activate

# 3. Verify activation
which python    # MUST show venv path
which pytest    # MUST show venv path

# 4. Test imports
python -c "from src.api.main import app; print('✅ OK')"

# 5. Verify pytest config
ls -la pyproject.toml  # Must exist
```

### Basic Test Execution

```bash
# Run all tests
pytest tests/ -v

# Run with output capture disabled (see print statements)
pytest tests/ -v -s

# Run with detailed output
pytest tests/ -vv

# Run and stop at first failure
pytest tests/ -x

# Run and stop after N failures
pytest tests/ --maxfail=3
```

### Test Collection

```bash
# List all tests without running
pytest tests/ --collect-only

# Count total tests
pytest tests/ --collect-only -q

# List tests matching pattern
pytest tests/ --collect-only -k "extraction"
```

### Running Specific Tests

```bash
# Run specific test file
pytest tests/unit/test_extraction_service.py -v

# Run specific test function
pytest tests/unit/test_extraction_service.py::test_extract_entities -v

# Run specific test class
pytest tests/unit/test_extraction_service.py::TestExtractionService -v

# Run specific test method in class
pytest tests/unit/test_extraction_service.py::TestExtractionService::test_extract -v

# Run tests matching pattern
pytest tests/ -k "extraction" -v
pytest tests/ -k "test_extract and not slow" -v
```

### Test Categories with Markers

```bash
# Run only unit tests
pytest tests/ -m unit -v

# Run only integration tests
pytest tests/ -m integration -v

# Run all except slow tests
pytest tests/ -m "not slow" -v

# Run unit OR integration tests
pytest tests/ -m "unit or integration" -v
```

### Coverage Reports

```bash
# Run tests with coverage
pytest tests/ --cov=src --cov-report=term-missing

# Generate HTML coverage report
pytest tests/ --cov=src --cov-report=html

# View HTML coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux

# Generate XML coverage report (for CI/CD)
pytest tests/ --cov=src --cov-report=xml

# Set minimum coverage threshold
pytest tests/ --cov=src --cov-fail-under=80
```

### Parallel Test Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (auto-detect CPU count)
pytest tests/ -n auto

# Run tests using 4 workers
pytest tests/ -n 4

# Run tests in parallel with coverage
pytest tests/ -n auto --cov=src --cov-report=html
```

## Test Categories

### Unit Tests

**Location**: `tests/unit/`
**Purpose**: Test individual components in isolation
**Dependencies**: None (mocked)

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific unit test category
pytest tests/unit/test_extraction_service.py -v
pytest tests/unit/test_regex_engine.py -v
pytest tests/unit/test_pattern_loader.py -v
```

**Example Unit Test:**

```python
# tests/unit/test_extraction_service.py
import pytest
from unittest.mock import Mock, patch

from src.core.extraction_service import ExtractionService
from src.models.entities import EntityType
from src.models.requests import ExtractionRequest

@pytest.fixture
def extraction_service():
    """Create ExtractionService with mocked dependencies"""
    with patch('src.core.extraction_service.RegexEngine'):
        service = ExtractionService()
        return service

def test_extract_entities_success(extraction_service):
    """Test successful entity extraction"""
    request = ExtractionRequest(
        document_id="test_001",
        content="In Smith v. Jones, 123 F.3d 456 (9th Cir. 2023)...",
        extraction_mode="regex"
    )

    result = extraction_service.extract(request)

    assert result.status == "completed"
    assert len(result.entities) > 0
    assert result.document_id == "test_001"

def test_extract_empty_content(extraction_service):
    """Test extraction with empty content"""
    request = ExtractionRequest(
        document_id="test_002",
        content="",
        extraction_mode="regex"
    )

    result = extraction_service.extract(request)

    assert result.status == "completed"
    assert len(result.entities) == 0
```

### Integration Tests

**Location**: `tests/integration/`
**Purpose**: Test component interactions
**Dependencies**: Real services (mocked external APIs)

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run with slow tests
pytest tests/integration/ -v -m "not slow"

# Run specific integration test
pytest tests/integration/test_api_endpoints.py -v
```

**Example Integration Test:**

```python
# tests/integration/test_api_endpoints.py
import pytest
from fastapi.testclient import TestClient

from src.api.main import app

@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)

def test_extract_endpoint_success(client):
    """Test POST /extract endpoint"""
    response = client.post("/api/v1/extract", json={
        "document_id": "test_001",
        "content": "In Brown v. Board of Education, 347 U.S. 483 (1954)...",
        "extraction_mode": "regex",
        "confidence_threshold": 0.7
    })

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "completed"
    assert data["document_id"] == "test_001"
    assert len(data["entities"]) > 0
    assert "extraction_id" in data

def test_health_ready_endpoint(client):
    """Test GET /health/ready endpoint"""
    response = client.get("/api/v1/health/ready")

    # May return 200 (full_service) or 503 (vllm_only)
    assert response.status_code in [200, 503]

    data = response.json()
    assert "status" in data
    assert "mode" in data

    # vLLM-only mode is expected behavior
    if data["mode"] == "vllm_only":
        assert data["status"] == "not_ready"
        assert "notes" in data
```

### Performance Tests

**Location**: `tests/performance/`
**Purpose**: Test performance characteristics
**Markers**: `@pytest.mark.slow`

```bash
# Run performance tests
pytest tests/performance/ -v -s

# Run with timing information
pytest tests/performance/ -v -s --durations=10
```

**Example Performance Test:**

```python
# tests/performance/test_extraction_performance.py
import pytest
import time
from fastapi.testclient import TestClient

from src.api.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.slow
def test_extraction_performance(client):
    """Test extraction performance on large document"""
    # Load large test document
    with open("/srv/luris/be/tests/docs/Rahimi.pdf.txt", "r") as f:
        content = f.read()

    start_time = time.time()

    response = client.post("/api/v1/extract", json={
        "document_id": "perf_test_001",
        "content": content,
        "extraction_mode": "regex"
    })

    elapsed_time = time.time() - start_time

    assert response.status_code == 200
    assert elapsed_time < 5.0, f"Extraction took {elapsed_time:.2f}s (expected <5s)"

    data = response.json()
    print(f"\nPerformance Metrics:")
    print(f"  Elapsed time: {elapsed_time:.2f}s")
    print(f"  Processing time: {data['processing_time_ms']}ms")
    print(f"  Entities extracted: {len(data['entities'])}")
```

### End-to-End Tests

**Location**: `tests/e2e/`
**Purpose**: Test complete workflows
**Dependencies**: All services running

```bash
# Run E2E tests (requires all services)
pytest tests/e2e/ -v -s

# Skip E2E tests if services not available
pytest tests/ -v -m "not e2e"
```

## Troubleshooting

### Import Errors

#### Problem: ModuleNotFoundError: No module named 'src'

**Symptoms:**
```bash
$ pytest tests/ -v
ModuleNotFoundError: No module named 'src'
```

**Solution:**

```bash
# 1. Check current directory
pwd  # Should be: /srv/luris/be/entity-extraction-service

# 2. Activate venv
source venv/bin/activate

# 3. Verify venv activation
which python  # Must show venv path

# 4. Test imports
python -c "from src.api.main import app"

# 5. Run tests again
pytest tests/ -v
```

#### Problem: ImportError: attempted relative import beyond top-level package

**Symptoms:**
```bash
ImportError: attempted relative import beyond top-level package
```

**Solution:**

1. **Find offending import:**
```bash
grep -r "from \.\.\." tests/
```

2. **Fix import pattern:**
```python
# Before (WRONG):
from ...src.core.extraction_service import ExtractionService

# After (CORRECT):
from src.core.extraction_service import ExtractionService
```

3. **Verify fix:**
```bash
pytest tests/ --collect-only  # Should succeed
```

### Test Collection Issues

#### Problem: Pytest can't find tests

**Symptoms:**
```bash
$ pytest tests/ -v
collected 0 items
```

**Solution:**

```bash
# 1. Check pyproject.toml exists
ls -la pyproject.toml

# 2. Verify pytest configuration
cat pyproject.toml | grep pytest

# 3. List files pytest is looking for
pytest --collect-only -v

# 4. Check test file naming
ls tests/  # Should have test_*.py or *_test.py files
```

### Test Execution Failures

#### Problem: Tests fail with fixture not found

**Symptoms:**
```bash
fixture 'client' not found
```

**Solution:**

1. **Check for conftest.py:**
```bash
ls -la tests/conftest.py
```

2. **Create conftest.py if missing:**
```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient

from src.api.main import app

@pytest.fixture
def client():
    """Create FastAPI test client"""
    return TestClient(app)
```

#### Problem: Test timeouts

**Symptoms:**
```bash
FAILED tests/test_extraction.py::test_large_document - Timeout
```

**Solution:**

```python
# Add timeout marker to slow tests
@pytest.mark.timeout(300)  # 5 minute timeout
def test_large_document():
    # Test implementation
    pass
```

### Coverage Issues

#### Problem: Coverage report shows 0% coverage

**Symptoms:**
```bash
$ pytest --cov=src
Coverage: 0%
```

**Solution:**

```bash
# 1. Verify venv activation
which python  # Must be venv python

# 2. Reinstall coverage
pip install --upgrade pytest-cov

# 3. Run with explicit paths
pytest tests/ --cov=/srv/luris/be/entity-extraction-service/src

# 4. Check .coveragerc if present
cat .coveragerc
```

## Best Practices

### Writing Testable Code

1. **Use Dependency Injection:**
```python
# Good: Dependencies injected
def extract_entities(
    content: str,
    regex_engine: RegexEngine,
    ai_enhancer: AIEnhancer
) -> List[Entity]:
    # Easily testable with mocks
    pass

# Bad: Hard-coded dependencies
def extract_entities(content: str) -> List[Entity]:
    regex_engine = RegexEngine()  # Hard to mock
    ai_enhancer = AIEnhancer()    # Hard to mock
    pass
```

2. **Keep Functions Small:**
```python
# Good: Small, focused function
def validate_entity(entity: Entity) -> bool:
    return (
        entity.text and
        entity.entity_type and
        entity.confidence_score >= 0.0
    )

# Bad: Large, complex function
def process_document(content: str) -> Dict:
    # 200 lines of mixed concerns
    pass
```

3. **Use Type Hints:**
```python
# Good: Clear types
def extract(
    request: ExtractionRequest
) -> ExtractionResponse:
    pass

# Bad: No types
def extract(request):
    pass
```

### Test Organization

1. **One Test File Per Module:**
```
src/core/extraction_service.py
tests/unit/test_extraction_service.py

src/core/regex_engine.py
tests/unit/test_regex_engine.py
```

2. **Group Related Tests:**
```python
class TestExtractionService:
    """Tests for ExtractionService"""

    def test_extract_success(self):
        pass

    def test_extract_empty_content(self):
        pass

    def test_extract_invalid_mode(self):
        pass
```

3. **Use Descriptive Names:**
```python
# Good: Descriptive
def test_extract_entities_with_high_confidence_threshold():
    pass

# Bad: Vague
def test_extract():
    pass
```

### Fixture Best Practices

1. **Reusable Fixtures:**
```python
# tests/conftest.py
@pytest.fixture
def sample_document():
    """Sample legal document for testing"""
    return "In Brown v. Board of Education, 347 U.S. 483 (1954)..."

@pytest.fixture
def extraction_request(sample_document):
    """Sample extraction request"""
    return ExtractionRequest(
        document_id="test_001",
        content=sample_document,
        extraction_mode="regex"
    )
```

2. **Fixture Scopes:**
```python
@pytest.fixture(scope="session")
def test_database():
    """Database connection (created once per session)"""
    db = create_test_db()
    yield db
    db.close()

@pytest.fixture(scope="function")
def client():
    """Test client (created for each test)"""
    return TestClient(app)
```

### Assertion Best Practices

1. **Use Specific Assertions:**
```python
# Good: Specific
assert response.status_code == 200
assert len(entities) == 5
assert entity.entity_type == EntityType.CASE_CITATION

# Bad: Generic
assert response
assert entities
assert entity
```

2. **Provide Error Messages:**
```python
# Good: With message
assert elapsed_time < 5.0, f"Extraction took {elapsed_time:.2f}s (expected <5s)"

# Bad: No message
assert elapsed_time < 5.0
```

## Continuous Integration

### GitHub Actions Configuration

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.10'

    - name: Activate venv and install dependencies
      run: |
        source venv/bin/activate
        pip install -r requirements.txt

    - name: Run tests
      run: |
        source venv/bin/activate
        pytest tests/ -v --cov=src --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml
```

### Pre-Commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: bash -c 'source venv/bin/activate && pytest tests/ -v'
        language: system
        pass_filenames: false
        always_run: true

      - id: check-imports
        name: check-imports
        entry: bash -c 'grep -r "from \.\.\." tests/ && exit 1 || exit 0'
        language: system
        pass_filenames: false
        always_run: true
```

## Quick Reference

### Common Commands

```bash
# Setup
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate

# Verify
which python && which pytest
python -c "from src.api.main import app; print('✅ OK')"

# Run tests
pytest tests/ -v                          # All tests
pytest tests/unit/ -v                     # Unit tests only
pytest tests/integration/ -v              # Integration tests only
pytest tests/ -k "extraction" -v          # Pattern match
pytest tests/ -x                          # Stop at first failure
pytest tests/ --cov=src --cov-report=html # With coverage

# Debug
pytest tests/ -v -s                       # Show print statements
pytest tests/ -vv                         # Very verbose
pytest tests/ --pdb                       # Drop into debugger on failure
```

### Troubleshooting Checklist

- [ ] In correct directory: `/srv/luris/be/entity-extraction-service`
- [ ] Virtual environment activated: `source venv/bin/activate`
- [ ] Correct Python: `which python` shows venv path
- [ ] Imports work: `python -c "from src.api.main import app"`
- [ ] Pytest configured: `pyproject.toml` exists
- [ ] No relative imports: `grep -r "from \.\.\." tests/` returns nothing
- [ ] No sys.path manipulation: `grep -r "sys.path" tests/` returns nothing

---

**Document Version**: 2.0.0
**Last Updated**: 2025-01-14
**Status**: Current (Post P0/P1 Fixes)
