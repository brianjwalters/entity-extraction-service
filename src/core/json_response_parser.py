"""
Enhanced JSON Response Parser for vLLM/AI Agent Responses

This module provides bulletproof JSON parsing capabilities specifically designed for
vLLM-generated responses that may contain formatting issues, explanatory text,
or edge cases despite template directives.

Version: 2.0 - Enhanced with aggressive extraction and template-aware parsing
"""

import json
import re
import logging
import time
from typing import Dict, Any, Optional, List

# Import LurisEntityV2 for schema enforcement
from src.core.schema.luris_entity_schema import LurisEntityV2

logger = logging.getLogger(__name__)


class JSONResponseParser:
    """
    Bulletproof parser for vLLM/AI-generated JSON responses with comprehensive
    error correction, template awareness, and performance optimization.
    """
    
    # Cache compiled regex patterns for performance
    _REGEX_CACHE = {}
    
    # Template type hints for smarter parsing
    TEMPLATE_TYPES = {
        'multipass': ['pass_1', 'pass_2', 'pass_3', 'extraction_summary'],
        'ai_enhanced': ['entities', 'citations', 'confidence_score'],
        'unified': ['entities', 'citations', 'relationships', 'summary'],
        'entity_extraction': ['entities', 'extraction_metadata'],
        'relationship': ['extracted_relationships', 'extraction_summary'],
        'citation': ['citations', 'validation_results']
    }
    
    # Common vLLM response patterns to strip
    VLLM_PATTERNS = [
        r'^.*?(?=\{)',  # Everything before first {
        r'(?<=\}).*$',   # Everything after last }
        r'^```json\s*',  # Markdown JSON block start
        r'\s*```$',      # Markdown block end
        r'^Here\'s.*?:\s*',  # Common prefixes
        r'^The JSON.*?:\s*',
        r'^Response:\s*',
        r'^Output:\s*'
    ]
    
    @classmethod
    def _get_cached_regex(cls, pattern: str) -> re.Pattern:
        """Get or create cached compiled regex pattern."""
        if pattern not in cls._REGEX_CACHE:
            cls._REGEX_CACHE[pattern] = re.compile(pattern, re.MULTILINE | re.DOTALL)
        return cls._REGEX_CACHE[pattern]
    
    @staticmethod
    def standardize_entities_with_luris_v2(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Standardize entities using LurisEntityV2 schema.

        This handles field name variations and ensures all entities
        conform to the LurisEntityV2 specification.

        Args:
            entities: List of entity dictionaries with potential field variations

        Returns:
            List of standardized entity dictionaries
        """
        standardized = []

        for entity_dict in entities:
            try:
                # Use LurisEntityV2 to normalize fields
                # This automatically handles:
                # - type → entity_type
                # - start/end → start_pos/end_pos
                # - confidence_score → confidence
                # - Confidence range validation (0.0-1.0)
                # - Position validation
                entity_v2 = LurisEntityV2.from_dict(entity_dict)

                # Validate the entity
                if entity_v2.is_valid():
                    standardized.append(entity_v2.to_dict())
                else:
                    # Log validation issues but still include entity
                    issues = entity_v2.validate()
                    logger.warning(f"Entity validation issues: {issues}, including anyway")
                    standardized.append(entity_v2.to_dict())

            except Exception as e:
                logger.warning(f"Failed to standardize entity: {e}, using original")
                # Fall back to original if standardization fails
                standardized.append(entity_dict)

        return standardized

    @staticmethod
    def parse_ai_json_response(raw_response: str, agent_name: str = "Unknown",
                               template_hint: Optional[str] = None) -> Dict[str, Any]:
        """
        Bulletproof parsing of vLLM/AI-generated JSON responses with aggressive extraction.
        
        Args:
            raw_response: Raw response from vLLM/AI model
            agent_name: Name of the agent for logging purposes
            template_hint: Optional hint about expected template type
            
        Returns:
            Parsed JSON dictionary with validation
            
        Raises:
            ValueError: Only if response is completely unparseable
        """
        start_time = time.time()
        logger.debug(f"{agent_name}: Parsing JSON response ({len(raw_response)} chars)")
        
        # Fast path: Check if response starts with { and ends with } (object format)
        trimmed = raw_response.strip()
        if trimmed.startswith('{') and trimmed.endswith('}'):
            try:
                result = json.loads(trimmed)
                elapsed = (time.time() - start_time) * 1000
                logger.debug(f"{agent_name}: Fast-path object JSON parsing successful ({elapsed:.1f}ms)")
                return JSONResponseParser._validate_and_fix_response(result, template_hint)
            except json.JSONDecodeError:
                pass  # Fall through to aggressive extraction
        
        # PRIORITY: Direct array format (ai_enhanced strategy template)
        if trimmed.startswith('[') and trimmed.endswith(']'):
            try:
                result = json.loads(trimmed)
                elapsed = (time.time() - start_time) * 1000
                logger.debug(f"{agent_name}: Fast-path array JSON parsing successful ({elapsed:.1f}ms)")
                logger.debug(f"🔍 DEBUG Parser: Parsed array with {len(result)} items")
                if result:
                    logger.debug(f"🔍 DEBUG Parser: First item: {result[0]}")
                # For direct array responses, standardize using LurisEntityV2
                logger.debug(f"🔍 DEBUG Parser: Standardizing {len(result)} entities with LurisEntityV2")
                standardized = JSONResponseParser.standardize_entities_with_luris_v2(result)
                logger.debug(f"✅ DEBUG Parser: Standardized to {len(standardized)} valid entities")
                return standardized
            except json.JSONDecodeError as e:
                logger.debug(f"{agent_name}: Direct array parsing failed: {e}, falling through to extraction")
                pass  # Fall through to aggressive extraction
        
        # Aggressive extraction: Strip any text before { and after }
        json_content = JSONResponseParser._aggressive_json_extraction(raw_response)
        
        # Try direct parsing after extraction
        try:
            result = json.loads(json_content)
            elapsed = (time.time() - start_time) * 1000
            logger.debug(f"{agent_name}: JSON parsing successful after extraction ({elapsed:.1f}ms)")
            return JSONResponseParser._validate_and_fix_response(result, template_hint)
        except json.JSONDecodeError as e:
            logger.debug(f"{agent_name}: Initial parsing failed: {e}")
        
        # Progressive correction pipeline
        correction_pipeline = [
            ("strip_vllm_artifacts", JSONResponseParser._strip_vllm_artifacts),
            ("fix_unterminated_strings_v2", JSONResponseParser._fix_unterminated_strings_v2),
            ("fix_unescaped_quotes_v2", JSONResponseParser._fix_unescaped_quotes_v2),
            ("fix_json_structure", JSONResponseParser._fix_json_structure),
            ("fix_numeric_values", JSONResponseParser._fix_numeric_values),
            ("aggressive_cleanup", JSONResponseParser._aggressive_cleanup),
        ]
        
        current_content = json_content
        for step_name, fix_function in correction_pipeline:
            try:
                fixed_content = fix_function(current_content)
                if fixed_content != current_content:
                    logger.debug(f"{agent_name}: Applied {step_name}")
                    current_content = fixed_content
                    
                    # Try parsing after each fix
                    try:
                        result = json.loads(current_content)
                        elapsed = (time.time() - start_time) * 1000
                        logger.info(f"{agent_name}: Parsing successful after {step_name} ({elapsed:.1f}ms)")
                        return JSONResponseParser._validate_and_fix_response(result, template_hint)
                    except json.JSONDecodeError:
                        continue
            except Exception as e:
                logger.debug(f"{agent_name}: Error in {step_name}: {e}")
        
        # Template-aware recovery
        if template_hint:
            result = JSONResponseParser._template_aware_recovery(current_content, template_hint, agent_name)
            if result:
                elapsed = (time.time() - start_time) * 1000
                logger.info(f"{agent_name}: Template-aware recovery successful ({elapsed:.1f}ms)")
                return result
        
        # Final fallback: Return minimal valid structure
        elapsed = (time.time() - start_time) * 1000
        logger.warning(f"{agent_name}: Using fallback response after {elapsed:.1f}ms")
        return JSONResponseParser._create_fallback_response(raw_response, agent_name, template_hint)
    
    @staticmethod
    def _aggressive_json_extraction(raw_response: str) -> str:
        """
        Aggressively extract JSON content from response, removing ALL non-JSON text.
        This is specifically designed for vLLM responses with the new directive templates.
        """
        content = raw_response.strip()
        
        # Priority 1: Find content between outermost { and }
        first_brace = content.find('{')
        last_brace = content.rfind('}')
        
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            json_content = content[first_brace:last_brace + 1]
            logger.debug(f"Extracted JSON from positions {first_brace} to {last_brace + 1}")
            return json_content
        
        # Priority 2: Handle markdown code blocks
        patterns = [
            (r'```json\s*(.*?)\s*```', 1),
            (r'```\s*(.*?)\s*```', 1),
            (r'`(.*?)`', 1)
        ]
        
        for pattern, group in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                extracted = match.group(group).strip()
                if extracted.startswith('{'):
                    logger.debug(f"Extracted JSON from markdown block")
                    return extracted
        
        # Priority 3: Strip known vLLM patterns
        for pattern in JSONResponseParser.VLLM_PATTERNS:
            regex = JSONResponseParser._get_cached_regex(pattern)
            content = regex.sub('', content, 1)
        
        # Priority 4: If still no valid JSON, try to find any JSON-like structure
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, content)
        if matches:
            # Return the largest match (likely the main JSON object)
            largest = max(matches, key=len)
            logger.debug(f"Found JSON-like structure of {len(largest)} chars")
            return largest
        
        # Return whatever we have left
        return content.strip()
    
    @staticmethod
    def _strip_vllm_artifacts(json_content: str) -> str:
        """Remove common vLLM response artifacts that break JSON parsing."""
        # Remove explanatory text that vLLM might add despite directives
        artifacts = [
            r'^\s*Sure[,!]?\s+',
            r'^\s*Here\'s\s+',
            r'^\s*I\'ll\s+',
            r'^\s*The\s+',
            r'^\s*This\s+',
            r'\s*\nNote:.*$',
            r'\s*\nExplanation:.*$',
            r'\s*Let me.*?\n',
        ]
        
        cleaned = json_content
        for pattern in artifacts:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.MULTILINE)
        
        return cleaned.strip()
    
    @staticmethod
    def _fix_unterminated_strings_v2(json_content: str) -> str:
        """
        Enhanced version that specifically handles vLLM's tendency to break strings.
        This version properly escapes newlines WITHIN string values.
        """
        result = []
        i = 0
        in_string = False
        escape_next = False
        
        while i < len(json_content):
            char = json_content[i]
            
            if escape_next:
                # Character is escaped, add it as-is
                result.append(char)
                escape_next = False
                i += 1
                continue
            
            if char == '\\' and in_string:
                # Next character will be escaped
                result.append(char)
                escape_next = True
                i += 1
                continue
            
            if char == '"':
                # Check if this quote is escaped
                if i > 0 and json_content[i-1] == '\\' and not escape_next:
                    # This quote is already escaped
                    result.append(char)
                else:
                    # Toggle string state
                    in_string = not in_string
                    result.append(char)
            elif in_string:
                # We're inside a string - escape problematic characters
                if char == '\n':
                    result.append('\\n')  # Escape the newline
                elif char == '\r':
                    result.append('\\r')  # Escape the carriage return
                elif char == '\t':
                    result.append('\\t')  # Escape the tab
                elif ord(char) < 32:
                    # Other control characters
                    result.append(f'\\u{ord(char):04x}')
                else:
                    result.append(char)
            else:
                # Outside string, keep as-is
                result.append(char)
            
            i += 1
        
        # If we end while still in a string, close it
        if in_string:
            logger.debug("Fixing unterminated string at end of content")
            result.append('"')
        
        return ''.join(result)
    
    @staticmethod
    def _fix_unescaped_quotes_v2(json_content: str) -> str:
        """
        Smarter quote fixing that understands JSON structure better.
        Handles unescaped quotes within string values.
        """
        result = []
        i = 0
        in_key = False
        in_value = False
        after_colon = False
        brace_depth = 0
        bracket_depth = 0
        
        while i < len(json_content):
            char = json_content[i]
            
            # Track structure depth
            if not in_key and not in_value:
                if char == '{':
                    brace_depth += 1
                elif char == '}':
                    brace_depth -= 1
                elif char == '[':
                    bracket_depth += 1
                elif char == ']':
                    bracket_depth -= 1
            
            # Handle quotes
            if char == '"':
                # Check if we're starting/ending a key or value
                if not in_key and not in_value:
                    # Starting a key or value
                    if after_colon:
                        in_value = True
                        after_colon = False
                    else:
                        in_key = True
                    result.append(char)
                elif in_key:
                    # Ending a key
                    in_key = False
                    result.append(char)
                elif in_value:
                    # Check if this is the end of the value or an unescaped quote within
                    # Look ahead to see what follows
                    next_chars = json_content[i+1:i+3] if i+1 < len(json_content) else ""
                    
                    # If followed by comma, bracket, brace, or end, it's the closing quote
                    if next_chars and next_chars[0] in ',}]\n\r \t':
                        in_value = False
                        result.append(char)
                    else:
                        # It's an unescaped quote within the value - escape it
                        result.append('\\"')
                else:
                    result.append(char)
            elif char == ':' and not in_key and not in_value:
                after_colon = True
                result.append(char)
            else:
                result.append(char)
            
            i += 1
        
        return ''.join(result)
    
    @staticmethod
    def _fix_json_structure(json_content: str) -> str:
        """Fix structural issues in JSON (brackets, braces, commas)."""
        # Remove trailing commas
        fixed = re.sub(r',(\s*[}\]])', r'\1', json_content)
        
        # Fix missing commas between elements
        fixed = re.sub(r'"\s*\n\s*"', '",\n"', fixed)
        fixed = re.sub(r'}\s*\n\s*{', '},\n{', fixed)
        fixed = re.sub(r']\s*\n\s*\[', '],\n[', fixed)
        
        # Balance brackets and braces
        open_braces = fixed.count('{')
        close_braces = fixed.count('}')
        open_brackets = fixed.count('[')
        close_brackets = fixed.count(']')
        
        if open_braces > close_braces:
            fixed += '}' * (open_braces - close_braces)
        if open_brackets > close_brackets:
            fixed += ']' * (open_brackets - close_brackets)
        
        return fixed
    
    @staticmethod  
    def _fix_numeric_values(json_content: str) -> str:
        """Fix numeric values that might be incorrectly formatted."""
        # Fix confidence scores that might be out of range
        def fix_confidence(match):
            value = float(match.group(1))
            if value > 1.0:
                # Likely a percentage, convert to decimal
                return f'"confidence": {value / 100}'
            return match.group(0)
        
        fixed = re.sub(r'"confidence":\s*(\d+\.?\d*)', fix_confidence, json_content)
        
        # Fix NaN, Infinity, etc.
        fixed = re.sub(r'\bNaN\b', 'null', fixed)
        fixed = re.sub(r'\bInfinity\b', '999999', fixed)
        fixed = re.sub(r'-Infinity\b', '-999999', fixed)
        
        return fixed
    
    @staticmethod
    def _aggressive_cleanup(json_content: str) -> str:
        """Last-ditch aggressive cleanup to make JSON parseable."""
        # Remove all control characters except newline and tab
        cleaned = ''.join(char if char == '\n' or char == '\t' or ord(char) >= 32 else '' 
                         for char in json_content)
        
        # Ensure proper quote pairing
        quote_count = cleaned.count('"') - cleaned.count('\\"')
        if quote_count % 2 != 0:
            # Odd number of quotes, add one at the end
            cleaned += '"'
        
        # Ensure it starts with { and ends with }
        cleaned = cleaned.strip()
        if not cleaned.startswith('{'):
            cleaned = '{' + cleaned
        if not cleaned.endswith('}'):
            cleaned = cleaned + '}'
        
        return cleaned
    
    @staticmethod
    def _fix_unescaped_quotes(json_content: str) -> str:
        """Fix unescaped quotes within JSON string values."""
        # This is a complex problem - we'll use a heuristic approach
        
        # Pattern to find strings that might have unescaped quotes
        # Look for quotes that are not escaped and are within string values
        
        def fix_quotes_in_match(match):
            full_match = match.group(0)
            key_part = match.group(1)  # The "key":
            quote_part = match.group(2)  # Opening quote
            value_part = match.group(3)  # The value content
            
            # Escape any unescaped quotes in the value part
            # Be careful not to double-escape already escaped quotes
            fixed_value = re.sub(r'(?<!\\)"', '\\"', value_part)
            
            return f'{key_part}{quote_part}{fixed_value}'
        
        # Pattern to match JSON string values: "key": "value with possible "quotes""
        pattern = r'("[\w_]+"\s*:\s*)(")([^"]*(?:\\.[^"]*)*?)(?="[\s,}]|$)'
        
        try:
            fixed = re.sub(pattern, fix_quotes_in_match, json_content)
            return fixed
        except Exception:
            return json_content
    
    @staticmethod
    def _fix_trailing_commas(json_content: str) -> str:
        """Remove trailing commas before closing brackets/braces."""
        # Remove trailing commas before }
        fixed = re.sub(r',(\s*})', r'\1', json_content)
        # Remove trailing commas before ]
        fixed = re.sub(r',(\s*])', r'\1', fixed)
        return fixed
    
    @staticmethod
    def _fix_unterminated_strings(json_content: str) -> str:
        """
        Enhanced fix for unterminated strings using character-by-character analysis.
        
        This addresses the specific "Unterminated string starting at: line X column Y" errors
        we're seeing in the logs by doing precise character-level tracking.
        """
        if not json_content.strip():
            return json_content
            
        result = []
        i = 0
        in_string = False
        escape_next = False
        quote_start_pos = None
        
        while i < len(json_content):
            char = json_content[i]
            
            if escape_next:
                # Character is escaped, add it as-is
                result.append(char)
                escape_next = False
                i += 1
                continue
            
            if char == '\\' and in_string:
                # Next character will be escaped
                result.append(char)
                escape_next = True
                i += 1
                continue
            
            if char == '"':
                if not in_string:
                    # Starting a string
                    in_string = True
                    quote_start_pos = i
                    result.append(char)
                else:
                    # Ending a string
                    in_string = False
                    quote_start_pos = None
                    result.append(char)
            
            elif in_string:
                # We're inside a string
                if char in ['\n', '\r']:
                    # Unescaped newline in string - this is likely the issue!
                    # Close the string before the newline and reopen after
                    result.append('"')  # Close current string
                    result.append(char)  # Add the newline
                    in_string = False
                    quote_start_pos = None
                    
                    # Look ahead to see if we need to reopen a string
                    next_i = i + 1
                    while next_i < len(json_content) and json_content[next_i] in [' ', '\t']:
                        next_i += 1
                    
                    # If next significant character suggests we're continuing a string value
                    if (next_i < len(json_content) and 
                        json_content[next_i] not in [',', '}', ']', '"'] and
                        json_content[next_i].isprintable()):
                        
                        # Skip whitespace and reopen string
                        while i + 1 < len(json_content) and json_content[i + 1] in [' ', '\t']:
                            i += 1
                            result.append(json_content[i])
                        
                        if i + 1 < len(json_content):
                            result.append('"')  # Reopen string
                            in_string = True
                            quote_start_pos = len(result) - 1
                
                elif char == '\t':
                    # Escape tabs properly
                    result.append('\\t')
                elif ord(char) < 32 and char not in ['\n', '\r', '\t']:
                    # Other control characters - escape them
                    result.append(f'\\u{ord(char):04x}')
                else:
                    # Regular character in string
                    result.append(char)
            
            else:
                # We're outside a string
                result.append(char)
            
            i += 1
        
        # If we end while still in a string, close it
        if in_string:
            logger.warning(f"Fixing unterminated string that started at position {quote_start_pos}")
            result.append('"')
        
        return ''.join(result)
    
    @staticmethod
    def _fix_missing_brackets(json_content: str) -> str:
        """Add missing closing brackets/braces."""
        # Count opening vs closing brackets
        open_braces = json_content.count('{') - json_content.count('}')
        open_brackets = json_content.count('[') - json_content.count(']')
        
        fixed = json_content
        
        if open_braces > 0:
            logger.debug(f"Adding {open_braces} missing closing braces")
            fixed += '}' * open_braces
            
        if open_brackets > 0:
            logger.debug(f"Adding {open_brackets} missing closing brackets")
            fixed += ']' * open_brackets
        
        return fixed
    
    @staticmethod
    def _fix_newlines_and_tabs(json_content: str) -> str:
        """Fix unescaped newlines and tabs in string values."""
        # Replace unescaped newlines and tabs in string values
        def escape_in_strings(match):
            quote_content = match.group(1)
            # Escape newlines and tabs
            escaped = quote_content.replace('\n', '\\n').replace('\t', '\\t').replace('\r', '\\r')
            return f'"{escaped}"'
        
        # Pattern to match quoted strings
        pattern = r'"([^"\\]*(?:\\.[^"\\]*)*)"'
        
        try:
            fixed = re.sub(pattern, escape_in_strings, json_content)
            return fixed
        except Exception:
            return json_content
    
    @staticmethod
    def _fix_control_characters(json_content: str) -> str:
        """Remove or escape control characters that break JSON."""
        # Remove most control characters except those we want to keep
        fixed = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', json_content)
        return fixed
    
    @staticmethod
    def _validate_and_fix_response(response: Dict[str, Any], 
                                   template_hint: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate and fix the parsed response based on expected structure.
        """
        # Fix confidence scores that might be out of range
        if 'confidence_score' in response:
            score = response['confidence_score']
            if isinstance(score, (int, float)):
                if score > 1.0:
                    response['confidence_score'] = score / 100.0
                elif score < 0:
                    response['confidence_score'] = 0.0
        
        # Standardize entities using LurisEntityV2
        if 'entities' in response and isinstance(response['entities'], list):
            logger.debug(f"Standardizing {len(response['entities'])} entities with LurisEntityV2")
            response['entities'] = JSONResponseParser.standardize_entities_with_luris_v2(response['entities'])
        
        # Ensure citations have required fields
        if 'citations' in response and isinstance(response['citations'], list):
            for citation in response['citations']:
                if 'citation_text' not in citation and 'text' in citation:
                    citation['citation_text'] = citation['text']
                if 'citation_type' not in citation and 'type' in citation:
                    citation['citation_type'] = citation['type']
        
        # Add default extraction_summary if missing
        if 'extraction_summary' not in response and template_hint in ['relationship', 'multipass']:
            response['extraction_summary'] = {
                'total_items_analyzed': len(response.get('entities', [])),
                'relationships_extracted': len(response.get('extracted_relationships', [])),
                'processing_status': 'completed'
            }
        
        return response
    
    @staticmethod
    def _template_aware_recovery(json_content: str, template_type: str, 
                                 agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Attempt recovery based on known template structure.
        """
        try:
            expected_keys = JSONResponseParser.TEMPLATE_TYPES.get(template_type, [])
            
            # Try to extract specific sections based on template
            recovered = {}
            
            # Look for entities array
            entity_pattern = r'"entities"\s*:\s*\[(.*?)\]'
            entity_match = re.search(entity_pattern, json_content, re.DOTALL)
            if entity_match:
                try:
                    entities_str = '[' + entity_match.group(1) + ']'
                    entities = json.loads(entities_str)
                    recovered['entities'] = entities
                except:
                    recovered['entities'] = []
            
            # Look for citations array
            citation_pattern = r'"citations"\s*:\s*\[(.*?)\]'
            citation_match = re.search(citation_pattern, json_content, re.DOTALL)
            if citation_match:
                try:
                    citations_str = '[' + citation_match.group(1) + ']'
                    citations = json.loads(citations_str)
                    recovered['citations'] = citations
                except:
                    recovered['citations'] = []
            
            # Look for relationships array
            rel_pattern = r'"(?:extracted_)?relationships"\s*:\s*\[(.*?)\]'
            rel_match = re.search(rel_pattern, json_content, re.DOTALL)
            if rel_match:
                try:
                    rels_str = '[' + rel_match.group(1) + ']'
                    relationships = json.loads(rels_str)
                    recovered['extracted_relationships'] = relationships
                except:
                    recovered['extracted_relationships'] = []
            
            # Look for confidence score
            conf_pattern = r'"confidence(?:_score)?"\s*:\s*([0-9.]+)'
            conf_match = re.search(conf_pattern, json_content)
            if conf_match:
                try:
                    confidence = float(conf_match.group(1))
                    if confidence > 1.0:
                        confidence = confidence / 100.0
                    recovered['confidence_score'] = confidence
                except:
                    pass
            
            # Add extraction summary if we recovered anything
            if recovered:
                recovered['extraction_summary'] = {
                    'total_items_analyzed': len(recovered.get('entities', [])),
                    'relationships_extracted': len(recovered.get('extracted_relationships', [])),
                    'citations_found': len(recovered.get('citations', [])),
                    'recovery_method': 'template_aware_recovery',
                    'template_type': template_type
                }
                
                logger.info(f"{agent_name}: Template-aware recovery extracted {len(recovered)} sections")
                return recovered
        
        except Exception as e:
            logger.debug(f"{agent_name}: Template recovery failed: {e}")
        
        return None
    
    @staticmethod
    def _create_fallback_response(raw_response: str, agent_name: str, 
                                  template_hint: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a minimal valid response when all parsing attempts fail.
        This ensures the system can continue operating.
        """
        logger.error(f"{agent_name}: Creating fallback response after all parsing attempts failed")
        
        # Log a sample of the problematic response for debugging
        sample = raw_response[:500] if len(raw_response) > 500 else raw_response
        logger.error(f"{agent_name}: Problematic response sample: {sample}")
        
        # Create a minimal valid structure based on template hint
        if template_hint == 'relationship':
            return {
                'extracted_relationships': [],
                'extraction_summary': {
                    'total_items_analyzed': 0,
                    'relationships_extracted': 0,
                    'error': 'JSON parsing failed - returning empty result',
                    'parsing_method': 'fallback'
                },
                'processing_metrics': {
                    'parsing_success': False,
                    'error_type': 'complete_parsing_failure'
                }
            }
        elif template_hint == 'entity_extraction':
            return {
                'entities': [],
                'extraction_metadata': {
                    'total_extracted': 0,
                    'error': 'JSON parsing failed - returning empty result',
                    'parsing_method': 'fallback'
                }
            }
        elif template_hint == 'citation':
            return {
                'citations': [],
                'validation_results': {
                    'total_citations': 0,
                    'valid_citations': 0,
                    'error': 'JSON parsing failed - returning empty result'
                }
            }
        else:
            # Generic fallback
            return {
                'entities': [],
                'citations': [],
                'extracted_relationships': [],
                'extraction_summary': {
                    'error': 'Complete JSON parsing failure',
                    'parsing_method': 'generic_fallback',
                    'response_length': len(raw_response),
                    'agent': agent_name
                }
            }
    
    @staticmethod
    def _last_resort_parsing(json_content: str, agent_name: str) -> Optional[Dict[str, Any]]:
        """Last resort parsing attempt using liberal interpretation."""
        try:
            # Try to extract just the main structure
            logger.warning(f"{agent_name}: Attempting last resort parsing")
            
            # Look for basic JSON structure patterns
            if '{' in json_content and '}' in json_content:
                # Try to find the main JSON object
                start = json_content.find('{')
                end = json_content.rfind('}') + 1
                
                if start != -1 and end > start:
                    main_json = json_content[start:end]
                    
                    # Apply all fixes again
                    main_json = JSONResponseParser._fix_trailing_commas(main_json)
                    main_json = JSONResponseParser._fix_missing_brackets(main_json)
                    
                    try:
                        result = json.loads(main_json)
                        logger.info(f"{agent_name}: Last resort parsing successful")
                        return result
                    except json.JSONDecodeError:
                        pass
            
            # Try to extract any valid JSON objects from the content
            # Look for patterns that suggest relationship data
            relationships_found = []
            
            # Try to find individual relationship objects
            import re
            relationship_pattern = r'\{[^{}]*"source_entity_id"[^{}]*"target_entity_id"[^{}]*\}'
            matches = re.findall(relationship_pattern, json_content, re.DOTALL)
            
            for match in matches:
                try:
                    rel_obj = json.loads(match)
                    if "source_entity_id" in rel_obj and "target_entity_id" in rel_obj:
                        relationships_found.append(rel_obj)
                except:
                    pass
            
            # Return a minimal valid response structure as absolute fallback
            logger.warning(f"{agent_name}: Returning minimal fallback response with {len(relationships_found)} recovered relationships")
            return {
                "extracted_relationships": relationships_found,
                "extraction_summary": {
                    "total_items_analyzed": 0,
                    "relationships_extracted": len(relationships_found),
                    "error": "JSON parsing partially recovered" if relationships_found else "JSON parsing failed - returning empty result"
                },
                "processing_metrics": {
                    "parsing_success": len(relationships_found) > 0
                }
            }
            
        except Exception as e:
            logger.error(f"{agent_name}: Last resort parsing error: {e}")
            return None
    
    @staticmethod
    def validate_response_structure(parsed_response: Dict[str, Any], expected_keys: list) -> bool:
        """Validate that the parsed response has expected structure."""
        try:
            # Check for required top-level keys
            for key in expected_keys:
                if key not in parsed_response:
                    logger.warning(f"Missing expected key in response: {key}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating response structure: {e}")
            return False