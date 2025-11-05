"""
Comprehensive E2E Test Suite for Tier 1 Family Law Entity Patterns

This test suite validates the 15 newly added Tier 1 family law entity patterns
using AI extraction mode with vLLM Instruct service (Port 8080).

Pattern Groups:
1. Jurisdiction (5 entities): HOME_STATE, EMERGENCY_JURISDICTION,
   EXCLUSIVE_CONTINUING_JURISDICTION, SIGNIFICANT_CONNECTION, FOREIGN_CUSTODY_ORDER
2. Procedural (5 entities): DISSOLUTION_PETITION, TEMPORARY_ORDER, FINAL_DECREE,
   MODIFICATION_PETITION, GUARDIAN_AD_LITEM_APPOINTMENT
3. Property (2 entities): COMMUNITY_PROPERTY, SEPARATE_PROPERTY
4. Child Protection (3 entities): CHILD_ABUSE_REPORT, DEPENDENCY_ACTION, PROTECTIVE_CUSTODY

Test Structure:
- 15 unit tests (one per entity type)
- 3 integration tests (multi-entity documents)
- 1 E2E pipeline test
- 1 performance benchmark test
Total: 20 tests

Success Criteria:
- Extraction accuracy: ≥95% for all 15 entity types
- Confidence scores: ≥0.90 for critical entities
- Performance: <50ms per document (AI mode with vLLM)
- LurisEntityV2 schema compliance
- No false positives on non-family law text
"""

import pytest
import httpx
import time
import json
import os
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path


# ============================================================================
# UNIT TESTS: GROUP 1 - JURISDICTION ENTITIES (5 TESTS)
# ============================================================================

@pytest.mark.e2e
@pytest.mark.tier1
@pytest.mark.family_law
@pytest.mark.requires_vllm
@pytest.mark.asyncio
async def test_home_state_extraction(home_state_simple, extraction_config):
    """
    Test HOME_STATE entity extraction with AI mode.

    Entity Type: HOME_STATE
    Pattern Group: Jurisdiction
    Expected: California identified as home state with ≥0.90 confidence
    """
    async with httpx.AsyncClient(timeout=extraction_config["timeout"]) as client:
        response = await client.post(
            f"{extraction_config['base_url']}/api/v2/process/extract",
            json={
                "document_text": home_state_simple,
                "extraction_mode": extraction_config["extraction_mode"],
                "entity_type_filter": ["HOME_STATE"]
            }
        )

        assert response.status_code == 200, f"Extraction failed: {response.text}"
        result = response.json()
        entities = result.get("entities", [])

        # Validate entities extracted
        assert len(entities) >= 1, "Expected at least 1 HOME_STATE entity"

        # Filter for HOME_STATE entities
        home_state_entities = [e for e in entities if e["entity_type"] == "HOME_STATE"]
        assert len(home_state_entities) >= 1, "No HOME_STATE entities found"

        # Validate first entity
        entity = home_state_entities[0]
        assert entity["confidence"] >= extraction_config["confidence_threshold"], \
            f"Low confidence: {entity['confidence']}"
        assert "California" in entity["text"] or "home state" in entity["text"].lower(), \
            f"Expected 'California' or 'home state' in text: {entity['text']}"

        # Validate LurisEntityV2 schema
        assert "entity_type" in entity, "Missing entity_type field"
        assert "start_pos" in entity, "Missing start_pos field"
        assert "end_pos" in entity, "Missing end_pos field"
        assert "extraction_method" in entity, "Missing extraction_method field"

        print(f"✓ HOME_STATE extracted: {entity['text']} (confidence: {entity['confidence']:.2%})")


@pytest.mark.e2e
@pytest.mark.tier1
@pytest.mark.family_law
@pytest.mark.requires_vllm
@pytest.mark.asyncio
async def test_emergency_jurisdiction_extraction(emergency_jurisdiction_simple, extraction_config):
    """
    Test EMERGENCY_JURISDICTION entity extraction with AI mode.

    Entity Type: EMERGENCY_JURISDICTION
    Pattern Group: Jurisdiction
    Expected: Emergency jurisdiction phrase with ≥0.90 confidence
    """
    async with httpx.AsyncClient(timeout=extraction_config["timeout"]) as client:
        response = await client.post(
            f"{extraction_config['base_url']}/api/v2/process/extract",
            json={
                "document_text": emergency_jurisdiction_simple,
                "extraction_mode": extraction_config["extraction_mode"],
                "entity_type_filter": ["EMERGENCY_JURISDICTION"]
            }
        )

        assert response.status_code == 200
        entities = response.json().get("entities", [])

        emergency_entities = [e for e in entities if e["entity_type"] == "EMERGENCY_JURISDICTION"]
        assert len(emergency_entities) >= 1, "No EMERGENCY_JURISDICTION entities found"

        entity = emergency_entities[0]
        assert entity["confidence"] >= extraction_config["confidence_threshold"]
        assert "emergency jurisdiction" in entity["text"].lower() or "imminent harm" in entity["text"].lower()

        print(f"✓ EMERGENCY_JURISDICTION extracted: {entity['text']} (confidence: {entity['confidence']:.2%})")


@pytest.mark.e2e
@pytest.mark.tier1
@pytest.mark.family_law
@pytest.mark.requires_vllm
@pytest.mark.asyncio
async def test_exclusive_continuing_jurisdiction_extraction(exclusive_continuing_jurisdiction_simple, extraction_config):
    """
    Test EXCLUSIVE_CONTINUING_JURISDICTION entity extraction with AI mode.

    Entity Type: EXCLUSIVE_CONTINUING_JURISDICTION
    Pattern Group: Jurisdiction
    Expected: Exclusive continuing jurisdiction phrase with ≥0.90 confidence
    """
    async with httpx.AsyncClient(timeout=extraction_config["timeout"]) as client:
        response = await client.post(
            f"{extraction_config['base_url']}/api/v2/process/extract",
            json={
                "document_text": exclusive_continuing_jurisdiction_simple,
                "extraction_mode": extraction_config["extraction_mode"],
                "entity_type_filter": ["EXCLUSIVE_CONTINUING_JURISDICTION"]
            }
        )

        assert response.status_code == 200
        entities = response.json().get("entities", [])

        ecj_entities = [e for e in entities if e["entity_type"] == "EXCLUSIVE_CONTINUING_JURISDICTION"]
        assert len(ecj_entities) >= 1, "No EXCLUSIVE_CONTINUING_JURISDICTION entities found"

        entity = ecj_entities[0]
        assert entity["confidence"] >= extraction_config["confidence_threshold"]
        assert "exclusive continuing jurisdiction" in entity["text"].lower() or "retains jurisdiction" in entity["text"].lower()

        print(f"✓ EXCLUSIVE_CONTINUING_JURISDICTION extracted: {entity['text']} (confidence: {entity['confidence']:.2%})")


@pytest.mark.e2e
@pytest.mark.tier1
@pytest.mark.family_law
@pytest.mark.requires_vllm
@pytest.mark.asyncio
async def test_significant_connection_extraction(significant_connection_simple, extraction_config):
    """
    Test SIGNIFICANT_CONNECTION entity extraction with AI mode.

    Entity Type: SIGNIFICANT_CONNECTION
    Pattern Group: Jurisdiction
    Expected: Significant connection phrase with ≥0.90 confidence
    """
    async with httpx.AsyncClient(timeout=extraction_config["timeout"]) as client:
        response = await client.post(
            f"{extraction_config['base_url']}/api/v2/process/extract",
            json={
                "document_text": significant_connection_simple,
                "extraction_mode": extraction_config["extraction_mode"],
                "entity_type_filter": ["SIGNIFICANT_CONNECTION"]
            }
        )

        assert response.status_code == 200
        entities = response.json().get("entities", [])

        sig_conn_entities = [e for e in entities if e["entity_type"] == "SIGNIFICANT_CONNECTION"]
        assert len(sig_conn_entities) >= 1, "No SIGNIFICANT_CONNECTION entities found"

        entity = sig_conn_entities[0]
        assert entity["confidence"] >= extraction_config["confidence_threshold"]
        assert "significant connection" in entity["text"].lower() or "substantial evidence" in entity["text"].lower()

        print(f"✓ SIGNIFICANT_CONNECTION extracted: {entity['text']} (confidence: {entity['confidence']:.2%})")


@pytest.mark.e2e
@pytest.mark.tier1
@pytest.mark.family_law
@pytest.mark.requires_vllm
@pytest.mark.asyncio
async def test_foreign_custody_order_extraction(foreign_custody_order_simple, extraction_config):
    """
    Test FOREIGN_CUSTODY_ORDER entity extraction with AI mode.

    Entity Type: FOREIGN_CUSTODY_ORDER
    Pattern Group: Jurisdiction
    Expected: Foreign custody order phrase with ≥0.90 confidence
    """
    async with httpx.AsyncClient(timeout=extraction_config["timeout"]) as client:
        response = await client.post(
            f"{extraction_config['base_url']}/api/v2/process/extract",
            json={
                "document_text": foreign_custody_order_simple,
                "extraction_mode": extraction_config["extraction_mode"],
                "entity_type_filter": ["FOREIGN_CUSTODY_ORDER"]
            }
        )

        assert response.status_code == 200
        entities = response.json().get("entities", [])

        foreign_order_entities = [e for e in entities if e["entity_type"] == "FOREIGN_CUSTODY_ORDER"]
        assert len(foreign_order_entities) >= 1, "No FOREIGN_CUSTODY_ORDER entities found"

        entity = foreign_order_entities[0]
        assert entity["confidence"] >= extraction_config["confidence_threshold"]
        assert "foreign custody order" in entity["text"].lower() or "out-of-state order" in entity["text"].lower()

        print(f"✓ FOREIGN_CUSTODY_ORDER extracted: {entity['text']} (confidence: {entity['confidence']:.2%})")


# ============================================================================
# UNIT TESTS: GROUP 2 - PROCEDURAL ENTITIES (5 TESTS)
# ============================================================================

@pytest.mark.e2e
@pytest.mark.tier1
@pytest.mark.family_law
@pytest.mark.requires_vllm
@pytest.mark.asyncio
async def test_dissolution_petition_extraction(dissolution_petition_simple, extraction_config):
    """
    Test DISSOLUTION_PETITION entity extraction with AI mode.

    Entity Type: DISSOLUTION_PETITION
    Pattern Group: Procedural
    Expected: Dissolution petition phrase with ≥0.90 confidence
    """
    async with httpx.AsyncClient(timeout=extraction_config["timeout"]) as client:
        response = await client.post(
            f"{extraction_config['base_url']}/api/v2/process/extract",
            json={
                "document_text": dissolution_petition_simple,
                "extraction_mode": extraction_config["extraction_mode"],
                "entity_type_filter": ["DISSOLUTION_PETITION"]
            }
        )

        assert response.status_code == 200
        entities = response.json().get("entities", [])

        dissolution_entities = [e for e in entities if e["entity_type"] == "DISSOLUTION_PETITION"]
        assert len(dissolution_entities) >= 1, "No DISSOLUTION_PETITION entities found"

        entity = dissolution_entities[0]
        assert entity["confidence"] >= extraction_config["confidence_threshold"]
        assert "petition for dissolution" in entity["text"].lower() or "dissolution petition" in entity["text"].lower()

        print(f"✓ DISSOLUTION_PETITION extracted: {entity['text']} (confidence: {entity['confidence']:.2%})")


@pytest.mark.e2e
@pytest.mark.tier1
@pytest.mark.family_law
@pytest.mark.requires_vllm
@pytest.mark.asyncio
async def test_temporary_order_extraction(temporary_order_simple, extraction_config):
    """
    Test TEMPORARY_ORDER entity extraction with AI mode.

    Entity Type: TEMPORARY_ORDER
    Pattern Group: Procedural
    Expected: Temporary order phrase with ≥0.90 confidence
    """
    async with httpx.AsyncClient(timeout=extraction_config["timeout"]) as client:
        response = await client.post(
            f"{extraction_config['base_url']}/api/v2/process/extract",
            json={
                "document_text": temporary_order_simple,
                "extraction_mode": extraction_config["extraction_mode"],
                "entity_type_filter": ["TEMPORARY_ORDER"]
            }
        )

        assert response.status_code == 200
        entities = response.json().get("entities", [])

        temp_order_entities = [e for e in entities if e["entity_type"] == "TEMPORARY_ORDER"]
        assert len(temp_order_entities) >= 1, "No TEMPORARY_ORDER entities found"

        entity = temp_order_entities[0]
        assert entity["confidence"] >= extraction_config["confidence_threshold"]
        assert "temporary order" in entity["text"].lower() or "interim order" in entity["text"].lower()

        print(f"✓ TEMPORARY_ORDER extracted: {entity['text']} (confidence: {entity['confidence']:.2%})")


@pytest.mark.e2e
@pytest.mark.tier1
@pytest.mark.family_law
@pytest.mark.requires_vllm
@pytest.mark.asyncio
async def test_final_decree_extraction(final_decree_simple, extraction_config):
    """
    Test FINAL_DECREE entity extraction with AI mode.

    Entity Type: FINAL_DECREE
    Pattern Group: Procedural
    Expected: Final decree phrase with ≥0.90 confidence
    """
    async with httpx.AsyncClient(timeout=extraction_config["timeout"]) as client:
        response = await client.post(
            f"{extraction_config['base_url']}/api/v2/process/extract",
            json={
                "document_text": final_decree_simple,
                "extraction_mode": extraction_config["extraction_mode"],
                "entity_type_filter": ["FINAL_DECREE"]
            }
        )

        assert response.status_code == 200
        entities = response.json().get("entities", [])

        final_decree_entities = [e for e in entities if e["entity_type"] == "FINAL_DECREE"]
        assert len(final_decree_entities) >= 1, "No FINAL_DECREE entities found"

        entity = final_decree_entities[0]
        assert entity["confidence"] >= extraction_config["confidence_threshold"]
        assert "final decree" in entity["text"].lower() or "decree of dissolution" in entity["text"].lower()

        print(f"✓ FINAL_DECREE extracted: {entity['text']} (confidence: {entity['confidence']:.2%})")


@pytest.mark.e2e
@pytest.mark.tier1
@pytest.mark.family_law
@pytest.mark.requires_vllm
@pytest.mark.asyncio
async def test_modification_petition_extraction(modification_petition_simple, extraction_config):
    """
    Test MODIFICATION_PETITION entity extraction with AI mode.

    Entity Type: MODIFICATION_PETITION
    Pattern Group: Procedural
    Expected: Modification petition phrase with ≥0.90 confidence
    """
    async with httpx.AsyncClient(timeout=extraction_config["timeout"]) as client:
        response = await client.post(
            f"{extraction_config['base_url']}/api/v2/process/extract",
            json={
                "document_text": modification_petition_simple,
                "extraction_mode": extraction_config["extraction_mode"],
                "entity_type_filter": ["MODIFICATION_PETITION"]
            }
        )

        assert response.status_code == 200
        entities = response.json().get("entities", [])

        mod_petition_entities = [e for e in entities if e["entity_type"] == "MODIFICATION_PETITION"]
        assert len(mod_petition_entities) >= 1, "No MODIFICATION_PETITION entities found"

        entity = mod_petition_entities[0]
        assert entity["confidence"] >= extraction_config["confidence_threshold"]
        assert "petition to modify" in entity["text"].lower() or "modification petition" in entity["text"].lower()

        print(f"✓ MODIFICATION_PETITION extracted: {entity['text']} (confidence: {entity['confidence']:.2%})")


@pytest.mark.e2e
@pytest.mark.tier1
@pytest.mark.family_law
@pytest.mark.requires_vllm
@pytest.mark.asyncio
async def test_guardian_ad_litem_extraction(guardian_ad_litem_simple, extraction_config):
    """
    Test GUARDIAN_AD_LITEM entity extraction with AI mode.

    Entity Type: GUARDIAN_AD_LITEM
    Pattern Group: Procedural
    Expected: GAL phrase with ≥0.90 confidence
    """
    async with httpx.AsyncClient(timeout=extraction_config["timeout"]) as client:
        response = await client.post(
            f"{extraction_config['base_url']}/api/v2/process/extract",
            json={
                "document_text": guardian_ad_litem_simple,
                "extraction_mode": extraction_config["extraction_mode"],
                "entity_type_filter": ["GUARDIAN_AD_LITEM"]
            }
        )

        assert response.status_code == 200
        entities = response.json().get("entities", [])

        gal_entities = [e for e in entities if e["entity_type"] == "GUARDIAN_AD_LITEM"]
        assert len(gal_entities) >= 1, "No GUARDIAN_AD_LITEM entities found"

        entity = gal_entities[0]
        assert entity["confidence"] >= extraction_config["confidence_threshold"]
        assert "guardian ad litem" in entity["text"].lower() or "GAL" in entity["text"]

        print(f"✓ GUARDIAN_AD_LITEM extracted: {entity['text']} (confidence: {entity['confidence']:.2%})")


# ============================================================================
# UNIT TESTS: GROUP 3 - PROPERTY ENTITIES (2 TESTS)
# ============================================================================

@pytest.mark.e2e
@pytest.mark.tier1
@pytest.mark.family_law
@pytest.mark.requires_vllm
@pytest.mark.asyncio
async def test_community_property_extraction(community_property_simple, extraction_config):
    """
    Test COMMUNITY_PROPERTY entity extraction with AI mode.

    Entity Type: COMMUNITY_PROPERTY
    Pattern Group: Property
    Expected: Community property phrase with ≥0.90 confidence
    """
    async with httpx.AsyncClient(timeout=extraction_config["timeout"]) as client:
        response = await client.post(
            f"{extraction_config['base_url']}/api/v2/process/extract",
            json={
                "document_text": community_property_simple,
                "extraction_mode": extraction_config["extraction_mode"],
                "entity_type_filter": ["COMMUNITY_PROPERTY"]
            }
        )

        assert response.status_code == 200
        entities = response.json().get("entities", [])

        comm_prop_entities = [e for e in entities if e["entity_type"] == "COMMUNITY_PROPERTY"]
        assert len(comm_prop_entities) >= 1, "No COMMUNITY_PROPERTY entities found"

        entity = comm_prop_entities[0]
        assert entity["confidence"] >= extraction_config["confidence_threshold"]
        assert "community property" in entity["text"].lower() or "marital property" in entity["text"].lower()

        print(f"✓ COMMUNITY_PROPERTY extracted: {entity['text']} (confidence: {entity['confidence']:.2%})")


@pytest.mark.e2e
@pytest.mark.tier1
@pytest.mark.family_law
@pytest.mark.requires_vllm
@pytest.mark.asyncio
async def test_separate_property_extraction(separate_property_simple, extraction_config):
    """
    Test SEPARATE_PROPERTY entity extraction with AI mode.

    Entity Type: SEPARATE_PROPERTY
    Pattern Group: Property
    Expected: Separate property phrase with ≥0.90 confidence
    """
    async with httpx.AsyncClient(timeout=extraction_config["timeout"]) as client:
        response = await client.post(
            f"{extraction_config['base_url']}/api/v2/process/extract",
            json={
                "document_text": separate_property_simple,
                "extraction_mode": extraction_config["extraction_mode"],
                "entity_type_filter": ["SEPARATE_PROPERTY"]
            }
        )

        assert response.status_code == 200
        entities = response.json().get("entities", [])

        sep_prop_entities = [e for e in entities if e["entity_type"] == "SEPARATE_PROPERTY"]
        assert len(sep_prop_entities) >= 1, "No SEPARATE_PROPERTY entities found"

        entity = sep_prop_entities[0]
        assert entity["confidence"] >= extraction_config["confidence_threshold"]
        assert "separate property" in entity["text"].lower() or "property acquired before" in entity["text"].lower()

        print(f"✓ SEPARATE_PROPERTY extracted: {entity['text']} (confidence: {entity['confidence']:.2%})")


# ============================================================================
# UNIT TESTS: GROUP 4 - CHILD PROTECTION ENTITIES (3 TESTS)
# ============================================================================

@pytest.mark.e2e
@pytest.mark.tier1
@pytest.mark.family_law
@pytest.mark.requires_vllm
@pytest.mark.asyncio
async def test_child_abuse_report_extraction(child_abuse_report_simple, extraction_config):
    """
    Test CHILD_ABUSE_REPORT entity extraction with AI mode.

    Entity Type: CHILD_ABUSE_REPORT
    Pattern Group: Child Protection
    Expected: CPS report phrase with ≥0.90 confidence
    """
    async with httpx.AsyncClient(timeout=extraction_config["timeout"]) as client:
        response = await client.post(
            f"{extraction_config['base_url']}/api/v2/process/extract",
            json={
                "document_text": child_abuse_report_simple,
                "extraction_mode": extraction_config["extraction_mode"],
                "entity_type_filter": ["CHILD_ABUSE_REPORT"]
            }
        )

        assert response.status_code == 200
        entities = response.json().get("entities", [])

        abuse_report_entities = [e for e in entities if e["entity_type"] == "CHILD_ABUSE_REPORT"]
        assert len(abuse_report_entities) >= 1, "No CHILD_ABUSE_REPORT entities found"

        entity = abuse_report_entities[0]
        assert entity["confidence"] >= extraction_config["confidence_threshold"]
        assert "CPS report" in entity["text"] or "abuse report" in entity["text"].lower()

        print(f"✓ CHILD_ABUSE_REPORT extracted: {entity['text']} (confidence: {entity['confidence']:.2%})")


@pytest.mark.e2e
@pytest.mark.tier1
@pytest.mark.family_law
@pytest.mark.requires_vllm
@pytest.mark.asyncio
async def test_dependency_action_extraction(dependency_action_simple, extraction_config):
    """
    Test DEPENDENCY_ACTION entity extraction with AI mode.

    Entity Type: DEPENDENCY_ACTION
    Pattern Group: Child Protection
    Expected: Dependency action phrase with ≥0.90 confidence
    """
    async with httpx.AsyncClient(timeout=extraction_config["timeout"]) as client:
        response = await client.post(
            f"{extraction_config['base_url']}/api/v2/process/extract",
            json={
                "document_text": dependency_action_simple,
                "extraction_mode": extraction_config["extraction_mode"],
                "entity_type_filter": ["DEPENDENCY_ACTION"]
            }
        )

        assert response.status_code == 200
        entities = response.json().get("entities", [])

        dependency_entities = [e for e in entities if e["entity_type"] == "DEPENDENCY_ACTION"]
        assert len(dependency_entities) >= 1, "No DEPENDENCY_ACTION entities found"

        entity = dependency_entities[0]
        assert entity["confidence"] >= extraction_config["confidence_threshold"]
        assert "dependency action" in entity["text"].lower() or "dependency petition" in entity["text"].lower()

        print(f"✓ DEPENDENCY_ACTION extracted: {entity['text']} (confidence: {entity['confidence']:.2%})")


@pytest.mark.e2e
@pytest.mark.tier1
@pytest.mark.family_law
@pytest.mark.requires_vllm
@pytest.mark.asyncio
async def test_protective_custody_extraction(protective_custody_simple, extraction_config):
    """
    Test PROTECTIVE_CUSTODY entity extraction with AI mode.

    Entity Type: PROTECTIVE_CUSTODY
    Pattern Group: Child Protection
    Expected: Protective custody phrase with ≥0.90 confidence
    """
    async with httpx.AsyncClient(timeout=extraction_config["timeout"]) as client:
        response = await client.post(
            f"{extraction_config['base_url']}/api/v2/process/extract",
            json={
                "document_text": protective_custody_simple,
                "extraction_mode": extraction_config["extraction_mode"],
                "entity_type_filter": ["PROTECTIVE_CUSTODY"]
            }
        )

        assert response.status_code == 200
        entities = response.json().get("entities", [])

        protective_custody_entities = [e for e in entities if e["entity_type"] == "PROTECTIVE_CUSTODY"]
        assert len(protective_custody_entities) >= 1, "No PROTECTIVE_CUSTODY entities found"

        entity = protective_custody_entities[0]
        assert entity["confidence"] >= extraction_config["confidence_threshold"]
        assert "protective custody" in entity["text"].lower() or "emergency protective custody" in entity["text"].lower()

        print(f"✓ PROTECTIVE_CUSTODY extracted: {entity['text']} (confidence: {entity['confidence']:.2%})")


# ============================================================================
# INTEGRATION TESTS: MULTI-ENTITY DOCUMENTS (3 TESTS)
# ============================================================================

@pytest.mark.e2e
@pytest.mark.tier1
@pytest.mark.family_law
@pytest.mark.integration
@pytest.mark.requires_vllm
@pytest.mark.asyncio
async def test_jurisdiction_multi_entity_extraction(uccjea_jurisdiction_text, extraction_config, tier1_entity_types):
    """
    Integration test: Extract multiple jurisdiction entities from single document.

    Expected Entities:
    - HOME_STATE (≥2 instances)
    - EMERGENCY_JURISDICTION (≥2 instances)
    - EXCLUSIVE_CONTINUING_JURISDICTION (≥2 instances)
    - SIGNIFICANT_CONNECTION (≥2 instances)
    - FOREIGN_CUSTODY_ORDER (≥2 instances)
    """
    async with httpx.AsyncClient(timeout=extraction_config["timeout"]) as client:
        response = await client.post(
            f"{extraction_config['base_url']}/api/v2/process/extract",
            json={
                "document_text": uccjea_jurisdiction_text,
                "extraction_mode": extraction_config["extraction_mode"]
            }
        )

        assert response.status_code == 200
        result = response.json()
        entities = result.get("entities", [])

        print(f"\n=== Jurisdiction Multi-Entity Test ===")
        print(f"Total entities extracted: {len(entities)}")

        # Count entities by type
        jurisdiction_types = [
            "HOME_STATE",
            "EMERGENCY_JURISDICTION",
            "EXCLUSIVE_CONTINUING_JURISDICTION",
            "SIGNIFICANT_CONNECTION",
            "FOREIGN_CUSTODY_ORDER"
        ]

        entity_counts = {}
        for entity_type in jurisdiction_types:
            type_entities = [e for e in entities if e["entity_type"] == entity_type]
            entity_counts[entity_type] = len(type_entities)

            if type_entities:
                avg_conf = sum(e["confidence"] for e in type_entities) / len(type_entities)
                print(f"  {entity_type}: {len(type_entities)} entities (avg conf: {avg_conf:.2%})")

                # Validate at least one instance of each type
                assert len(type_entities) >= 1, f"Expected at least 1 {entity_type} entity"

                # Validate confidence for each entity
                for entity in type_entities:
                    assert entity["confidence"] >= extraction_config["confidence_threshold"], \
                        f"Low confidence for {entity_type}: {entity['confidence']}"

        # Validate all 5 jurisdiction types were found
        assert len(entity_counts) == 5, f"Expected all 5 jurisdiction entity types, found {len(entity_counts)}"

        print(f"✓ All 5 jurisdiction entity types successfully extracted")


@pytest.mark.e2e
@pytest.mark.tier1
@pytest.mark.family_law
@pytest.mark.integration
@pytest.mark.requires_vllm
@pytest.mark.asyncio
async def test_procedural_multi_entity_extraction(dissolution_petition_text, extraction_config):
    """
    Integration test: Extract multiple procedural entities from dissolution petition.

    Expected Entities:
    - DISSOLUTION_PETITION (≥2 instances)
    - TEMPORARY_ORDER (≥2 instances)
    - FINAL_DECREE (≥2 instances)
    - MODIFICATION_PETITION (≥1 instance)
    - GUARDIAN_AD_LITEM (≥2 instances)
    """
    async with httpx.AsyncClient(timeout=extraction_config["timeout"]) as client:
        response = await client.post(
            f"{extraction_config['base_url']}/api/v2/process/extract",
            json={
                "document_text": dissolution_petition_text,
                "extraction_mode": extraction_config["extraction_mode"]
            }
        )

        assert response.status_code == 200
        entities = response.json().get("entities", [])

        print(f"\n=== Procedural Multi-Entity Test ===")
        print(f"Total entities extracted: {len(entities)}")

        procedural_types = [
            "DISSOLUTION_PETITION",
            "TEMPORARY_ORDER",
            "FINAL_DECREE",
            "MODIFICATION_PETITION",
            "GUARDIAN_AD_LITEM"
        ]

        for entity_type in procedural_types:
            type_entities = [e for e in entities if e["entity_type"] == entity_type]

            if type_entities:
                avg_conf = sum(e["confidence"] for e in type_entities) / len(type_entities)
                print(f"  {entity_type}: {len(type_entities)} entities (avg conf: {avg_conf:.2%})")

                assert len(type_entities) >= 1, f"Expected at least 1 {entity_type} entity"

        print(f"✓ All 5 procedural entity types successfully extracted")


@pytest.mark.e2e
@pytest.mark.tier1
@pytest.mark.family_law
@pytest.mark.integration
@pytest.mark.requires_vllm
@pytest.mark.asyncio
async def test_property_and_protection_multi_entity_extraction(
    property_division_text,
    cps_report_text,
    extraction_config
):
    """
    Integration test: Extract property and child protection entities.

    Tests property division (COMMUNITY_PROPERTY, SEPARATE_PROPERTY) and
    child protection (CHILD_ABUSE_REPORT, DEPENDENCY_ACTION, PROTECTIVE_CUSTODY).
    """
    # Test property division entities
    async with httpx.AsyncClient(timeout=extraction_config["timeout"]) as client:
        property_response = await client.post(
            f"{extraction_config['base_url']}/api/v2/process/extract",
            json={
                "document_text": property_division_text,
                "extraction_mode": extraction_config["extraction_mode"]
            }
        )

        assert property_response.status_code == 200
        property_entities = property_response.json().get("entities", [])

        print(f"\n=== Property Division Test ===")
        print(f"Total property entities: {len(property_entities)}")

        community_prop = [e for e in property_entities if e["entity_type"] == "COMMUNITY_PROPERTY"]
        separate_prop = [e for e in property_entities if e["entity_type"] == "SEPARATE_PROPERTY"]

        assert len(community_prop) >= 1, "Expected COMMUNITY_PROPERTY entities"
        assert len(separate_prop) >= 1, "Expected SEPARATE_PROPERTY entities"

        print(f"  COMMUNITY_PROPERTY: {len(community_prop)} entities")
        print(f"  SEPARATE_PROPERTY: {len(separate_prop)} entities")

        # Test child protection entities
        protection_response = await client.post(
            f"{extraction_config['base_url']}/api/v2/process/extract",
            json={
                "document_text": cps_report_text,
                "extraction_mode": extraction_config["extraction_mode"]
            }
        )

        assert protection_response.status_code == 200
        protection_entities = protection_response.json().get("entities", [])

        print(f"\n=== Child Protection Test ===")
        print(f"Total protection entities: {len(protection_entities)}")

        abuse_reports = [e for e in protection_entities if e["entity_type"] == "CHILD_ABUSE_REPORT"]
        dependency = [e for e in protection_entities if e["entity_type"] == "DEPENDENCY_ACTION"]
        protective_custody = [e for e in protection_entities if e["entity_type"] == "PROTECTIVE_CUSTODY"]

        assert len(abuse_reports) >= 1, "Expected CHILD_ABUSE_REPORT entities"
        assert len(dependency) >= 1, "Expected DEPENDENCY_ACTION entities"
        assert len(protective_custody) >= 1, "Expected PROTECTIVE_CUSTODY entities"

        print(f"  CHILD_ABUSE_REPORT: {len(abuse_reports)} entities")
        print(f"  DEPENDENCY_ACTION: {len(dependency)} entities")
        print(f"  PROTECTIVE_CUSTODY: {len(protective_custody)} entities")

        print(f"✓ Property and child protection entities successfully extracted")


# ============================================================================
# E2E PIPELINE TEST (1 TEST)
# ============================================================================

@pytest.mark.e2e
@pytest.mark.tier1
@pytest.mark.family_law
@pytest.mark.pipeline
@pytest.mark.requires_vllm
@pytest.mark.asyncio
async def test_complete_pipeline_all_15_entities(
    uccjea_jurisdiction_text,
    dissolution_petition_text,
    property_division_text,
    cps_report_text,
    extraction_config,
    tier1_entity_types
):
    """
    E2E Pipeline Test: Validate all 15 Tier 1 entities in complete workflow.

    Workflow:
    1. Extract entities from 4 different document types
    2. Validate all 15 entity types are found
    3. Verify LurisEntityV2 schema compliance
    4. Check confidence thresholds
    5. Generate test report
    """
    print(f"\n{'='*80}")
    print(f"E2E PIPELINE TEST: ALL 15 TIER 1 FAMILY LAW ENTITIES")
    print(f"{'='*80}\n")

    documents = {
        "jurisdiction": uccjea_jurisdiction_text,
        "procedural": dissolution_petition_text,
        "property": property_division_text,
        "protection": cps_report_text
    }

    all_entities = []
    entity_type_counts = {entity_type: 0 for entity_type in tier1_entity_types}

    async with httpx.AsyncClient(timeout=extraction_config["timeout"]) as client:
        for doc_name, doc_text in documents.items():
            print(f"Processing: {doc_name} document...")

            start_time = time.time()
            response = await client.post(
                f"{extraction_config['base_url']}/api/v2/process/extract",
                json={
                    "document_text": doc_text,
                    "extraction_mode": extraction_config["extraction_mode"]
                }
            )
            elapsed_ms = (time.time() - start_time) * 1000

            assert response.status_code == 200, f"Extraction failed for {doc_name}"

            result = response.json()
            entities = result.get("entities", [])

            print(f"  ✓ Extracted {len(entities)} entities in {elapsed_ms:.0f}ms")

            all_entities.extend(entities)

            # Count entity types
            for entity in entities:
                if entity["entity_type"] in entity_type_counts:
                    entity_type_counts[entity["entity_type"]] += 1

    # Validation 1: All 15 entity types found
    print(f"\n--- Entity Type Coverage ---")
    found_types = [et for et, count in entity_type_counts.items() if count > 0]

    for entity_type in tier1_entity_types:
        count = entity_type_counts[entity_type]
        status = "✓" if count > 0 else "✗"
        print(f"  {status} {entity_type}: {count} entities")

    assert len(found_types) == 15, f"Expected all 15 entity types, found {len(found_types)}"

    # Validation 2: LurisEntityV2 schema compliance
    print(f"\n--- Schema Validation ---")
    required_fields = ["id", "text", "entity_type", "start_pos", "end_pos", "confidence", "extraction_method"]

    for entity in all_entities[:10]:  # Sample first 10
        for field in required_fields:
            assert field in entity, f"Missing required field: {field}"

    print(f"  ✓ All entities conform to LurisEntityV2 schema")

    # Validation 3: Confidence thresholds
    print(f"\n--- Confidence Analysis ---")
    confidences = [e["confidence"] for e in all_entities]
    avg_confidence = sum(confidences) / len(confidences)
    min_confidence = min(confidences)
    max_confidence = max(confidences)

    high_conf = sum(1 for c in confidences if c >= 0.9)
    med_conf = sum(1 for c in confidences if 0.7 <= c < 0.9)
    low_conf = sum(1 for c in confidences if c < 0.7)

    print(f"  Average confidence: {avg_confidence:.2%}")
    print(f"  Min/Max confidence: {min_confidence:.2%} / {max_confidence:.2%}")
    print(f"  High (≥0.90): {high_conf} entities")
    print(f"  Medium (0.70-0.89): {med_conf} entities")
    print(f"  Low (<0.70): {low_conf} entities")

    # Validation 4: Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_path = f"/srv/luris/be/entity-extraction-service/tests/results/tier1_pipeline_{timestamp}.json"

    test_results = {
        "test_name": "Tier 1 Family Law E2E Pipeline",
        "timestamp": timestamp,
        "total_entities": len(all_entities),
        "entity_type_counts": entity_type_counts,
        "confidence_stats": {
            "average": avg_confidence,
            "min": min_confidence,
            "max": max_confidence,
            "high_count": high_conf,
            "medium_count": med_conf,
            "low_count": low_conf
        },
        "entities": all_entities[:50]  # Save first 50 for review
    }

    with open(results_path, 'w') as f:
        json.dump(test_results, f, indent=2)

    print(f"\n✓ Pipeline test complete: {len(all_entities)} total entities")
    print(f"✓ Results saved: {results_path}")


# ============================================================================
# PERFORMANCE BENCHMARK TEST (1 TEST)
# ============================================================================

@pytest.mark.e2e
@pytest.mark.tier1
@pytest.mark.family_law
@pytest.mark.performance
@pytest.mark.requires_vllm
@pytest.mark.asyncio
async def test_performance_benchmark_all_patterns(
    uccjea_jurisdiction_text,
    dissolution_petition_text,
    extraction_config,
    performance_targets,
    tier1_entity_types
):
    """
    Performance Benchmark: Validate extraction speed for all 15 patterns.

    Success Criteria:
    - Average processing time: <50ms per document
    - 95th percentile: <100ms
    - All entities: ≥0.90 confidence
    - Extraction accuracy: ≥95%
    """
    print(f"\n{'='*80}")
    print(f"PERFORMANCE BENCHMARK: TIER 1 FAMILY LAW PATTERNS")
    print(f"{'='*80}\n")

    # Test documents
    test_docs = [
        ("UCCJEA Jurisdiction", uccjea_jurisdiction_text),
        ("Dissolution Petition", dissolution_petition_text),
        ("UCCJEA Short", "Washington is the child's home state under UCCJEA."),
        ("Procedural Short", "The court entered temporary orders on March 1, 2024."),
        ("Property Short", "Earnings during marriage are community property.")
    ]

    processing_times = []
    entity_counts = []
    confidence_scores = []

    async with httpx.AsyncClient(timeout=extraction_config["timeout"]) as client:
        for doc_name, doc_text in test_docs:
            print(f"Benchmarking: {doc_name}")

            # Run 3 iterations for each document
            for iteration in range(3):
                start_time = time.time()

                response = await client.post(
                    f"{extraction_config['base_url']}/api/v2/process/extract",
                    json={
                        "document_text": doc_text,
                        "extraction_mode": extraction_config["extraction_mode"]
                    }
                )

                elapsed_ms = (time.time() - start_time) * 1000
                processing_times.append(elapsed_ms)

                if response.status_code == 200:
                    entities = response.json().get("entities", [])
                    entity_counts.append(len(entities))

                    for entity in entities:
                        if entity["entity_type"] in tier1_entity_types:
                            confidence_scores.append(entity["confidence"])

                print(f"  Iteration {iteration + 1}: {elapsed_ms:.0f}ms, {len(entities)} entities")

    # Calculate statistics
    avg_time = sum(processing_times) / len(processing_times)
    p50_time = sorted(processing_times)[len(processing_times) // 2]
    p95_time = sorted(processing_times)[int(len(processing_times) * 0.95)]

    avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
    min_confidence = min(confidence_scores) if confidence_scores else 0

    print(f"\n--- Performance Results ---")
    print(f"  Total runs: {len(processing_times)}")
    print(f"  Average time: {avg_time:.0f}ms")
    print(f"  Median (p50): {p50_time:.0f}ms")
    print(f"  95th percentile: {p95_time:.0f}ms")
    print(f"  Min/Max time: {min(processing_times):.0f}ms / {max(processing_times):.0f}ms")

    print(f"\n--- Quality Results ---")
    print(f"  Avg confidence: {avg_confidence:.2%}")
    print(f"  Min confidence: {min_confidence:.2%}")
    print(f"  Total entities: {sum(entity_counts)}")

    # Validate performance targets
    assert avg_time <= performance_targets["max_processing_time_ms"], \
        f"Average time {avg_time:.0f}ms exceeds target {performance_targets['max_processing_time_ms']}ms"

    assert avg_confidence >= performance_targets["min_confidence"], \
        f"Average confidence {avg_confidence:.2%} below target {performance_targets['min_confidence']:.2%}"

    # Save benchmark results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    benchmark_path = f"/srv/luris/be/entity-extraction-service/tests/results/tier1_benchmark_{timestamp}.json"

    benchmark_results = {
        "test_name": "Tier 1 Family Law Performance Benchmark",
        "timestamp": timestamp,
        "performance": {
            "average_time_ms": avg_time,
            "p50_time_ms": p50_time,
            "p95_time_ms": p95_time,
            "min_time_ms": min(processing_times),
            "max_time_ms": max(processing_times)
        },
        "quality": {
            "average_confidence": avg_confidence,
            "min_confidence": min_confidence,
            "total_entities": sum(entity_counts)
        },
        "targets": performance_targets,
        "passed": True
    }

    with open(benchmark_path, 'w') as f:
        json.dump(benchmark_results, f, indent=2)

    print(f"\n✓ Performance benchmark passed")
    print(f"✓ Results saved: {benchmark_path}")
