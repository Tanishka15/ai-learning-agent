"""
Curriculum Generator Module

Creates structured learning paths and curricula based on topics and difficulty levels.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class LearningModule:
    """Represents a learning module in a curriculum."""
    id: str
    title: str
    description: str
    concepts: List[str]
    prerequisites: List[str]
    estimated_time_minutes: int
    difficulty_level: str
    learning_objectives: List[str]


@dataclass
class Curriculum:
    """Represents a complete curriculum for a topic."""
    topic: str
    difficulty_level: str
    total_estimated_time: int
    modules: List[LearningModule]
    learning_path: List[str]
    assessment_strategy: str


class CurriculumGenerator:
    """
    Generates structured curricula and learning paths for topics.
    
    Features:
    - Adaptive curriculum based on difficulty level
    - Prerequisite management
    - Learning objective definition
    - Time estimation
    - Assessment integration
    """
    
    def __init__(self, config):
        """Initialize the curriculum generator."""
        self.config = config
        self.logger = logging.getLogger("curriculum_generator")
        
        # Curriculum templates
        self.module_templates = {
            "introduction": {
                "title": "Introduction to {topic}",
                "description": "Overview and fundamental concepts",
                "estimated_time": 30,
                "objectives": ["Understand basic concepts", "Identify key terminology"]
            },
            "fundamentals": {
                "title": "Fundamental Principles",
                "description": "Core principles and theories",
                "estimated_time": 45,
                "objectives": ["Learn core principles", "Understand theoretical foundation"]
            },
            "applications": {
                "title": "Practical Applications",
                "description": "Real-world applications and examples",
                "estimated_time": 60,
                "objectives": ["Apply concepts to real scenarios", "Analyze practical examples"]
            },
            "advanced": {
                "title": "Advanced Topics",
                "description": "Complex concepts and cutting-edge developments",
                "estimated_time": 90,
                "objectives": ["Master advanced concepts", "Synthesize complex information"]
            }
        }
        
        self.logger.info("Curriculum generator initialized")
    
    async def create_curriculum(self, topic: str, knowledge: Dict[str, Any], difficulty: str) -> Curriculum:
        """
        Create a structured curriculum for a topic.
        
        Args:
            topic: The main topic
            knowledge: Available knowledge about the topic
            difficulty: Target difficulty level
            
        Returns:
            Generated curriculum
        """
        self.logger.info(f"Creating curriculum for {topic} at {difficulty} level")
        
        # Extract concepts from knowledge
        concepts = knowledge.get('concepts', [])
        
        # Generate learning modules
        modules = await self._generate_modules(topic, concepts, difficulty)
        
        # Create learning path
        learning_path = await self._create_learning_path(modules)
        
        # Calculate total time
        total_time = sum(module.estimated_time_minutes for module in modules)
        
        # Define assessment strategy
        assessment_strategy = await self._define_assessment_strategy(difficulty)
        
        curriculum = Curriculum(
            topic=topic,
            difficulty_level=difficulty,
            total_estimated_time=total_time,
            modules=modules,
            learning_path=learning_path,
            assessment_strategy=assessment_strategy
        )
        
        self.logger.info(f"Generated curriculum with {len(modules)} modules")
        return curriculum
    
    async def _generate_modules(self, topic: str, concepts: List[str], difficulty: str) -> List[LearningModule]:
        """Generate learning modules based on difficulty level."""
        modules = []
        
        if difficulty == "beginner":
            module_types = ["introduction", "fundamentals"]
        elif difficulty == "intermediate":
            module_types = ["introduction", "fundamentals", "applications"]
        else:  # advanced
            module_types = ["introduction", "fundamentals", "applications", "advanced"]
        
        # Distribute concepts across modules
        concepts_per_module = max(1, len(concepts) // len(module_types))
        
        for i, module_type in enumerate(module_types):
            template = self.module_templates[module_type]
            
            # Get concepts for this module
            start_idx = i * concepts_per_module
            end_idx = start_idx + concepts_per_module
            module_concepts = concepts[start_idx:end_idx]
            
            # Handle remaining concepts in the last module
            if i == len(module_types) - 1:
                module_concepts.extend(concepts[end_idx:])
            
            # Create module
            module = LearningModule(
                id=f"{topic.lower().replace(' ', '_')}_{module_type}",
                title=template["title"].format(topic=topic),
                description=template["description"],
                concepts=module_concepts,
                prerequisites=self._get_prerequisites(i, module_types),
                estimated_time_minutes=template["estimated_time"],
                difficulty_level=difficulty,
                learning_objectives=template["objectives"]
            )
            
            modules.append(module)
        
        return modules
    
    async def _create_learning_path(self, modules: List[LearningModule]) -> List[str]:
        """Create an optimal learning path through modules."""
        # Simple sequential path based on prerequisites
        path = []
        
        # Sort modules by prerequisites (modules with fewer prerequisites first)
        sorted_modules = sorted(modules, key=lambda m: len(m.prerequisites))
        
        for module in sorted_modules:
            path.append(module.id)
        
        return path
    
    async def _define_assessment_strategy(self, difficulty: str) -> str:
        """Define assessment strategy based on difficulty level."""
        strategies = {
            "beginner": "Multiple choice quizzes and basic concept identification exercises",
            "intermediate": "Short answer questions, practical applications, and case studies",
            "advanced": "Complex problem solving, critical analysis, and project-based assessments"
        }
        
        return strategies.get(difficulty, strategies["beginner"])
    
    def _get_prerequisites(self, module_index: int, module_types: List[str]) -> List[str]:
        """Get prerequisites for a module based on its position."""
        prerequisites = []
        
        # Each module depends on the previous ones
        for i in range(module_index):
            prerequisite_id = f"module_{module_types[i]}"
            prerequisites.append(prerequisite_id)
        
        return prerequisites
    
    async def adapt_curriculum(self, curriculum: Curriculum, user_progress: Dict[str, Any]) -> Curriculum:
        """
        Adapt curriculum based on user progress and performance.
        
        Args:
            curriculum: Original curriculum
            user_progress: User progress data
            
        Returns:
            Adapted curriculum
        """
        self.logger.info("Adapting curriculum based on user progress")
        
        # Simple adaptation logic
        adapted_modules = []
        
        for module in curriculum.modules:
            adapted_module = module
            
            # Adjust time estimates based on performance
            if user_progress.get('average_quiz_score', 70) < 60:
                # Increase time for struggling learners
                adapted_module.estimated_time_minutes = int(module.estimated_time_minutes * 1.3)
            elif user_progress.get('average_quiz_score', 70) > 85:
                # Decrease time for fast learners
                adapted_module.estimated_time_minutes = int(module.estimated_time_minutes * 0.8)
            
            adapted_modules.append(adapted_module)
        
        # Update total time
        curriculum.total_estimated_time = sum(m.estimated_time_minutes for m in adapted_modules)
        curriculum.modules = adapted_modules
        
        return curriculum
    
    async def generate_module_content(self, module: LearningModule, knowledge: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate detailed content for a learning module.
        
        Args:
            module: The learning module
            knowledge: Available knowledge
            
        Returns:
            Module content dictionary
        """
        self.logger.info(f"Generating content for module: {module.title}")
        
        content = {
            "module_info": {
                "title": module.title,
                "description": module.description,
                "estimated_time": module.estimated_time_minutes,
                "difficulty": module.difficulty_level
            },
            "learning_objectives": module.learning_objectives,
            "concepts": module.concepts,
            "content_sections": [],
            "activities": [],
            "assessment": {}
        }
        
        # Generate content sections for each concept
        for concept in module.concepts:
            section = {
                "concept": concept,
                "explanation": f"Detailed explanation of {concept} in the context of {module.title}",
                "examples": [f"Example demonstrating {concept}"],
                "key_points": [f"Key point about {concept}"]
            }
            content["content_sections"].append(section)
        
        # Generate activities
        activities = await self._generate_module_activities(module)
        content["activities"] = activities
        
        # Generate assessment
        assessment = await self._generate_module_assessment(module)
        content["assessment"] = assessment
        
        return content
    
    async def _generate_module_activities(self, module: LearningModule) -> List[Dict[str, Any]]:
        """Generate learning activities for a module."""
        activities = []
        
        activity_types = {
            "beginner": ["reading", "concept_identification", "simple_quiz"],
            "intermediate": ["case_study", "problem_solving", "discussion"],
            "advanced": ["research", "analysis", "synthesis"]
        }
        
        relevant_activities = activity_types.get(module.difficulty_level, activity_types["beginner"])
        
        for activity_type in relevant_activities:
            activity = {
                "type": activity_type,
                "title": f"{activity_type.replace('_', ' ').title()} Activity",
                "description": f"Engage with {module.title} through {activity_type}",
                "estimated_time": 15,
                "concepts_covered": module.concepts[:2]  # Cover first 2 concepts
            }
            activities.append(activity)
        
        return activities
    
    async def _generate_module_assessment(self, module: LearningModule) -> Dict[str, Any]:
        """Generate assessment for a module."""
        assessment_types = {
            "beginner": "multiple_choice",
            "intermediate": "short_answer",
            "advanced": "essay"
        }
        
        assessment_type = assessment_types.get(module.difficulty_level, "multiple_choice")
        
        return {
            "type": assessment_type,
            "questions_count": 5,
            "time_limit_minutes": 15,
            "passing_score": 70,
            "concepts_tested": module.concepts,
            "objectives_assessed": module.learning_objectives
        }
    
    def get_curriculum_summary(self, curriculum: Curriculum) -> str:
        """Get a human-readable summary of the curriculum."""
        summary_parts = [
            f"Curriculum: {curriculum.topic}",
            f"Difficulty Level: {curriculum.difficulty_level.title()}",
            f"Total Estimated Time: {curriculum.total_estimated_time} minutes",
            f"Number of Modules: {len(curriculum.modules)}",
            "",
            "Learning Path:"
        ]
        
        for i, module in enumerate(curriculum.modules, 1):
            summary_parts.append(f"  {i}. {module.title} ({module.estimated_time_minutes} min)")
        
        summary_parts.extend([
            "",
            f"Assessment Strategy: {curriculum.assessment_strategy}"
        ])
        
        return "\n".join(summary_parts)