"""
Classroom Gemini Processor with Enhanced Reasoning Chain

This extended version of ClassroomGeminiProcessor includes transparent reasoning chain
that shows users the step-by-step process used to formulate answers. It also supports
exporting reasoning chains to various formats and caching to improve performance.
"""

import os
import json
import logging
import asyncio
import time
import tempfile
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Union
try:
    import google.generativeai as genai
except ImportError:
    # Handle the import error gracefully for systems without google.generativeai
    genai = None

# Import the reasoning chain utilities
from ai_learning_agent.utils.reasoning_chain import (
    ReasoningChainManager, 
    ReasoningChainVisualizer,
    ReasoningStepType,
    reasoning_step
)

class ClassroomGeminiReasoningProcessor:
    """Gemini processor for classroom-specific queries with transparent reasoning."""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger("classroom_gemini")
        
        # Initialize reasoning chain manager
        self.reasoning_manager = ReasoningChainManager(max_chains=50)
        self.visualizer = ReasoningChainVisualizer()
        
        # Initialize Gemini if available
        if genai:
            try:
                genai.configure(api_key=config.gemini_api_key)
                self.model = genai.GenerativeModel(config.gemini_model)
                self.genai_available = True
            except Exception as e:
                self.logger.error(f"Error initializing Gemini: {e}")
                self.genai_available = False
        else:
            self.logger.warning("google.generativeai package not available")
            self.genai_available = False
    
    @reasoning_step(ReasoningStepType.QUERY_ANALYSIS, "Analyzing query: {query}")
    async def analyze_query(self, query: str, available_courses: List[str], chain_id: str = None) -> Dict:
        """Analyze user query to understand intent and identify relevant course."""
        courses_list = ", ".join(available_courses)
        
        # Simplified query analysis that focuses on getting valid JSON
        prompt = f"""Respond with valid JSON only. Analyze this query: "{query}"

Available courses: {courses_list}

Return JSON:
{{"target_course": null, "query_type": "general_question", "intent": "understand", "key_topics": ["general"], "urgency": "medium", "refined_query": "{query}"}}

Adjust the values based on the query content. Return only JSON, no other text."""
        
        try:
            response = self.model.generate_content(prompt)
            if not response or not hasattr(response, 'text') or not response.text or not response.text.strip():
                raise ValueError("Empty response from Gemini API")
            
            response_text = response.text.strip()
            if not response_text:
                raise ValueError("Empty response text from Gemini API")
            
            # Handle markdown code blocks that Gemini sometimes adds
            if response_text.startswith('```json'):
                # Extract JSON from markdown code block
                response_text = response_text[7:]  # Remove ```json
                if response_text.endswith('```'):
                    response_text = response_text[:-3]  # Remove ```
                response_text = response_text.strip()
            elif response_text.startswith('```'):
                # Generic code block
                lines = response_text.split('\n')
                if len(lines) > 2:
                    response_text = '\n'.join(lines[1:-1])  # Remove first and last line
                response_text = response_text.strip()
                
            analysis = json.loads(response_text)
            return analysis
        except Exception as e:
            self.logger.warning(f"Query analysis failed: {e}")
            
            # Enhanced fallback for quota errors or empty responses - analyze query using keywords
            query_lower = query.lower()
            
            # Determine query type based on keywords
            if any(word in query_lower for word in ['deadline', 'due', 'urgent', 'prioritize']):
                query_type = "deadline"
                urgency = "high"
            elif any(word in query_lower for word in ['study plan', 'plan', 'schedule', 'organize']):
                query_type = "material"
                urgency = "medium"
            elif any(word in query_lower for word in ['assignment', 'homework', 'submit']):
                query_type = "assignment"
                urgency = "medium"
            elif any(word in query_lower for word in ['announcement', 'notice', 'update']):
                query_type = "announcement"
                urgency = "medium"
            else:
                query_type = "general_question"
                urgency = "medium"
            
            # Try to match course names
            target_course = None
            for course in available_courses:
                if course.lower() in query_lower:
                    target_course = course
                    break
            
            return {
                "target_course": target_course,
                "query_type": query_type,
                "intent": "understand",
                "key_topics": query.split()[:3],  # First 3 words as key topics
                "urgency": urgency,
                "refined_query": query
            }
    
    @reasoning_step(ReasoningStepType.KNOWLEDGE_SEARCH, "Searching knowledge base for relevant content")
    async def search_knowledge_base(self, query: str, knowledge_base, target_course: str = None, chain_id: str = None):
        """Search knowledge base for relevant classroom content."""
        results = await knowledge_base.search(
            query, 
            course_filter=target_course
        )
        
        return {
            "results": results,
            "count": len(results),
            "course_filter": target_course
        }
    
    @reasoning_step(ReasoningStepType.RELEVANCE_RANKING, "Ranking and filtering search results")
    async def rank_and_filter_results(self, search_results: List[Dict], query: str, chain_id: str = None) -> List[Dict]:
        """Rank and filter search results based on relevance to the query."""
        if not search_results:
            return []
        
        # Get top results
        top_results = search_results[:5]  # Limit to top 5 results
        
        # Rank results by relevance
        ranked_results = sorted(
            top_results, 
            key=lambda x: x.get('distance', 1.0)
        )
        
        return ranked_results
    
    @reasoning_step(ReasoningStepType.INFORMATION_EXTRACTION, "Extracting key information from classroom content")
    async def extract_key_information(self, context_docs: List[Dict], query_analysis: Dict, chain_id: str = None) -> Dict:
        """Extract key information from classroom content."""
        # Prepare context from retrieved documents
        extracted_info = {
            "documents": [],
            "course_names": set(),
            "topics": set(),
            "deadlines": [],
            "assignments": [],
            "key_phrases": []
        }
        
        for doc in context_docs:
            metadata = doc.get('metadata', {})
            content = doc.get('document', '')
            course_name = metadata.get('course_name', 'Unknown')
            
            extracted_info["documents"].append({
                "course": course_name,
                "type": metadata.get('content_type', 'unknown'),
                "content": content[:500]  # Limit content size
            })
            
            # Extract course names
            extracted_info["course_names"].add(course_name)
            
            # Extract potential deadlines
            if "due" in content.lower() or "deadline" in content.lower():
                extracted_info["deadlines"].append({
                    "course": course_name,
                    "content": content[:200]  # Excerpt with deadline info
                })
            
            # Extract assignments
            if "assignment" in content.lower() or "homework" in content.lower():
                extracted_info["assignments"].append({
                    "course": course_name,
                    "content": content[:200]  # Excerpt with assignment info
                })
        
        # Convert sets to lists for JSON serialization
        extracted_info["course_names"] = list(extracted_info["course_names"])
        extracted_info["topics"] = list(extracted_info["topics"])
        
        return extracted_info
    
    @reasoning_step(ReasoningStepType.ANSWER_FORMULATION, "Formulating detailed answer based on classroom content")
    async def generate_answer(self, query: str, context_docs: List[Dict], query_analysis: Dict, extracted_info: Dict, chain_id: str = None) -> str:
        """Generate intelligent answer based on classroom content with reasoning."""
        
        # Prepare context from retrieved documents
        context = ""
        for i, doc in enumerate(context_docs, 1):
            metadata = doc.get('metadata', {})
            content = doc.get('document', '')
            context += f"\nContext {i} (Course: {metadata.get('course_name', 'Unknown')}, Type: {metadata.get('content_type', 'unknown')}):\n{content}\n"
        
        # Check if this is a study plan request
        is_study_plan = any(keyword in query.lower() for keyword in ['study plan', 'plan', 'schedule', 'organize'])
        
        if is_study_plan:
            prompt = f"""
            You are an AI study planner helping a student create a structured study plan based on their Google Classroom content.
            
            Student Request: "{query}"
            Query Analysis: {json.dumps(query_analysis, indent=2)}
            
            Relevant Classroom Content:
            {context}
            
            Create a well-formatted study plan using markdown formatting:
            
            ## Priority Tasks & Deadlines:
            **HIGH PRIORITY** (Immediate Action Required):
            - List urgent assignments and deadlines
            
            **MEDIUM PRIORITY**:
            - List upcoming but not immediate tasks
            
            **LOW PRIORITY** (But Important):
            - List longer-term goals and preparations
            
            ## Weekly Study Schedule (Adjust to your needs):
            Provide a day-by-day breakdown with time estimates
            
            ## Study Strategies:
            - Recommend specific approaches for different subjects
            - Include review techniques and preparation methods
            
            ## Tips for Success:
            - Practical advice for staying organized
            - Motivational encouragement
            
            Use markdown formatting (##, **, *, bullet points) for clean structure.
            Be specific about dates, course names, and requirements.
            Keep it realistic and actionable.
            """
        else:
            prompt = f"""
            You are an AI teaching assistant helping a student with their Google Classroom content.
            
            Student Query: "{query}"
            Query Analysis: {json.dumps(query_analysis, indent=2)}
            
            Relevant Classroom Content:
            {context}
            
            Please provide a helpful, accurate answer that:
            1. Directly addresses the student's question
            2. References specific classroom content when relevant
            3. Is educational and encouraging
            4. Includes specific details from the course materials
            5. Suggests next steps if appropriate
            6. Is 150-300 words
            
            If the query is about deadlines or assignments, be specific about dates and requirements.
            If asking for help understanding concepts, explain clearly with examples from the course content.
            Always be supportive and educational in tone.
            """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            self.logger.warning(f"Answer generation failed: {e}")
            
            # Enhanced fallback response based on query type
            if "429" in str(e) or "quota" in str(e).lower():
                return self._generate_quota_fallback_response(query, context_docs, query_analysis, extracted_info)
            else:
                return f"I found some relevant information in your classroom content, but I'm having trouble processing it right now. Here's what I found: {context[:200]}..."
    
    @reasoning_step(ReasoningStepType.SELF_REFLECTION, "Reflecting on answer quality and completeness")
    async def reflect_on_answer(self, answer: str, query: str, query_analysis: Dict, chain_id: str = None) -> Dict:
        """Evaluate and reflect on the generated answer."""
        # Perform self-evaluation of the answer
        reflection = {
            "completeness": 0.8,  # Default values
            "relevance": 0.8,
            "specificity": 0.7,
            "improvement_areas": []
        }
        
        # Check if answer addresses the query intent
        if query_analysis.get('intent') in answer.lower():
            reflection["relevance"] = 0.9
        
        # Check if answer includes specific details
        if len(answer.split()) > 100:
            reflection["specificity"] = 0.9
        
        # Check for course references
        if query_analysis.get('target_course') and query_analysis.get('target_course') in answer:
            reflection["relevance"] = 0.95
        
        return reflection
    
    async def process_query_with_reasoning(self, query: str, knowledge_base, available_courses: List[str]) -> Dict:
        """Process a query with full reasoning chain visualization."""
        # Create a new reasoning chain
        chain = self.reasoning_manager.create_chain(query=query)
        chain_id = chain.chain_id
        
        # Initialize variables for fallback
        query_analysis = None
        search_data = None
        ranked_results = []
        extracted_info = {}
        answer = ""
        reflection = {}
        
        try:
            # Step 1: Analyze query
            query_analysis = await self.analyze_query(query, available_courses, chain_id=chain_id)
            
            # Step 2: Search knowledge base
            search_data = await self.search_knowledge_base(
                query_analysis.get('refined_query', query),
                knowledge_base,
                target_course=query_analysis.get('target_course'),
                chain_id=chain_id
            )
            
            # Step 3: Rank and filter results
            ranked_results = await self.rank_and_filter_results(
                search_data.get('results', []),
                query,
                chain_id=chain_id
            )
            
            # Step 4: Extract key information
            extracted_info = await self.extract_key_information(
                ranked_results,
                query_analysis,
                chain_id=chain_id
            )
            
            # Step 5: Generate answer
            answer = await self.generate_answer(
                query,
                ranked_results,
                query_analysis,
                extracted_info,
                chain_id=chain_id
            )
            
            # Step 6: Reflect on answer
            reflection = await self.reflect_on_answer(
                answer,
                query,
                query_analysis,
                chain_id=chain_id
            )
            
            # Complete the reasoning chain
            chain.complete()
            
            # Generate visualization
            visualization = self.visualizer.generate_text_visualization(chain)
            
            return {
                "answer": answer,
                "chain_id": chain_id,
                "reasoning_visualization": visualization,
                "reasoning_steps": len(chain.steps)
            }
            
        except Exception as e:
            # Complete the chain even on error
            chain.complete()
            self.logger.error(f"Error in reasoning chain: {e}")
            
            # Generate fallback response if quota error
            if "429" in str(e) or "quota" in str(e).lower():
                # Use whatever data we have so far for fallback response
                if not query_analysis:
                    query_analysis = {"query_type": "deadline", "urgency": "high"}
                if not extracted_info:
                    extracted_info = {"course_names": set(["Future Leaders Program Central Classroom", "Hs 103 Satvik", "HS 103 | 2023-4"]), 
                                    "deadlines": [], "documents": []}
                
                fallback_answer = self._generate_quota_fallback_response(query, ranked_results, query_analysis, extracted_info)
            else:
                fallback_answer = f"I encountered an error while processing your question: {str(e)}"
            
            # Return error info with reasoning visualization (what was completed)
            visualization = self.visualizer.generate_text_visualization(chain)
            
            return {
                "answer": fallback_answer,
                "chain_id": chain_id,
                "reasoning_visualization": visualization,
                "reasoning_steps": len(chain.steps),
                "error": str(e)
            }
    
    def get_reasoning_chain(self, chain_id: str) -> Optional[str]:
        """Get visualization of a specific reasoning chain."""
        chain = self.reasoning_manager.get_chain(chain_id)
        if not chain:
            return None
        
        return self.visualizer.generate_text_visualization(chain)
    
    def get_reasoning_html(self, chain_id: str) -> Optional[str]:
        """Get HTML visualization of a specific reasoning chain."""
        chain = self.reasoning_manager.get_chain(chain_id)
        if not chain:
            return None
        
        return self.visualizer.generate_html_visualization(chain)
    
    def list_recent_chains(self, limit: int = 5) -> List[Dict]:
        """List recent reasoning chains."""
        chains = self.reasoning_manager.list_chains()
        # Sort by start time (newest first)
        sorted_chains = sorted(
            chains, 
            key=lambda x: x.get('start_time', ''),
            reverse=True
        )
        return sorted_chains[:limit]
    
    def export_reasoning_chain(self, chain_id: str, format: str = 'json') -> Optional[Union[str, Dict]]:
        """
        Export a reasoning chain to various formats.
        
        Args:
            chain_id: ID of the chain to export
            format: Output format - 'json', 'html', 'markdown', or 'text'
            
        Returns:
            Exported chain in the requested format or None if chain not found
        """
        chain = self.reasoning_manager.get_chain(chain_id)
        if not chain:
            return None
            
        if format.lower() == 'json':
            return chain.to_dict()
        elif format.lower() == 'html':
            return self.visualizer.generate_html_visualization(chain)
        elif format.lower() == 'markdown':
            return self.visualizer.generate_markdown_visualization(chain)
        elif format.lower() == 'text':
            return self.visualizer.generate_text_visualization(chain)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def save_reasoning_chain(self, chain_id: str, filepath: str, format: str = 'json') -> bool:
        """
        Save a reasoning chain to a file.
        
        Args:
            chain_id: ID of the chain to save
            filepath: Path to save the file
            format: Output format - 'json', 'html', 'markdown', or 'text'
            
        Returns:
            True if successfully saved, False otherwise
        """
        try:
            exported_chain = self.export_reasoning_chain(chain_id, format)
            if not exported_chain:
                return False
                
            with open(filepath, 'w', encoding='utf-8') as f:
                if format.lower() == 'json':
                    json.dump(exported_chain, f, indent=2)
                else:
                    f.write(exported_chain)
            return True
        except Exception as e:
            self.logger.error(f"Error saving reasoning chain: {e}")
            return False
    
    def _get_query_hash(self, query: str, context: str = "") -> str:
        """Generate a deterministic hash for a query and optional context."""
        hash_input = (query + context).encode('utf-8')
        return hashlib.md5(hash_input).hexdigest()
        
    async def process_query_cached(self, query: str, knowledge_base, available_courses: List[str], 
                                  cache_ttl: int = 3600) -> Dict:
        """
        Process a query with reasoning chain and caching for improved performance.
        
        Args:
            query: User query
            knowledge_base: Knowledge base to search
            available_courses: List of available course names
            cache_ttl: Time-to-live for cache in seconds (default: 1 hour)
            
        Returns:
            Processing result with answer and reasoning chain
        """
        # Generate cache key
        cache_key = self._get_query_hash(query, str(available_courses))
        
        # Check cache path
        cache_dir = os.path.join(tempfile.gettempdir(), "reasoning_chain_cache")
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, f"{cache_key}.json")
        
        # Check if we have a cached result
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                
                # Check TTL
                cache_time = cached_data.get("cache_time", 0)
                if time.time() - cache_time <= cache_ttl:
                    self.logger.info(f"Using cached result for query: {query[:30]}...")
                    return cached_data.get("result")
            except Exception as e:
                self.logger.warning(f"Error reading cache: {e}")
        
        # Process the query if not cached or cache expired
        result = await self.process_query_with_reasoning(query, knowledge_base, available_courses)
        
        # Save to cache
        try:
            with open(cache_file, 'w') as f:
                json.dump({
                    "cache_time": time.time(),
                    "result": result
                }, f)
        except Exception as e:
            self.logger.warning(f"Error saving to cache: {e}")
        
        return result
    
    def _format_deadline_fallback(self, context_docs: List[Dict], extracted_info: Dict) -> str:
        """Format a deadline prioritization fallback response."""
        response = "## 📅 **Deadline Prioritization Help**\n\n"
        
        # Extract deadline information from context
        deadlines = extracted_info.get('deadlines', [])
        courses = extracted_info.get('course_names', set())
        
        if deadlines:
            response += "### 🚨 **URGENT ITEMS FOUND:**\n"
            for i, item in enumerate(deadlines, 1):
                response += f"**{i}. {item['course']}**\n"
                response += f"   {item['content']}\n\n"
        
        if courses:
            response += "### 📚 **ACTIVE COURSES:**\n"
            for course in sorted(courses):
                response += f"- **{course}**\n"
            response += "\n"
        
        response += "### 💡 **Quick Prioritization Strategy:**\n"
        response += "1. **🔥 Immediate**: Handle anything due in next 1-2 days\n"
        response += "2. **⚡ This Week**: Plan work for items due within 7 days\n"
        response += "3. **📋 Upcoming**: Schedule time for longer projects\n"
        response += "4. **👀 Monitor**: Check for new announcements daily\n\n"
        response += "**🎯 Pro Tip**: Create a calendar and work backwards from due dates!"
        
        return response
    
    def _format_study_plan_fallback(self, context_docs: List[Dict], extracted_info: Dict) -> str:
        """Format a study plan fallback response."""
        response = "## 📚 **Your Personalized Study Plan**\n\n"
        
        courses = extracted_info.get('course_names', set())
        assignments = extracted_info.get('assignments', [])
        deadlines = extracted_info.get('deadlines', [])
        
        if deadlines:
            response += "### 🎯 **PRIORITY TASKS:**\n"
            for item in deadlines:
                response += f"- **{item['course']}**: {item['content'][:100]}...\n"
            response += "\n"
        
        if courses:
            response += "### 📖 **STUDY SCHEDULE BY COURSE:**\n"
            for course in sorted(courses):
                response += f"**{course}**\n"
                response += "- Review recent materials\n"
                response += "- Complete pending assignments\n"
                response += "- Prepare for upcoming deadlines\n\n"
        
        response += "### 📅 **WEEKLY PLAN TEMPLATE:**\n"
        response += "**Monday-Wednesday**: Focus on current assignments\n"
        response += "**Thursday-Friday**: Review and prepare for next week\n"
        response += "**Weekend**: Catch up and long-term project work\n\n"
        
        response += "### 🎯 **SUCCESS TIPS:**\n"
        response += "- Break large tasks into smaller chunks\n"
        response += "- Set specific time blocks for each subject\n"
        response += "- Review material regularly, not just before deadlines\n"
        response += "- Keep track of progress and adjust as needed\n\n"
        response += "**You've got this! Stay organized and take it one step at a time! 🌟**"
        
        return response
    
    def _format_general_fallback(self, query: str, context_docs: List[Dict], extracted_info: Dict) -> str:
        """Format a general fallback response."""
        response = f"## 🎓 **Help with: {query}**\n\n"
        
        courses = extracted_info.get('course_names', set())
        documents = extracted_info.get('documents', [])
        
        if documents:
            response += "### 📚 **Relevant Information Found:**\n"
            for i, doc in enumerate(documents[:3], 1):
                response += f"**{i}. {doc['course']}** ({doc['type'].replace('courseWork', 'Assignment').title()})\n"
                response += f"   {doc['content'][:150]}...\n\n"
        
        if courses:
            response += "### 📖 **From Your Courses:**\n"
            for course in sorted(courses):
                response += f"- **{course}**\n"
            response += "\n"
        
        response += "### 💡 **Next Steps:**\n"
        response += "- Check your Google Classroom for complete details\n"
        response += "- Review the specific course materials mentioned above\n"
        response += "- Contact your instructor if you need clarification\n"
        response += "- Break down complex tasks into manageable steps\n\n"
        response += "**📧 Remember**: Your instructors are there to help - don't hesitate to reach out!"
        
        return response
    
    def _generate_quota_fallback_response(self, query: str, context_docs: List[Dict], query_analysis: Dict, extracted_info: Dict) -> str:
        """Generate a detailed fallback response when API quota is exceeded."""
        query_lower = query.lower()
        query_type = query_analysis.get('query_type', 'general_question')
        
        # Deadline/Priority queries
        if query_type == 'deadline' or any(word in query_lower for word in ['prioritize', 'deadline', 'due', 'urgent']):
            return self._format_deadline_fallback(context_docs, extracted_info)
        
        # Study plan queries
        elif query_type == 'material' or any(word in query_lower for word in ['study plan', 'plan', 'schedule', 'organize']):
            return self._format_study_plan_fallback(context_docs, extracted_info)
        
        # General queries
        else:
            return self._format_general_fallback(query, context_docs, extracted_info)
    
    def _format_deadline_fallback(self, context_docs: List[Dict], extracted_info: Dict) -> str:
        """Format a deadline prioritization fallback response."""
        response = "## 📅 **Deadline Prioritization Help**\n\n"
        
        # Extract deadline information from context
        deadlines = extracted_info.get('deadlines', [])
        courses = extracted_info.get('course_names', set())
        
        if deadlines:
            response += "### 🚨 **URGENT ITEMS FOUND:**\n"
            for i, item in enumerate(deadlines, 1):
                response += f"**{i}. {item['course']}**\n"
                response += f"   {item['content']}\n\n"
        
        if courses:
            response += "### 📚 **ACTIVE COURSES:**\n"
            for course in sorted(courses):
                response += f"- **{course}**\n"
            response += "\n"
        
        response += "### 💡 **Quick Prioritization Strategy:**\n"
        response += "1. **🔥 Immediate**: Handle anything due in next 1-2 days\n"
        response += "2. **⚡ This Week**: Plan work for items due within 7 days\n"
        response += "3. **📋 Upcoming**: Schedule time for longer projects\n"
        response += "4. **👀 Monitor**: Check for new announcements daily\n\n"
        response += "**🎯 Pro Tip**: Create a calendar and work backwards from due dates!"
        
        return response
    
    def _format_study_plan_fallback(self, context_docs: List[Dict], extracted_info: Dict) -> str:
        """Format a study plan fallback response."""
        response = "## 📚 **Your Personalized Study Plan**\n\n"
        
        courses = extracted_info.get('course_names', set())
        assignments = extracted_info.get('assignments', [])
        deadlines = extracted_info.get('deadlines', [])
        
        if deadlines:
            response += "### 🎯 **PRIORITY TASKS:**\n"
            for item in deadlines:
                response += f"- **{item['course']}**: {item['content'][:100]}...\n"
            response += "\n"
        
        if courses:
            response += "### 📖 **STUDY SCHEDULE BY COURSE:**\n"
            for course in sorted(courses):
                response += f"**{course}**\n"
                response += "- Review recent materials\n"
                response += "- Complete pending assignments\n"
                response += "- Prepare for upcoming deadlines\n\n"
        
        response += "### 📅 **WEEKLY PLAN TEMPLATE:**\n"
        response += "**Monday-Wednesday**: Focus on current assignments\n"
        response += "**Thursday-Friday**: Review and prepare for next week\n"
        response += "**Weekend**: Catch up and long-term project work\n\n"
        
        response += "### 🎯 **SUCCESS TIPS:**\n"
        response += "- Break large tasks into smaller chunks\n"
        response += "- Set specific time blocks for each subject\n"
        response += "- Review material regularly, not just before deadlines\n"
        response += "- Keep track of progress and adjust as needed\n\n"
        response += "**You've got this! Stay organized and take it one step at a time! 🌟**"
        
        return response
    
    def _format_general_fallback(self, query: str, context_docs: List[Dict], extracted_info: Dict) -> str:
        """Format a general fallback response."""
        response = f"## 🎓 **Help with: {query}**\n\n"
        
        courses = extracted_info.get('course_names', set())
        documents = extracted_info.get('documents', [])
        
        if documents:
            response += "### 📚 **Relevant Information Found:**\n"
            for i, doc in enumerate(documents[:3], 1):
                response += f"**{i}. {doc['course']}** ({doc['type'].replace('courseWork', 'Assignment').title()})\n"
                response += f"   {doc['content'][:150]}...\n\n"
        
        if courses:
            response += "### 📖 **From Your Courses:**\n"
            for course in sorted(courses):
                response += f"- **{course}**\n"
            response += "\n"
        
        response += "### 💡 **Next Steps:**\n"
        response += "- Check your Google Classroom for complete details\n"
        response += "- Review the specific course materials mentioned above\n"
        response += "- Contact your instructor if you need clarification\n"
        response += "- Break down complex tasks into manageable steps\n\n"
        response += "**📧 Remember**: Your instructors are there to help - don't hesitate to reach out!"
        
        return response