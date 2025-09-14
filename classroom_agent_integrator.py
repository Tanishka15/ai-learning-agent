"""
Classroom Agent Integrator

This module integrates the GoogleClassroomAIAgent with the web application.
It provides a clean interface for the web app to use the classroom agent's features.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
import os
import re

# Import both agent types for integration
from ai_learning_agent.core.agent import Agent as CoreAgent
from ai_learning_agent.connectors.web_scraper import WebScraper
from classroom_agent import (
    GoogleClassroomAIAgent, 
    ClassroomConfig, 
    RAGKnowledgeBase,
    ClassroomGeminiProcessor
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("classroom_integrator")

class ClassroomAgentIntegrator:
    """
    Integrates the GoogleClassroomAIAgent with the web application.
    Provides methods that can be called from Flask routes.
    """
    
    def __init__(self, use_classroom_agent: bool = True):
        """
        Initialize the integrator with both agent types.
        
        Args:
            use_classroom_agent: Whether to use the classroom agent or fall back to the core agent
        """
        self.logger = logger
        self.use_classroom_agent = use_classroom_agent
        
        # Initialize the core agent (always available)
        self.core_agent = CoreAgent(config_path="config.yaml")
        
        # Initialize the classroom agent (if enabled)
        self.classroom_agent = None
        if use_classroom_agent:
            self.classroom_agent = GoogleClassroomAIAgent()
            self.classroom_agent_ready = False
        else:
            self.classroom_agent_ready = False
            
        self.logger.info(f"Classroom Agent Integrator initialized (use_classroom_agent={use_classroom_agent})")
    
    async def initialize_classroom_agent(self) -> bool:
        """
        Initialize the classroom agent asynchronously.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        if not self.use_classroom_agent or not self.classroom_agent:
            return False
            
        try:
            success = await self.classroom_agent.initialize()
            self.classroom_agent_ready = success
            return success
        except Exception as e:
            self.logger.warning(f"Google Classroom initialization failed: {e}")
            # Allow the classroom agent to work for reasoning even without full Google Classroom integration
            # The reasoning processor can work independently
            self.classroom_agent_ready = True
            self.logger.info("Classroom agent enabled for reasoning functionality (without Google Classroom)")
            return True
    
    async def ask_question(self, query: str, use_core_fallback: bool = True, use_web_search: bool = True, show_reasoning: bool = False) -> str:
        """
        Process a user question using the appropriate agent.
        Tries classroom agent first, falls back to core agent if needed.
        Can augment responses with web search results.
        
        Args:
            query: The user's question
            use_core_fallback: Whether to fall back to the core agent if classroom agent fails
            use_web_search: Whether to supplement with web search when classroom content is insufficient
            show_reasoning: Whether to include the reasoning chain visualization in the response
            
        Returns:
            The answer from the agent, potentially including reasoning chain visualization
        """
        # Try using classroom agent first
        if self.use_classroom_agent and self.classroom_agent_ready:
            try:
                # Get the answer from the classroom agent with reasoning if requested
                answer = await self.classroom_agent.ask_question(query, show_reasoning=show_reasoning)
                
                # Check if the answer indicates insufficient information
                insufficient_info_patterns = [
                    r"I couldn't find relevant information",
                    r"no relevant information",
                    r"not enough information",
                    r"don't have information",
                    r"no information available",
                    r"not found in your classroom content"
                ]
                
                needs_web_search = any(re.search(pattern, answer, re.IGNORECASE) for pattern in insufficient_info_patterns)
                
                # If the answer is insufficient and web search is enabled, augment with web search
                if needs_web_search and use_web_search:
                    self.logger.info(f"Augmenting classroom answer with web search for query: {query}")
                    web_results = await self.web_search(query)
                    
                    if web_results:
                        # Add web search results to the answer
                        web_info = "\n\n**Additional information from the web:**\n\n"
                        for i, result in enumerate(web_results[:2], 1):  # Limit to top 2 results
                            web_info += f"{i}. **{result['title']}**\n"
                            web_info += f"   {result['content'][:300]}...\n"
                            web_info += f"   Source: {result['url']}\n\n"
                            
                        # Combine classroom answer with web results
                        return answer + web_info
                
                return answer
                
            except Exception as e:
                self.logger.error(f"Error using classroom agent: {e}")
                if not use_core_fallback:
                    return f"Error processing question with classroom agent: {str(e)}"
        
        # Fall back to core agent
        if use_core_fallback:
            try:
                answer = await self.core_agent.ask_question(query)
                return answer
            except Exception as e:
                self.logger.error(f"Error using core agent: {e}")
                return f"I'm sorry, I encountered an error while processing your question: {str(e)}"
        
        return "No agent available to process your question."
    
    async def create_study_plan(
        self, 
        course_name: Optional[str] = None, 
        timeframe: str = "week",
        show_reasoning: bool = False
    ) -> Union[str, Dict]:
        """
        Create a study plan based on classroom content.
        
        Args:
            course_name: Optional specific course to create a plan for
            timeframe: The timeframe for the plan ("week", "month", or "all")
            show_reasoning: Whether to show the reasoning chain
            
        Returns:
            A formatted study plan, or an error message (or dict with reasoning if requested)
        """
        # Check if classroom agent is ready, if not, try to initialize it
        if not self.classroom_agent_ready and self.use_classroom_agent:
            self.logger.info("Classroom agent not initialized. Attempting initialization now...")
            success = await self.initialize_classroom_agent()
            if not success:
                return "Could not initialize classroom agent. Please ensure your Google Classroom is properly connected."
        
        # Double-check after potential initialization
        if not self.use_classroom_agent or not self.classroom_agent_ready:
            return "Classroom agent is not initialized. Cannot create study plan."
            
        try:
            study_plan = await self.classroom_agent.create_study_plan(course_name, timeframe, show_reasoning)
            return study_plan
        except Exception as e:
            self.logger.error(f"Error creating study plan: {e}")
            return f"❌ Could not create study plan: {str(e)}"
    
    async def get_bulletin_board_data(self) -> List[Dict]:
        """
        Get important deadlines, quizzes, and announcements for the bulletin board.
        
        Returns:
            List of bulletin board items with priority, dates, and course info
        """
        # Check if classroom agent is ready
        if not self.classroom_agent_ready and self.use_classroom_agent:
            self.logger.info("Classroom agent not initialized for bulletin board. Attempting initialization...")
            success = await self.initialize_classroom_agent()
            if not success:
                return []
        
        if not self.use_classroom_agent or not self.classroom_agent_ready:
            # Return sample data if classroom agent is not available
            return self._get_sample_bulletin_data()
            
        try:
            bulletin_items = await self.classroom_agent.get_bulletin_board_items()
            return bulletin_items
        except Exception as e:
            self.logger.error(f"Error getting bulletin board data: {e}")
            return self._get_sample_bulletin_data()
    
    def _get_sample_bulletin_data(self) -> List[Dict]:
        """Get sample bulletin board data for demo purposes."""
        from datetime import datetime, timedelta
        
        today = datetime.now()
        return [
            {
                "id": "sample_1",
                "title": "Programming Assignment Due",
                "description": "Complete the data structures assignment including linked lists and binary trees",
                "course": "CS 103",
                "date": (today + timedelta(days=2)).strftime("%Y-%m-%d"),
                "priority": "urgent",
                "type": "assignment",
                "time_until": "2 days"
            },
            {
                "id": "sample_2", 
                "title": "Midterm Exam",
                "description": "Comprehensive exam covering chapters 1-5, focus on algorithms and complexity analysis",
                "course": "CS 103",
                "date": (today + timedelta(days=7)).strftime("%Y-%m-%d"),
                "priority": "important",
                "type": "exam",
                "time_until": "1 week"
            },
            {
                "id": "sample_3",
                "title": "History Essay Submission",
                "description": "5-page essay on Renaissance art movements, MLA format required",
                "course": "HIST 201",
                "date": (today + timedelta(days=5)).strftime("%Y-%m-%d"),
                "priority": "important",
                "type": "assignment",
                "time_until": "5 days"
            },
            {
                "id": "sample_4",
                "title": "Lab Report",
                "description": "Chemistry lab analysis and conclusions from last week's experiments",
                "course": "CHEM 101",
                "date": (today + timedelta(days=10)).strftime("%Y-%m-%d"),
                "priority": "normal",
                "type": "assignment", 
                "time_until": "10 days"
            }
        ]
    
    async def search_course_content(self, query: str, course_name: Optional[str] = None) -> List[Dict]:
        """Search course content directly."""
        if not self.classroom_agent_ready:
            return []
        
        try:
            return await self.classroom_agent.search_course_content(query, course_name)
        except Exception as e:
            self.logger.error(f"Error searching course content: {e}")
            return []
    
    def list_courses(self) -> List[Dict[str, Any]]:
        """
        List the available courses from the classroom agent.
        
        Returns:
            A list of course information dictionaries, or an empty list
        """
        if not self.use_classroom_agent or not self.classroom_agent_ready:
            return []
            
        try:
            # Try to get courses from classroom API directly for better data
            from google_classroom_auth import GoogleClassroomAPI
            from google.oauth2.credentials import Credentials
            import json
            import os
            
            # Check if token file exists and use it to get direct course data
            token_path = "classroom_token.json"
            if os.path.exists(token_path):
                try:
                    with open(token_path, 'r') as token_file:
                        token_data = json.load(token_file)
                        
                    credentials = Credentials(
                        token=token_data['token'],
                        refresh_token=token_data['refresh_token'],
                        token_uri=token_data['token_uri'],
                        client_id=token_data['client_id'],
                        client_secret=token_data['client_secret'],
                        scopes=token_data['scopes']
                    )
                    
                    # Use the API directly to get more course details
                    classroom_api = GoogleClassroomAPI(credentials)
                    return classroom_api.list_courses()
                except Exception as api_error:
                    self.logger.warning(f"Couldn't get courses from API directly: {api_error}")
            
            # Fallback to the classroom agent's courses if API direct access fails
            raw_courses = self.classroom_agent.list_courses()
            courses = []
            
            for i, course in enumerate(raw_courses):
                # Remove emoji prefix if present
                course_name = course.replace("📖 ", "")
                
                courses.append({
                    "id": str(i + 1),  # Generate a simple ID
                    "name": course_name
                })
                
            return courses
        except Exception as e:
            self.logger.error(f"Error listing courses: {e}")
            return []
    
    async def search_course_content(self, query: str, course_name: Optional[str] = None) -> List[Dict]:
        """
        Search for content in the classroom knowledge base.
        
        Args:
            query: The search query
            course_name: Optional course to filter results
            
        Returns:
            A list of search results
        """
        if not self.use_classroom_agent or not self.classroom_agent_ready:
            return []
            
        try:
            results = await self.classroom_agent.search_course_content(query, course_name)
            # Format results for the web UI
            formatted_results = []
            
            for result in results:
                formatted_results.append({
                    "content": result["document"],
                    "course": result["metadata"]["course_name"],
                    "type": result["metadata"]["content_type"],
                    "relevance": round((1 - result["distance"]) * 100)  # Convert distance to relevance percentage
                })
                
            return formatted_results
        except Exception as e:
            self.logger.error(f"Error searching course content: {e}")
            return []
            
    async def web_search(self, query: str, max_results: int = 3) -> List[Dict]:
        """
        Perform a web search to augment classroom content.
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
            
        Returns:
            A list of search results from the web
        """
        try:
            # Initialize web scraper with default config
            scraper = WebScraper(self.core_agent.config)
            
            # Extract educational keywords from query
            educational_keywords = re.findall(r'\b(?:learn|study|course|concept|explain|tutorial|example|problem|solution)\b', query.lower())
            has_educational_intent = len(educational_keywords) > 0
            
            # Enhance query for educational searches
            enhanced_query = query
            if has_educational_intent:
                enhanced_query = f"{query} educational resources examples"
                
            # Execute web search
            search_results = await scraper.search(enhanced_query, max_results=max_results)
            
            # Format results for the web UI
            formatted_results = []
            for result in search_results:
                formatted_results.append({
                    "title": result.title,
                    "content": result.content[:500] + "..." if len(result.content) > 500 else result.content,
                    "url": result.url,
                    "source": "web"
                })
                
            return formatted_results
        except Exception as e:
            self.logger.error(f"Error during web search: {e}")
            return []

# Singleton instance for the web app to use
integrator = None

def get_integrator(use_classroom_agent: bool = True) -> ClassroomAgentIntegrator:
    """Get or create the integrator singleton."""
    global integrator
    if integrator is None:
        integrator = ClassroomAgentIntegrator(use_classroom_agent=use_classroom_agent)
    return integrator