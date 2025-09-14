"""
Text Processing Module

Provides text analysis, concept extraction, and NLP capabilities
for processing gathered information.
"""

import logging
import re
from typing import List, Dict, Any, Set, Tuple
from collections import Counter
from dataclasses import dataclass


@dataclass
class ProcessedDocument:
    """Represents a processed document."""
    original_text: str
    cleaned_text: str
    sentences: List[str]
    concepts: List[str]
    entities: List[str]
    summary: str
    metadata: Dict[str, Any]


@dataclass
class ConceptRelationship:
    """Represents a relationship between concepts."""
    source: str
    target: str
    relationship_type: str
    strength: float
    context: str


class TextProcessor:
    """
    Advanced text processor for analyzing and extracting information from text.
    
    Features:
    - Text cleaning and normalization
    - Concept and entity extraction
    - Relationship identification
    - Summarization
    - Content structuring
    """
    
    def __init__(self, config):
        """Initialize the text processor."""
        self.config = config
        self.logger = logging.getLogger("text_processor")

        # Text processing settings
        self.max_doc_length = getattr(config.knowledge, 'max_document_length', 10000)
        self.chunk_size = getattr(config.knowledge, 'chunk_size', 1000)
        self.chunk_overlap = getattr(config.knowledge, 'chunk_overlap', 200)

        # Stop words for concept extraction
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
            'what', 'how', 'why', 'when', 'where', 'who', 'which', 'their', 'there',
            'they', 'them', 'we', 'us', 'our', 'you', 'your', 'he', 'him', 'his',
            'she', 'her', 'it', 'its', 'i', 'me', 'my', 'mine'
        }

        self.logger.info("Text processor initialized")
    
    async def process_documents(self, documents: List[str]) -> str:
        """
        Process multiple documents into a single cleaned text.
        
        Args:
            documents: List of document texts
            
        Returns:
            Combined and cleaned text
        """
        self.logger.info(f"Processing {len(documents)} documents")
        
        combined_text = ""
        for doc in documents:
            if doc:
                cleaned = self._clean_text(doc)
                combined_text += cleaned + "\n\n"
        
        # Limit total length
        if len(combined_text) > self.max_doc_length:
            combined_text = combined_text[:self.max_doc_length]
            # Try to end at a sentence boundary
            last_period = combined_text.rfind('.')
            if last_period > self.max_doc_length * 0.8:
                combined_text = combined_text[:last_period + 1]
        
        return combined_text.strip()
    
    async def extract_concepts(self, text: str) -> List[str]:
        """
        Extract key concepts from text.
        
        Args:
            text: Input text
            
        Returns:
            List of extracted concepts
        """
        self.logger.info("Extracting concepts from text")
        
        # Clean and tokenize
        cleaned_text = self._clean_text(text)
        words = self._tokenize(cleaned_text)
        
        # Filter words
        filtered_words = [
            word for word in words
            if len(word) > 2 and word.lower() not in self.stop_words
        ]
        
        # Count word frequencies
        word_counts = Counter(filtered_words)
        
        # Extract noun phrases (simplified)
        noun_phrases = self._extract_noun_phrases(cleaned_text)
        
        # Combine single words and phrases
        concepts = []
        
        # Add high-frequency single words
        for word, count in word_counts.most_common(20):
            if count > 1:  # Appears more than once
                concepts.append(word.lower())
        
        # Add noun phrases
        for phrase in noun_phrases:
            if len(phrase.split()) > 1:  # Multi-word phrases
                concepts.append(phrase.lower())
        
        # Remove duplicates and return top concepts
        unique_concepts = list(set(concepts))
        return unique_concepts[:15]  # Return top 15 concepts
    
    async def extract_relationships(self, text: str) -> List[ConceptRelationship]:
        """
        Extract relationships between concepts in text.
        
        Args:
            text: Input text
            
        Returns:
            List of concept relationships
        """
        self.logger.info("Extracting concept relationships")
        
        # Get concepts first
        concepts = await self.extract_concepts(text)
        
        if len(concepts) < 2:
            return []
        
        relationships = []
        sentences = self._split_into_sentences(text)
        
        # Look for relationships within sentences
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            # Find concepts in this sentence
            sentence_concepts = [
                concept for concept in concepts
                if concept in sentence_lower
            ]
            
            if len(sentence_concepts) >= 2:
                # Create relationships between concepts in the same sentence
                for i, concept1 in enumerate(sentence_concepts):
                    for concept2 in sentence_concepts[i+1:]:
                        relationship_type = self._identify_relationship_type(sentence, concept1, concept2)
                        
                        relationships.append(ConceptRelationship(
                            source=concept1,
                            target=concept2,
                            relationship_type=relationship_type,
                            strength=0.5,  # Default strength
                            context=sentence[:100]  # First 100 chars of sentence
                        ))
        
        return relationships
    
    async def generate_summary(self, text: str, max_sentences: int = 3) -> str:
        """
        Generate a summary of the text.
        
        Args:
            text: Input text
            max_sentences: Maximum number of sentences in summary
            
        Returns:
            Generated summary
        """
        self.logger.info("Generating text summary")
        
        sentences = self._split_into_sentences(text)
        
        if len(sentences) <= max_sentences:
            return text
        
        # Score sentences based on concept density
        concepts = await self.extract_concepts(text)
        sentence_scores = []
        
        for sentence in sentences:
            score = 0
            sentence_lower = sentence.lower()
            
            # Count concept occurrences
            for concept in concepts:
                if concept in sentence_lower:
                    score += 1
            
            # Bonus for sentence position (earlier sentences often more important)
            position_bonus = max(0, 1 - (sentences.index(sentence) / len(sentences)))
            score += position_bonus * 0.5
            
            sentence_scores.append((sentence, score))
        
        # Sort by score and take top sentences
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        top_sentences = [sent for sent, score in sentence_scores[:max_sentences]]
        
        # Maintain original order
        summary_sentences = []
        for sentence in sentences:
            if sentence in top_sentences:
                summary_sentences.append(sentence)
        
        return ' '.join(summary_sentences)
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)]', '', text)
        
        # Fix spacing around punctuation
        text = re.sub(r'\s+([\.!?])', r'\1', text)
        text = re.sub(r'([\.!?])\s*', r'\1 ', text)
        
        return text.strip()
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        # Simple word tokenization
        words = re.findall(r'\b[a-zA-Z]+\b', text)
        return [word for word in words if len(word) > 1]
    
    def _extract_noun_phrases(self, text: str) -> List[str]:
        """Extract noun phrases (simplified approach)."""
        # This is a simplified implementation
        # In a full system, you'd use proper NLP libraries like spaCy
        
        noun_phrases = []
        
        # Look for patterns like "adjective noun" or "noun noun"
        patterns = [
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # Capitalized words
            r'\b[a-z]+ [a-z]+ing\b',  # word + gerund
            r'\b[a-z]+ed [a-z]+\b',   # past participle + noun
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            noun_phrases.extend(matches)
        
        return list(set(noun_phrases))
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'[\.!?]+', text)
        
        # Clean and filter sentences
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:  # Minimum sentence length
                cleaned_sentences.append(sentence)
        
        return cleaned_sentences
    
    def _identify_relationship_type(self, sentence: str, concept1: str, concept2: str) -> str:
        """Identify the type of relationship between two concepts."""
        sentence_lower = sentence.lower()
        
        # Look for relationship indicators
        if any(word in sentence_lower for word in ['is', 'are', 'was', 'were']):
            return "is_a"
        elif any(word in sentence_lower for word in ['has', 'have', 'contains', 'includes']):
            return "has"
        elif any(word in sentence_lower for word in ['causes', 'leads to', 'results in']):
            return "causes"
        elif any(word in sentence_lower for word in ['uses', 'applies', 'utilizes']):
            return "uses"
        elif any(word in sentence_lower for word in ['part of', 'component of', 'element of']):
            return "part_of"
        else:
            return "related_to"
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks for processing.
        
        Args:
            text: Input text
            
        Returns:
            List of text chunks
        """
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            if end >= len(text):
                chunks.append(text[start:])
                break
            
            # Try to end at a sentence boundary
            chunk = text[start:end]
            last_period = chunk.rfind('.')
            
            if last_period > self.chunk_size * 0.5:  # If we found a period in the latter half
                end = start + last_period + 1
                chunks.append(text[start:end])
                start = end - self.chunk_overlap
            else:
                chunks.append(chunk)
                start = end - self.chunk_overlap
        
        return chunks
    
    def get_text_statistics(self, text: str) -> Dict[str, Any]:
        """Get statistics about the text."""
        words = self._tokenize(text)
        sentences = self._split_into_sentences(text)
        
        return {
            'character_count': len(text),
            'word_count': len(words),
            'sentence_count': len(sentences),
            'average_words_per_sentence': len(words) / len(sentences) if sentences else 0,
            'unique_words': len(set(word.lower() for word in words)),
            'lexical_diversity': len(set(word.lower() for word in words)) / len(words) if words else 0
        }