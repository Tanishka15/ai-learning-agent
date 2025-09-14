"""
Reasoning and Planning Engine

This module provides intelligent reasoning capabilities for the AI agent,
including topic decomposition, question analysis, and strategic planning.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from transformers import pipeline
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False


class ReasoningType(Enum):
    """Types of reasoning the engine can perform."""
    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"
    ANALOGICAL = "analogical"


@dataclass
class ReasoningStep:
    """Represents a single step in the reasoning process."""
    step_type: ReasoningType
    input_data: Dict[str, Any]
    reasoning: str
    output: Any
    confidence: float


@dataclass
class QuestionAnalysis:
    """Analysis of a user question."""
    question_type: str
    key_concepts: List[str]
    difficulty_level: str
    required_knowledge_domains: List[str]
    confidence: float


class ReasoningEngine:
    """
    Advanced reasoning and planning engine for the AI agent.
    
    Provides capabilities for logical reasoning, planning, problem decomposition,
    and intelligent decision making.
    """
    
    def __init__(self, config):
        """Initialize the reasoning engine."""
        self.config = config
        self.logger = logging.getLogger("reasoning_engine")
        
        # Initialize AI models if available
        self.llm_client = None
        self.reasoning_pipeline = None
        
        if HAS_OPENAI and hasattr(config, 'ai_models'):
            try:
                openai.api_key = config.api_keys.get('openai')
                self.llm_client = openai
            except Exception as e:
                self.logger.warning(f"Failed to initialize OpenAI client: {e}")
        
        if HAS_TRANSFORMERS:
            try:
                self.reasoning_pipeline = pipeline(
                    "text-generation", 
                    model="microsoft/DialoGPT-medium"
                )
            except Exception as e:
                self.logger.warning(f"Failed to initialize reasoning pipeline: {e}")
    
    async def analyze_question(self, question: str) -> QuestionAnalysis:
        """
        Analyze a user question to understand its structure and requirements.
        
        Args:
            question: The question to analyze
            
        Returns:
            QuestionAnalysis object with detailed analysis
        """
        self.logger.info(f"Analyzing question: {question}")
        
        # Basic question type classification
        question_lower = question.lower().strip()
        
        if question_lower.startswith(('what', 'who', 'where', 'when')):
            question_type = "factual"
        elif question_lower.startswith(('how')):
            question_type = "procedural"
        elif question_lower.startswith(('why')):
            question_type = "explanatory"
        elif question_lower.startswith(('is', 'are', 'can', 'do', 'does')):
            question_type = "yes_no"
        else:
            question_type = "complex"
        
        # Extract key concepts (simplified approach)
        key_concepts = await self._extract_key_concepts(question)
        
        # Estimate difficulty
        difficulty_level = self._estimate_difficulty(question, key_concepts)
        
        # Identify knowledge domains
        domains = await self._identify_knowledge_domains(key_concepts)
        
        return QuestionAnalysis(
            question_type=question_type,
            key_concepts=key_concepts,
            difficulty_level=difficulty_level,
            required_knowledge_domains=domains,
            confidence=0.8
        )
    
    async def decompose_topic(self, topic: str) -> List[str]:
        """
        Break down a complex topic into manageable subtopics.
        
        Args:
            topic: The main topic to decompose
            
        Returns:
            List of subtopics
        """
        self.logger.info(f"Decomposing topic: {topic}")
        
        # Use LLM if available, otherwise use heuristic approach
        if self.llm_client:
            subtopics = await self._llm_decompose_topic(topic)
        else:
            subtopics = await self._heuristic_decompose_topic(topic)
        
        self.logger.info(f"Generated {len(subtopics)} subtopics for {topic}")
        return subtopics
    
    async def prioritize_subtopics(
        self, 
        subtopics: List[str], 
        difficulty_level: str
    ) -> List[str]:
        """
        Prioritize subtopics based on difficulty level and learning progression.
        
        Args:
            subtopics: List of subtopics to prioritize
            difficulty_level: Target difficulty level
            
        Returns:
            Prioritized list of subtopics
        """
        self.logger.info(f"Prioritizing {len(subtopics)} subtopics for {difficulty_level} level")
        
        # Create scoring for each subtopic
        scored_topics = []
        for subtopic in subtopics:
            score = await self._score_subtopic(subtopic, difficulty_level)
            scored_topics.append((subtopic, score))
        
        # Sort by score (higher score = higher priority)
        scored_topics.sort(key=lambda x: x[1], reverse=True)
        
        prioritized = [topic for topic, score in scored_topics]
        self.logger.info(f"Prioritized subtopics: {prioritized}")
        
        return prioritized
    
    async def generate_answer(
        self, 
        question: str, 
        knowledge: Dict[str, Any], 
        analysis: QuestionAnalysis
    ) -> str:
        """
        Generate an answer to a question using available knowledge.
        
        Args:
            question: The question to answer
            knowledge: Available knowledge base
            analysis: Question analysis results
            
        Returns:
            Generated answer
        """
        self.logger.info(f"Generating answer for: {question}")
        
        if self.llm_client:
            answer = await self._llm_generate_answer(question, knowledge, analysis)
        else:
            answer = await self._template_generate_answer(question, knowledge, analysis)
        
        return answer
    
    async def plan_learning_sequence(
        self, 
        topic: str, 
        user_knowledge: Dict[str, Any],
        target_level: str
    ) -> List[Dict[str, Any]]:
        """
        Create an optimal learning sequence for a topic.
        
        Args:
            topic: The topic to learn
            user_knowledge: Current user knowledge level
            target_level: Target knowledge level
            
        Returns:
            Structured learning plan
        """
        self.logger.info(f"Planning learning sequence for {topic}")
        
        # Decompose topic
        subtopics = await self.decompose_topic(topic)
        
        # Assess prerequisites
        prerequisites = await self._identify_prerequisites(subtopics)
        
        # Create dependency graph
        dependency_graph = await self._build_dependency_graph(subtopics, prerequisites)
        
        # Generate optimal sequence
        learning_sequence = await self._optimize_learning_sequence(
            dependency_graph, user_knowledge, target_level
        )
        
        return learning_sequence
    
    async def _extract_key_concepts(self, text: str) -> List[str]:
        """Extract key concepts from text."""
        # Simple keyword extraction (could be enhanced with NLP)
        import re
        
        # Remove common words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'what', 'how', 'why', 'when', 'where'
        }
        
        # Extract words and filter
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        concepts = [word for word in words if word not in stop_words]
        
        # Return unique concepts, limited to most relevant
        return list(set(concepts))[:10]
    
    def _estimate_difficulty(self, question: str, concepts: List[str]) -> str:
        """Estimate question difficulty based on structure and concepts."""
        # Simple heuristic-based difficulty estimation
        complexity_indicators = [
            'analyze', 'synthesize', 'evaluate', 'compare', 'contrast',
            'implications', 'consequences', 'relationships', 'framework'
        ]
        
        technical_indicators = [
            'algorithm', 'implementation', 'optimization', 'architecture',
            'quantum', 'neural', 'molecular', 'theoretical'
        ]
        
        question_lower = question.lower()
        
        if any(indicator in question_lower for indicator in complexity_indicators):
            return "advanced"
        elif any(indicator in question_lower for indicator in technical_indicators):
            return "intermediate"
        elif len(concepts) > 5:
            return "intermediate"
        else:
            return "beginner"
    
    async def _identify_knowledge_domains(self, concepts: List[str]) -> List[str]:
        """Identify knowledge domains based on concepts."""
        # Domain classification (simplified)
        domain_keywords = {
            'computer_science': ['algorithm', 'programming', 'software', 'computer', 'code'],
            'mathematics': ['equation', 'theorem', 'proof', 'calculation', 'formula'],
            'physics': ['quantum', 'energy', 'force', 'motion', 'particle'],
            'biology': ['cell', 'organism', 'dna', 'evolution', 'genetics'],
            'chemistry': ['molecule', 'reaction', 'element', 'compound', 'bond'],
            'history': ['war', 'empire', 'civilization', 'ancient', 'medieval'],
            'literature': ['novel', 'poetry', 'author', 'narrative', 'character']
        }
        
        identified_domains = []
        for domain, keywords in domain_keywords.items():
            if any(keyword in ' '.join(concepts) for keyword in keywords):
                identified_domains.append(domain)
        
        return identified_domains if identified_domains else ['general']
    
    async def _llm_decompose_topic(self, topic: str) -> List[str]:
        """Use LLM to decompose topic into subtopics."""
        try:
            prompt = f"""
            Break down the topic "{topic}" into 5-8 key subtopics that would be essential 
            for a comprehensive understanding. List only the subtopic names, one per line.
            """
            
            response = await self.llm_client.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200
            )
            
            content = response.choices[0].message.content
            subtopics = [line.strip() for line in content.split('\n') if line.strip()]
            return subtopics[:8]  # Limit to 8 subtopics
            
        except Exception as e:
            self.logger.error(f"LLM decomposition failed: {e}")
            return await self._heuristic_decompose_topic(topic)
    
    async def _heuristic_decompose_topic(self, topic: str) -> List[str]:
        """Use heuristic approach to decompose topic."""
        # Simple decomposition based on common patterns
        base_subtopics = [
            f"Introduction to {topic}",
            f"Basic concepts of {topic}",
            f"Applications of {topic}",
            f"Advanced {topic} techniques",
            f"Current research in {topic}"
        ]
        
        # Add domain-specific subtopics based on keywords
        topic_lower = topic.lower()
        
        if any(word in topic_lower for word in ['programming', 'software', 'algorithm']):
            base_subtopics.extend([
                f"{topic} implementation",
                f"{topic} best practices"
            ])
        elif any(word in topic_lower for word in ['theory', 'mathematics', 'physics']):
            base_subtopics.extend([
                f"Mathematical foundations of {topic}",
                f"Theoretical framework of {topic}"
            ])
        
        return base_subtopics[:6]  # Return first 6
    
    async def _score_subtopic(self, subtopic: str, difficulty_level: str) -> float:
        """Score a subtopic for prioritization."""
        score = 1.0
        
        subtopic_lower = subtopic.lower()
        
        # Adjust score based on difficulty level
        if difficulty_level == "beginner":
            if any(word in subtopic_lower for word in ['introduction', 'basic', 'fundamentals']):
                score += 2.0
            elif any(word in subtopic_lower for word in ['advanced', 'complex', 'research']):
                score -= 1.0
        elif difficulty_level == "advanced":
            if any(word in subtopic_lower for word in ['advanced', 'research', 'cutting-edge']):
                score += 2.0
            elif any(word in subtopic_lower for word in ['introduction', 'basic']):
                score -= 0.5
        
        return score
    
    async def _llm_generate_answer(
        self, 
        question: str, 
        knowledge: Dict[str, Any], 
        analysis: QuestionAnalysis
    ) -> str:
        """Generate answer using LLM."""
        try:
            # Prepare context from knowledge
            context = ""
            if 'summary' in knowledge:
                context += f"Summary: {knowledge['summary']}\n\n"
            
            if 'concepts' in knowledge:
                context += f"Key concepts: {', '.join(knowledge['concepts'][:10])}\n\n"
            
            prompt = f"""
            Context: {context}
            
            Question: {question}
            
            Please provide a clear, accurate answer based on the context provided.
            If the context doesn't contain enough information, please say so.
            """
            
            response = await self.llm_client.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"LLM answer generation failed: {e}")
            return await self._template_generate_answer(question, knowledge, analysis)
    
    async def _template_generate_answer(
        self, 
        question: str, 
        knowledge: Dict[str, Any], 
        analysis: QuestionAnalysis
    ) -> str:
        """Generate answer using template-based approach."""
        # Simple template-based answer generation
        if analysis.question_type == "factual":
            if 'summary' in knowledge:
                return f"Based on available information: {knowledge['summary'][:300]}..."
            else:
                return "I don't have enough specific information to answer this factual question."
        
        elif analysis.question_type == "explanatory":
            return f"This is a complex question about {', '.join(analysis.key_concepts)}. " \
                   f"To fully explain this, we would need to consider multiple aspects including " \
                   f"the fundamental concepts and their relationships."
        
        else:
            return f"This question relates to {', '.join(analysis.key_concepts)}. " \
                   f"Let me provide what information I have available."
    
    async def _identify_prerequisites(self, subtopics: List[str]) -> Dict[str, List[str]]:
        """Identify prerequisites for each subtopic."""
        prerequisites = {}
        
        for subtopic in subtopics:
            subtopic_lower = subtopic.lower()
            prereqs = []
            
            # Simple heuristic for identifying prerequisites
            if 'advanced' in subtopic_lower:
                # Advanced topics need basic understanding
                basic_topics = [t for t in subtopics if 'basic' in t.lower() or 'introduction' in t.lower()]
                prereqs.extend(basic_topics)
            
            elif 'application' in subtopic_lower:
                # Applications need conceptual understanding
                concept_topics = [t for t in subtopics if 'concept' in t.lower() or 'theory' in t.lower()]
                prereqs.extend(concept_topics)
            
            prerequisites[subtopic] = prereqs
        
        return prerequisites
    
    async def _build_dependency_graph(
        self, 
        subtopics: List[str], 
        prerequisites: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Build a dependency graph for learning sequence optimization."""
        graph = {
            'nodes': subtopics,
            'edges': [],
            'levels': {}
        }
        
        # Add edges for prerequisites
        for topic, prereqs in prerequisites.items():
            for prereq in prereqs:
                if prereq in subtopics:
                    graph['edges'].append((prereq, topic))
        
        # Calculate levels (topological sort)
        in_degree = {topic: 0 for topic in subtopics}
        for source, target in graph['edges']:
            in_degree[target] += 1
        
        level = 0
        remaining = set(subtopics)
        
        while remaining:
            current_level = [topic for topic in remaining if in_degree[topic] == 0]
            if not current_level:
                # Handle cycles by breaking them
                current_level = [min(remaining)]
            
            for topic in current_level:
                graph['levels'][topic] = level
                remaining.remove(topic)
                
                # Update in-degrees
                for source, target in graph['edges']:
                    if source == topic and target in remaining:
                        in_degree[target] -= 1
            
            level += 1
        
        return graph
    
    async def _optimize_learning_sequence(
        self, 
        dependency_graph: Dict[str, Any], 
        user_knowledge: Dict[str, Any],
        target_level: str
    ) -> List[Dict[str, Any]]:
        """Optimize the learning sequence based on dependencies and user knowledge."""
        sequence = []
        
        # Sort topics by level (prerequisites first)
        topics_by_level = {}
        for topic, level in dependency_graph['levels'].items():
            if level not in topics_by_level:
                topics_by_level[level] = []
            topics_by_level[level].append(topic)
        
        # Build sequence
        for level in sorted(topics_by_level.keys()):
            for topic in topics_by_level[level]:
                sequence.append({
                    'topic': topic,
                    'level': level,
                    'estimated_time_minutes': 30,  # Default estimate
                    'difficulty': self._estimate_topic_difficulty(topic),
                    'prerequisites_met': self._check_prerequisites_met(
                        topic, dependency_graph, user_knowledge
                    )
                })
        
        return sequence
    
    def _estimate_topic_difficulty(self, topic: str) -> str:
        """Estimate the difficulty of a topic."""
        topic_lower = topic.lower()
        
        if any(word in topic_lower for word in ['advanced', 'complex', 'research']):
            return "advanced"
        elif any(word in topic_lower for word in ['intermediate', 'application']):
            return "intermediate"
        else:
            return "beginner"
    
    def _check_prerequisites_met(
        self, 
        topic: str, 
        dependency_graph: Dict[str, Any], 
        user_knowledge: Dict[str, Any]
    ) -> bool:
        """Check if prerequisites for a topic are met."""
        # Simple check - in a real implementation, this would be more sophisticated
        return True  # Assume prerequisites are met for now