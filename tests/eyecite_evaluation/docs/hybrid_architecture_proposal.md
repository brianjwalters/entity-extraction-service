# Hybrid Architecture Proposal: Eyecite + LLM

## 💡 Core Insight

**Eyecite's UnknownCitation entries are perfect candidates for LLM classification.**

Instead of viewing the 182 UnknownCitation instances (137 in Rahimi, 45 in Dobbs) as failures, they represent:
1. **High-confidence detections**: Eyecite identified these as potential citations
2. **Low-confidence classification**: Eyecite couldn't determine the exact type
3. **LLM opportunity**: Perfect use case for contextual classification

---

## 🏗️ Proposed Architecture

### Stage 1: Fast Citation Extraction (Eyecite - 3-10 seconds)

```python
# Extract with Eyecite
citations = get_citations(document_text)
resolutions = resolve_citations(citations)

# Separate by confidence
known_citations = [c for c in citations if type(c).__name__ != 'UnknownCitation']
unknown_citations = [c for c in citations if type(c).__name__ == 'UnknownCitation']

# Results from test:
# - Rahimi: 505 known (79%) + 137 unknown (21%) = 642 total
# - Dobbs: 1,084 known (96%) + 45 unknown (4%) = 1,129 total
```

**Output**:
- ✅ 79-96% of citations extracted and classified (CPU only, milliseconds)
- ⚠️ 4-21% flagged as unknown (need LLM classification)

### Stage 2: LLM Classification (vLLM - 5-10 seconds)

```python
# Only send UnknownCitation to LLM
for unknown_cite in unknown_citations:
    # Extract context window around citation
    start, end = unknown_cite.span()
    context = document_text[start-200:end+200]

    # LLM classifies the unknown citation
    prompt = f"""
    Classify this legal citation:

    Citation text: {unknown_cite.matched_text()}
    Context: ...{context}...

    Is this a:
    1. Statutory citation (USC, CFR, state code)
    2. Case citation (short form)
    3. Internal reference (section/subsection)
    4. False positive (not a citation)

    Provide: type, confidence, reasoning
    """

    classification = llm_classify(prompt)

    # Convert to LurisEntityV2
    if classification.type == "statutory":
        entity = create_statute_citation(unknown_cite, classification)
    elif classification.type == "case":
        entity = create_case_citation(unknown_cite, classification)
    # ... etc
```

**Output**:
- ✅ UnknownCitation entries classified with context
- ✅ False positives filtered out
- ✅ High-confidence type assignment

### Stage 3: Merge & Enhance (5-8 seconds)

```python
# Merge Eyecite known + LLM classified unknown
all_entities = []

# Add known citations (already classified by Eyecite)
for cite in known_citations:
    entity = eyecite_to_luris_mapper(cite)
    entity.extraction_method = "eyecite"
    entity.confidence = 0.95  # Eyecite is highly accurate for known types
    all_entities.append(entity)

# Add LLM-classified unknown citations
for cite, classification in zip(unknown_citations, llm_classifications):
    if classification.is_valid_citation:
        entity = create_entity_from_llm_classification(cite, classification)
        entity.extraction_method = "hybrid_eyecite_llm"
        entity.confidence = classification.confidence
        all_entities.append(entity)

# Optional: LLM adds relationships and context
all_entities = llm_add_relationships(all_entities, document_text)
```

**Output**:
- ✅ Complete LurisEntityV2 entities
- ✅ Hybrid extraction_method tracking
- ✅ Confidence scores from both sources

---

## 📊 Performance Analysis

### Current System (vLLM Only)
```
Document → vLLM (35-50 seconds) → Entities
```
- **Time**: 35-50 seconds
- **Cost**: 4 A100 GPUs, full inference
- **Entities**: 195+ types extracted

### Proposed Hybrid System (Eyecite + vLLM)
```
Document → Eyecite (3-10s) → [Known (79-96%)] → Entities
                           ↓
                 [Unknown (4-21%)] → vLLM (5-10s) → Entities
```
- **Time**: 8-20 seconds (60% faster)
- **Cost**: CPU (Eyecite) + Minimal GPU (only for unknowns)
- **Entities**: Citations from Eyecite + LLM context + Other 175+ types

### Breakdown by Document

**Rahimi (103 pages)**:
| Stage | Current | Hybrid | Savings |
|-------|---------|--------|---------|
| Eyecite extraction | N/A | 3.43s | N/A |
| LLM for 137 unknowns | 35-50s | 5-8s | 85% less work |
| Total | 35-50s | 8-11s | 73-78% faster |

**Dobbs (213 pages)**:
| Stage | Current | Hybrid | Savings |
|-------|---------|--------|---------|
| Eyecite extraction | N/A | 10.36s | N/A |
| LLM for 45 unknowns | 35-50s | 2-4s | 92% less work |
| Total | 35-50s | 12-14s | 72-76% faster |

---

## 🔍 UnknownCitation Analysis

### What Are the "Unknown" Citations?

From the test results, most UnknownCitation entries are:

**1. Statutory Subsections** (80-85% of unknowns)
```
§922(g)(8)(C)(i)    ← Complex subsection reference
§924(a)(2)          ← Short statutory reference
§2(b)(i).           ← Internal section reference
§300gg–11,          ← Unusual formatting
```

**2. Internal Document References** (10-15% of unknowns)
```
§13                 ← Generic section number
§6,                 ← Ambiguous reference
§§1–2               ← Range reference
```

**3. Potential False Positives** (5% of unknowns)
```
§]922(g)(1)");      ← Malformed extraction
§922(g)(8)—quashing ← Citation + text merged
```

### LLM Classification Strategy

For each UnknownCitation, the LLM can:

1. **Determine if valid**: Is this actually a legal citation?
2. **Classify type**: Statutory, regulatory, internal, or false positive
3. **Extract metadata**: Full citation context, parent statute, subsection hierarchy
4. **Add confidence**: High (0.9+), Medium (0.7-0.9), Low (< 0.7)

**Example LLM Prompt**:
```
Context: "...in violation of 18 U. S. C. §922(g)(8). At the time, such a
violation was punishable by up to 10 years' imprisonment..."

Unknown citation: §922(g)(8)

Task: This appears to be a statutory subsection. The parent statute
is "18 U. S. C. §922" which was mentioned in the preceding text.
Therefore:
- Type: USC_SUBSECTION_CITATION
- Parent: 18 U.S.C. §922
- Subsection: (g)(8)
- Confidence: 0.95
- Context: Federal firearms statute criminalizing possession by
  individuals subject to domestic violence restraining orders
```

---

## 💰 Cost-Benefit Analysis

### Current Costs (Per Document)
- **GPU Time**: 35-50 seconds per document
- **GPU Cost**: 4 x A100 40GB @ full utilization
- **Annual Volume**: Assume 10,000 documents/year
- **Total GPU Hours**: ~97-139 hours/year

### Hybrid System Costs
- **Eyecite**: CPU only, negligible cost
- **GPU Time**: 5-10 seconds per document (only for unknowns)
- **Annual GPU Hours**: ~14-28 hours/year
- **Savings**: ~83-93 GPU hours/year (85-90% reduction)

### ROI Calculation
- **Development Time**: 1-2 weeks (1 engineer)
- **Ongoing Savings**: 85-90% GPU cost reduction
- **Performance Gain**: 60-78% faster processing
- **Payback Period**: 2-4 weeks of production use

---

## 🛠️ Implementation Plan

### Phase 1: Proof of Concept (1 week)

**Day 1-2: Schema Mapper**
```python
# Create eyecite_to_luris_mapper.py
def eyecite_to_luris(citation: EyeciteCitation) -> LurisEntityV2:
    """Map Eyecite citation to LurisEntityV2 entity."""

    if isinstance(citation, FullCaseCitation):
        return LurisEntityV2(
            id=str(uuid.uuid4()),
            text=citation.matched_text(),
            entity_type="CASE_CITATION",
            start_pos=citation.span()[0],
            end_pos=citation.span()[1],
            confidence=0.95,
            extraction_method="eyecite",
            metadata={
                "volume": citation.volume,
                "reporter": citation.reporter,
                "page": citation.page,
                "year": citation.metadata.year,
                "court": citation.metadata.court,
                "plaintiff": citation.metadata.plaintiff,
                "defendant": citation.metadata.defendant,
            }
        )
    # ... other citation types
```

**Day 3-4: LLM Classifier**
```python
# Create llm_unknown_classifier.py
async def classify_unknown_citations(
    unknown_citations: List[UnknownCitation],
    document_text: str,
    llm_client: vLLMClient
) -> List[ClassifiedEntity]:
    """
    Classify unknown citations using LLM with context.

    Process in batches to minimize LLM calls.
    """

    # Extract context for each unknown
    contexts = []
    for cite in unknown_citations:
        start, end = cite.span()
        context = extract_context_window(document_text, start, end, window=200)
        contexts.append({
            "citation": cite.matched_text(),
            "context": context,
            "position": (start, end)
        })

    # Batch classify with LLM
    prompt = create_classification_prompt(contexts)
    response = await llm_client.classify(prompt)

    # Parse LLM response and create entities
    return parse_llm_classifications(response, unknown_citations)
```

**Day 5: Integration**
```python
# Update extraction pipeline
async def extract_citations_hybrid(document_text: str) -> List[LurisEntityV2]:
    """
    Hybrid citation extraction using Eyecite + LLM.
    """

    # Stage 1: Eyecite extraction (fast)
    cleaned_text = clean_text(document_text)
    citations = get_citations(cleaned_text)

    # Stage 2: Separate known from unknown
    known = [c for c in citations if type(c).__name__ != 'UnknownCitation']
    unknown = [c for c in citations if type(c).__name__ == 'UnknownCitation']

    # Stage 3: Convert known citations immediately
    entities = [eyecite_to_luris(c) for c in known]

    # Stage 4: LLM classify unknowns (only if present)
    if unknown:
        classified = await classify_unknown_citations(unknown, document_text, llm_client)
        entities.extend(classified)

    return entities
```

### Phase 2: Testing & Validation (3-5 days)

1. **Run on test corpus**: Process all 5 documents in `/tests/docs/`
2. **Compare results**: Hybrid vs current system
3. **Measure metrics**:
   - Precision/recall for citations
   - Processing time
   - GPU utilization
   - Cost per document
4. **Validate LurisEntityV2 compliance**

### Phase 3: Production Deployment (2-3 days)

1. **Update API endpoints**: `/api/v2/process/extract` to use hybrid mode
2. **Add configuration**: Enable/disable hybrid extraction
3. **Monitor performance**: Track extraction_method field
4. **Documentation**: Update API docs and integration guides

---

## 🎯 Success Criteria

**The hybrid approach is successful if**:

✅ **Performance**:
- 60%+ faster than current system
- CPU-only Eyecite completes in < 15 seconds

✅ **Quality**:
- 95%+ precision for known citations (Eyecite)
- 90%+ precision for unknown classifications (LLM)
- No regression in overall entity extraction quality

✅ **Cost**:
- 80%+ reduction in GPU inference time
- Measurable cost savings within 30 days

✅ **Maintainability**:
- Clean abstraction between Eyecite and LLM stages
- Easy to disable/enable hybrid mode
- Clear extraction_method tracking in entities

---

## 🔮 Future Enhancements

### 1. Smart Fallback Strategy
```python
if eyecite_confidence < 0.8:
    # Use LLM to validate Eyecite result
    llm_validation = validate_with_llm(citation)
    if llm_validation.confidence > eyecite_confidence:
        use_llm_result()
```

### 2. Caching for Common Citations
```python
# Cache frequently seen citations
citation_cache = {
    "18 U.S.C. §922(g)(8)": LurisEntityV2(...),
    "554 U.S. 570": LurisEntityV2(...),
}

if citation.text in citation_cache:
    return citation_cache[citation.text]
```

### 3. Parallel Citation Enrichment
```python
# Use Eyecite's resolution to link parallel citations
# e.g., "554 U.S. 570" = "128 S.Ct. 2783" = "171 L.Ed.2d 637"
for resource, cites in resolutions.items():
    primary_entity = create_entity(resource.citation)
    parallel_entities = [create_entity(c) for c in cites[1:]]
    link_parallel_citations(primary_entity, parallel_entities)
```

### 4. Relationship Extraction
```python
# LLM extracts citation relationships
# "overruled by", "distinguished from", "followed in"
relationships = llm_extract_relationships(
    citations=all_entities,
    document_text=document_text
)
```

---

## 📚 Reference Documentation

**Key Files**:
- Test results: `/tests/eyecite_evaluation/results/`
- Full analysis: `/tests/eyecite_evaluation/docs/extraction_summary.md`
- This proposal: `/tests/eyecite_evaluation/docs/hybrid_architecture_proposal.md`

**Eyecite Resources**:
- GitHub: https://github.com/freelawproject/eyecite
- Tutorial: https://github.com/freelawproject/eyecite/blob/main/TUTORIAL.ipynb
- Documentation: Installed via `pip install eyecite`

**Current System**:
- Entity Extraction API: `/srv/luris/be/entity-extraction-service/api.md`
- LurisEntityV2 Spec: `/srv/luris/be/entity-extraction-service/docs/LurisEntityV2_Specification.md`
- Integration Guide: `/srv/luris/be/entity-extraction-service/docs/INTEGRATION_GUIDE.md`

---

## 🚀 Recommendation

**Proceed with Phase 1 (Proof of Concept)** immediately:

1. **Low Risk**: Eyecite is battle-tested, BSD-licensed, easily reversible
2. **High Reward**: 60-78% performance improvement, 85-90% cost reduction
3. **Fast Implementation**: 1-2 weeks to working prototype
4. **Clear Success Metrics**: Quantifiable improvements in speed and cost
5. **Strategic Fit**: Aligns with industry best practice of specialized tools + LLM reasoning

**Timeline**: 2-3 weeks from start to production deployment.
