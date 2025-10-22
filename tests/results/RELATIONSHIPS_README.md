# Entity Relationships Explorer

## Overview
The `relationships.html` dashboard provides comprehensive visualization and analysis of entity relationships extracted from legal documents. Built with DataTables, Chart.js, and Cytoscape.js for professional-grade data exploration.

## Features

### 1. Summary Cards
- **Total Relationships**: Count across all tests
- **Unique Types**: Number of distinct relationship types
- **Average Confidence**: Mean confidence score
- **Most Connected Entity**: Entity with highest connection count

### 2. Advanced Filtering
- **Relationship Type**: Multi-select dropdown for filtering by relationship type
- **Source/Target Entity Type**: Filter by entity types on either end
- **Document ID**: Filter by specific document
- **Confidence Range**: Dual-handle slider for confidence filtering (0.00 - 1.00)
- **Apply/Reset Buttons**: Quick filter application and reset

### 3. Interactive Data Table (DataTables)
- **Columns**:
  - Relationship ID (truncated)
  - Type (color-coded badge)
  - Source Entity (with type badge)
  - Target Entity (with type badge)
  - Confidence (visual progress bar)
  - Position (start-end)
  - Context (truncated with tooltip)
  - Test ID
  - Actions (View, Graph, Copy)

- **Features**:
  - Sortable columns
  - Global search
  - Pagination (25/50/100/All)
  - Export to CSV/Excel/Copy
  - Responsive design

### 4. Visualizations (Chart.js)
- **Relationship Type Distribution**: Bar chart showing count by type
- **Confidence Distribution**: Histogram in 5 buckets (0-20%, 20-40%, etc.)
- **Top 10 Most Connected Entities**: Horizontal bar chart
- **Relationships per Document**: Bar chart by document ID

### 5. Network Graph Preview (Cytoscape.js)
- **Top 20 Most Connected Entities**: Interactive network visualization
- **Node Colors**: Color-coded by entity type
  - JUDGE: Orange (#ff9800)
  - CASE_CITATION: Blue (#2196f3)
  - STATUTE: Pink (#e91e63)
  - COURT: Purple (#9c27b0)
  - PERSON: Cyan (#00bcd4)
  - DATE: Yellow (#ffc107)
  - ORGANIZATION: Green (#4caf50)
  - LOCATION: Light green (#9ccc65)

- **Edge Colors**: Color-coded by relationship type
  - CITES: Blue
  - PRESIDES_OVER: Orange
  - FILED_AGAINST: Pink
  - REPRESENTED_BY: Purple
  - OCCURRED_ON: Yellow

- **Interactions**:
  - Click node to filter table by that entity
  - Zoom/pan controls
  - Reset view button
  - "View Full Graph" button → navigate to graph.html

### 6. Detail Modal
Click "View" on any relationship to see:
- Full relationship ID
- Relationship type
- Source entity (text, type, ID)
- Target entity (text, type, ID)
- Confidence score with visual bar
- Position information
- Full context
- Metadata JSON
- Document and Test IDs

### 7. Additional Actions
- **View in Graph**: Opens graph.html with relationship highlighted
- **Copy ID**: Copy relationship ID to clipboard
- **Export**: Export filtered data to CSV/Excel

## Data Source
Loads from `entity_relationships.json` with the following structure:

```json
{
  "version": "1.0",
  "total_relationships": 33,
  "relationships_by_test": {
    "test_1760575089802": {
      "document_id": "case_001",
      "entity_count": 14,
      "relationship_count": 7,
      "relationships": [
        {
          "id": "rel-50755dab...",
          "source_entity_id": "uuid-string-1",
          "target_entity_id": "uuid-string-11",
          "relationship_type": "REPRESENTED_BY",
          "confidence": 0.88,
          "start_pos": 0,
          "end_pos": 220,
          "context": "United States of America as plaintiff...",
          "metadata": { ... }
        }
      ]
    }
  }
}
```

## Relationship Types (22 Total)
1. ACCOMPANIED_BY
2. APPEALED_FROM
3. ARGUED_ON
4. ARRESTED_ON
5. CHARGED_UNDER
6. CITES
7. CO_OCCURS
8. DECIDED_IN
9. DECIDED_ON
10. EMPLOYED_BY
11. FILED_AGAINST
12. FILED_IN
13. FILED_ON
14. LOCATED_IN
15. OCCURRED_ON
16. PRESIDED_OVER_BY
17. PRESIDES_OVER
18. PROSECUTING
19. REPORTED_AT
20. REPRESENTED_BY
21. RESULTED_IN
22. SCHEDULED_FOR

## Usage

### Opening the Dashboard
1. Navigate to: `/srv/luris/be/entity-extraction-service/tests/results/`
2. Open `relationships.html` in a web browser
3. Data loads automatically from `entity_relationships.json`

### Filtering Relationships
1. Select filter criteria:
   - Choose relationship types (multi-select)
   - Choose source/target entity types
   - Select document ID
   - Adjust confidence range slider
2. Click "Apply Filters"
3. Table updates with filtered results

### Exploring the Network
1. View the mini graph preview (top 20 entities)
2. Click any node to filter table by that entity
3. Use zoom/pan to explore connections
4. Click "View Full Graph" for comprehensive graph view

### Viewing Details
1. Click "View" button on any relationship row
2. Modal shows complete relationship information
3. Click "Graph" to see relationship in network context
4. Click "Copy" to copy relationship ID

### Exporting Data
1. Apply desired filters
2. Click CSV/Excel/Copy button in table toolbar
3. Filtered data exports to selected format

## Technical Stack
- **DataTables 1.13.7**: Advanced table functionality
- **Chart.js 4.4.0**: Interactive charts
- **Cytoscape.js 3.28.1**: Network graph visualization
- **noUiSlider 15.7.1**: Range slider component
- **jQuery 3.7.1**: DOM manipulation
- **JSZip 3.10.1**: Excel export support

## Dark Theme
- Matches entities.html styling
- Background: Dark gradient (#1a1a2e → #0f0f1e)
- Cards: Gradient (#2d2d44 → #252538)
- Accent color: Blue (#6c9bcf)
- Responsive design for mobile/tablet

## Browser Compatibility
- Chrome/Edge: Full support
- Firefox: Full support
- Safari: Full support
- Mobile browsers: Responsive layout

## Performance
- Loads 33 relationships instantly
- Filters apply in <100ms
- Graph renders top 20 entities efficiently
- Table pagination for large datasets

## Future Enhancements
- Real-time relationship discovery
- Temporal analysis (relationships over time)
- Strength/weight visualization for edges
- Community detection highlighting
- Path finding between entities
- Export to GraphML/GEXF formats
