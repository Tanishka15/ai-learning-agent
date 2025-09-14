"""
Main AI Learning Agent

This module contains the core Agent class that orchestrates all components
of the AI learning system including data collection, reasoning, and teaching.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..connectors.web_scraper import WebScraper
from ..connectors.api_client import APIClient
from ..processors.text_processor import TextProcessor
from ..processors.knowledge_graph import KnowledgeGraph
from ..teacher.tutor import Tutor
from ..teacher.curriculum import CurriculumGenerator
from .reasoning import ReasoningEngine
from .memory import MemorySystem
from ..utils.config import Config
from ..utils.logger import setup_logger


@dataclass
class LearningRequest:
    """Represents a learning request from the user."""
    topic: str
    difficulty_level: str = "beginner"
    learning_style: str = "comprehensive"
    specific_questions: List[str] = None
    time_limit_minutes: Optional[int] = None


@dataclass
class ResearchPlan:
    """Represents a plan for researching a topic."""
    topic: str
    subtopics: List[str]
    data_sources: List[str]
    estimated_time: int
    priority_order: List[str]


class Agent:
    """
    Main AI Learning Agent that coordinates all components.
    
    The agent can autonomously research topics, process information,
    and provide interactive teaching experiences.
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the agent with configuration."""
        self.config = Config(config_path)
        self.logger = setup_logger("agent", self.config.logging.level)
        
        # Initialize core components
        self.memory = MemorySystem(self.config)
        self.reasoning = ReasoningEngine(self.config)
        
        # Initialize data connectors
        self.web_scraper = WebScraper(self.config)
        self.api_client = APIClient(self.config)
        
        # Initialize processors
        self.text_processor = TextProcessor(self.config)
        self.knowledge_graph = KnowledgeGraph(self.config)
        
        # Initialize teaching components
        self.tutor = Tutor(self.config, self.knowledge_graph)
        self.curriculum_generator = CurriculumGenerator(self.config)
        
        self.logger.info("AI Learning Agent initialized successfully")
    
    async def learn_topic(self, topic: str, difficulty: str = "beginner") -> Dict[str, Any]:
        """
        Autonomously research and learn about a topic.
        
        Args:
            topic: The topic to research
            difficulty: Target difficulty level
            
        Returns:
            Dictionary containing learned information and teaching materials
        """
        self.logger.info(f"Starting to learn about: {topic}")
        
        # Create learning request
        request = LearningRequest(
            topic=topic,
            difficulty_level=difficulty
        )
        
        # Plan the research
        plan = await self._create_research_plan(request)
        self.logger.info(f"Research plan created: {plan}")
        
        # Execute the research
        research_results = await self._execute_research(plan)
        
        # Process and structure the information
        processed_knowledge = await self._process_knowledge(research_results)
        
        # Store in memory
        await self.memory.store_knowledge(topic, processed_knowledge)
        
        # Generate teaching materials
        teaching_materials = await self._generate_teaching_materials(
            topic, processed_knowledge, difficulty
        )
        
        self.logger.info(f"Successfully learned about: {topic}")
        return {
            "topic": topic,
            "knowledge": processed_knowledge,
            "teaching_materials": teaching_materials,
            "research_plan": plan
        }
    
    async def teach_me(self, topic: str, interactive: bool = True) -> None:
        """
        Start an interactive teaching session about a topic.
        
        Args:
            topic: The topic to teach
            interactive: Whether to make it interactive
        """
        self.logger.info(f"Starting teaching session for: {topic}")
        
        # Check if we have knowledge about the topic
        existing_knowledge = await self.memory.retrieve_knowledge(topic)
        
        if not existing_knowledge:
            self.logger.info(f"No existing knowledge found. Learning about {topic} first...")
            learning_result = await self.learn_topic(topic)
            knowledge = learning_result["knowledge"]
        else:
            knowledge = existing_knowledge
        
        # Start teaching session
        if interactive:
            await self.tutor.start_interactive_session(topic, knowledge)
        else:
            await self.tutor.present_material(topic, knowledge)
    
    async def ask_question(self, question: str, show_reasoning: bool = False) -> str:
        """
        Answer a specific question using available knowledge.
        
        Args:
            question: The question to answer
            show_reasoning: Whether to include reasoning process visualization
            
        Returns:
            The answer to the question, optionally with reasoning chain
        """
        self.logger.info(f"Answering question: {question}")
        
        # Use reasoning engine to understand the question
        question_analysis = await self.reasoning.analyze_question(question)
        
        # Search for relevant knowledge
        relevant_knowledge = await self.memory.search_knowledge(
            question_analysis.key_concepts
        )
        
        # Generate answer
        answer = await self.reasoning.generate_answer(
            question, relevant_knowledge, question_analysis
        )
        
        # If reasoning visualization is requested, format the response appropriately
        if show_reasoning:
            reasoning_chain = f"""
🧠 REASONING PROCESS
{"="*50}

📊 **Stage 1: Question Analysis**
Question Type: {question_analysis.question_type}
Key Concepts: {', '.join(question_analysis.key_concepts)}
Difficulty Level: {question_analysis.difficulty_level}
Required Knowledge Domains: {', '.join(question_analysis.required_knowledge_domains)}
Confidence: {question_analysis.confidence:.2f}

🔍 **Stage 2: Knowledge Search**
Searched for concepts: {', '.join(question_analysis.key_concepts)}
Found {len(relevant_knowledge.get('entries', []))} relevant knowledge entries

🧠 **Stage 3: Context Integration**
Integrating knowledge from {len(question_analysis.required_knowledge_domains)} domains
Processing {question_analysis.difficulty_level} level complexity

💡 **Stage 4: Answer Formulation**
Generating response based on available knowledge and context

✅ **Stage 5: Quality Check**
Ensuring answer relevance and accuracy

🎯 **Stage 6: Final Delivery**
Presenting comprehensive response
"""
            
            # Add reasoning chain with separator
            answer += "\n\n" + "="*50 + reasoning_chain
        
        return answer
    
    async def _create_research_plan(self, request: LearningRequest) -> ResearchPlan:
        """Create a research plan for the given learning request."""
        self.logger.info(f"Creating research plan for: {request.topic}")
        
        # Use reasoning engine to break down the topic
        subtopics = await self.reasoning.decompose_topic(request.topic)
        
        # Determine data sources
        data_sources = [
            "web_search",
            "wikipedia", 
            "educational_websites",
            "academic_papers"
        ]
        
        # Estimate time requirements
        estimated_time = len(subtopics) * 5  # 5 minutes per subtopic
        
        # Prioritize subtopics
        priority_order = await self.reasoning.prioritize_subtopics(
            subtopics, request.difficulty_level
        )
        
        return ResearchPlan(
            topic=request.topic,
            subtopics=subtopics,
            data_sources=data_sources,
            estimated_time=estimated_time,
            priority_order=priority_order
        )
    
    async def _execute_research(self, plan: ResearchPlan) -> Dict[str, Any]:
        """Execute the research plan by gathering data from various sources."""
        self.logger.info(f"Executing research plan for: {plan.topic}")
        
        research_results = {
            "web_content": [],
            "api_data": [],
            "structured_data": {}
        }
        
        # Research each subtopic
        for subtopic in plan.priority_order:
            self.logger.info(f"Researching subtopic: {subtopic}")
            
            # Web scraping
            if "web_search" in plan.data_sources:
                web_results = await self.web_scraper.search_and_scrape(
                    f"{plan.topic} {subtopic}"
                )
                research_results["web_content"].extend(web_results)
            
            # API calls
            if "wikipedia" in plan.data_sources:
                wiki_data = await self.api_client.get_wikipedia_content(subtopic)
                if wiki_data:
                    research_results["api_data"].append(wiki_data)
            
            # Allow for rate limiting
            await asyncio.sleep(1)
        
        return research_results
    
    async def _process_knowledge(self, research_results: Dict[str, Any]) -> Dict[str, Any]:
        """Process raw research results into structured knowledge."""
        self.logger.info("Processing gathered research data")
        
        # Combine all text content
        all_text = []
        for content in research_results["web_content"]:
            all_text.append(content.get("text", ""))
        
        for data in research_results["api_data"]:
            all_text.append(data.get("content", ""))
        
        # Process text
        processed_text = await self.text_processor.process_documents(all_text)
        
        # Extract key concepts and relationships
        concepts = await self.text_processor.extract_concepts(processed_text)
        relationships = await self.text_processor.extract_relationships(processed_text)
        
        # Build knowledge graph
        knowledge_graph = await self.knowledge_graph.build_graph(concepts, relationships)
        
        # Generate summary
        summary = await self.text_processor.generate_summary(processed_text)
        
        return {
            "summary": summary,
            "concepts": concepts,
            "relationships": relationships,
            "knowledge_graph": knowledge_graph,
            "source_content": processed_text
        }
    
    async def _generate_teaching_materials(
        self, 
        topic: str, 
        knowledge: Dict[str, Any], 
        difficulty: str
    ) -> Dict[str, Any]:
        """Generate teaching materials from processed knowledge."""
        self.logger.info(f"Generating teaching materials for: {topic}")
        
        # Generate curriculum
        curriculum = await self.curriculum_generator.create_curriculum(
            topic, knowledge, difficulty
        )
        
        # Generate explanations
        explanations = await self.tutor.generate_explanations(
            knowledge["concepts"], difficulty
        )
        
        # Generate examples
        examples = await self.tutor.generate_examples(
            topic, knowledge["concepts"]
        )
        
        # Generate quiz questions
        quiz_questions = await self.tutor.generate_quiz_questions(
            knowledge["concepts"], difficulty
        )
        
        return {
            "curriculum": curriculum,
            "explanations": explanations,
            "examples": examples,
            "quiz_questions": quiz_questions
        }
    
    async def get_learning_progress(self, topic: str) -> Dict[str, Any]:
        """Get learning progress for a specific topic."""
        return await self.memory.get_learning_progress(topic)
    
    async def list_learned_topics(self) -> List[str]:
        """Get a list of all topics the agent has learned about."""
        return await self.memory.list_topics()
    
    def __repr__(self) -> str:
        return f"Agent(topics_learned={len(self.memory.topics) if hasattr(self.memory, 'topics') else 0})"