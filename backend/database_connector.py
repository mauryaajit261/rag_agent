"""
mySetu AI - Database Connector
Precision database indexing with summary-first architecture.

Key design: Every table gets a SUMMARY chunk (with exact row count, schema,
and aggregate stats) stored as its own vector. This ensures count/aggregate
queries are answered precisely from the summary — not by counting rows
across scattered chunks.
"""

import uuid
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd

# Database drivers
try:
    import pymysql
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

try:
    import psycopg2
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False

try:
    from pymongo import MongoClient
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False

import sqlite3

from langchain_core.documents import Document as LangChainDocument
from config import settings
from models import DatabaseType, DatabaseConnectionRequest, DatabaseConnectionInfo, ProcessingStatus

class DatabaseConnector:
    """Enterprise database connector with precision semantic indexing"""
    
    def __init__(self, document_processor):
        self.document_processor = document_processor
        self.connections: Dict[str, DatabaseConnectionInfo] = {}
        # Load saved connections from disk (just like documents load from metadata.json)
        self._load_connections()
    
    # ── Persistence ──────────────────────────────────────────────────────
    
    def _load_connections(self):
        """Load database connection metadata from JSON file"""
        conn_path = settings.BASE_DIR / "db_connections.json"
        if conn_path.exists():
            try:
                with open(conn_path, 'r') as f:
                    conn_dict = json.load(f)
                    for conn_id, conn_data in conn_dict.items():
                        if conn_data.get('indexed_date'):
                            conn_data['indexed_date'] = datetime.fromisoformat(conn_data['indexed_date'])
                        self.connections[conn_id] = DatabaseConnectionInfo(**conn_data)
                print(f"✅ Loaded {len(self.connections)} saved database connections")
            except Exception as e:
                print(f"⚠️ Could not load database connections: {e}")
    
    def _save_connections(self):
        """Save database connection metadata to JSON file"""
        conn_path = settings.BASE_DIR / "db_connections.json"
        try:
            conn_dict = {}
            for conn_id, conn_info in self.connections.items():
                # mode='json' ensures enums → strings, datetime → ISO strings
                data = conn_info.model_dump(mode='json')
                conn_dict[conn_id] = data
            
            with open(conn_path, 'w') as f:
                json.dump(conn_dict, f, indent=2)
            print(f"✅ Saved {len(self.connections)} database connections to disk")
        except Exception as e:
            print(f"⚠️ Could not save database connections: {e}")
    
    # ── Connection Methods ───────────────────────────────────────────────
    
    def _connect_mysql(self, config: DatabaseConnectionRequest):
        """Connect to MySQL database"""
        if not MYSQL_AVAILABLE:
            raise ImportError("pymysql not installed. Install with: pip install pymysql")
        
        connection = pymysql.connect(
            host=config.host,
            port=config.port,
            user=config.username,
            password=config.password,
            database=config.database,
            connect_timeout=settings.DB_CONNECTION_TIMEOUT
        )
        return connection
    
    def _connect_postgresql(self, config: DatabaseConnectionRequest):
        """Connect to PostgreSQL database"""
        if not POSTGRESQL_AVAILABLE:
            raise ImportError("psycopg2 not installed. Install with: pip install psycopg2-binary")
        
        connection = psycopg2.connect(
            host=config.host,
            port=config.port,
            user=config.username,
            password=config.password,
            database=config.database,
            connect_timeout=settings.DB_CONNECTION_TIMEOUT
        )
        return connection
    
    def _connect_mongodb(self, config: DatabaseConnectionRequest):
        """Connect to MongoDB database"""
        if not MONGODB_AVAILABLE:
            raise ImportError("pymongo not installed. Install with: pip install pymongo")
        
        connection_string = f"mongodb://{config.username}:{config.password}@{config.host}:{config.port}/{config.database}"
        client = MongoClient(connection_string, serverSelectionTimeoutMS=settings.DB_CONNECTION_TIMEOUT * 1000)
        return client[config.database]
    
    def _connect_sqlite(self, config: DatabaseConnectionRequest):
        """Connect to SQLite database"""
        connection = sqlite3.connect(config.database)
        return connection
    
    # ── Table/Collection Discovery ───────────────────────────────────────
    
    def _get_sql_tables(self, connection, db_type: DatabaseType, specified_tables: Optional[List[str]] = None) -> List[str]:
        """Get list of tables from SQL database"""
        cursor = connection.cursor()
        
        if db_type == DatabaseType.MYSQL:
            cursor.execute("SHOW TABLES")
        elif db_type == DatabaseType.POSTGRESQL:
            cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        elif db_type == DatabaseType.SQLITE:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        
        all_tables = [row[0] for row in cursor.fetchall()]
        
        if specified_tables:
            all_tables = [t for t in all_tables if t in specified_tables]
        
        cursor.close()
        return all_tables
    
    def _get_mongodb_collections(self, db, specified_collections: Optional[List[str]] = None) -> List[str]:
        """Get list of collections from MongoDB"""
        all_collections = db.list_collection_names()
        
        if specified_collections:
            all_collections = [c for c in all_collections if c in specified_collections]
        
        return all_collections
    
    # ── SQL: Get EXACT row count ─────────────────────────────────────────
    
    def _get_sql_row_count(self, connection, table_name: str) -> int:
        """Get the EXACT total row count for a SQL table"""
        cursor = connection.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        cursor.close()
        return count
    
    def _get_sql_schema(self, connection, table_name: str, db_type: DatabaseType) -> List[Dict[str, str]]:
        """Get detailed schema info for a SQL table"""
        cursor = connection.cursor()
        
        if db_type == DatabaseType.MYSQL:
            cursor.execute(f"DESCRIBE {table_name}")
            schema = cursor.fetchall()
            columns = [{"name": col[0], "type": col[1], "nullable": col[2]} for col in schema]
        elif db_type == DatabaseType.POSTGRESQL:
            cursor.execute(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """)
            schema = cursor.fetchall()
            columns = [{"name": col[0], "type": col[1], "nullable": col[2]} for col in schema]
        elif db_type == DatabaseType.SQLITE:
            cursor.execute(f"PRAGMA table_info({table_name})")
            schema = cursor.fetchall()
            columns = [{"name": col[1], "type": col[2], "nullable": "NO" if col[3] else "YES"} for col in schema]
        
        cursor.close()
        return columns
    
    # ── Precision Text Conversion ────────────────────────────────────────
    
    def _sql_table_to_structured_text(self, connection, table_name: str, db_type: DatabaseType) -> Dict[str, Any]:
        """
        Convert SQL table to structured text with separate summary and data sections.
        
        Returns:
            {
                "summary": "Table summary with exact counts and schema",
                "data_chunks": ["chunk1", "chunk2", ...],  # Row data in manageable chunks
                "total_rows": int,
                "columns": [...]
            }
        """
        # Get exact row count
        total_rows = self._get_sql_row_count(connection, table_name)
        
        # Get schema
        schema = self._get_sql_schema(connection, table_name, db_type)
        column_names = [col["name"] for col in schema]
        
        # Build summary text (this is the most important chunk for aggregate queries)
        schema_description = "\n".join([
            f"  - {col['name']} ({col['type']})" for col in schema
        ])
        
        summary = f"""DATABASE TABLE SUMMARY: {table_name}
Total number of rows/records: {total_rows}
Total number of registered entries: {total_rows}
Number of columns: {len(schema)}

Schema/Columns:
{schema_description}

IMPORTANT FACTS:
- This table "{table_name}" contains EXACTLY {total_rows} rows/records/entries.
- When asked "how many" records/users/entries are in {table_name}, the answer is {total_rows}.
- The table has {len(schema)} columns: {', '.join(column_names)}.
"""
        
        # Get all data rows (up to limit)
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {settings.DB_MAX_ROWS_PER_QUERY}")
        rows = cursor.fetchall()
        cursor.close()
        
        # Build data chunks — group rows together (10 rows per chunk for database content)
        ROWS_PER_CHUNK = 10
        data_chunks = []
        
        for batch_start in range(0, len(rows), ROWS_PER_CHUNK):
            batch_end = min(batch_start + ROWS_PER_CHUNK, len(rows))
            batch_rows = rows[batch_start:batch_end]
            
            chunk_header = f"[Database: {table_name} | Rows {batch_start + 1}-{batch_end} of {total_rows} total]"
            
            row_texts = []
            for idx, row in enumerate(batch_rows, batch_start + 1):
                row_text = " | ".join([f"{col}: {val}" for col, val in zip(column_names, row)])
                row_texts.append(f"Row {idx}: {row_text}")
            
            chunk_text = f"{chunk_header}\n\n" + "\n".join(row_texts)
            data_chunks.append(chunk_text)
        
        return {
            "summary": summary,
            "data_chunks": data_chunks,
            "total_rows": total_rows,
            "columns": column_names
        }
    
    def _mongodb_collection_to_structured_text(self, db, collection_name: str) -> Dict[str, Any]:
        """Convert MongoDB collection to structured text with summary"""
        collection = db[collection_name]
        
        # Get exact count
        total_docs = collection.count_documents({})
        
        # Get documents
        documents = list(collection.find().limit(settings.DB_MAX_ROWS_PER_QUERY))
        
        if not documents:
            return {
                "summary": f"MongoDB Collection: {collection_name}\nNo documents found.\nTotal documents: 0",
                "data_chunks": [],
                "total_rows": 0,
                "columns": []
            }
        
        # Get all unique fields
        all_fields = set()
        for doc in documents:
            all_fields.update(doc.keys())
        all_fields.discard('_id')
        field_list = sorted(all_fields)
        
        # Build summary
        summary = f"""DATABASE COLLECTION SUMMARY: {collection_name}
Total number of documents/records: {total_docs}
Total number of registered entries: {total_docs}
Number of fields: {len(field_list)}

Fields: {', '.join(field_list)}

IMPORTANT FACTS:
- This collection "{collection_name}" contains EXACTLY {total_docs} documents/records.
- When asked "how many" records are in {collection_name}, the answer is {total_docs}.
"""
        
        # Build data chunks
        DOCS_PER_CHUNK = 10
        data_chunks = []
        
        for batch_start in range(0, len(documents), DOCS_PER_CHUNK):
            batch_end = min(batch_start + DOCS_PER_CHUNK, len(documents))
            batch_docs = documents[batch_start:batch_end]
            
            chunk_header = f"[Collection: {collection_name} | Documents {batch_start + 1}-{batch_end} of {total_docs} total]"
            
            doc_texts = []
            for idx, doc in enumerate(batch_docs, batch_start + 1):
                doc_text = " | ".join([f"{k}: {v}" for k, v in doc.items() if k != '_id'])
                doc_texts.append(f"Document {idx}: {doc_text}")
            
            chunk_text = f"{chunk_header}\n\n" + "\n".join(doc_texts)
            data_chunks.append(chunk_text)
        
        return {
            "summary": summary,
            "data_chunks": data_chunks,
            "total_rows": total_docs,
            "columns": field_list
        }
    
    # ── Main Connect & Index Pipeline ────────────────────────────────────
    
    async def connect_and_index(self, config: DatabaseConnectionRequest) -> DatabaseConnectionInfo:
        """Connect to database and index its content with precision"""
        conn_id = str(uuid.uuid4())
        
        conn_info = DatabaseConnectionInfo(
            id=conn_id,
            connection_name=config.connection_name,
            db_type=config.db_type,
            host=config.host,
            port=config.port,
            database=config.database,
            status=ProcessingStatus.PROCESSING
        )
        
        try:
            total_tables = 0
            
            if config.db_type == DatabaseType.MYSQL:
                connection = self._connect_mysql(config)
                tables = self._get_sql_tables(connection, config.db_type, config.tables)
                
                for table in tables:
                    structured = self._sql_table_to_structured_text(connection, table, config.db_type)
                    await self._index_structured_content(structured, config.connection_name, table, conn_id)
                    total_tables += 1
                
                connection.close()
                
            elif config.db_type == DatabaseType.POSTGRESQL:
                connection = self._connect_postgresql(config)
                tables = self._get_sql_tables(connection, config.db_type, config.tables)
                
                for table in tables:
                    structured = self._sql_table_to_structured_text(connection, table, config.db_type)
                    await self._index_structured_content(structured, config.connection_name, table, conn_id)
                    total_tables += 1
                
                connection.close()
                
            elif config.db_type == DatabaseType.SQLITE:
                connection = self._connect_sqlite(config)
                tables = self._get_sql_tables(connection, config.db_type, config.tables)
                
                for table in tables:
                    structured = self._sql_table_to_structured_text(connection, table, config.db_type)
                    await self._index_structured_content(structured, config.connection_name, table, conn_id)
                    total_tables += 1
                
                connection.close()
                
            elif config.db_type == DatabaseType.MONGODB:
                db = self._connect_mongodb(config)
                collections = self._get_mongodb_collections(db, config.tables)
                
                for collection in collections:
                    structured = self._mongodb_collection_to_structured_text(db, collection)
                    await self._index_structured_content(structured, config.connection_name, collection, conn_id)
                    total_tables += 1
            
            conn_info.table_count = total_tables
            conn_info.status = ProcessingStatus.COMPLETED
            conn_info.indexed_date = datetime.now()
            self.connections[conn_id] = conn_info
            
            # Persist to disk so connections survive backend restarts
            self._save_connections()
            
            print(f"✅ Database indexed: {config.connection_name} ({total_tables} tables)")
            
        except Exception as e:
            conn_info.status = ProcessingStatus.FAILED
            print(f"❌ Database connection failed: {config.connection_name} - {e}")
            raise
        
        return conn_info
    
    # ── Precision Indexing ───────────────────────────────────────────────
    
    async def _index_structured_content(self, structured: Dict[str, Any], db_name: str, table_name: str, conn_id: str):
        """
        Index database content with a summary-first approach.
        
        Creates:
        1. A SUMMARY chunk — contains exact row count, schema, and aggregate facts.
           This is the primary chunk retrieved for count/aggregate questions.
        2. DATA chunks — contain the actual row data in groups of 10.
           These are retrieved for specific data lookup questions.
        """
        base_metadata = {
            "document_id": f"db_{conn_id}_{table_name}",
            "filename": f"{db_name} - {table_name}",
            "file_type": "database",
            "source": "database",
            "database_name": db_name,
            "table_name": table_name,
            "total_rows": structured["total_rows"],
            "indexed_date": datetime.now().isoformat()
        }
        
        all_chunks = []
        
        # 1. SUMMARY CHUNK — highest priority for aggregate queries
        summary_metadata = base_metadata.copy()
        summary_metadata["chunk_type"] = "table_summary"
        summary_metadata["chunk_index"] = 0
        summary_metadata["total_chunks"] = len(structured["data_chunks"]) + 1
        
        all_chunks.append(LangChainDocument(
            page_content=structured["summary"],
            metadata=summary_metadata
        ))
        
        # 2. DATA CHUNKS — for specific row-level queries
        for i, data_chunk in enumerate(structured["data_chunks"]):
            data_metadata = base_metadata.copy()
            data_metadata["chunk_type"] = "table_data"
            data_metadata["chunk_index"] = i + 1
            data_metadata["total_chunks"] = len(structured["data_chunks"]) + 1
            
            all_chunks.append(LangChainDocument(
                page_content=data_chunk,
                metadata=data_metadata
            ))
        
        # Store all chunks in vector store
        if self.document_processor.vector_store is None:
            from langchain_pinecone import PineconeVectorStore
            self.document_processor.vector_store = PineconeVectorStore.from_documents(
                all_chunks, 
                self.document_processor.embeddings,
                index_name=settings.PINECONE_INDEX_NAME
            )
        else:
            self.document_processor.vector_store.add_documents(all_chunks)
        
        print(f"✅ Indexed {table_name}: 1 summary + {len(structured['data_chunks'])} data chunks ({structured['total_rows']} rows)")
    
    def list_connections(self) -> List[DatabaseConnectionInfo]:
        """List all database connections"""
        return list(self.connections.values())
    
    def get_connection_count(self) -> int:
        """Get total number of connected databases"""
        return len(self.connections)
        
    async def delete_connection(self, conn_id: str):
        """Remove a database connection and its indexed Pinecone vectors"""
        if conn_id not in self.connections:
            raise KeyError(f"Connection {conn_id} not found")
            
        conn_info = self.connections[conn_id]
        
        # Delete from Pinecone using the correct Pinecone client
        if self.document_processor.vector_store and hasattr(self.document_processor, 'pc'):
            try:
                from config import settings
                index = self.document_processor.pc.Index(settings.PINECONE_INDEX_NAME)
                # Delete all vectors indexed for this database connection
                index.delete(filter={"source": "database", "database_name": conn_info.connection_name})
                print(f"✅ Purged Pinecone vectors for database: {conn_info.connection_name}")
            except Exception as e:
                print(f"⚠️ Failed to delete database vectors from Pinecone: {e}")
                
        # Remove from internal state
        del self.connections[conn_id]
        self._save_connections()
        print(f"🧹 Removed database connection: {conn_info.connection_name}")
