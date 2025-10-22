# Document Upload Service API Reference

## Overview

The Document Upload Service provides comprehensive document upload, processing, and storage capabilities for legal documents with advanced OCR and conversion features.

- **Service**: Document Upload Service  
- **Version**: 1.0.0
- **Port**: 8008
- **Base URL**: `http://localhost:8008/api/v1`
- **Health Check**: `http://localhost:8008/api/v1/health/ping`

## Features

- **Advanced Document Processing**: MarkItDown conversion with intelligent OCR fallback
- **Format Support**: PDF, DOCX, PPTX, XLSX, TXT, MD, HTML, Images
- **Quality Assessment**: Text extraction quality analysis and validation
- **Duplicate Detection**: Content-based SHA256 hashing for duplicate prevention
- **Schema Routing**: Automatic document classification and routing
- **Comprehensive Metadata**: Detailed file and processing information

## Authentication

This service operates without authentication for internal use. Ensure proper network security in production deployments.

## Content Types

All requests use `multipart/form-data` for file uploads and `application/json` for responses.

---

## Main Endpoints

### Document Upload

#### POST /upload

Upload and convert a single document with advanced processing capabilities.

**Request Parameters:**

- `file` (required): File to upload and convert to markdown
- `client_id` (required): Client identifier for document organization  
- `case_id` (optional): Case identifier for document grouping
- `override_schema` (optional): Schema override (law, client, graph)
- `enable_ocr` (optional, default: true): Enable OCR processing for scanned documents
- `quality_threshold` (optional): Custom quality threshold for OCR fallback

**Example Request:**
```bash
curl -X POST "http://localhost:8008/api/v1/upload" \
     -F "file=@document.pdf" \
     -F "client_id=client_123" \
     -F "case_id=case_456" \
     -F "enable_ocr=true"
```

**Success Response (200):**
```json
{
  "status": "success",
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "does_exist": false,
  "markdown_content": "# Document Title\n\nDocument content converted to markdown...",
  "metadata": {
    "filename": "document.pdf",
    "original_size": 1048576,
    "file_size_bytes": 1048576,
    "mime_type": "application/pdf",
    "content_hash": "sha256:abcdef123456...",
    "word_count": 1250,
    "processing_time_ms": 3420,
    "total_processing_time_ms": 3456.78,
    "document_schema": "law",
    "uploaded_at": "2025-01-15T10:30:00Z"
  },
  "processing_info": {
    "extraction_method": "markitdown_primary",
    "ocr_used": false,
    "quality_score": 0.95,
    "conversion_successful": true,
    "processing_stages": [
      "file_validation",
      "duplicate_check",
      "markitdown_conversion",
      "quality_assessment",
      "schema_routing",
      "storage"
    ]
  }
}
```

**Duplicate Response (200):**
```json
{
  "status": "duplicate",
  "document_id": "existing-doc-id",
  "does_exist": true,
  "markdown_content": "Previously processed content...",
  "metadata": {
    "content_hash": "sha256:abcdef123456...",
    "original_upload_date": "2025-01-10T15:20:00Z",
    "duplicate_detected_at": "2025-01-15T10:30:00Z"
  }
}
```

### Batch Upload

#### POST /upload/batch

Upload multiple documents in a single request with concurrent processing.

**Request Parameters:**

- `files` (required): Array of files to upload
- `client_id` (required): Client identifier for all documents
- `case_id` (optional): Case identifier for all documents  
- `enable_ocr` (optional, default: true): Enable OCR for all documents

**Example Request:**
```bash
curl -X POST "http://localhost:8008/api/v1/upload/batch" \
     -F "files=@document1.pdf" \
     -F "files=@document2.docx" \
     -F "client_id=client_123" \
     -F "case_id=case_456"
```

**Response (200):**
```json
{
  "batch_status": "completed",
  "summary": {
    "total_files": 2,
    "successful_uploads": 2,
    "failed_uploads": 0,
    "processing_time_ms": 5678.90
  },
  "results": [
    {
      "status": "success", 
      "document_id": "doc-1-id",
      "filename": "document1.pdf",
      "batch_index": 0,
      "processing_time_ms": 3456.78
    },
    {
      "status": "success",
      "document_id": "doc-2-id", 
      "filename": "document2.docx",
      "batch_index": 1,
      "processing_time_ms": 2222.12
    }
  ],
  "request_id": "batch-req-123",
  "timestamp": 1705312200.0
}
```

### Upload Status

#### GET /upload/status/{document_id}

Get comprehensive status and details of a previously uploaded document.

**Path Parameters:**
- `document_id` (required): Document identifier

**Example Request:**
```bash
curl "http://localhost:8008/api/v1/upload/status/550e8400-e29b-41d4-a716-446655440000"
```

**Success Response (200):**
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "metadata": {
    "filename": "document.pdf",
    "client_id": "client_123",
    "case_id": "case_456",
    "file_size_bytes": 1048576,
    "mime_type": "application/pdf",
    "content_hash": "sha256:abcdef123456...",
    "uploaded_at": "2025-01-15T10:30:00Z",
    "last_accessed": "2025-01-15T10:45:00Z",
    "word_count": 1250,
    "document_schema": "law"
  },
  "storage": {
    "file_path": "clients/client_123/cases/case_456/documents/doc-id/document.pdf",
    "storage_bucket": "document-uploads"
  },
  "processing_info": {
    "extraction_method": "markitdown_primary",
    "quality_score": 0.95,
    "processing_time_ms": 3456
  },
  "availability": {
    "markdown_available": true,
    "original_file_available": true
  }
}
```

### Format Information

#### GET /upload/formats

Get detailed information about supported file formats and processing capabilities.

**Example Request:**
```bash
curl "http://localhost:8008/api/v1/upload/formats"
```

**Response (200):**
```json
{
  "supported_formats": {
    "pdf": {
      "description": "Portable Document Format",
      "extensions": [".pdf"],
      "processing_methods": ["markitdown", "ocr_fallback"],
      "ocr_supported": true,
      "notes": "Supports both text-based and scanned PDFs"
    },
    "docx": {
      "description": "Microsoft Word Document", 
      "extensions": [".docx"],
      "processing_methods": ["markitdown"],
      "ocr_supported": false,
      "notes": "Native text extraction with formatting preservation"
    },
    "images": {
      "description": "Image files with OCR text extraction",
      "extensions": [".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".webp"],
      "processing_methods": ["ocr"],
      "ocr_supported": true,
      "notes": "Uses Tesseract OCR for text extraction"
    }
  },
  "file_limits": {
    "max_file_size_mb": 100,
    "max_files_per_batch": 50,
    "processing_timeout_seconds": 300
  },
  "ocr_capabilities": {
    "enabled": true,
    "primary_language": "eng",
    "additional_languages": ["spa", "fra"],
    "quality_threshold": 0.7,
    "dpi": 300
  },
  "processing_features": {
    "duplicate_detection": true,
    "schema_routing": true,
    "metadata_extraction": true,
    "quality_assessment": true,
    "parallel_processing": true
  }
}
```

---

## Health & Status Endpoints

### Health Check Endpoints

#### GET /health

Basic health check endpoint with service status information.

**Request:**
```bash
curl http://localhost:8008/api/v1/health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-29T10:30:00Z",
  "service": "document-upload-service",
  "version": "1.0.0",
  "uptime_seconds": 3600.45
}
```

**Response (503 Service Unavailable) - If unhealthy:**
```json
{
  "status": "unhealthy",
  "timestamp": "2025-07-29T10:30:00Z",
  "service": "document-upload-service",
  "version": "1.0.0",
  "errors": ["supabase_connection_failed", "tesseract_unavailable"]
}
```

#### GET /health/ping

Simple ping check for load balancers with minimal response data.

**Response (200):**
```json
{
  "ping": "pong",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### GET /health/ready

Readiness check with dependency verification to ensure the service can process requests.

**Request:**
```bash
curl http://localhost:8008/api/v1/health/ready
```

**Response (200 OK) - Ready to process requests:**
```json
{
  "status": "ready",
  "timestamp": "2025-07-29T10:30:00Z",
  "service": "document-upload-service",
  "version": "1.0.0",
  "ready": true,
  "checks": {
    "supabase": "healthy",
    "tesseract": "healthy",
    "markitdown": "healthy",
    "storage": "healthy"
  }
}
```

**Response (503 Service Unavailable) - Not ready:**
```json
{
  "status": "not_ready",
  "timestamp": "2025-07-29T10:30:00Z",
  "service": "document-upload-service",
  "version": "1.0.0",
  "ready": false,
  "checks": {
    "supabase": "healthy",
    "tesseract": "unhealthy",
    "markitdown": "healthy",
    "storage": "healthy"
  },
  "blocking_issues": ["tesseract_unavailable"]
}
```

#### GET /health/detailed

Comprehensive health status including component checks.

**Response (200):**
```json
{
  "status": "healthy",
  "service": "document-upload-service", 
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "checks": {
    "supabase": {
      "status": "healthy",
      "response_time_ms": 45
    },
    "tesseract": {
      "status": "healthy", 
      "version": "5.3.0"
    },
    "markitdown": {
      "status": "healthy",
      "version": "0.0.1a2"
    },
    "storage": {
      "status": "healthy",
      "free_space_gb": 250.5
    }
  },
  "metrics": {
    "total_uploads": 1250,
    "successful_uploads": 1238,
    "failed_uploads": 12,
    "average_processing_time_ms": 2345
  }
}
```

---

## Error Responses

The service returns structured error responses with detailed information:

### Validation Errors (400)

```json
{
  "status": "error",
  "error_code": "INVALID_CLIENT_ID", 
  "error_message": "Client ID is required and cannot be empty",
  "details": {
    "provided_client_id": "",
    "requirements": "Non-empty client identifier required"
  },
  "timestamp": 1705312200.0,
  "service": "document-upload-service"
}
```

### File Too Large (413)

```json
{
  "status": "error",
  "error_code": "FILE_TOO_LARGE",
  "error_message": "File size 150.5MB exceeds maximum 100MB",
  "details": {
    "filename": "large_document.pdf",
    "file_size_mb": 150.5,
    "max_file_size_mb": 100,
    "processing_time_ms": 125.5
  }
}
```

### Processing Errors (422)

```json
{
  "status": "error",
  "error_code": "CONVERSION_FAILED",
  "error_message": "Document conversion failed: corrupted PDF structure",
  "details": {
    "filename": "corrupted.pdf",
    "processing_time_ms": 1250.5,
    "attempted_methods": ["markitdown", "ocr_fallback"],
    "suggestion": "Verify file integrity and try again"
  }
}
```

### System Errors (500)

```json
{
  "status": "error",
  "error_code": "SYSTEM_ERROR", 
  "error_message": "An internal error occurred during document processing",
  "details": {
    "filename": "document.pdf",
    "processing_time_ms": 2345.5,
    "error_details": "Contact support for assistance",
    "request_id": "req-12345"
  }
}
```

---

## Processing Pipeline

### Document Processing Flow

1. **File Validation**: Size, type, and content validation
2. **Duplicate Detection**: SHA256 content hashing 
3. **Format Detection**: Automatic file format identification
4. **Conversion Processing**:
   - Primary: MarkItDown conversion for text-based documents
   - Fallback: OCR processing for scanned documents  
   - Quality assessment and method selection
5. **Schema Routing**: Automatic classification (law/client/graph)
6. **Storage**: Original file storage in Supabase Storage
7. **Registry**: Metadata and content storage in document_registry

### Quality Assessment

- **Text Quality Analysis**: Evaluates extraction quality
- **OCR Confidence Scoring**: Per-word confidence metrics
- **Conversion Validation**: Ensures successful text extraction
- **Quality Thresholds**: Configurable quality requirements

### Schema Routing Logic

Documents are automatically classified:

- **Law Schema**: Court opinions, statutes, regulations
- **Client Schema**: Contracts, correspondence, business documents  
- **Graph Schema**: Knowledge graph and relationship data

---

## Rate Limits

- **Single Upload**: 100 requests per minute per client
- **Batch Upload**: 10 concurrent batches per service instance
- **File Size**: Maximum 100MB per file
- **Batch Size**: Maximum 50 files per batch

---

## Client Examples

### Python Client

```python
import httpx
import asyncio

async def upload_document(file_path: str, client_id: str):
    async with httpx.AsyncClient() as client:
        with open(file_path, "rb") as f:
            response = await client.post(
                "http://localhost:8008/api/v1/upload",
                files={"file": (file_path, f, "application/pdf")},
                data={
                    "client_id": client_id,
                    "case_id": "case_123", 
                    "enable_ocr": True
                }
            )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Upload successful: {result['document_id']}")
            return result
        else:
            print(f"Upload failed: {response.text}")
            return None

# Usage
result = asyncio.run(upload_document("document.pdf", "client_123"))
```

### JavaScript/Node.js Client

```javascript
const FormData = require('form-data');
const fs = require('fs');

async function uploadDocument(filePath, clientId) {
    const form = new FormData();
    form.append('file', fs.createReadStream(filePath));
    form.append('client_id', clientId);
    form.append('case_id', 'case_123');
    form.append('enable_ocr', 'true');
    
    const response = await fetch('http://localhost:8008/api/v1/upload', {
        method: 'POST',
        body: form
    });
    
    const result = await response.json();
    
    if (response.ok) {
        console.log(`Upload successful: ${result.document_id}`);
        return result;
    } else {
        console.error(`Upload failed: ${result.error_message}`);
        return null;
    }
}
```

---

## Monitoring & Troubleshooting

### Performance Metrics

- **Throughput**: 50 small files/minute, 20 medium files/minute, 5 large files/minute
- **Memory Usage**: 512MB - 2GB depending on file sizes and OCR usage
- **OCR Performance**: ~1-2 pages/second with parallel processing

### Common Issues

1. **OCR Not Working**: Verify Tesseract installation and system dependencies
2. **Large File Failures**: Check file size limits and processing timeout settings
3. **Storage Issues**: Verify Supabase configuration and bucket permissions
4. **Performance Issues**: Monitor memory usage and adjust parallel processing

### Health Monitoring

Use `/health/detailed` endpoint for comprehensive service monitoring including:
- Component health status
- Performance metrics
- Resource utilization
- Recent error rates

For detailed troubleshooting, refer to service logs and the comprehensive error responses provided by all endpoints.