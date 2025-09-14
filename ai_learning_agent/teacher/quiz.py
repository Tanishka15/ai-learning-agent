"""
Quiz Generation Module

Provides intelligent quiz generation capabilities for testing knowledge
and reinforcing learning through interactive assessments.
"""

import logging
import random
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class QuestionType(Enum):
    """Types of quiz questions."""
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    FILL_IN_BLANK = "fill_in_blank"
    MATCHING = "matching"


class DifficultyLevel(Enum):
    """Question difficulty levels."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


@dataclass
class QuizQuestion:
    """Represents a single quiz question."""
    id: str
    question_type: QuestionType
    difficulty: DifficultyLevel
    question_text: str
    correct_answer: str
    options: List[str]  # For multiple choice
    explanation: str
    topic: str
    concepts: List[str]
    points: int = 1


@dataclass
class QuizResult:
    """Results from a completed quiz."""
    total_questions: int
    correct_answers: int
    score_percentage: float
    time_taken_seconds: int
    questions_results: List[Dict[str, Any]]
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]


class QuizGenerator:
    """
    Intelligent quiz generator that creates assessments based on learned content.
    
    Features:
    - Multiple question types
    - Adaptive difficulty
    - Concept-based question generation
    - Performance analysis
    - Learning recommendations
    """
    
    def __init__(self, config):
        """Initialize the quiz generator."""
        self.config = config
        self.logger = logging.getLogger("quiz_generator")
        
        # Configuration
        self.default_questions_per_topic = config.teaching.quiz_questions_per_topic
        
        # Question templates for different types
        self.question_templates = self._initialize_question_templates()
        
        self.logger.info("Quiz generator initialized")
    
    async def generate_quiz(
        self, 
        topic: str, 
        concepts: List[str], 
        difficulty: str = "beginner",
        num_questions: int = None,
        question_types: List[QuestionType] = None
    ) -> List[QuizQuestion]:
        """
        Generate a quiz for a given topic and concepts.
        
        Args:
            topic: The main topic
            concepts: List of concepts to test
            difficulty: Target difficulty level
            num_questions: Number of questions to generate
            question_types: Types of questions to include
            
        Returns:
            List of quiz questions
        """
        self.logger.info(f"Generating quiz for topic: {topic}")
        
        num_questions = num_questions or self.default_questions_per_topic
        question_types = question_types or [
            QuestionType.MULTIPLE_CHOICE,
            QuestionType.TRUE_FALSE,
            QuestionType.SHORT_ANSWER
        ]
        
        questions = []
        difficulty_enum = DifficultyLevel(difficulty)
        
        # Generate questions for each concept
        concepts_to_use = concepts[:num_questions] if len(concepts) >= num_questions else concepts
        
        for i, concept in enumerate(concepts_to_use):
            # Vary question types
            question_type = question_types[i % len(question_types)]
            
            # Generate question based on type
            question = await self._generate_question_for_concept(
                concept, topic, question_type, difficulty_enum, i + 1
            )
            
            if question:
                questions.append(question)
        
        # Fill remaining questions if needed
        while len(questions) < num_questions and concepts:
            concept = random.choice(concepts)
            question_type = random.choice(question_types)
            
            question = await self._generate_question_for_concept(
                concept, topic, question_type, difficulty_enum, len(questions) + 1
            )
            
            if question:
                questions.append(question)
        
        self.logger.info(f"Generated {len(questions)} quiz questions")
        return questions
    
    async def conduct_interactive_quiz(self, questions: List[QuizQuestion]) -> QuizResult:
        """
        Conduct an interactive quiz session.
        
        Args:
            questions: List of quiz questions
            
        Returns:
            Quiz results
        """
        self.logger.info("Starting interactive quiz session")
        
        import time
        start_time = time.time()
        
        correct_answers = 0
        question_results = []
        
        print(f"\n🎯 Quiz Time! {len(questions)} questions waiting for you.")
        print("=" * 50)
        
        for i, question in enumerate(questions, 1):
            print(f"\nQuestion {i}/{len(questions)}")
            print(f"Topic: {question.topic} | Difficulty: {question.difficulty.value}")
            print("-" * 30)
            
            # Display question based on type
            user_answer = await self._display_and_get_answer(question)
            
            # Check answer
            is_correct = self._check_answer(question, user_answer)
            
            if is_correct:
                correct_answers += 1
                print("✅ Correct!")
            else:
                print(f"❌ Incorrect. The correct answer is: {question.correct_answer}")
            
            print(f"💡 Explanation: {question.explanation}")
            
            # Store result
            question_results.append({
                'question_id': question.id,
                'question': question.question_text,
                'user_answer': user_answer,
                'correct_answer': question.correct_answer,
                'is_correct': is_correct,
                'concept': question.concepts[0] if question.concepts else question.topic
            })
            
            # Brief pause between questions
            if i < len(questions):
                input("\nPress Enter to continue...")
        
        end_time = time.time()
        time_taken = int(end_time - start_time)
        
        # Calculate results
        score_percentage = (correct_answers / len(questions)) * 100
        
        # Analyze performance
        strengths, weaknesses = self._analyze_performance(question_results)
        recommendations = self._generate_recommendations(score_percentage, weaknesses)
        
        result = QuizResult(
            total_questions=len(questions),
            correct_answers=correct_answers,
            score_percentage=score_percentage,
            time_taken_seconds=time_taken,
            questions_results=question_results,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations
        )
        
        # Display results
        self._display_quiz_results(result)
        
        return result
    
    async def _generate_question_for_concept(
        self, 
        concept: str, 
        topic: str, 
        question_type: QuestionType, 
        difficulty: DifficultyLevel,
        question_id: int
    ) -> Optional[QuizQuestion]:
        """Generate a specific question for a concept."""
        
        if question_type == QuestionType.MULTIPLE_CHOICE:
            return self._generate_multiple_choice(concept, topic, difficulty, question_id)
        
        elif question_type == QuestionType.TRUE_FALSE:
            return self._generate_true_false(concept, topic, difficulty, question_id)
        
        elif question_type == QuestionType.SHORT_ANSWER:
            return self._generate_short_answer(concept, topic, difficulty, question_id)
        
        elif question_type == QuestionType.FILL_IN_BLANK:
            return self._generate_fill_in_blank(concept, topic, difficulty, question_id)
        
        return None
    
    def _generate_multiple_choice(
        self, 
        concept: str, 
        topic: str, 
        difficulty: DifficultyLevel, 
        question_id: int
    ) -> QuizQuestion:
        """Generate a multiple choice question."""
        
        templates = self.question_templates["multiple_choice"][difficulty.value]
        template = random.choice(templates)
        
        question_text = template["question"].format(concept=concept, topic=topic)
        
        # Generate plausible wrong answers
        options = [template["correct_answer"].format(concept=concept, topic=topic)]
        
        for wrong_template in template["wrong_answers"]:
            options.append(wrong_template.format(concept=concept, topic=topic))
        
        # Shuffle options
        correct_answer = options[0]
        random.shuffle(options)
        
        # Label options A, B, C, D
        labeled_options = []
        for i, option in enumerate(options):
            label = chr(65 + i)  # A, B, C, D
            labeled_options.append(f"{label}. {option}")
            if option == correct_answer:
                correct_answer = label
        
        return QuizQuestion(
            id=f"mc_{question_id}",
            question_type=QuestionType.MULTIPLE_CHOICE,
            difficulty=difficulty,
            question_text=question_text + "\n" + "\n".join(labeled_options),
            correct_answer=correct_answer,
            options=labeled_options,
            explanation=template["explanation"].format(concept=concept, topic=topic),
            topic=topic,
            concepts=[concept]
        )
    
    def _generate_true_false(
        self, 
        concept: str, 
        topic: str, 
        difficulty: DifficultyLevel, 
        question_id: int
    ) -> QuizQuestion:
        """Generate a true/false question."""
        
        templates = self.question_templates["true_false"][difficulty.value]
        template = random.choice(templates)
        
        # Randomly choose true or false statement
        is_true_statement = random.choice([True, False])
        
        if is_true_statement:
            question_text = template["true_statement"].format(concept=concept, topic=topic)
            correct_answer = "True"
            explanation = template["true_explanation"].format(concept=concept, topic=topic)
        else:
            question_text = template["false_statement"].format(concept=concept, topic=topic)
            correct_answer = "False"
            explanation = template["false_explanation"].format(concept=concept, topic=topic)
        
        return QuizQuestion(
            id=f"tf_{question_id}",
            question_type=QuestionType.TRUE_FALSE,
            difficulty=difficulty,
            question_text=question_text + "\n(True/False)",
            correct_answer=correct_answer,
            options=["True", "False"],
            explanation=explanation,
            topic=topic,
            concepts=[concept]
        )
    
    def _generate_short_answer(
        self, 
        concept: str, 
        topic: str, 
        difficulty: DifficultyLevel, 
        question_id: int
    ) -> QuizQuestion:
        """Generate a short answer question."""
        
        templates = self.question_templates["short_answer"][difficulty.value]
        template = random.choice(templates)
        
        question_text = template["question"].format(concept=concept, topic=topic)
        correct_answer = template["answer"].format(concept=concept, topic=topic)
        explanation = template["explanation"].format(concept=concept, topic=topic)
        
        return QuizQuestion(
            id=f"sa_{question_id}",
            question_type=QuestionType.SHORT_ANSWER,
            difficulty=difficulty,
            question_text=question_text,
            correct_answer=correct_answer,
            options=[],
            explanation=explanation,
            topic=topic,
            concepts=[concept]
        )
    
    def _generate_fill_in_blank(
        self, 
        concept: str, 
        topic: str, 
        difficulty: DifficultyLevel, 
        question_id: int
    ) -> QuizQuestion:
        """Generate a fill-in-the-blank question."""
        
        templates = self.question_templates["fill_blank"][difficulty.value]
        template = random.choice(templates)
        
        question_text = template["question"].format(concept=concept, topic=topic)
        correct_answer = template["answer"].format(concept=concept, topic=topic)
        explanation = template["explanation"].format(concept=concept, topic=topic)
        
        return QuizQuestion(
            id=f"fb_{question_id}",
            question_type=QuestionType.FILL_IN_BLANK,
            difficulty=difficulty,
            question_text=question_text,
            correct_answer=correct_answer,
            options=[],
            explanation=explanation,
            topic=topic,
            concepts=[concept]
        )
    
    async def _display_and_get_answer(self, question: QuizQuestion) -> str:
        """Display question and get user answer."""
        
        print(f"\n{question.question_text}")
        
        if question.question_type == QuestionType.MULTIPLE_CHOICE:
            while True:
                answer = input("\nYour answer (A/B/C/D): ").strip().upper()
                if answer in ['A', 'B', 'C', 'D']:
                    return answer
                print("Please enter A, B, C, or D")
        
        elif question.question_type == QuestionType.TRUE_FALSE:
            while True:
                answer = input("\nYour answer (True/False): ").strip().lower()
                if answer in ['true', 't', 'false', 'f']:
                    return "True" if answer in ['true', 't'] else "False"
                print("Please enter True or False")
        
        else:  # Short answer or fill in blank
            return input("\nYour answer: ").strip()
    
    def _check_answer(self, question: QuizQuestion, user_answer: str) -> bool:
        """Check if the user's answer is correct."""
        
        if question.question_type in [QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE]:
            return user_answer.upper() == question.correct_answer.upper()
        
        else:  # Short answer or fill in blank
            # Simple string matching (could be enhanced with fuzzy matching)
            user_lower = user_answer.lower().strip()
            correct_lower = question.correct_answer.lower().strip()
            
            # Check exact match or if user answer is contained in correct answer
            return user_lower == correct_lower or user_lower in correct_lower
    
    def _analyze_performance(self, question_results: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
        """Analyze quiz performance to identify strengths and weaknesses."""
        
        concept_performance = {}
        
        for result in question_results:
            concept = result['concept']
            is_correct = result['is_correct']
            
            if concept not in concept_performance:
                concept_performance[concept] = {'correct': 0, 'total': 0}
            
            concept_performance[concept]['total'] += 1
            if is_correct:
                concept_performance[concept]['correct'] += 1
        
        strengths = []
        weaknesses = []
        
        for concept, performance in concept_performance.items():
            percentage = (performance['correct'] / performance['total']) * 100
            
            if percentage >= 80:
                strengths.append(concept)
            elif percentage < 60:
                weaknesses.append(concept)
        
        return strengths, weaknesses
    
    def _generate_recommendations(self, score_percentage: float, weaknesses: List[str]) -> List[str]:
        """Generate learning recommendations based on performance."""
        
        recommendations = []
        
        if score_percentage >= 90:
            recommendations.append("Excellent work! You've mastered this topic.")
            recommendations.append("Consider exploring advanced topics or related subjects.")
        
        elif score_percentage >= 70:
            recommendations.append("Good job! You have a solid understanding.")
            if weaknesses:
                recommendations.append(f"Focus on improving: {', '.join(weaknesses)}")
        
        elif score_percentage >= 50:
            recommendations.append("You're making progress, but more study is needed.")
            recommendations.append("Review the material and try the quiz again.")
            if weaknesses:
                recommendations.append(f"Pay special attention to: {', '.join(weaknesses)}")
        
        else:
            recommendations.append("Consider reviewing the fundamental concepts.")
            recommendations.append("Take time to understand the basics before proceeding.")
            recommendations.append("Don't worry - learning takes time and practice!")
        
        return recommendations
    
    def _display_quiz_results(self, result: QuizResult):
        """Display comprehensive quiz results."""
        
        print("\n" + "=" * 50)
        print("🎯 QUIZ RESULTS")
        print("=" * 50)
        
        print(f"📊 Score: {result.correct_answers}/{result.total_questions} ({result.score_percentage:.1f}%)")
        print(f"⏱️  Time taken: {result.time_taken_seconds // 60}m {result.time_taken_seconds % 60}s")
        
        # Performance indicator
        if result.score_percentage >= 90:
            print("🌟 Outstanding performance!")
        elif result.score_percentage >= 80:
            print("🎉 Great job!")
        elif result.score_percentage >= 70:
            print("👍 Good work!")
        elif result.score_percentage >= 60:
            print("📈 Keep improving!")
        else:
            print("📚 More study needed!")
        
        # Strengths
        if result.strengths:
            print(f"\n💪 Strengths: {', '.join(result.strengths)}")
        
        # Weaknesses
        if result.weaknesses:
            print(f"\n🎯 Areas to improve: {', '.join(result.weaknesses)}")
        
        # Recommendations
        if result.recommendations:
            print("\n💡 Recommendations:")
            for rec in result.recommendations:
                print(f"   • {rec}")
        
        print("=" * 50)
    
    def _initialize_question_templates(self) -> Dict[str, Any]:
        """Initialize question templates for different types and difficulties."""
        
        return {
            "multiple_choice": {
                "beginner": [
                    {
                        "question": "What is {concept}?",
                        "correct_answer": "A fundamental concept in {topic}",
                        "wrong_answers": [
                            "An advanced technique in {topic}",
                            "A type of software tool",
                            "A mathematical formula"
                        ],
                        "explanation": "{concept} is an important concept in {topic} that forms the foundation for understanding more advanced topics."
                    }
                ],
                "intermediate": [
                    {
                        "question": "How does {concept} relate to other concepts in {topic}?",
                        "correct_answer": "It serves as a building block for more complex ideas",
                        "wrong_answers": [
                            "It is completely independent of other concepts",
                            "It only applies to theoretical scenarios",
                            "It is rarely used in practical applications"
                        ],
                        "explanation": "{concept} is interconnected with other concepts in {topic} and understanding these relationships is key to mastery."
                    }
                ],
                "advanced": [
                    {
                        "question": "What are the implications of {concept} in advanced {topic} applications?",
                        "correct_answer": "It enables sophisticated problem-solving approaches",
                        "wrong_answers": [
                            "It has no practical applications",
                            "It only works in simple scenarios",
                            "It is being replaced by newer methods"
                        ],
                        "explanation": "{concept} plays a crucial role in advanced {topic} applications and enables sophisticated approaches to complex problems."
                    }
                ]
            },
            "true_false": {
                "beginner": [
                    {
                        "true_statement": "{concept} is an important part of {topic}",
                        "false_statement": "{concept} is not related to {topic}",
                        "true_explanation": "Correct! {concept} is indeed a fundamental part of {topic}.",
                        "false_explanation": "Incorrect. {concept} is actually closely related to {topic}."
                    }
                ],
                "intermediate": [
                    {
                        "true_statement": "{concept} can be applied in multiple ways within {topic}",
                        "false_statement": "{concept} has only one specific use in {topic}",
                        "true_explanation": "Correct! {concept} is versatile and can be applied in various ways.",
                        "false_explanation": "Incorrect. {concept} actually has multiple applications in {topic}."
                    }
                ],
                "advanced": [
                    {
                        "true_statement": "Advanced understanding of {concept} requires knowledge of its theoretical foundations",
                        "false_statement": "{concept} can be fully understood without any theoretical background",
                        "true_explanation": "Correct! Deep understanding of {concept} requires solid theoretical knowledge.",
                        "false_explanation": "Incorrect. {concept} requires theoretical understanding for advanced applications."
                    }
                ]
            },
            "short_answer": {
                "beginner": [
                    {
                        "question": "Define {concept} in the context of {topic}.",
                        "answer": "{concept}",
                        "explanation": "A good definition should capture the essential meaning of {concept} within {topic}."
                    }
                ],
                "intermediate": [
                    {
                        "question": "Explain how {concept} is used in {topic}.",
                        "answer": "practical application of {concept}",
                        "explanation": "The answer should demonstrate understanding of how {concept} is practically applied in {topic}."
                    }
                ],
                "advanced": [
                    {
                        "question": "Analyze the role of {concept} in advanced {topic} theory.",
                        "answer": "theoretical foundation",
                        "explanation": "An advanced answer should show deep understanding of {concept}'s theoretical significance."
                    }
                ]
            },
            "fill_blank": {
                "beginner": [
                    {
                        "question": "In {topic}, _____ is a fundamental concept that helps us understand the subject.",
                        "answer": "{concept}",
                        "explanation": "{concept} is indeed a fundamental concept in {topic}."
                    }
                ],
                "intermediate": [
                    {
                        "question": "The concept of _____ is essential for understanding how {topic} works in practice.",
                        "answer": "{concept}",
                        "explanation": "{concept} is crucial for practical understanding of {topic}."
                    }
                ],
                "advanced": [
                    {
                        "question": "Advanced practitioners of {topic} must master _____ to solve complex problems.",
                        "answer": "{concept}",
                        "explanation": "{concept} is essential for advanced problem-solving in {topic}."
                    }
                ]
            }
        }