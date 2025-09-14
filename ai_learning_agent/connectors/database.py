"""
Database Connector Module

Provides unified database connectivity for various database systems
including SQLite, PostgreSQL, and MongoDB for storing agent data.
"""

import logging
import sqlite3
import asyncio
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from urllib.parse import urlparse

try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False

try:
    import motor.motor_asyncio
    HAS_MOTOR = True
except ImportError:
    HAS_MOTOR = False

try:
    import sqlalchemy
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False


@dataclass
class DatabaseConfig:
    """Database configuration."""
    url: str
    database_type: str
    max_connections: int = 10
    timeout: int = 30


@dataclass
class QueryResult:
    """Database query result."""
    success: bool
    data: List[Dict[str, Any]]
    error_message: Optional[str] = None
    rows_affected: int = 0


class DatabaseConnector:
    """
    Unified database connector supporting multiple database systems.
    
    Supports:
    - SQLite (built-in)
    - PostgreSQL (via asyncpg)
    - MongoDB (via motor)
    """
    
    def __init__(self, config):
        """Initialize database connector."""
        self.config = config
        self.logger = logging.getLogger("database_connector")
        
        # Connection pools
        self.sqlite_connections = {}
        self.postgres_pool = None
        self.mongo_client = None
        
        # Database configurations
        self.databases = {
            'sqlite': DatabaseConfig(
                url=getattr(config, 'DATABASE_URL', 'sqlite:///agent_memory.db'),
                database_type='sqlite'
            ),
            'postgres': DatabaseConfig(
                url=getattr(config, 'POSTGRES_URL', ''),
                database_type='postgres'
            ),
            'mongodb': DatabaseConfig(
                url=getattr(config, 'MONGODB_URL', ''),
                database_type='mongodb'
            )
        }
        
        self.logger.info("Database connector initialized")
    
    async def connect(self, database_name: str = 'sqlite') -> bool:
        """
        Connect to the specified database.
        
        Args:
            database_name: Name of database configuration to use
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            db_config = self.databases.get(database_name)
            if not db_config or not db_config.url:
                self.logger.warning(f"No configuration found for database: {database_name}")
                return False
            
            if db_config.database_type == 'sqlite':
                return await self._connect_sqlite(db_config)
            elif db_config.database_type == 'postgres':
                return await self._connect_postgres(db_config)
            elif db_config.database_type == 'mongodb':
                return await self._connect_mongodb(db_config)
            
            return False
        
        except Exception as e:
            self.logger.error(f"Database connection error: {e}")
            return False
    
    async def execute_query(
        self, 
        query: str, 
        params: Optional[Union[tuple, dict]] = None,
        database_name: str = 'sqlite'
    ) -> QueryResult:
        """
        Execute a database query.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            database_name: Database to query
            
        Returns:
            QueryResult object
        """
        try:
            db_config = self.databases.get(database_name)
            
            if db_config.database_type == 'sqlite':
                return await self._execute_sqlite_query(query, params)
            elif db_config.database_type == 'postgres':
                return await self._execute_postgres_query(query, params)
            else:
                return QueryResult(
                    success=False,
                    data=[],
                    error_message=f"Unsupported database type: {db_config.database_type}"
                )
        
        except Exception as e:
            self.logger.error(f"Query execution error: {e}")
            return QueryResult(
                success=False,
                data=[],
                error_message=str(e)
            )
    
    async def store_document(
        self, 
        collection: str, 
        document: Dict[str, Any],
        database_name: str = 'mongodb'
    ) -> QueryResult:
        """
        Store a document in a NoSQL database.
        
        Args:
            collection: Collection/table name
            document: Document to store
            database_name: Database to use
            
        Returns:
            QueryResult object
        """
        try:
            if database_name == 'mongodb' and self.mongo_client:
                return await self._store_mongodb_document(collection, document)
            else:
                # Fallback to SQLite for document storage
                return await self._store_sqlite_document(collection, document)
        
        except Exception as e:
            self.logger.error(f"Document storage error: {e}")
            return QueryResult(
                success=False,
                data=[],
                error_message=str(e)
            )
    
    async def find_documents(
        self, 
        collection: str, 
        query: Dict[str, Any] = None,
        limit: int = 100,
        database_name: str = 'mongodb'
    ) -> QueryResult:
        """
        Find documents in a NoSQL database.
        
        Args:
            collection: Collection name
            query: Query filter
            limit: Maximum number of documents
            database_name: Database to query
            
        Returns:
            QueryResult object
        """
        try:
            query = query or {}
            
            if database_name == 'mongodb' and self.mongo_client:
                return await self._find_mongodb_documents(collection, query, limit)
            else:
                # Fallback to SQLite
                return await self._find_sqlite_documents(collection, query, limit)
        
        except Exception as e:
            self.logger.error(f"Document search error: {e}")
            return QueryResult(
                success=False,
                data=[],
                error_message=str(e)
            )
    
    async def _connect_sqlite(self, db_config: DatabaseConfig) -> bool:
        """Connect to SQLite database."""
        try:
            # Parse SQLite URL
            url_parts = urlparse(db_config.url)
            db_path = url_parts.path[1:]  # Remove leading slash
            
            # Test connection
            conn = sqlite3.connect(db_path)
            conn.close()
            
            self.sqlite_connections['default'] = db_path
            self.logger.info(f"Connected to SQLite database: {db_path}")
            return True
        
        except Exception as e:
            self.logger.error(f"SQLite connection error: {e}")
            return False
    
    async def _connect_postgres(self, db_config: DatabaseConfig) -> bool:
        """Connect to PostgreSQL database."""
        if not HAS_ASYNCPG:
            self.logger.warning("asyncpg not available, cannot connect to PostgreSQL")
            return False
        
        try:
            self.postgres_pool = await asyncpg.create_pool(
                db_config.url,
                min_size=1,
                max_size=db_config.max_connections,
                command_timeout=db_config.timeout
            )
            
            # Test connection
            async with self.postgres_pool.acquire() as conn:
                await conn.execute('SELECT 1')
            
            self.logger.info("Connected to PostgreSQL database")
            return True
        
        except Exception as e:
            self.logger.error(f"PostgreSQL connection error: {e}")
            return False
    
    async def _connect_mongodb(self, db_config: DatabaseConfig) -> bool:
        """Connect to MongoDB database."""
        if not HAS_MOTOR:
            self.logger.warning("motor not available, cannot connect to MongoDB")
            return False
        
        try:
            self.mongo_client = motor.motor_asyncio.AsyncIOMotorClient(
                db_config.url,
                serverSelectionTimeoutMS=db_config.timeout * 1000
            )
            
            # Test connection
            await self.mongo_client.admin.command('ping')
            
            self.logger.info("Connected to MongoDB database")
            return True
        
        except Exception as e:
            self.logger.error(f"MongoDB connection error: {e}")
            return False
    
    async def _execute_sqlite_query(self, query: str, params: Optional[tuple] = None) -> QueryResult:
        """Execute SQLite query."""
        try:
            db_path = self.sqlite_connections.get('default')
            if not db_path:
                return QueryResult(
                    success=False,
                    data=[],
                    error_message="SQLite not connected"
                )
            
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Handle different query types
            if query.strip().upper().startswith('SELECT'):
                rows = cursor.fetchall()
                data = [dict(row) for row in rows]
                rows_affected = len(data)
            else:
                conn.commit()
                data = []
                rows_affected = cursor.rowcount
            
            conn.close()
            
            return QueryResult(
                success=True,
                data=data,
                rows_affected=rows_affected
            )
        
        except Exception as e:
            return QueryResult(
                success=False,
                data=[],
                error_message=str(e)
            )
    
    async def _execute_postgres_query(self, query: str, params: Optional[tuple] = None) -> QueryResult:
        """Execute PostgreSQL query."""
        if not self.postgres_pool:
            return QueryResult(
                success=False,
                data=[],
                error_message="PostgreSQL not connected"
            )
        
        try:
            async with self.postgres_pool.acquire() as conn:
                if query.strip().upper().startswith('SELECT'):
                    if params:
                        rows = await conn.fetch(query, *params)
                    else:
                        rows = await conn.fetch(query)
                    
                    data = [dict(row) for row in rows]
                    rows_affected = len(data)
                else:
                    if params:
                        result = await conn.execute(query, *params)
                    else:
                        result = await conn.execute(query)
                    
                    data = []
                    rows_affected = int(result.split()[-1]) if result else 0
            
            return QueryResult(
                success=True,
                data=data,
                rows_affected=rows_affected
            )
        
        except Exception as e:
            return QueryResult(
                success=False,
                data=[],
                error_message=str(e)
            )
    
    async def _store_mongodb_document(self, collection: str, document: Dict[str, Any]) -> QueryResult:
        """Store document in MongoDB."""
        try:
            db = self.mongo_client.agent_db
            collection_obj = db[collection]
            
            result = await collection_obj.insert_one(document)
            
            return QueryResult(
                success=True,
                data=[{'_id': str(result.inserted_id)}],
                rows_affected=1
            )
        
        except Exception as e:
            return QueryResult(
                success=False,
                data=[],
                error_message=str(e)
            )
    
    async def _find_mongodb_documents(
        self, 
        collection: str, 
        query: Dict[str, Any], 
        limit: int
    ) -> QueryResult:
        """Find documents in MongoDB."""
        try:
            db = self.mongo_client.agent_db
            collection_obj = db[collection]
            
            cursor = collection_obj.find(query).limit(limit)
            documents = await cursor.to_list(length=limit)
            
            # Convert ObjectId to string
            for doc in documents:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
            
            return QueryResult(
                success=True,
                data=documents,
                rows_affected=len(documents)
            )
        
        except Exception as e:
            return QueryResult(
                success=False,
                data=[],
                error_message=str(e)
            )
    
    async def _store_sqlite_document(self, collection: str, document: Dict[str, Any]) -> QueryResult:
        """Store document in SQLite as JSON."""
        import json
        
        # Create table if not exists
        create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {collection} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        
        await self._execute_sqlite_query(create_table_query)
        
        # Insert document
        insert_query = f"INSERT INTO {collection} (document) VALUES (?)"
        
        return await self._execute_sqlite_query(
            insert_query, 
            (json.dumps(document),)
        )
    
    async def _find_sqlite_documents(
        self, 
        collection: str, 
        query: Dict[str, Any], 
        limit: int
    ) -> QueryResult:
        """Find documents in SQLite."""
        import json
        
        # Simple query - in reality, you'd need more sophisticated JSON querying
        select_query = f"SELECT document FROM {collection} LIMIT ?"
        
        result = await self._execute_sqlite_query(select_query, (limit,))
        
        if result.success:
            documents = []
            for row in result.data:
                try:
                    doc = json.loads(row['document'])
                    documents.append(doc)
                except json.JSONDecodeError:
                    continue
            
            result.data = documents
        
        return result
    
    async def close_connections(self):
        """Close all database connections."""
        try:
            if self.postgres_pool:
                await self.postgres_pool.close()
                self.logger.info("PostgreSQL connections closed")
            
            if self.mongo_client:
                self.mongo_client.close()
                self.logger.info("MongoDB connection closed")
            
            self.sqlite_connections.clear()
            self.logger.info("All database connections closed")
        
        except Exception as e:
            self.logger.error(f"Error closing connections: {e}")
    
    def get_connection_status(self) -> Dict[str, bool]:
        """Get status of all database connections."""
        return {
            'sqlite': bool(self.sqlite_connections),
            'postgres': self.postgres_pool is not None,
            'mongodb': self.mongo_client is not None
        }