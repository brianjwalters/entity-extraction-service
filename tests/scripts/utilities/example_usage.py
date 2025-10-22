#!/usr/bin/env python3
"""
Example of how to use the IntegratedLegalPipeline from other services
"""

# Import the integrated pipeline from the spacy module
from src.spacy import IntegratedLegalPipeline, create_pipeline

def main():
    # Create a pipeline instance (fast mode without vLLM for quick extraction)
    pipeline = create_pipeline(mode="fast", use_vllm=False)

    # Example legal text
    text = """
    In Smith v. Jones, 123 F.3d 456 (9th Cir. 2023), Judge Mary Smith
    ruled in favor of the plaintiff, awarding $2.5 million in damages.
    """

    # Extract entities
    result = pipeline.extract(text)

    # Process results
    print(f"Found {result['entity_count']} entities:")
    for entity in result['entities']:
        print(f"  - {entity['text']} ({entity['type']})")

    print(f"\nProcessing time: {result['metadata']['processing_time']:.3f}s")

if __name__ == "__main__":
    main()