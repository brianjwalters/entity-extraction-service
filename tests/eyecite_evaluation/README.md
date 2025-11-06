# Eyecite Citation Extraction Evaluation

This directory contains tools for evaluating Eyecite's legal citation extraction capabilities on real legal documents.

## Purpose

Test Eyecite's performance on complex legal documents (Supreme Court cases) to determine if it should be integrated into the entity-extraction-service as a citation extraction tool.

## Test Documents

- **rahimi.pdf**: U.S. Supreme Court case (complex citations)
- **dobbs.pdf**: U.S. Supreme Court case (complex citations)

## Setup

1. Activate the entity-extraction-service virtual environment:
```bash
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate
```

2. Install Eyecite dependencies:
```bash
pip install -r tests/eyecite_evaluation/requirements.txt
```

## Usage

Run the extraction script on test documents:

```bash
# Extract citations from both documents
python tests/eyecite_evaluation/extract_citations.py

# Extract from specific document
python tests/eyecite_evaluation/extract_citations.py --doc rahimi
python tests/eyecite_evaluation/extract_citations.py --doc dobbs
```

## Output

Results are saved to `results/` directory:

- **JSON files**: Structured citation data with full metadata
- **TXT files**: Human-readable citation lists
- **extraction_summary.md**: Summary statistics and samples

## What Eyecite Extracts

- **FullCaseCitation**: Complete case citations (e.g., "Brown v. Board, 347 U.S. 483 (1954)")
- **ShortCaseCitation**: Short-form references (e.g., "347 U.S., at 485")
- **IdCitation**: Id. and Ibid. references
- **SupraCitation**: Supra references
- **StatuteCitation**: Statutory references (e.g., "18 U.S.C. § 922")

## Evaluation

After running the extraction:

1. Review `results/*_citations.txt` files for readability
2. Check `docs/extraction_summary.md` for statistics
3. Manually evaluate citation quality and coverage
4. Decide if Eyecite should be integrated

## Next Steps

If Eyecite performance is satisfactory:
- Design schema mapper (Eyecite → LurisEntityV2)
- Implement hybrid approach (Eyecite + LLM contextualization)
- Benchmark against current system
