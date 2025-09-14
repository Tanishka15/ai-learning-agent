"""
Google Classroom AI Agent with RAG Integration

This agent connects to Google Classroom, parses course content,
builds a RAG knowledge base, and provides intelligent answers
based on your actual classroom materials.
"""

import asyncio
import sys
import os
import pickle
import logging
import json
import re
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime

# Google APIs
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# AI and RAG
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import numpy as np

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class ClassroomConfig:
    def __init__(self):
        # Try to load from .env file first, fall back to hardcoded value if not found
        try:
            from dotenv import load_dotenv
            load_dotenv()
            self.gemini_api_key = os.environ.get('GEMINI_API_KEY', "AIzaSyC88vGjUkqyu4Ux_9zVCdk7Z88cpQi7uEM")
        except ImportError:
            self.gemini_api_key = "AIzaSyC88vGjUkqyu4Ux_9zVCdk7Z88cpQi7uEM"
            
        self.scopes = [
            'https://www.googleapis.com/auth/classroom.courses.readonly',
            'https://www.googleapis.com/auth/classroom.rosters.readonly',
            'https://www.googleapis.com/auth/classroom.announcements.readonly'
            # Removed coursework.students.readonly scope which was causing auth issues
        ]
        self.credentials_file = 'credentials.json'
        self.token_file = 'token.json'
        self.embedding_model = 'all-MiniLM-L6-v2'
        self.gemini_model = "gemini-1.5-flash"
        self.max_results = 5

def setup_classroom_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


class GoogleClassroomConnector:
    """Connects to Google Classroom API and retrieves course data."""
    
    def __init__(self, config):
        self.config = config
        self.logger = setup_classroom_logger("classroom_connector")
        self.service = None
        self.courses = {}
        
    async def authenticate(self):
        """Authenticate with Google Classroom API."""
        print("🔐 Authenticating with Google Classroom...")
        
        creds = None
        
        # Load existing token
        if os.path.exists(self.config.token_file):
            with open(self.config.token_file, 'r') as token:
                creds = Credentials.from_authorized_user_info(
                    json.load(token), self.config.scopes
                )
        
        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.config.credentials_file):
                    print("❌ credentials.json not found!")
                    print("📋 Please follow CLASSROOM_SETUP.md to set up Google Classroom API")
                    return False
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.config.credentials_file, self.config.scopes
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for future use
            with open(self.config.token_file, 'w') as token:
                token.write(creds.to_json())
        
        try:
            self.service = build('classroom', 'v1', credentials=creds)
            print("✅ Successfully connected to Google Classroom!")
            return True
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False
    
    async def get_courses(self) -> Dict:
        """Retrieve all accessible courses."""
        if not self.service:
            return {}
        
        try:
            print("📚 Fetching your courses...")
            
            results = self.service.courses().list(pageSize=50).execute()
            courses = results.get('courses', [])
            
            course_data = {}
            for course in courses:
                course_id = course['id']
                course_name = course['name']
                course_state = course.get('courseState', 'UNKNOWN')
                
                if course_state == 'ACTIVE':
                    course_data[course_id] = {
                        'name': course_name,
                        'description': course.get('description', ''),
                        'section': course.get('section', ''),
                        'room': course.get('room', ''),
                        'teacher_folder': course.get('teacherFolder', {}),
                        'course_state': course_state
                    }
                    print(f"  📖 {course_name}")
            
            self.courses = course_data
            print(f"✅ Found {len(course_data)} active courses")
            return course_data
            
        except HttpError as error:
            print(f"❌ Error fetching courses: {error}")
            return {}
    
    async def get_course_content(self, course_id: str) -> Dict:
        """Get comprehensive content for a specific course."""
        if not self.service:
            return {}
        
        print(f"📖 Fetching content for course: {self.courses.get(course_id, {}).get('name', course_id)}")
        
        content = {
            'announcements': [],
            'coursework': [],
            'materials': [],
            'topics': []
        }
        
        try:
            # Get announcements
            announcements = self.service.courses().announcements().list(
                courseId=course_id, pageSize=50
            ).execute()
            
            for announcement in announcements.get('announcements', []):
                content['announcements'].append({
                    'id': announcement['id'],
                    'text': announcement.get('text', ''),
                    'creation_time': announcement.get('creationTime', ''),
                    'materials': announcement.get('materials', [])
                })
            
            # Get coursework (assignments)
            coursework = self.service.courses().courseWork().list(
                courseId=course_id, pageSize=50
            ).execute()
            
            for work in coursework.get('courseWork', []):
                content['coursework'].append({
                    'id': work['id'],
                    'title': work.get('title', ''),
                    'description': work.get('description', ''),
                    'creation_time': work.get('creationTime', ''),
                    'due_date': work.get('dueDate', {}),
                    'materials': work.get('materials', []),
                    'work_type': work.get('workType', 'ASSIGNMENT')
                })
            
            # Get course materials (if any)
            try:
                materials = self.service.courses().courseWorkMaterials().list(
                    courseId=course_id, pageSize=50
                ).execute()
                
                for material in materials.get('courseWorkMaterial', []):
                    content['materials'].append({
                        'id': material['id'],
                        'title': material.get('title', ''),
                        'description': material.get('description', ''),
                        'materials': material.get('materials', [])
                    })
            except:
                pass  # Some courses might not have materials
            
            # Get topics
            try:
                topics = self.service.courses().topics().list(
                    courseId=course_id
                ).execute()
                
                for topic in topics.get('topic', []):
                    content['topics'].append({
                        'topic_id': topic['topicId'],
                        'name': topic['name']
                    })
            except:
                pass  # Some courses might not have topics
            
            print(f"  📢 {len(content['announcements'])} announcements")
            print(f"  📝 {len(content['coursework'])} assignments")
            print(f"  📎 {len(content['materials'])} materials")
            print(f"  🏷️ {len(content['topics'])} topics")
            
            return content
            
        except HttpError as error:
            print(f"❌ Error fetching course content: {error}")
            return content


class RAGKnowledgeBase:
    """RAG (Retrieval-Augmented Generation) knowledge base for classroom content."""
    
    def __init__(self, config):
        self.config = config
        self.logger = setup_classroom_logger("rag_kb")
        
        # Initialize embedding model
        print("🧠 Loading sentence transformer model...")
        self.embedder = SentenceTransformer(config.embedding_model)
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.Client(Settings(
            persist_directory="./classroom_knowledge_base",
            anonymized_telemetry=False
        ))
        
        try:
            self.collection = self.chroma_client.get_collection("classroom_content")
            print("📚 Loaded existing knowledge base")
        except:
            self.collection = self.chroma_client.create_collection(
                name="classroom_content",
                metadata={"description": "Google Classroom course content"}
            )
            print("🆕 Created new knowledge base")
    
    async def index_course_content(self, course_id: str, course_name: str, content: Dict):
        """Index course content into the RAG knowledge base."""
        print(f"🔍 Indexing content for {course_name}...")
        
        documents = []
        metadatas = []
        ids = []
        
        # Index announcements
        for i, announcement in enumerate(content.get('announcements', [])):
            if announcement.get('text'):
                doc_id = f"{course_id}_announcement_{i}"
                doc_text = f"Course: {course_name}\nType: Announcement\nContent: {announcement['text']}"
                
                documents.append(doc_text)
                metadatas.append({
                    'course_id': course_id,
                    'course_name': course_name,
                    'content_type': 'announcement',
                    'creation_time': announcement.get('creation_time', ''),
                    'source_id': announcement['id']
                })
                ids.append(doc_id)
        
        # Index coursework
        for i, work in enumerate(content.get('coursework', [])):
            doc_id = f"{course_id}_coursework_{i}"
            doc_text = f"Course: {course_name}\nType: Assignment\nTitle: {work.get('title', '')}\nDescription: {work.get('description', '')}"
            
            documents.append(doc_text)
            metadatas.append({
                'course_id': course_id,
                'course_name': course_name,
                'content_type': 'coursework',
                'title': work.get('title', ''),
                'work_type': work.get('work_type', 'ASSIGNMENT'),
                'source_id': work['id']
            })
            ids.append(doc_id)
        
        # Index materials
        for i, material in enumerate(content.get('materials', [])):
            if material.get('title') or material.get('description'):
                doc_id = f"{course_id}_material_{i}"
                doc_text = f"Course: {course_name}\nType: Material\nTitle: {material.get('title', '')}\nDescription: {material.get('description', '')}"
                
                documents.append(doc_text)
                metadatas.append({
                    'course_id': course_id,
                    'course_name': course_name,
                    'content_type': 'material',
                    'title': material.get('title', ''),
                    'source_id': material['id']
                })
                ids.append(doc_id)
        
        if documents:
            # Generate embeddings and store
            embeddings = self.embedder.encode(documents)
            
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings.tolist()
            )
            
            print(f"✅ Indexed {len(documents)} content items from {course_name}")
        else:
            print(f"⚠️ No content to index for {course_name}")
    
    async def search(self, query: str, course_filter: Optional[str] = None) -> List[Dict]:
        """Search the knowledge base for relevant content."""
        print(f"🔍 Searching knowledge base for: '{query}'")
        
        # Generate query embedding
        query_embedding = self.embedder.encode([query])
        
        # Prepare where clause for filtering
        where = {}
        if course_filter:
            where["course_name"] = {"$eq": course_filter}
        
        # Search
        results = self.collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=self.config.max_results,
            where=where if where else None
        )
        
        # Format results
        formatted_results = []
        if results['documents']:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i]
                })
        
        print(f"📊 Found {len(formatted_results)} relevant results")
        return formatted_results


class ClassroomGeminiProcessor:
    """Gemini processor for classroom-specific queries."""
    
    def __init__(self, config):
        self.config = config
        genai.configure(api_key=config.gemini_api_key)
        self.model = genai.GenerativeModel(config.gemini_model)
        self.logger = setup_classroom_logger("classroom_gemini")
        
        # Initialize reasoning chain support
        try:
            from ai_learning_agent.utils.reasoning_processor import ClassroomGeminiReasoningProcessor
            self.reasoning_processor = ClassroomGeminiReasoningProcessor(config)
            self.reasoning_enabled = True
            self.logger.info("Reasoning chain visualization enabled")
        except ImportError:
            self.reasoning_enabled = False
            self.logger.warning("Reasoning chain visualization not available")
    
    async def analyze_query(self, query: str, available_courses: List[str]) -> Dict:
        """Analyze user query to understand intent and identify relevant course."""
        courses_list = ", ".join(available_courses)
        
        prompt = f"""
        Analyze this student query and extract the following information:
        Query: "{query}"
        
        Available courses: {courses_list}
        
        Please provide a JSON response with:
        1. target_course: Which specific course this query is about (exact name from list, or null if unclear)
        2. query_type: Type of query (assignment, announcement, general_question, deadline, material)
        3. intent: What the student wants (understand, complete, find, deadline, help)
        4. key_topics: List of key topics/subjects mentioned
        5. urgency: low, medium, high (based on language like "urgent", "due soon", etc.)
        6. refined_query: A cleaner version of the query for searching
        
        Response format: Valid JSON only, no markdown formatting.
        """
        
        try:
            response = self.model.generate_content(prompt)
            analysis = json.loads(response.text.strip())
            return analysis
        except Exception as e:
            self.logger.warning(f"Query analysis failed: {e}")
            return {
                "target_course": None,
                "query_type": "general_question",
                "intent": "understand",
                "key_topics": [],
                "urgency": "medium",
                "refined_query": query
            }
    
    async def generate_answer(self, query: str, context_docs: List[Dict], query_analysis: Dict) -> str:
        """Generate intelligent answer based on classroom content."""
        
        # Prepare context from retrieved documents
        context = ""
        for i, doc in enumerate(context_docs, 1):
            metadata = doc['metadata']
            content = doc['document']
            context += f"\nContext {i} (Course: {metadata['course_name']}, Type: {metadata['content_type']}):\n{content}\n"
        
        prompt = f"""
        You are an AI teaching assistant helping a student with their Google Classroom content.
        
        Student Query: "{query}"
        Query Analysis: {json.dumps(query_analysis, indent=2)}
        
        Relevant Classroom Content:
        {context}
        
        Please provide a well-formatted, helpful answer using these guidelines:
        
        **Content Requirements:**
        1. Directly address the student's question
        2. Reference specific classroom content when relevant
        3. Include specific details from course materials
        4. Be educational, encouraging, and supportive
        5. Suggest practical next steps when appropriate
        
        **Formatting Guidelines:**
        - Use **bold** for important points, course names, and deadlines
        - Use *italics* for emphasis and time references
        - Use bullet points (-) for lists and multiple items
        - Use ## for section headers when organizing complex information
        - Use > for important quotes or key information from course materials
        - Keep paragraphs concise and well-structured
        
        **Specific Instructions:**
        - For deadlines/assignments: Be specific about dates, requirements, and course names
        - For concept explanations: Use clear examples from course content
        - For multiple items: Organize with bullet points or numbered lists
        - Always end with an encouraging note or helpful suggestion
        
        Aim for 150-300 words with clean, readable formatting.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            self.logger.warning(f"Answer generation failed: {e}")
            # Check if it's a quota error and provide a detailed fallback
            if "429" in str(e) or "quota" in str(e).lower():
                return self._generate_quota_exceeded_response(query, context_docs, query_analysis)
            else:
                return f"I found some relevant information in your classroom content, but I'm having trouble processing it right now. Here's what I found: {context[:200]}..."
    
    async def process_with_reasoning(self, query: str, knowledge_base, available_courses: List[str]) -> Dict:
        """Process a query with full reasoning chain visualization."""
        if not self.reasoning_enabled:
            # Fallback to standard processing if reasoning is not available
            query_analysis = await self.analyze_query(query, available_courses)
            results = await knowledge_base.search(query_analysis.get('refined_query', query), 
                                                  course_filter=query_analysis.get('target_course'))
            answer = await self.generate_answer(query, results, query_analysis)
            return {
                "answer": answer,
                "reasoning_enabled": False
            }
        
        # Use the reasoning processor for enhanced processing
        result = await self.reasoning_processor.process_query_with_reasoning(
            query, 
            knowledge_base, 
            available_courses
        )
        
        return result

    def _generate_quota_exceeded_response(self, query: str, context_docs: List[Dict], query_analysis: Dict) -> str:
        """Generate a detailed response when Gemini API quota is exceeded."""
        query_lower = query.lower()
        
        # Check if this is a prioritization/deadline question
        if any(word in query_lower for word in ['prioritize', 'deadline', 'due', 'urgent']):
            return self._format_deadline_response(context_docs)
        
        # Check if this is a study plan request
        if any(word in query_lower for word in ['study plan', 'plan', 'schedule', 'organize']):
            return self._format_study_plan_response(context_docs)
        
        # General question - format the context nicely
        return self._format_general_response(query, context_docs)
    
    def _format_deadline_response(self, context_docs: List[Dict]) -> str:
        """Format a deadline prioritization response."""
        response = "## 📅 **Deadline Prioritization Help**\n\n"
        
        urgent_items = []
        announcements = []
        
        for doc in context_docs:
            content = doc.get('document', '')
            metadata = doc.get('metadata', {})
            course_name = metadata.get('course_name', 'Unknown Course')
            content_type = metadata.get('content_type', 'material')
            
            if 'due' in content.lower() or 'deadline' in content.lower() or content_type == 'courseWork':
                urgent_items.append({
                    'course': course_name,
                    'content': content[:250] + ("..." if len(content) > 250 else ""),
                    'type': content_type
                })
            elif content_type == 'announcement':
                announcements.append({
                    'course': course_name,
                    'content': content[:200] + ("..." if len(content) > 200 else "")
                })
        
        if urgent_items:
            response += "### 🚨 **URGENT ITEMS FOUND:**\n"
            for i, item in enumerate(urgent_items, 1):
                response += f"**{i}. {item['course']}** ({item['type'].replace('courseWork', 'Assignment').title()})\n"
                response += f"   {item['content']}\n\n"
        
        if announcements:
            response += "### 📢 **IMPORTANT ANNOUNCEMENTS:**\n"
            for i, ann in enumerate(announcements, 1):
                response += f"**{i}. {ann['course']}**\n"
                response += f"   {ann['content']}\n\n"
        
        response += "### 💡 **Quick Prioritization Strategy:**\n"
        response += "1. **🔥 Immediate**: Handle anything due in next 1-2 days\n"
        response += "2. **⚡ This Week**: Plan work for items due within 7 days\n"
        response += "3. **📋 Upcoming**: Schedule time for longer projects\n"
        response += "4. **👀 Monitor**: Check for new announcements daily\n\n"
        response += "**🎯 Pro Tip**: Create a calendar and work backwards from due dates!"
        
        return response
    
    def _format_study_plan_response(self, context_docs: List[Dict]) -> str:
        """Format a study plan response."""
        response = "## 📚 **Your Personalized Study Plan**\n\n"
        
        courses = {}
        for doc in context_docs:
            metadata = doc.get('metadata', {})
            course_name = metadata.get('course_name', 'Unknown Course')
            content = doc.get('document', '')
            content_type = metadata.get('content_type', 'material')
            
            if course_name not in courses:
                courses[course_name] = {'assignments': [], 'materials': [], 'announcements': []}
            
            if content_type == 'courseWork':
                courses[course_name]['assignments'].append(content[:150])
            elif content_type == 'announcement':
                courses[course_name]['announcements'].append(content[:150])
            else:
                courses[course_name]['materials'].append(content[:150])
        
        for course_name, content in courses.items():
            response += f"### 📖 **{course_name}**\n"
            
            if content['assignments']:
                response += "**📝 Key Assignments:**\n"
                for assignment in content['assignments'][:2]:
                    response += f"- {assignment}...\n"
                response += "\n"
            
            if content['announcements']:
                response += "**📢 Important Updates:**\n"
                for announcement in content['announcements'][:2]:
                    response += f"- {announcement}...\n"
                response += "\n"
        
        response += "### 🗓️ **Suggested Weekly Schedule:**\n"
        response += "- **Monday/Wednesday/Friday**: Focus on active assignments\n"
        response += "- **Tuesday/Thursday**: Review and preparation\n"
        response += "- **Weekends**: Catch up and plan ahead\n\n"
        response += "**✨ Adjust this plan based on your actual schedule and preferences!**"
        
        return response
    
    def _format_general_response(self, query: str, context_docs: List[Dict]) -> str:
        """Format a general response."""
        response = f"## 🤔 **Answer to: \"{query}\"**\n\n"
        response += "Based on your classroom content:\n\n"
        
        for i, doc in enumerate(context_docs[:3], 1):  # Limit to 3 sources
            metadata = doc.get('metadata', {})
            content = doc.get('document', '')
            course_name = metadata.get('course_name', 'Unknown Course')
            content_type = metadata.get('content_type', 'material')
            
            response += f"### 📖 **{course_name}** ({content_type.title()})\n"
            response += f"{content[:300]}{'...' if len(content) > 300 else ''}\n\n"
        
        response += "---\n\n💡 **Need more specific help?** Try asking about specific courses, assignments, or deadlines!"
        
        return response


class GoogleClassroomAIAgent:
    """Main AI agent that connects Google Classroom with RAG and Gemini."""
    
    def __init__(self):
        self.config = ClassroomConfig()
        self.logger = setup_classroom_logger("classroom_agent")
        
        self.classroom = GoogleClassroomConnector(self.config)
        self.knowledge_base = RAGKnowledgeBase(self.config)
        self.gemini = ClassroomGeminiProcessor(self.config)
        
        self.courses = {}
        self.initialized = False
        
        print("🎓 Google Classroom AI Agent initialized!")
        print("🧠 Powered by Gemini AI + RAG")
        print("📚 Ready to connect to your classroom content")
    
    async def initialize(self):
        """Initialize the agent by connecting to classroom and building knowledge base."""
        print("\n🚀 Initializing Classroom AI Agent...")
        
        # Set basic initialization to allow reasoning processor to work
        self.initialized = True
        
        try:
            # Authenticate with Google Classroom
            if not await self.classroom.authenticate():
                print("⚠️ Google Classroom authentication failed, but reasoning processor still available")
                self.courses = {}
                return True  # Allow reasoning processor to work without classroom content
            
            # Get courses
            self.courses = await self.classroom.get_courses()
            if not self.courses:
                print("⚠️ No courses found or accessible, but reasoning processor still available")
                self.courses = {}
                return True  # Allow reasoning processor to work without classroom content
            
            # Index course content
            print("\n📚 Building RAG knowledge base from your courses...")
            for course_id, course_info in self.courses.items():
                try:
                    content = await self.classroom.get_course_content(course_id)
                    await self.knowledge_base.index_course_content(
                        course_id, course_info['name'], content
                    )
                except Exception as e:
                    print(f"⚠️ Failed to index content for {course_info['name']}: {e}")
                    continue
            
            print("\n✅ Classroom AI Agent ready!")
            print("💡 You can now ask questions about your course content!")
            return True
        
        except Exception as e:
            print(f"⚠️ Partial initialization error: {e}")
            print("🧠 Reasoning processor still available for general questions")
            self.courses = {}
            return True  # Allow reasoning processor to work even with errors
    
    async def ask_question(self, query: str, show_reasoning: bool = False) -> str:
        """Process a student question using RAG and Gemini."""
        if not self.initialized:
            return "❌ Agent not initialized. Please run initialize() first."
        
        print(f"\n🤔 Processing: '{query}'")
        
        # Check if we should use the enhanced reasoning processor
        if show_reasoning and hasattr(self.gemini, 'reasoning_enabled') and self.gemini.reasoning_enabled:
            print("🧠 Using reasoning chain visualization...")
            
            # Get course names (handle case where courses might be empty)
            course_names = [info['name'] for info in self.courses.values()] if self.courses else []
            
            # Use the enhanced reasoning processor
            result = await self.gemini.process_with_reasoning(query, self.knowledge_base, course_names)
            
            # Format the response with reasoning chain
            answer = result.get('answer', '')
            
            if result.get('reasoning_visualization'):
                # Add reasoning chain visualization if requested
                answer += "\n\n" + "="*50 + "\n"
                answer += "🧠 REASONING PROCESS\n"
                answer += "="*50 + "\n"
                answer += result.get('reasoning_visualization')
            
            return answer
        
        # Standard processing without reasoning chain visualization
        course_names = [info['name'] for info in self.courses.values()] if self.courses else []
        query_analysis = await self.gemini.analyze_query(query, course_names)
        
        target_course = query_analysis.get('target_course')
        refined_query = query_analysis.get('refined_query', query)
        
        print(f"🎯 Target course: {target_course or 'All courses'}")
        print(f"📝 Query type: {query_analysis.get('query_type', 'unknown')}")
        
        # Search knowledge base
        context_docs = await self.knowledge_base.search(
            refined_query, 
            course_filter=target_course
        )
        
        if not context_docs:
            return "🤷‍♂️ I couldn't find relevant information in your classroom content for that question. Could you be more specific or check if the content has been posted to Google Classroom?"
        
        # Try to generate answer using Gemini, with fallback for quota errors
        try:
            answer = await self.gemini.generate_answer(query, context_docs, query_analysis)
            return answer
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                # Quota exceeded - provide a detailed manual response
                return await self._generate_fallback_answer(query, context_docs, query_analysis)
            else:
                # Other error - still try fallback
                print(f"⚠️ Gemini API error: {e}")
                return await self._generate_fallback_answer(query, context_docs, query_analysis)
    
    async def _generate_fallback_answer(self, query: str, context_docs: List[Dict], query_analysis: Dict) -> str:
        """Generate a detailed answer without using Gemini API (fallback for quota issues)."""
        query_lower = query.lower()
        
        # Check if this is a prioritization/deadline question
        if any(word in query_lower for word in ['prioritize', 'deadline', 'due', 'urgent']):
            return await self._generate_deadline_prioritization_answer(context_docs)
        
        # Check if this is a study plan request
        if any(word in query_lower for word in ['study plan', 'plan', 'schedule', 'organize']):
            return await self._generate_study_plan_answer(context_docs)
        
        # General question - format the context nicely
        return await self._generate_general_answer(query, context_docs, query_analysis)
    
    async def _generate_deadline_prioritization_answer(self, context_docs: List[Dict]) -> str:
        """Generate a deadline prioritization answer."""
        deadlines = []
        announcements = []
        assignments = []
        
        for doc in context_docs:
            content = doc.get('document', '').lower()
            metadata = doc.get('metadata', {})
            course_name = metadata.get('course_name', 'Unknown Course')
            content_type = metadata.get('content_type', 'unknown')
            
            full_content = doc.get('document', '')
            
            if content_type == 'announcement':
                announcements.append({
                    'course': course_name,
                    'content': full_content[:200] + "..." if len(full_content) > 200 else full_content
                })
            
            if 'due' in content or 'deadline' in content or 'submit' in content:
                deadlines.append({
                    'course': course_name,
                    'content': full_content[:300] + "..." if len(full_content) > 300 else full_content,
                    'type': content_type
                })
        
        response = "## 📅 Deadline Prioritization Help\n\n"
        
        if deadlines:
            response += "### 🚨 **URGENT DEADLINES FOUND:**\n"
            for i, deadline in enumerate(deadlines, 1):
                response += f"**{i}. {deadline['course']}** ({deadline['type'].title()})\n"
                response += f"   {deadline['content']}\n\n"
        
        if announcements:
            response += "### 📢 **IMPORTANT ANNOUNCEMENTS:**\n"
            for i, ann in enumerate(announcements, 1):
                response += f"**{i}. {ann['course']}**\n"
                response += f"   {ann['content']}\n\n"
        
        response += "### 💡 **Prioritization Strategy:**\n"
        response += "1. **Immediate (Today/Tomorrow)**: Handle any assignments due within 24-48 hours\n"
        response += "2. **This Week**: Plan work for assignments due within 7 days\n" 
        response += "3. **Upcoming**: Schedule time for longer-term projects\n"
        response += "4. **Stay Updated**: Check for new announcements regularly\n\n"
        
        response += "**🎯 Pro Tip**: Create a calendar with all these deadlines and work backwards from due dates!"
        
        return response
    
    async def _generate_study_plan_answer(self, context_docs: List[Dict]) -> str:
        """Generate a study plan answer."""
        courses = {}
        
        for doc in context_docs:
            metadata = doc.get('metadata', {})
            course_name = metadata.get('course_name', 'Unknown Course')
            content = doc.get('document', '')
            content_type = metadata.get('content_type', 'material')
            
            if course_name not in courses:
                courses[course_name] = {'materials': [], 'assignments': [], 'announcements': []}
            
            courses[course_name][f"{content_type}s"].append(content[:150] + "..." if len(content) > 150 else content)
        
        response = "## 📚 Personalized Study Plan\n\n"
        
        for course_name, content in courses.items():
            response += f"### 📖 **{course_name}**\n"
            
            if content['assignments']:
                response += "**📝 Assignments to Focus On:**\n"
                for assignment in content['assignments'][:3]:  # Top 3
                    response += f"- {assignment}\n"
                response += "\n"
            
            if content['materials']:
                response += "**📑 Study Materials:**\n"
                for material in content['materials'][:3]:  # Top 3
                    response += f"- {material}\n"
                response += "\n"
            
            if content['announcements']:
                response += "**📢 Important Updates:**\n"
                for announcement in content['announcements'][:2]:  # Top 2
                    response += f"- {announcement}\n"
                response += "\n"
        
        response += "### 🗓️ **Weekly Schedule Suggestion:**\n"
        response += "- **Monday/Wednesday/Friday**: Focus on active courses with assignments\n"
        response += "- **Tuesday/Thursday**: Review materials and prepare for upcoming deadlines\n"
        response += "- **Weekend**: Catch up on readings and start longer-term projects\n\n"
        response += "**✨ Remember**: Adjust this plan based on your actual class schedule and personal preferences!"
        
        return response
    
    async def _generate_general_answer(self, query: str, context_docs: List[Dict], query_analysis: Dict) -> str:
        """Generate a general answer."""
        response = f"## 🤔 Answer to: \"{query}\"\n\n"
        
        response += "Based on your classroom content, here's what I found:\n\n"
        
        for i, doc in enumerate(context_docs, 1):
            metadata = doc.get('metadata', {})
            content = doc.get('document', '')
            course_name = metadata.get('course_name', 'Unknown Course')
            content_type = metadata.get('content_type', 'material')
            
            response += f"### 📖 **Source {i}: {course_name}** ({content_type.title()})\n"
            response += f"{content[:400]}{'...' if len(content) > 400 else ''}\n\n"
        
        response += "---\n\n"
        response += "💡 **Need more specific help?** Try asking about:\n"
        response += "- Specific assignment details\n"
        response += "- Study materials for a particular topic\n"
        response += "- Upcoming deadlines\n"
        response += "- Course announcements\n"
        
        return response

    def list_courses(self) -> List[str]:
        """List available courses."""
        return [f"📖 {info['name']}" for info in self.courses.values()]
    
    async def search_course_content(self, query: str, course_name: Optional[str] = None) -> List[Dict]:
        """Search course content directly."""
        return await self.knowledge_base.search(query, course_filter=course_name)
    
    async def create_study_plan(self, course_name: Optional[str] = None, timeframe: str = "week", show_reasoning: bool = False) -> Union[str, Dict]:
        """Create a tentative study plan based on course assignments and announcements.
        
        Args:
            course_name: Optional specific course to create a plan for. If None, creates a plan across all courses.
            timeframe: The timeframe for the plan ("week", "month", or "all").
            show_reasoning: Whether to show the step-by-step reasoning process.
            
        Returns:
            A structured study plan as a string, or a dict with reasoning chain if show_reasoning=True.
        """
        if not self.initialized:
            return "❌ Agent not initialized. Please run initialize() first."
        
        print(f"\n📝 Creating {timeframe}ly study plan" + (f" for {course_name}" if course_name else " across all courses"))
        
        # Create a study plan query for the reasoning processor
        study_plan_query = f"Create a {timeframe}ly study plan" + (f" for {course_name}" if course_name else " across all courses") + " based on my assignments, deadlines, and announcements"
        
        # Check if we should use the enhanced reasoning processor
        if show_reasoning and hasattr(self.gemini, 'reasoning_enabled') and self.gemini.reasoning_enabled:
            print("🧠 Using reasoning chain visualization for study plan...")
            
            # Get course names
            course_names = [info['name'] for info in self.courses.values()]
            
            # Use the enhanced reasoning processor
            result = await self.gemini.process_with_reasoning(study_plan_query, self.knowledge_base, course_names)
            
            # Format the study plan response with reasoning chain
            study_plan = result.get('answer', '')
            
            if result.get('reasoning_visualization'):
                # Add reasoning chain visualization if requested
                study_plan += "\n\n" + "="*50 + "\n"
                study_plan += "🧠 REASONING PROCESS\n"
                study_plan += "="*50 + "\n"
                study_plan += result.get('reasoning_visualization')
            
            return study_plan
        
        # Standard study plan generation without reasoning chain
        # Search for assignments, deadlines and announcements separately for better coverage
        assignment_results = await self.knowledge_base.search("assignment deadline due date exam quiz project", course_filter=course_name)
        announcement_results = await self.knowledge_base.search("announcement important notice update information", course_filter=course_name)
        
        # Combine the results, prioritizing assignments first
        combined_results = assignment_results + [item for item in announcement_results if item not in assignment_results]
        
        if not combined_results:
            return "No assignments, deadlines or announcements found to create a study plan. Try a different course or check if content has been posted."
        
        # Prepare context for Gemini to create the study plan
        context = ""
        for i, result in enumerate(combined_results[:12]):  # Limit to top 12 results (increased from 10)
            metadata = result['metadata']
            context += f"\nItem {i+1} ({metadata['course_name']} - {metadata['content_type']}):\n{result['document']}\n"
        
        prompt = f"""
        Create a structured study plan based on the following Google Classroom content:
        
        {context}
        
        The study plan should:
        1. Identify assignments, deadlines, and exams from both direct assignments and announcements
        2. Extract any mentioned due dates or important events
        3. Organize tasks in priority order (based on due dates and importance)
        4. Suggest a realistic daily/weekly study schedule
        5. Include time estimates for each study topic
        6. Recommend study strategies specific to the content
        7. Include any specific instructions or requirements mentioned
        8. Pay special attention to important information in announcements that might affect studying
        
        Timeframe focus: {timeframe} ({"next 7 days" if timeframe == "week" else "next 30 days" if timeframe == "month" else "all upcoming"})
        
        Format the plan clearly with sections, bullet points, and prioritized tasks.
        If dates are mentioned, include them in the plan.
        If specific courses need more attention based on deadlines or announcements, highlight this.
        Include a brief motivational message at the end.
        """
        
        try:
            # Generate the study plan using Gemini
            response = self.gemini.model.generate_content(prompt)
            study_plan = response.text.strip()
            
            # Clean and format the study plan
            cleaned_plan = study_plan.strip()
            
            # Add a clean header
            formatted_plan = f"# 📚 Study Plan ({timeframe.capitalize()})\n\n{cleaned_plan}"
            
            return formatted_plan
        except Exception as e:
            self.logger.warning(f"Study plan generation failed: {e}")
            return f"❌ Could not generate study plan: {str(e)}"
    
    async def get_bulletin_board_items(self) -> List[Dict]:
        """Get urgent deadlines, quizzes, and important announcements for bulletin board."""
        if not self.initialized:
            return []
        
        try:
            # Search for urgent items - assignments, exams, quizzes, deadlines
            urgent_queries = [
                "assignment due exam quiz test deadline urgent",
                "important announcement notice update required",
                "project submission due date"
            ]
            
            all_items = []
            for query in urgent_queries:
                results = await self.knowledge_base.search(query)
                # Limit results to top 10 manually
                limited_results = results[:10]
                all_items.extend(limited_results)
            
            # Remove duplicates and process items
            processed_items = []
            seen_content = set()
            
            for item in all_items:
                content = item.get('document', '')
                if content in seen_content:
                    continue
                seen_content.add(content)
                
                # Extract key information
                bulletin_item = await self._process_bulletin_item(item)
                if bulletin_item:
                    processed_items.append(bulletin_item)
            
            # Sort by priority and date
            processed_items.sort(key=lambda x: (
                0 if x['priority'] == 'urgent' else 1 if x['priority'] == 'important' else 2,
                x.get('date', '9999-12-31')
            ))
            
            return processed_items[:8]  # Limit to top 8 items
            
        except Exception as e:
            self.logger.error(f"Error getting bulletin board items: {e}")
            return []
    
    async def _process_bulletin_item(self, item: Dict) -> Optional[Dict]:
        """Process a knowledge base item into a bulletin board item (without API calls)."""
        try:
            content = item.get('document', '')
            metadata = item.get('metadata', {})
            content_lower = content.lower()
            
            # Skip empty content
            if not content.strip():
                return None
            
            # Determine item type
            item_type = metadata.get('content_type', 'other')
            if item_type == 'courseWork':
                item_type = 'assignment'
            
            # Determine priority based on content keywords
            priority = "normal"
            if any(word in content_lower for word in ['urgent', 'asap', 'immediately', 'today', 'tomorrow']):
                priority = "urgent"
            elif any(word in content_lower for word in ['important', 'due', 'deadline', 'exam', 'quiz', 'test']):
                priority = "important"
            
            # Extract a meaningful title
            title = content.split('.')[0].strip()
            if len(title) > 50:
                title = title[:47] + "..."
            elif not title:
                title = f"{metadata.get('course_name', 'Course')} Update"
            
            # Check if it has deadline indicators
            has_deadline = any(word in content_lower for word in ['due', 'deadline', 'submit', 'turn in', 'by'])
            
            # Only include if it's important content
            if item_type == 'announcement' or has_deadline or priority in ['urgent', 'important']:
                return {
                    "id": f"item_{hash(content) % 100000}",
                    "title": title,
                    "description": content[:120] + ("..." if len(content) > 120 else ""),
                    "course": metadata.get('course_name', 'Unknown'),
                    "date": None,  # We could extract dates with regex if needed
                    "priority": priority,
                    "type": item_type,
                    "time_until": "Unknown"
                }
            
            return None  # Skip items that don't meet criteria
                
        except Exception as e:
            self.logger.warning(f"Error processing bulletin item: {e}")
            return None
    
    def _calculate_time_until(self, date_str: Optional[str]) -> str:
        """Calculate human-readable time until a date."""
        if not date_str:
            return "No deadline"
        
        try:
            from datetime import datetime
            due_date = datetime.strptime(date_str, "%Y-%m-%d")
            today = datetime.now()
            diff = (due_date - today).days
            
            if diff < 0:
                return "Overdue"
            elif diff == 0:
                return "Today"
            elif diff == 1:
                return "Tomorrow"
            elif diff < 7:
                return f"{diff} days"
            elif diff < 30:
                weeks = diff // 7
                return f"{weeks} week{'s' if weeks > 1 else ''}"
            else:
                return f"{diff} days"
        except:
            return "Unknown"


async def main():
    """Main interactive loop for the Classroom AI Agent."""
    print("🎓 GOOGLE CLASSROOM AI AGENT")
    print("=" * 50)
    print("🧠 Powered by Gemini + RAG")
    print("📚 Connects to your actual Google Classroom content")
    print("=" * 50)
    
    agent = GoogleClassroomAIAgent()
    
    # Initialize
    if not await agent.initialize():
        print("\n❌ Failed to initialize. Please check:")
        print("1. credentials.json exists (see CLASSROOM_SETUP.md)")
        print("2. You have access to Google Classroom courses")
        print("3. Internet connection is available")
        return
    
    # Show available courses
    courses = agent.list_courses()
    if courses:
        print(f"\n📚 Your courses:")
        for course in courses:
            print(f"  {course}")
    
    print("\n" + "="*60)
    print("🎓 Classroom AI Agent - Ready for Questions!")
    print("="*60)
    print("Available commands:")
    print("  ask <question>     - Ask about your course content")
    print("  ask+ <question>    - Ask with reasoning chain visualization")
    print("  courses            - List your courses")
    print("  search <query>     - Search course content")
    print("  plan [course] [week|month|all] - Create a study plan")
    print("  help               - Show this help")
    print("  quit               - Exit")
    print("="*60)
    print("💡 Examples:")
    print("  ask What's my next assignment due?")
    print("  ask+ Explain the concept from today's announcement with reasoning")
    print("  plan week         - Create a weekly study plan")
    print("  plan \"HS 103\" month - Create a monthly plan for specific course")
    
    while True:
        try:
            user_input = input("\n> ").strip()
            
            if not user_input:
                continue
            
            parts = user_input.split(maxsplit=1)
            command = parts[0].lower()
            
            if command == "quit":
                print("👋 Thanks for using Classroom AI Agent!")
                break
            elif command == "help":
                print("\nAvailable commands:")
                print("  ask <question>     - Ask about course content")
                print("  courses            - List your courses")
                print("  search <query>     - Search content")
                print("  plan [course] [week|month|all] - Create a study plan")
                print("  quit               - Exit")
            elif command == "ask" or command == "ask+":
                if len(parts) > 1:
                    # Use reasoning visualization for ask+ command
                    show_reasoning = (command == "ask+")
                    answer = await agent.ask_question(parts[1], show_reasoning=show_reasoning)
                    
                    if show_reasoning:
                        print(f"\n🧠 AI Answer (with reasoning):\n{answer}")
                    else:
                        print(f"\n🤖 AI Answer:\n{answer}")
                else:
                    print("❌ Please ask a question about your courses.")
            elif command == "courses":
                courses = agent.list_courses()
                if courses:
                    print("\n📚 Your courses:")
                    for course in courses:
                        print(f"  {course}")
                else:
                    print("📭 No courses found.")
            elif command == "search":
                if len(parts) > 1:
                    results = await agent.search_course_content(parts[1])
                    if results:
                        print(f"\n🔍 Search results for '{parts[1]}':")
                        for i, result in enumerate(results[:3], 1):
                            metadata = result['metadata']
                            print(f"\n{i}. {metadata['course_name']} - {metadata['content_type']}")
                            print(f"   {result['document'][:150]}...")
                    else:
                        print("🤷‍♂️ No results found.")
                else:
                    print("❌ Please provide a search query.")
            elif command == "plan":
                # Parse plan command options: plan [course] [timeframe]
                course_name = None
                timeframe = "week"  # Default timeframe
                
                if len(parts) > 1:
                    # Check if the second part is a timeframe option
                    if parts[1].lower() in ["week", "month", "all"]:
                        timeframe = parts[1].lower()
                    else:
                        # Assume it's a course name
                        course_name = parts[1]
                        
                        # Check for optional timeframe as third parameter
                        if len(parts) > 2 and parts[2].lower() in ["week", "month", "all"]:
                            timeframe = parts[2].lower()
                
                # Generate and display study plan
                study_plan = await agent.create_study_plan(course_name, timeframe)
                print(f"\n{study_plan}")
            else:
                print(f"❓ Unknown command: {command}")
                print("Type 'help' to see available commands.")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            print("Please try again or type 'help' for available commands.")


if __name__ == "__main__":
    asyncio.run(main())