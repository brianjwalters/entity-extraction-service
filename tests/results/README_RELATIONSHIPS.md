# Entity Relationship Data - Usage Guide

**Location:** `/srv/luris/be/entity-extraction-service/tests/results/`
**Generated:** 2025-10-15

## 📁 Files Generated

### Core Data Files

1. **`test_history.json`** (UPDATED)
   - Contains original test data PLUS new relationship arrays
   - Each test now has a `relationships` array with 5-10 relationships
   - Total: 59 relationships across 6 tests

2. **`relationship_network.json`** (NEW)
   - Network graph format for D3.js/Cytoscape visualization
   - Contains nodes (entities) and links (relationships)
   - Ready for graph visualization libraries

3. **`relationships_export.csv`** (NEW)
   - CSV export of all relationships
   - Importable into Excel, Google Sheets, data analysis tools
   - Headers: id, test_id, document_id, relationship_type, source, target, confidence, positions, context

### Documentation & Tools

4. **`relationship_generation_summary.md`**
   - Comprehensive documentation of relationship generation
   - Statistics, validation results, usage patterns

5. **`analyze_relationships.py`**
   - Python script for relationship analysis
   - Command-line tool for querying and exporting data

6. **`README_RELATIONSHIPS.md`** (this file)
   - Usage guide and quick start instructions

---

## 🚀 Quick Start

### View Overall Statistics

```bash
cd /srv/luris/be/entity-extraction-service/tests/results
python3 analyze_relationships.py
```

**Output:**
- Total relationships count
- Confidence statistics (avg, min, max)
- Distribution by relationship type
- Per-test breakdown with ratios

### Analyze Specific Test

```bash
python3 analyze_relationships.py --test-id test_1760575089802
```

Shows relationships only for the specified test.

### Filter by Relationship Type

```bash
python3 analyze_relationships.py --relationship-type CO_OCCURS
```

Lists all relationships of the specified type.

### Export to CSV

```bash
python3 analyze_relationships.py --export-csv my_export.csv
```

Creates CSV file with all relationship data.

### View Help

```bash
python3 analyze_relationships.py --help
```

---

## 📊 Data Structure

### Relationship Object Schema

Each relationship in `test_history.json` follows this structure:

```json
{
  "id": "rel-a05cf930-e011-445d-809f-30fe2999aa71",
  "source_entity_id": "uuid-string-1",
  "target_entity_id": "uuid-string-3",
  "relationship_type": "CO_OCCURS",
  "confidence": 0.72,
  "start_pos": 0,
  "end_pos": 58,
  "context": "The relationship between Entity1 and Entity2...",
  "test_id": "test_1760575089802",
  "document_id": "case_001",
  "metadata": {
    "proximity_distance": 150,
    "co_occurrence_strength": "moderate"
  }
}
```

### Network Graph Schema

`relationship_network.json` uses this format:

```json
{
  "directed": true,
  "nodes": [
    {
      "id": 0,
      "entity_id": "uuid-string-1",
      "label": "United States of America",
      "entity_type": "PARTY",
      "confidence": 0.95,
      "size": 29
    }
  ],
  "links": [
    {
      "source": 0,
      "target": 2,
      "relationship_type": "CO_OCCURS",
      "confidence": 0.72,
      "weight": 7.2
    }
  ]
}
```

---

## 📈 Statistics Summary

### Overall Metrics

| Metric | Value |
|--------|-------|
| Total Tests | 6 |
| Total Entities | 52 (18 unique) |
| Total Relationships | 59 |
| Unique Relationship Types | 3 |
| Avg Relationships/Test | 9.8 |
| Avg Confidence | 0.761 |
| Network Density | 19.28% |

### Relationship Type Breakdown

| Type | Count | Percentage | Avg Confidence |
|------|-------|------------|----------------|
| CO_OCCURS | 53 | 89.8% | 0.745 |
| FILED_IN | 3 | 5.1% | 0.923 |
| REPRESENTS | 3 | 5.1% | 0.893 |

### Entity Type Distribution

Top entity types in network:
- PARTY: 2 entities
- CASE_CITATION: 2 entities
- STATUTE_CITATION: 2 entities
- DATE: 2 entities
- COURT, ATTORNEY, ORGANIZATION, etc.: 1 each

---

## 🔧 Integration Examples

### Python Integration

```python
import json

# Load relationship data
with open('test_history.json', 'r') as f:
    data = json.load(f)

# Get all relationships from first test
test = data['tests'][0]
relationships = test['relationships']

# Filter high-confidence relationships
high_conf = [r for r in relationships if r['confidence'] > 0.8]

# Group by type
from collections import defaultdict
by_type = defaultdict(list)
for rel in relationships:
    by_type[rel['relationship_type']].append(rel)
```

### JavaScript/D3.js Integration

```javascript
// Load network data
fetch('relationship_network.json')
  .then(response => response.json())
  .then(data => {
    // Create force-directed graph
    const simulation = d3.forceSimulation(data.nodes)
      .force("link", d3.forceLink(data.links).id(d => d.id))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2));

    // Render nodes and links
    // ... (standard D3.js graph visualization)
  });
```

### Pandas Analysis

```python
import pandas as pd

# Load CSV export
df = pd.read_csv('relationships_export.csv')

# Analyze by relationship type
type_stats = df.groupby('relationship_type').agg({
    'confidence': ['mean', 'min', 'max', 'count'],
    'id': 'count'
})

# Find most connected entities
source_counts = df['source_entity_id'].value_counts()
target_counts = df['target_entity_id'].value_counts()
```

---

## 🎯 Use Cases

### 1. Dashboard Visualization

**Network Graph:**
- Use `relationship_network.json` with D3.js, Cytoscape, or vis.js
- Color nodes by entity type
- Size nodes by confidence
- Weight edges by relationship confidence

**Statistics Panel:**
- Display relationship type distribution (pie chart)
- Show confidence score histogram
- List top entity pairs by connection count

### 2. Quality Analysis

**Relationship Quality Metrics:**
```python
# Using analyze_relationships.py
from analyze_relationships import RelationshipAnalyzer

analyzer = RelationshipAnalyzer()
stats = analyzer.calculate_stats(analyzer.get_all_relationships())

print(f"Average Confidence: {stats.avg_confidence:.3f}")
print(f"Relationships by Type: {stats.relationships_by_type}")
```

### 3. Test Comparison

**Compare relationship density across tests:**
```python
for test in data['tests']:
    entity_count = len(test['raw_response']['entities'])
    rel_count = len(test.get('relationships', []))
    density = rel_count / entity_count if entity_count > 0 else 0

    print(f"{test['test_id']}: {density:.2f} relationships per entity")
```

### 4. Entity Network Analysis

**Find highly connected entities:**
```python
analyzer = RelationshipAnalyzer()

# For a specific entity
entity_id = "uuid-string-1"
test_id = "test_1760575089802"

rels = analyzer.get_entity_relationships(test_id, entity_id)
total_connections = len(rels['as_source']) + len(rels['as_target'])

print(f"Entity has {total_connections} total connections")
```

---

## 🛠️ Advanced Usage

### Custom Filtering

```python
from analyze_relationships import RelationshipAnalyzer

analyzer = RelationshipAnalyzer()

# Find high-confidence CO_OCCURS relationships
high_conf_co_occur = analyzer.filter_relationships(
    relationship_type='CO_OCCURS',
    min_confidence=0.8
)

print(f"Found {len(high_conf_co_occur)} high-confidence co-occurrences")
```

### Export Filtered Data

```python
import json

# Export only FILED_IN and REPRESENTS relationships
filtered = analyzer.filter_relationships(
    relationship_type='FILED_IN'
) + analyzer.filter_relationships(
    relationship_type='REPRESENTS'
)

with open('legal_relationships.json', 'w') as f:
    json.dump(filtered, f, indent=2)
```

### Generate Custom Network

```python
# Create network for specific test only
test = analyzer.get_test_by_id('test_1760575089802')
relationships = test['relationships']
entities = test['raw_response']['entities']

# Build custom network structure
custom_network = {
    'nodes': [{'id': e['id'], 'label': e['text']} for e in entities],
    'edges': [{'from': r['source_entity_id'], 'to': r['target_entity_id']}
              for r in relationships]
}
```

---

## ✅ Validation

All relationship data has been validated:

- ✅ **Entity ID Validation:** All source/target IDs exist
- ✅ **Confidence Range:** All scores in [0.0, 1.0]
- ✅ **Position Validity:** All ranges are valid
- ✅ **Test Consistency:** All relationships reference valid tests
- ✅ **Document Consistency:** All document IDs are correct

**Validation Rate:** 100% (0 errors found)

---

## 📝 Notes

### Relationship Generation Logic

1. **REPRESENTS:** Generated for PARTY + ATTORNEY pairs
2. **FILED_IN:** Generated for PARTY + COURT pairs
3. **CITES:** Generated for CASE_CITATION + STATUTE pairs
4. **PRESIDES_OVER:** Generated for JUDGE + COURT pairs
5. **OCCURS_ON:** Generated for DATE + PARTY/EVENT pairs
6. **CO_OCCURS:** Generated for entities within 200 characters

### Confidence Calibration

- **REPRESENTS/FILED_IN:** 0.85 - 0.98 (high certainty)
- **CITES/PRESIDES_OVER:** 0.80 - 0.95 (moderate-high)
- **OCCURS_ON:** 0.75 - 0.92 (moderate)
- **CO_OCCURS:** 0.65 - 0.85 (lower, proximity-based)

### Future Enhancements

Potential additions to relationship system:
- Temporal relationships (BEFORE, AFTER, DURING)
- Hierarchical relationships (PART_OF, BELONGS_TO)
- Semantic relationships (CONFLICTS_WITH, SUPPORTS)
- Relationship strength scoring beyond confidence
- Legal significance weighting

---

## 🔗 Related Files

- **Test Data:** `/srv/luris/be/tests/docs/Rahimi.pdf` (source document)
- **Entity Data:** Embedded in `test_history.json` under `raw_response.entities`
- **Test Results:** `/srv/luris/be/entity-extraction-service/tests/results/`

---

## 📞 Support

For questions or issues with relationship data:

1. Review `relationship_generation_summary.md` for detailed documentation
2. Run validation: `python3 analyze_relationships.py`
3. Check entity data integrity in `test_history.json`
4. Verify network structure in `relationship_network.json`

**Last Updated:** 2025-10-15
**Data Version:** 1.0
