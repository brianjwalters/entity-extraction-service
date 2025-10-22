"""
Entity Registry Integration for Extraction Pipeline

This module provides integration between the entity registry and the existing
extraction pipeline, supporting all extraction modes and the 7-pass strategy.
"""

import json
import logging
from typing import List, Dict, Optional, Any

from .entity_registry import EntityRegistry
from ..models.entities import Entity
from ..models.registry import EntityGraph


class RegistryIntegration:
    """
    Integrates entity registry with the extraction pipeline.
    
    Provides methods for processing documents with cross-chunk context
    preservation, entity deduplication, and relationship discovery.
    """
    
    def __init__(
        self,
        enable_registry: bool = True,
        similarity_threshold: float = 0.85,
        cache_dir: Optional[str] = None,
        auto_merge: bool = True,
        auto_resolve_references: bool = True
    ):
        """
        Initialize registry integration.
        
        Args:
            enable_registry: Enable entity registry functionality
            similarity_threshold: Threshold for entity similarity
            cache_dir: Directory for registry caching
            auto_merge: Automatically merge duplicates after each chunk
            auto_resolve_references: Automatically resolve references
        """
        self.logger = logging.getLogger(__name__)
        self.enable_registry = enable_registry
        self.similarity_threshold = similarity_threshold
        self.cache_dir = cache_dir or "./cache/registry"
        self.auto_merge = auto_merge
        self.auto_resolve_references = auto_resolve_references
        
        # Active registries by document
        self.registries: Dict[str, EntityRegistry] = {}
        
        # Processing statistics
        self.stats = {
            "documents_processed": 0,
            "chunks_processed": 0,
            "entities_registered": 0,
            "merges_performed": 0,
            "references_resolved": 0
        }
    
    async def initialize_document(
        self,
        document_id: str,
        document_name: str,
        total_chunks: int
    ) -> EntityRegistry:
        """
        Initialize registry for a new document.
        
        Args:
            document_id: Unique document identifier
            document_name: Document name
            total_chunks: Total number of chunks
            
        Returns:
            Initialized EntityRegistry
        """
        if not self.enable_registry:
            return None
        
        registry = EntityRegistry(
            document_id=document_id,
            document_name=document_name,
            total_chunks=total_chunks,
            similarity_threshold=self.similarity_threshold,
            enable_caching=True,
            cache_dir=self.cache_dir
        )
        
        self.registries[document_id] = registry
        self.logger.info(f"Initialized registry for document {document_id} with {total_chunks} chunks")
        
        return registry
    
    async def process_chunk_entities(
        self,
        document_id: str,
        chunk_id: str,
        chunk_index: int,
        chunk_text: str,
        entities: List[Entity],
        global_offset: int = 0
    ) -> Dict[str, Any]:
        """
        Process entities from a chunk through the registry.
        
        Args:
            document_id: Document identifier
            chunk_id: Chunk identifier
            chunk_index: Sequential chunk index
            chunk_text: Full text of the chunk
            entities: Extracted entities from the chunk
            global_offset: Character offset of chunk in document
            
        Returns:
            Processing results with registered entity IDs
        """
        if not self.enable_registry or document_id not in self.registries:
            return {"status": "registry_disabled"}
        
        registry = self.registries[document_id]
        results = {
            "chunk_id": chunk_id,
            "chunk_index": chunk_index,
            "registered_entities": [],
            "merges": [],
            "references": {}
        }
        
        # Register each entity
        for entity in entities:
            try:
                registered_id = await registry.register_entity(
                    entity=entity,
                    chunk_id=chunk_id,
                    chunk_index=chunk_index,
                    global_offset=global_offset
                )
                
                results["registered_entities"].append({
                    "original_id": entity.id,
                    "registered_id": registered_id,
                    "text": entity.text,
                    "entity_type": entity.entity_type.value
                })
                
                self.stats["entities_registered"] += 1
                
            except Exception as e:
                self.logger.error(f"Failed to register entity {entity.id}: {e}")
        
        # Auto-merge duplicates if enabled
        if self.auto_merge and chunk_index % 5 == 0:  # Merge every 5 chunks
            merges = await registry.merge_duplicates(aggressive=False)
            results["merges"] = [
                {"from": m[0], "to": m[1]} for m in merges
            ]
            self.stats["merges_performed"] += len(merges)
        
        # Resolve references if enabled
        if self.auto_resolve_references:
            references = await registry.resolve_references(chunk_id, chunk_text)
            results["references"] = references
            self.stats["references_resolved"] += len(references)
        
        self.stats["chunks_processed"] += 1
        
        return results
    
    async def finalize_document(
        self,
        document_id: str,
        extract_relationships: bool = True,
        aggressive_merge: bool = True
    ) -> EntityGraph:
        """
        Finalize document processing and get entity graph.
        
        Args:
            document_id: Document identifier
            extract_relationships: Extract entity relationships
            aggressive_merge: Perform aggressive final merge
            
        Returns:
            Final entity graph
        """
        if not self.enable_registry or document_id not in self.registries:
            return None
        
        registry = self.registries[document_id]
        
        # Final aggressive merge
        if aggressive_merge:
            merges = await registry.merge_duplicates(aggressive=True)
            self.logger.info(f"Final merge performed {len(merges)} merges")
            self.stats["merges_performed"] += len(merges)
        
        # Extract relationships if requested
        if extract_relationships:
            await self._extract_relationships(registry)
        
        # Build final graph
        graph = await registry.build_entity_graph()
        
        # Save final snapshot
        snapshot_id = await registry.save_snapshot()
        self.logger.info(f"Saved final snapshot {snapshot_id} for document {document_id}")
        
        self.stats["documents_processed"] += 1
        
        return graph
    
    async def _extract_relationships(self, registry: EntityRegistry):
        """Extract relationships between entities."""
        # Get active entities
        entities = [
            e for e in registry.entities.values()
            if e.resolution_status.value != "merged"
        ]
        
        # Look for common relationship patterns
        relationship_patterns = [
            ("represents", ["attorney", "law_firm"], ["party", "plaintiff", "defendant"]),
            ("opposes", ["plaintiff"], ["defendant"]),
            ("presides_over", ["judge", "magistrate"], ["case", "proceeding"]),
            ("filed_by", ["motion", "brief", "complaint"], ["party", "attorney"]),
            ("employed_by", ["attorney", "paralegal"], ["law_firm"]),
            ("governs", ["statute", "regulation"], ["conduct", "procedure"])
        ]
        
        for rel_type, source_types, target_types in relationship_patterns:
            # Find matching entity pairs
            source_entities = [
                e for e in entities 
                if any(t in e.entity_type.value.lower() for t in source_types)
            ]
            target_entities = [
                e for e in entities
                if any(t in e.entity_type.value.lower() for t in target_types)
            ]
            
            # Check for relationships based on proximity
            for source in source_entities:
                for target in target_entities:
                    # Check if entities appear in same or adjacent chunks
                    source_chunks = {occ.chunk_index for occ in source.occurrences}
                    target_chunks = {occ.chunk_index for occ in target.occurrences}
                    
                    # If entities appear in overlapping or adjacent chunks
                    if source_chunks & target_chunks or \
                       any(abs(s - t) <= 1 for s in source_chunks for t in target_chunks):
                        
                        # Add relationship
                        await registry.add_relationship(
                            source_entity_id=source.id,
                            target_entity_id=target.id,
                            relationship_type=rel_type,
                            confidence=0.7,
                            chunk_ids=[str(c) for c in (source_chunks & target_chunks)]
                        )
    
    async def get_document_summary(self, document_id: str) -> Dict[str, Any]:
        """
        Get summary statistics for a document's registry.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Summary statistics
        """
        if document_id not in self.registries:
            return {"error": "Document not found"}
        
        registry = self.registries[document_id]
        stats = registry.get_statistics()
        
        # Add top entities by frequency
        active_entities = [
            e for e in registry.entities.values()
            if e.resolution_status.value != "merged"
        ]
        
        top_entities = sorted(
            active_entities,
            key=lambda e: e.total_occurrences,
            reverse=True
        )[:10]
        
        stats["top_entities"] = [
            {
                "text": e.canonical_text,
                "entity_type": e.entity_type.value,
                "occurrences": e.total_occurrences,
                "confidence": e.aggregate_confidence
            }
            for e in top_entities
        ]
        
        return stats
    
    async def export_document_entities(
        self,
        document_id: str,
        output_format: str = "json",
        output_path: Optional[str] = None
    ) -> Any:
        """
        Export document entities in specified format.
        
        Args:
            document_id: Document identifier
            output_format: Export format (json, csv, graphml)
            output_path: Optional output file path
            
        Returns:
            Exported data
        """
        if document_id not in self.registries:
            return None
        
        registry = self.registries[document_id]
        
        if output_format == "json":
            data = await registry.export_registry(include_merged=False)
            
            if output_path:
                with open(output_path, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                self.logger.info(f"Exported to {output_path}")
            
            return data
        
        elif output_format == "csv":
            # Export as CSV for analysis
            import csv
            
            active_entities = [
                e for e in registry.entities.values()
                if e.resolution_status.value != "merged"
            ]
            
            rows = []
            for entity in active_entities:
                rows.append({
                    "id": entity.id,
                    "canonical_text": entity.canonical_text,
                    "entity_type": entity.entity_type.value,
                    "subtype": entity.entity_subtype,
                    "occurrences": entity.total_occurrences,
                    "confidence": entity.aggregate_confidence,
                    "first_chunk": entity.first_seen_chunk,
                    "last_chunk": entity.last_seen_chunk,
                    "variants": "|".join(entity.all_variants)
                })
            
            if output_path:
                with open(output_path, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)
                self.logger.info(f"Exported CSV to {output_path}")
            
            return rows
        
        elif output_format == "graphml":
            # Export as GraphML for visualization
            graph = await registry.build_entity_graph()
            
            graphml = self._generate_graphml(graph)
            
            if output_path:
                with open(output_path, 'w') as f:
                    f.write(graphml)
                self.logger.info(f"Exported GraphML to {output_path}")
            
            return graphml
        
        else:
            raise ValueError(f"Unsupported format: {output_format}")
    
    def _generate_graphml(self, graph: EntityGraph) -> str:
        """Generate GraphML representation of entity graph."""
        lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        lines.append('<graphml xmlns="http://graphml.graphdrawing.org/xmlns">')
        lines.append('  <graph id="EntityGraph" edgedefault="directed">')
        
        # Add nodes
        for node in graph.nodes:
            lines.append(f'    <node id="{node.id}">')
            lines.append(f'      <data key="label">{node.canonical_text}</data>')
            lines.append(f'      <data key="type">{node.entity_type.value}</data>')
            lines.append(f'      <data key="occurrences">{node.total_occurrences}</data>')
            lines.append(f'      <data key="confidence">{node.aggregate_confidence}</data>')
            lines.append('    </node>')
        
        # Add edges
        for edge in graph.edges:
            lines.append(f'    <edge source="{edge.source_entity_id}" target="{edge.target_entity_id}">')
            lines.append(f'      <data key="type">{edge.relationship_type}</data>')
            lines.append(f'      <data key="confidence">{edge.confidence}</data>')
            lines.append('    </edge>')
        
        lines.append('  </graph>')
        lines.append('</graphml>')
        
        return '\n'.join(lines)
    
    def cleanup_document(self, document_id: str):
        """
        Clean up registry for a document.
        
        Args:
            document_id: Document identifier
        """
        if document_id in self.registries:
            del self.registries[document_id]
            self.logger.info(f"Cleaned up registry for document {document_id}")
    
    def get_global_statistics(self) -> Dict[str, Any]:
        """Get global statistics across all documents."""
        return {
            "documents_in_memory": len(self.registries),
            "total_documents_processed": self.stats["documents_processed"],
            "total_chunks_processed": self.stats["chunks_processed"],
            "total_entities_registered": self.stats["entities_registered"],
            "total_merges_performed": self.stats["merges_performed"],
            "total_references_resolved": self.stats["references_resolved"],
            "registries": {
                doc_id: registry.get_statistics()
                for doc_id, registry in self.registries.items()
            }
        }


class RegistryPipeline:
    """
    Complete pipeline for document processing with entity registry.
    
    Implements the 7-pass extraction strategy with cross-chunk context.
    """
    
    def __init__(
        self,
        extraction_client: Any,  # EntityExtractionClient
        registry_integration: Optional[RegistryIntegration] = None
    ):
        """
        Initialize registry pipeline.
        
        Args:
            extraction_client: Entity extraction client
            registry_integration: Registry integration instance
        """
        self.logger = logging.getLogger(__name__)
        self.extraction_client = extraction_client
        self.registry = registry_integration or RegistryIntegration()
    
    async def process_document(
        self,
        document_id: str,
        document_name: str,
        chunks: List[Dict[str, Any]],
        extraction_mode: str = "hybrid",
        passes: int = 7
    ) -> EntityGraph:
        """
        Process a document through the full pipeline.
        
        Args:
            document_id: Document identifier
            document_name: Document name
            chunks: List of document chunks
            extraction_mode: Extraction mode to use
            passes: Number of extraction passes
            
        Returns:
            Final entity graph
        """
        self.logger.info(f"Processing document {document_id} with {len(chunks)} chunks")
        
        # Initialize registry
        registry = await self.registry.initialize_document(
            document_id=document_id,
            document_name=document_name,
            total_chunks=len(chunks)
        )
        
        # Process each chunk
        global_offset = 0
        
        for pass_num in range(1, min(passes + 1, 8)):
            self.logger.info(f"Starting pass {pass_num} of {passes}")
            
            for i, chunk in enumerate(chunks):
                chunk_id = chunk.get("chunk_id", f"chunk_{i}")
                chunk_text = chunk.get("content", "")
                
                # Extract entities (mode varies by pass in 7-pass strategy)
                extraction_mode_for_pass = self._get_mode_for_pass(
                    pass_num, extraction_mode
                )
                
                # Call extraction service
                extraction_response = await self.extraction_client.extract_entities(
                    text=chunk_text,
                    mode=extraction_mode_for_pass,
                    include_positions=True
                )
                
                if extraction_response.success:
                    # Process through registry
                    await self.registry.process_chunk_entities(
                        document_id=document_id,
                        chunk_id=chunk_id,
                        chunk_index=i,
                        chunk_text=chunk_text,
                        entities=extraction_response.entities,
                        global_offset=global_offset
                    )
                
                global_offset += len(chunk_text)
            
            # Merge after each pass
            if pass_num in [3, 5, 7]:  # Strategic merge points
                await registry.merge_duplicates(aggressive=(pass_num == 7))
        
        # Finalize and return graph
        graph = await self.registry.finalize_document(
            document_id=document_id,
            extract_relationships=True,
            aggressive_merge=True
        )
        
        return graph
    
    def _get_mode_for_pass(self, pass_num: int, base_mode: str) -> str:
        """Determine extraction mode for specific pass."""
        # 7-pass strategy modes
        pass_modes = {
            1: "regex",  # Initial regex extraction
            2: "regex",  # Second regex with patterns
            3: "ai_enhanced",  # AI-enhanced NLP extraction
            4: "ai_enhanced",  # AI enhancement
            5: "ai_enhanced",  # AI discovery
            6: "hybrid",  # Hybrid consensus
            7: "hybrid"  # Final hybrid pass
        }

        if base_mode == "regex":
            return "regex"
        else:
            return pass_modes.get(pass_num, base_mode)