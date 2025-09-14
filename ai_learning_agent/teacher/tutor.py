"""
Interactive Tutor Module

Provides personalized teaching experiences and interactive learning sessions.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import random


@dataclass
class LearningSession:
    """Represents a learning session."""
    topic: str
    difficulty_level: str
    duration_minutes: int
    completed_sections: List[str]
    quiz_scores: List[float]
    user_feedback: Dict[str, Any]


@dataclass
class Explanation:
    """Represents an explanation of a concept."""
    concept: str
    explanation: str
    examples: List[str]
    difficulty_level: str
    analogies: List[str]


class Tutor:
    """
    Intelligent tutor that provides personalized teaching experiences.
    
    Features:
    - Adaptive explanations based on difficulty level
    - Interactive Q&A sessions
    - Progress tracking
    - Personalized examples and analogies
    - Quiz generation and evaluation
    """
    
    def __init__(self, config, knowledge_graph):
        """Initialize the tutor."""
        self.config = config
        self.knowledge_graph = knowledge_graph
        self.logger = logging.getLogger("tutor")

        # Teaching configuration
        self.explanation_style = getattr(config.teaching, 'explanation_style', 'conversational')
        self.include_examples = getattr(config.teaching, 'include_examples', True)
        self.adaptive_learning = getattr(config.teaching, 'adaptive_learning', True)

        # Session state
        self.current_session = None

        self.logger.info("Tutor initialized")
    
    async def start_interactive_session(self, topic: str, knowledge: Dict[str, Any]) -> None:
        """
        Start an interactive teaching session.
        
        Args:
            topic: The topic to teach
            knowledge: Available knowledge about the topic
        """
        self.logger.info(f"Starting interactive session for: {topic}")
        
        # Initialize session
        self.current_session = LearningSession(
            topic=topic,
            difficulty_level="beginner",
            duration_minutes=0,
            completed_sections=[],
            quiz_scores=[],
            user_feedback={}
        )
        
        print(f"\n🎓 Interactive Learning Session: {topic}")
        print("=" * 60)
        
        # Present topic overview
        await self._present_overview(topic, knowledge)
        
        # Interactive learning loop
        await self._interactive_learning_loop(topic, knowledge)
        
        # Session summary
        await self._present_session_summary()
    
    async def present_material(self, topic: str, knowledge: Dict[str, Any]) -> None:
        """
        Present material in a non-interactive format.
        
        Args:
            topic: The topic to present
            knowledge: Available knowledge about the topic
        """
        self.logger.info(f"Presenting material for: {topic}")
        
        print(f"\n📚 Learning Material: {topic}")
        print("=" * 60)
        
        # Present overview
        await self._present_overview(topic, knowledge)
        
        # Present detailed explanations
        concepts = knowledge.get('concepts', [])
        for concept in concepts[:5]:  # Limit to top 5 concepts
            explanation = await self.generate_explanations([concept], "beginner")
            if explanation:
                print(f"\n🔍 **{concept.title()}**")
                print(explanation[concept])
                
                if self.include_examples:
                    examples = await self.generate_examples(topic, [concept])
                    if examples:
                        print(f"\n💡 Example: {examples[0]}")
        
        print("\n" + "=" * 60)
        print("📝 End of material presentation")
    
    async def generate_explanations(self, concepts: List[str], difficulty: str) -> Dict[str, str]:
        """
        Generate explanations for concepts based on difficulty level.
        
        Args:
            concepts: List of concepts to explain
            difficulty: Target difficulty level
            
        Returns:
            Dictionary mapping concepts to explanations
        """
        self.logger.info(f"Generating explanations for {len(concepts)} concepts at {difficulty} level")
        
        explanations = {}
        
        for concept in concepts:
            explanation = await self._generate_concept_explanation(concept, difficulty)
            explanations[concept] = explanation
        
        return explanations
    
    async def generate_examples(self, topic: str, concepts: List[str]) -> List[str]:
        """
        Generate examples for given concepts.
        
        Args:
            topic: Main topic context
            concepts: List of concepts
            
        Returns:
            List of examples
        """
        self.logger.info(f"Generating examples for concepts in {topic}")
        
        examples = []
        
        for concept in concepts[:3]:  # Limit to first 3 concepts
            example = await self._generate_concept_example(topic, concept)
            if example:
                examples.append(example)
        
        return examples
    
    async def generate_quiz_questions(self, concepts: List[str], difficulty: str) -> List[Dict[str, Any]]:
        """
        Generate quiz questions for concepts.
        
        Args:
            concepts: List of concepts
            difficulty: Target difficulty level
            
        Returns:
            List of quiz questions
        """
        self.logger.info(f"Generating quiz questions for {len(concepts)} concepts")
        
        questions = []
        question_count = self.config.teaching.get('quiz_questions_per_topic', 5)
        
        for i, concept in enumerate(concepts[:question_count]):
            question = await self._generate_quiz_question(concept, difficulty)
            if question:
                questions.append(question)
        
        return questions
    
    async def _present_overview(self, topic: str, knowledge: Dict[str, Any]) -> None:
        """Present an overview of the topic."""
        print(f"\n📖 **Overview of {topic}**")
        
        # Present summary
        summary = knowledge.get('summary', '')
        if summary:
            print(f"\n{summary}")
        
        # Present key concepts
        concepts = knowledge.get('concepts', [])
        if concepts:
            print(f"\n🧠 **Key Concepts:**")
            for i, concept in enumerate(concepts[:5], 1):
                print(f"  {i}. {concept.title()}")
        
        print("\n" + "-" * 40)
    
    async def _interactive_learning_loop(self, topic: str, knowledge: Dict[str, Any]) -> None:
        """Main interactive learning loop."""
        concepts = knowledge.get('concepts', [])
        
        while True:
            print(f"\n🎯 **What would you like to do?**")
            print("1. Learn about a specific concept")
            print("2. See examples")
            print("3. Take a quiz")
            print("4. Ask a question")
            print("5. Get summary")
            print("6. Finish session")
            
            try:
                choice = input("\nEnter your choice (1-6): ").strip()
                
                if choice == "1":
                    await self._teach_specific_concept(concepts)
                elif choice == "2":
                    await self._show_examples(topic, concepts)
                elif choice == "3":
                    await self._conduct_quiz(concepts)
                elif choice == "4":
                    await self._handle_user_question()
                elif choice == "5":
                    await self._show_summary(knowledge)
                elif choice == "6":
                    print("📚 Great job learning! Session ending.")
                    break
                else:
                    print("❌ Invalid choice. Please try again.")
                    
            except KeyboardInterrupt:
                print("\n📚 Session interrupted. Goodbye!")
                break
            except Exception as e:
                self.logger.error(f"Error in learning loop: {e}")
                print(f"❌ An error occurred: {e}")
    
    async def _teach_specific_concept(self, concepts: List[str]) -> None:
        """Teach about a specific concept."""
        if not concepts:
            print("❌ No concepts available to teach.")
            return
        
        print(f"\n🧠 **Available Concepts:**")
        for i, concept in enumerate(concepts[:10], 1):
            print(f"  {i}. {concept.title()}")
        
        try:
            choice = input(f"\nChoose a concept (1-{min(10, len(concepts))}): ").strip()
            concept_index = int(choice) - 1
            
            if 0 <= concept_index < len(concepts):
                concept = concepts[concept_index]
                
                # Determine difficulty
                difficulty = await self._ask_difficulty_preference()
                
                # Generate and present explanation
                explanation = await self._generate_concept_explanation(concept, difficulty)
                print(f"\n🔍 **{concept.title()}**")
                print(explanation)
                
                # Add to completed sections
                if self.current_session:
                    self.current_session.completed_sections.append(concept)
                
            else:
                print("❌ Invalid concept choice.")
                
        except ValueError:
            print("❌ Please enter a valid number.")
        except Exception as e:
            self.logger.error(f"Error teaching concept: {e}")
            print("❌ Error teaching concept.")
    
    async def _show_examples(self, topic: str, concepts: List[str]) -> None:
        """Show examples for concepts."""
        examples = await self.generate_examples(topic, concepts[:3])
        
        if examples:
            print(f"\n💡 **Examples for {topic}:**")
            for i, example in enumerate(examples, 1):
                print(f"\n{i}. {example}")
        else:
            print("❌ No examples available.")
    
    async def _conduct_quiz(self, concepts: List[str]) -> None:
        """Conduct a quiz session."""
        if not concepts:
            print("❌ No concepts available for quiz.")
            return
        
        print(f"\n📝 **Quiz Time!**")
        
        difficulty = await self._ask_difficulty_preference()
        questions = await self.generate_quiz_questions(concepts[:3], difficulty)
        
        if not questions:
            print("❌ No quiz questions available.")
            return
        
        score = 0
        total_questions = len(questions)
        
        for i, question in enumerate(questions, 1):
            print(f"\nQuestion {i}/{total_questions}:")
            print(question['question'])
            
            if question['type'] == 'multiple_choice':
                for j, option in enumerate(question['options'], 1):
                    print(f"  {j}. {option}")
                
                try:
                    answer = input("\nYour answer (enter number): ").strip()
                    answer_index = int(answer) - 1
                    
                    if 0 <= answer_index < len(question['options']):
                        if answer_index == question['correct_answer']:
                            print("✅ Correct!")
                            score += 1
                        else:
                            correct_option = question['options'][question['correct_answer']]
                            print(f"❌ Incorrect. The correct answer is: {correct_option}")
                    else:
                        print("❌ Invalid answer choice.")
                        
                except ValueError:
                    print("❌ Please enter a valid number.")
            
            else:  # Open-ended question
                user_answer = input("\nYour answer: ").strip()
                print("✅ Thank you for your answer!")
                score += 0.5  # Give partial credit for attempt
        
        # Present results
        percentage = (score / total_questions) * 100
        print(f"\n🎯 **Quiz Results:**")
        print(f"Score: {score}/{total_questions} ({percentage:.1f}%)")
        
        if percentage >= 80:
            print("🎉 Excellent work!")
        elif percentage >= 60:
            print("👍 Good job!")
        else:
            print("📚 Keep studying - you'll get there!")
        
        # Record score
        if self.current_session:
            self.current_session.quiz_scores.append(percentage)
    
    async def _handle_user_question(self) -> None:
        """Handle a user question."""
        question = input("\n❓ What's your question? ").strip()
        
        if question:
            print(f"\n🤔 You asked: {question}")
            
            # Simple response generation
            response = await self._generate_question_response(question)
            print(f"\n💭 {response}")
        else:
            print("❌ No question entered.")
    
    async def _show_summary(self, knowledge: Dict[str, Any]) -> None:
        """Show a summary of the topic."""
        print(f"\n📋 **Topic Summary:**")
        
        summary = knowledge.get('summary', 'No summary available.')
        print(f"\n{summary}")
        
        if self.current_session and self.current_session.completed_sections:
            print(f"\n✅ **Concepts you've learned:**")
            for concept in self.current_session.completed_sections:
                print(f"  • {concept.title()}")
    
    async def _present_session_summary(self) -> None:
        """Present a summary of the learning session."""
        if not self.current_session:
            return
        
        print(f"\n📊 **Session Summary for {self.current_session.topic}**")
        print("=" * 60)
        
        print(f"📚 Concepts learned: {len(self.current_session.completed_sections)}")
        
        if self.current_session.completed_sections:
            for concept in self.current_session.completed_sections:
                print(f"  ✅ {concept.title()}")
        
        if self.current_session.quiz_scores:
            avg_score = sum(self.current_session.quiz_scores) / len(self.current_session.quiz_scores)
            print(f"🎯 Average quiz score: {avg_score:.1f}%")
        
        print("\n🎓 Great job learning today!")
    
    async def _ask_difficulty_preference(self) -> str:
        """Ask user for difficulty preference."""
        while True:
            print("\n📊 Choose difficulty level:")
            print("1. Beginner")
            print("2. Intermediate") 
            print("3. Advanced")
            
            choice = input("Enter choice (1-3): ").strip()
            
            if choice == "1":
                return "beginner"
            elif choice == "2":
                return "intermediate"
            elif choice == "3":
                return "advanced"
            else:
                print("❌ Invalid choice. Please try again.")
    
    async def _generate_concept_explanation(self, concept: str, difficulty: str) -> str:
        """Generate an explanation for a concept."""
        # This is a simplified explanation generator
        # In a full system, you'd use more sophisticated NLP
        
        explanations = {
            "beginner": f"{concept.title()} is a fundamental concept that refers to the basic principles and ideas related to {concept}. It's important to understand because it forms the foundation for more advanced topics.",
            
            "intermediate": f"{concept.title()} involves more complex interactions and relationships. It builds upon basic principles and introduces additional factors that influence how {concept} works in practice.",
            
            "advanced": f"{concept.title()} encompasses sophisticated mechanisms and theoretical frameworks. It requires understanding of underlying mathematical or scientific principles and their applications in real-world scenarios."
        }
        
        return explanations.get(difficulty, explanations["beginner"])
    
    async def _generate_concept_example(self, topic: str, concept: str) -> str:
        """Generate an example for a concept."""
        # Simple example generation
        examples = [
            f"For example, when studying {topic}, {concept} can be seen in everyday situations like...",
            f"A practical example of {concept} in {topic} would be...",
            f"To illustrate {concept}, consider how it applies to {topic}..."
        ]
        
        return random.choice(examples)
    
    async def _generate_quiz_question(self, concept: str, difficulty: str) -> Dict[str, Any]:
        """Generate a quiz question for a concept."""
        # Simple quiz question generation
        question_templates = {
            "beginner": f"What is the main purpose of {concept}?",
            "intermediate": f"How does {concept} relate to other concepts in this topic?",
            "advanced": f"What are the theoretical implications of {concept}?"
        }
        
        question = question_templates.get(difficulty, question_templates["beginner"])
        
        # Generate multiple choice options
        options = [
            f"It is primarily used for basic functions",
            f"It serves as a connecting element",
            f"It provides advanced capabilities",
            f"It has no specific purpose"
        ]
        
        return {
            "question": question,
            "type": "multiple_choice",
            "options": options,
            "correct_answer": 0,  # First option is correct for this simple example
            "concept": concept,
            "difficulty": difficulty
        }
    
    async def _generate_question_response(self, question: str) -> str:
        """Generate a response to a user question."""
        # Simple response generation
        responses = [
            "That's a great question! Let me think about it...",
            "Interesting question! Here's what I understand...",
            "Good question! Based on what we've learned...",
            "Excellent inquiry! From my knowledge..."
        ]
        
        intro = random.choice(responses)
        
        # Simple keyword-based response
        if any(word in question.lower() for word in ['what', 'define', 'meaning']):
            return f"{intro} This seems to be asking for a definition or explanation of a concept."
        elif any(word in question.lower() for word in ['how', 'process', 'work']):
            return f"{intro} This appears to be asking about how something works or a process."
        elif any(word in question.lower() for word in ['why', 'reason', 'because']):
            return f"{intro} This is asking for reasoning or explanation of causes."
        else:
            return f"{intro} This is an interesting question that requires careful consideration."