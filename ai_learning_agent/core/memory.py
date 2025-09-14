"""
Memory System for AI Learning Agent

This module provides persistent storage and retrieval capabilities for the agent's
learned knowledge, including topics, concepts, and learning progress.
"""

import asyncio
import json
import sqlite3
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import hashlib

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False


@dataclass
class KnowledgeEntry:
    """Represents a stored knowledge entry."""
    id: str
    topic: str
    content: Dict[str, Any]
    concepts: List[str]
    timestamp: datetime
    confidence: float
    source: str
    embedding: Optional[List[float]] = None


@dataclass
class LearningProgress:
    """Tracks learning progress for a topic."""
    topic: str
    completion_percentage: float
    time_spent_minutes: int
    last_accessed: datetime
    quiz_scores: List[float]
    difficulty_level: str
    mastery_level: str


class MemorySystem:
    """
    Persistent memory system for the AI learning agent.
    
    Handles storage, retrieval, and organization of learned knowledge,
    concepts, and user progress.
    """
    
    def __init__(self, config):
        """Initialize the memory system."""
        self.config = config
        self.logger = logging.getLogger("memory_system")
        self.db_path = "agent_memory.db"

        # Initialize embedding model if available
        self.embedding_model = None
        if HAS_SENTENCE_TRANSFORMERS:
            try:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                self.logger.info("Embedding model initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize embedding model: {e}")

        # Initialize database synchronously for web apps
        self._initialize_database_sync()

        # In-memory cache for quick access
        self.cache = {
            'topics': {},
            'concepts': {},
            'recent_queries': []
        }

        self.logger.info("Memory system initialized")

    def _initialize_database_sync(self):
        """Synchronously initialize the SQLite database with required tables."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Knowledge entries table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS knowledge_entries (
                    id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    content TEXT NOT NULL,
                    concepts TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    source TEXT NOT NULL,
                    embedding BLOB
                )
            ''')

            # Learning progress table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS learning_progress (
                    topic TEXT PRIMARY KEY,
                    completion_percentage REAL NOT NULL,
                    time_spent_minutes INTEGER NOT NULL,
                    last_accessed TEXT NOT NULL,
                    quiz_scores TEXT NOT NULL,
                    difficulty_level TEXT NOT NULL,
                    mastery_level TEXT NOT NULL
                )
            ''')

            # Concepts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS concepts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    definition TEXT,
                    related_topics TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    embedding BLOB
                )
            ''')

            # Relationships table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS relationships (
                    id TEXT PRIMARY KEY,
                    source_concept TEXT NOT NULL,
                    target_concept TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    strength REAL NOT NULL,
                    context TEXT
                )
            ''')

            conn.commit()
            conn.close()

            self.logger.info("Database initialized successfully (sync)")

        except Exception as e:
            self.logger.error(f"Failed to initialize database (sync): {e}")
            raise
    
    async def _initialize_database(self):
        """Initialize the SQLite database with required tables."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Knowledge entries table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS knowledge_entries (
                    id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    content TEXT NOT NULL,
                    concepts TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    source TEXT NOT NULL,
                    embedding BLOB
                )
            ''')
            
            # Learning progress table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS learning_progress (
                    topic TEXT PRIMARY KEY,
                    completion_percentage REAL NOT NULL,
                    time_spent_minutes INTEGER NOT NULL,
                    last_accessed TEXT NOT NULL,
                    quiz_scores TEXT NOT NULL,
                    difficulty_level TEXT NOT NULL,
                    mastery_level TEXT NOT NULL
                )
            ''')
            
            # Concepts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS concepts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    definition TEXT,
                    related_topics TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    embedding BLOB
                )
            ''')
            
            # Relationships table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS relationships (
                    id TEXT PRIMARY KEY,
                    source_concept TEXT NOT NULL,
                    target_concept TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    strength REAL NOT NULL,
                    context TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            
            self.logger.info("Database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def store_knowledge(self, topic: str, knowledge: Dict[str, Any]) -> str:
        """
        Store processed knowledge for a topic.
        
        Args:
            topic: The topic name
            knowledge: Processed knowledge dictionary
            
        Returns:
            Knowledge entry ID
        """
        self.logger.info(f"Storing knowledge for topic: {topic}")
        
        # Generate unique ID
        knowledge_id = hashlib.md5(f"{topic}_{datetime.now().isoformat()}".encode()).hexdigest()
        
        # Extract concepts
        concepts = knowledge.get('concepts', [])
        
        # Generate embedding if model available
        embedding = None
        if self.embedding_model and 'summary' in knowledge:
            try:
                embedding_vector = self.embedding_model.encode(knowledge['summary'])
                embedding = embedding_vector.tolist() if HAS_NUMPY else None
            except Exception as e:
                self.logger.warning(f"Failed to generate embedding: {e}")
        
        # Create knowledge entry
        entry = KnowledgeEntry(
            id=knowledge_id,
            topic=topic,
            content=knowledge,
            concepts=concepts,
            timestamp=datetime.now(),
            confidence=0.8,  # Default confidence
            source="autonomous_research",
            embedding=embedding
        )
        
        # Store in database
        await self._store_knowledge_entry(entry)
        
        # Store concepts
        for concept in concepts:
            await self._store_concept(concept, topic)
        
        # Update cache
        self.cache['topics'][topic] = entry
        
        self.logger.info(f"Successfully stored knowledge for {topic}")
        return knowledge_id
    
    async def retrieve_knowledge(self, topic: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve stored knowledge for a topic.
        
        Args:
            topic: The topic to retrieve
            
        Returns:
            Knowledge dictionary or None if not found
        """
        self.logger.info(f"Retrieving knowledge for: {topic}")
        
        # Check cache first
        if topic in self.cache['topics']:
            return self.cache['topics'][topic].content
        
        # Query database
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT content FROM knowledge_entries WHERE topic = ? ORDER BY timestamp DESC LIMIT 1",
                (topic,)
            )
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                knowledge = json.loads(result[0])
                # Update cache
                # Note: This is simplified - in reality, we'd reconstruct the full KnowledgeEntry
                self.cache['topics'][topic] = knowledge
                return knowledge
            else:
                self.logger.info(f"No knowledge found for topic: {topic}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error retrieving knowledge for {topic}: {e}")
            return None
    
    async def search_knowledge(self, concepts: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for knowledge entries related to given concepts.
        
        Args:
            concepts: List of concepts to search for
            limit: Maximum number of results
            
        Returns:
            List of relevant knowledge entries
        """
        self.logger.info(f"Searching knowledge for concepts: {concepts}")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build search query
            concept_conditions = []
            params = []
            
            for concept in concepts:
                concept_conditions.append("concepts LIKE ?")
                params.append(f"%{concept}%")
            
            query = f"""
                SELECT topic, content, confidence 
                FROM knowledge_entries 
                WHERE {' OR '.join(concept_conditions)}
                ORDER BY confidence DESC, timestamp DESC
                LIMIT ?
            """
            params.append(limit)
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            conn.close()
            
            # Parse results
            knowledge_entries = []
            for topic, content_json, confidence in results:
                try:
                    content = json.loads(content_json)
                    knowledge_entries.append({
                        'topic': topic,
                        'content': content,
                        'confidence': confidence
                    })
                except json.JSONDecodeError:
                    self.logger.warning(f"Failed to parse content for topic: {topic}")
            
            self.logger.info(f"Found {len(knowledge_entries)} relevant knowledge entries")
            return knowledge_entries
            
        except Exception as e:
            self.logger.error(f"Error searching knowledge: {e}")
            return []
    
    async def semantic_search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Perform semantic search using embeddings.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of semantically similar knowledge entries
        """
        if not self.embedding_model:
            self.logger.warning("Semantic search not available - no embedding model")
            return []
        
        self.logger.info(f"Performing semantic search for: {query}")
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query)
            
            # Retrieve all stored embeddings
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, topic, content, embedding FROM knowledge_entries WHERE embedding IS NOT NULL")
            results = cursor.fetchall()
            conn.close()
            
            if not results:
                return []
            
            # Calculate similarities
            similarities = []
            for entry_id, topic, content_json, embedding_blob in results:
                try:
                    # Deserialize embedding
                    stored_embedding = np.frombuffer(embedding_blob, dtype=np.float32) if HAS_NUMPY else None
                    
                    if stored_embedding is not None:
                        # Calculate cosine similarity
                        similarity = np.dot(query_embedding, stored_embedding) / (
                            np.linalg.norm(query_embedding) * np.linalg.norm(stored_embedding)
                        )
                        
                        content = json.loads(content_json)
                        similarities.append({
                            'topic': topic,
                            'content': content,
                            'similarity': float(similarity)
                        })
                        
                except Exception as e:
                    self.logger.warning(f"Error processing embedding for {topic}: {e}")
            
            # Sort by similarity and return top results
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            return similarities[:limit]
            
        except Exception as e:
            self.logger.error(f"Error in semantic search: {e}")
            return []
    
    async def store_learning_progress(self, topic: str, progress: LearningProgress) -> None:
        """Store learning progress for a topic."""
        self.logger.info(f"Storing learning progress for: {topic}")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO learning_progress 
                (topic, completion_percentage, time_spent_minutes, last_accessed, 
                 quiz_scores, difficulty_level, mastery_level)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                progress.topic,
                progress.completion_percentage,
                progress.time_spent_minutes,
                progress.last_accessed.isoformat(),
                json.dumps(progress.quiz_scores),
                progress.difficulty_level,
                progress.mastery_level
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Learning progress stored for: {topic}")
            
        except Exception as e:
            self.logger.error(f"Error storing learning progress: {e}")
    
    async def get_learning_progress(self, topic: str) -> Optional[LearningProgress]:
        """Retrieve learning progress for a topic."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM learning_progress WHERE topic = ?", (topic,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return LearningProgress(
                    topic=result[0],
                    completion_percentage=result[1],
                    time_spent_minutes=result[2],
                    last_accessed=datetime.fromisoformat(result[3]),
                    quiz_scores=json.loads(result[4]),
                    difficulty_level=result[5],
                    mastery_level=result[6]
                )
            return None
            
        except Exception as e:
            self.logger.error(f"Error retrieving learning progress: {e}")
            return None
    
    async def list_topics(self) -> List[str]:
        """Get a list of all stored topics."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT DISTINCT topic FROM knowledge_entries ORDER BY topic")
            results = cursor.fetchall()
            conn.close()
            
            return [result[0] for result in results]
            
        except Exception as e:
            self.logger.error(f"Error listing topics: {e}")
            return []
    
    async def get_related_concepts(self, concept: str, limit: int = 10) -> List[Tuple[str, float]]:
        """Get concepts related to the given concept."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT target_concept, strength 
                FROM relationships 
                WHERE source_concept = ? 
                ORDER BY strength DESC 
                LIMIT ?
            ''', (concept, limit))
            
            results = cursor.fetchall()
            conn.close()
            
            return [(concept, strength) for concept, strength in results]
            
        except Exception as e:
            self.logger.error(f"Error getting related concepts: {e}")
            return []
    
    async def update_concept_frequency(self, concept: str) -> None:
        """Update the frequency count for a concept."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE concepts 
                SET frequency = frequency + 1 
                WHERE name = ?
            ''', (concept,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error updating concept frequency: {e}")
    
    async def cleanup_old_entries(self, days_old: int = 30) -> None:
        """Remove old knowledge entries to manage storage."""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "DELETE FROM knowledge_entries WHERE timestamp < ?",
                (cutoff_date.isoformat(),)
            )
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            self.logger.info(f"Cleaned up {deleted_count} old knowledge entries")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    async def _store_knowledge_entry(self, entry: KnowledgeEntry) -> None:
        """Store a knowledge entry in the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Serialize embedding if present
            embedding_blob = None
            if entry.embedding and HAS_NUMPY:
                embedding_blob = np.array(entry.embedding, dtype=np.float32).tobytes()
            
            cursor.execute('''
                INSERT OR REPLACE INTO knowledge_entries 
                (id, topic, content, concepts, timestamp, confidence, source, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                entry.id,
                entry.topic,
                json.dumps(entry.content),
                json.dumps(entry.concepts),
                entry.timestamp.isoformat(),
                entry.confidence,
                entry.source,
                embedding_blob
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error storing knowledge entry: {e}")
            raise
    
    async def _store_concept(self, concept: str, topic: str) -> None:
        """Store or update a concept in the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Generate concept ID
            concept_id = hashlib.md5(concept.encode()).hexdigest()
            
            # Check if concept exists
            cursor.execute("SELECT related_topics, frequency FROM concepts WHERE id = ?", (concept_id,))
            result = cursor.fetchone()
            
            if result:
                # Update existing concept
                existing_topics = json.loads(result[0])
                if topic not in existing_topics:
                    existing_topics.append(topic)
                
                cursor.execute('''
                    UPDATE concepts 
                    SET related_topics = ?, frequency = frequency + 1 
                    WHERE id = ?
                ''', (json.dumps(existing_topics), concept_id))
            else:
                # Insert new concept
                cursor.execute('''
                    INSERT INTO concepts (id, name, related_topics, frequency)
                    VALUES (?, ?, ?, ?)
                ''', (concept_id, concept, json.dumps([topic]), 1))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error storing concept: {e}")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about stored memory."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Count knowledge entries
            cursor.execute("SELECT COUNT(*) FROM knowledge_entries")
            knowledge_count = cursor.fetchone()[0]
            
            # Count unique topics
            cursor.execute("SELECT COUNT(DISTINCT topic) FROM knowledge_entries")
            topic_count = cursor.fetchone()[0]
            
            # Count concepts
            cursor.execute("SELECT COUNT(*) FROM concepts")
            concept_count = cursor.fetchone()[0]
            
            # Count relationships
            cursor.execute("SELECT COUNT(*) FROM relationships")
            relationship_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'knowledge_entries': knowledge_count,
                'unique_topics': topic_count,
                'concepts': concept_count,
                'relationships': relationship_count,
                'cache_size': len(self.cache['topics'])
            }
            
        except Exception as e:
            self.logger.error(f"Error getting memory stats: {e}")
            return {}