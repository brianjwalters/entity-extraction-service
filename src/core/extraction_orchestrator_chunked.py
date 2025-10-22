"""
THREE_WAVE_CHUNKED implementation for ExtractionOrchestrator.

This file contains the chunked extraction method to be added to extraction_orchestrator.py
"""

async def _extract_three_wave_chunked(
    self,
    document_text: str,
    routing_decision: RoutingDecision,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Extract entities using 3-wave system with smart chunking for large documents.

    Process:
    1. Determine if SmartChunker should be used (>50K chars)
    2. Chunk document using SmartChunker
    3. Process each chunk through 3-wave extraction
    4. Adjust entity positions relative to original document
    5. Deduplicate entities across chunks
    6. Aggregate results

    Use for: Medium-Large documents (50K-1M+ chars)
    Expected tokens: Variable based on chunk count

    Args:
        document_text: Full document text
        routing_decision: Routing decision with chunk config
        metadata: Optional document metadata

    Returns:
        Dictionary with entities and stats
    """
    from core.smart_chunker import SmartChunker, ChunkingStrategy

    logger.info(f"Executing 3-wave chunked extraction: {len(document_text):,} chars")

    # Initialize SmartChunker
    smart_chunker = SmartChunker()

    # Check if smart chunking should be used
    use_smart_chunking = smart_chunker.should_use_smart_chunking(document_text)

    if use_smart_chunking:
        # Use smart chunking with legal-aware strategy
        logger.info("Using SmartChunker with LEGAL_AWARE strategy")
        chunks = smart_chunker.smart_chunk_document(
            text=document_text,
            strategy=ChunkingStrategy.LEGAL_AWARE,
            document_type=None  # Auto-detect
        )
    else:
        # Document not large enough for smart chunking, use three-wave directly
        logger.info("Document below smart chunking threshold, using standard 3-wave")
        return await self._extract_three_wave(document_text, metadata)

    logger.info(f"Document chunked into {len(chunks)} pieces")

    # Process each chunk through 3-wave extraction
    all_entities = []
    total_tokens = 0
    chunk_results = []

    for chunk in chunks:
        logger.info(f"Processing chunk {chunk.chunk_index + 1}/{len(chunks)}: "
                   f"{chunk.length:,} chars (pos {chunk.start_pos:,}-{chunk.end_pos:,})")

        # Extract entities from this chunk
        try:
            chunk_result = await self._extract_three_wave(
                chunk.text,
                metadata={
                    **(metadata or {}),
                    "chunk_index": chunk.chunk_index,
                    "chunk_start_pos": chunk.start_pos,
                    "chunk_end_pos": chunk.end_pos,
                    "total_chunks": len(chunks)
                }
            )

            # Adjust entity positions relative to original document
            adjusted_entities = []
            for entity in chunk_result["entities"]:
                adjusted_entity = entity.copy()

                # Adjust positions if present
                if "start_pos" in entity and entity["start_pos"] is not None:
                    adjusted_entity["start_pos"] = chunk.start_pos + entity["start_pos"]
                if "end_pos" in entity and entity["end_pos"] is not None:
                    adjusted_entity["end_pos"] = chunk.start_pos + entity["end_pos"]

                # Add chunk metadata
                adjusted_entity["chunk_index"] = chunk.chunk_index
                adjusted_entity["chunk_metadata"] = {
                    "chunk_start": chunk.start_pos,
                    "chunk_end": chunk.end_pos,
                    "chunk_type": chunk.chunk_type,
                    "in_overlap": False  # TODO: Detect overlap regions
                }

                adjusted_entities.append(adjusted_entity)

            # Accumulate results
            all_entities.extend(adjusted_entities)
            total_tokens += chunk_result["tokens_used"]

            chunk_results.append({
                "chunk_index": chunk.chunk_index,
                "entities_count": len(adjusted_entities),
                "tokens_used": chunk_result["tokens_used"],
                "chunk_length": chunk.length,
                "waves_executed": chunk_result["waves_executed"]
            })

            logger.info(f"Chunk {chunk.chunk_index + 1} complete: "
                       f"{len(adjusted_entities)} entities, "
                       f"{chunk_result['tokens_used']:,} tokens")

        except Exception as e:
            logger.error(f"Error processing chunk {chunk.chunk_index}: {e}")
            # Continue with next chunk rather than failing entire extraction
            chunk_results.append({
                "chunk_index": chunk.chunk_index,
                "entities_count": 0,
                "tokens_used": 0,
                "error": str(e)
            })
            continue

    # Deduplicate entities across chunks
    logger.info(f"Deduplicating {len(all_entities)} entities across {len(chunks)} chunks")
    deduplicated_entities = self._deduplicate_entities(all_entities)

    # Calculate deduplication stats
    deduplication_ratio = len(deduplicated_entities) / len(all_entities) if all_entities else 1.0
    entities_removed = len(all_entities) - len(deduplicated_entities)

    logger.info(
        f"3-wave chunked extraction complete: "
        f"{len(all_entities)} total entities, "
        f"{len(deduplicated_entities)} after deduplication "
        f"({entities_removed} duplicates removed, {deduplication_ratio:.1%} retention)"
    )

    # Get chunk statistics
    chunk_stats = smart_chunker.get_chunk_statistics(chunks)

    return {
        "entities": deduplicated_entities,
        "waves_executed": 3,
        "tokens_used": total_tokens,
        "metadata": {
            "prompt_version": "three_wave_chunked",
            "chunking_applied": True,
            "chunking_strategy": "smart_legal_aware",
            "total_chunks": len(chunks),
            "chunk_results": chunk_results,
            "chunk_statistics": chunk_stats,
            "deduplication_ratio": deduplication_ratio,
            "entities_before_dedup": len(all_entities),
            "entities_after_dedup": len(deduplicated_entities),
            "entities_by_chunk": {
                f"chunk_{r['chunk_index']}": r["entities_count"]
                for r in chunk_results
            },
            "average_entities_per_chunk": len(all_entities) / len(chunks) if chunks else 0,
            "average_tokens_per_chunk": total_tokens / len(chunks) if chunks else 0
        }
    }
