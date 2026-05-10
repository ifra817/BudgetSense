"""
MongoDB Connection Management
Demonstrates: Connection Pooling, Error Handling, Singleton Pattern
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import os
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

class MongoDBConnection:
    """
    Singleton class for MongoDB connection management
    Ensures only one connection is maintained throughout the application
    """
    
    _instance = None
    _client = None
    _db = None
    
    def __new__(cls):
        """Singleton pattern - create only one instance"""
        if cls._instance is None:
            cls._instance = super(MongoDBConnection, cls).__new__(cls)
        return cls._instance
    
    def connect(self):
        """
        Establish MongoDB connection
        Implements connection pooling and error handling
        """
        try:
            mongo_uri = os.getenv('MONGO_URI')
            
            if not mongo_uri:
                raise ValueError("MONGO_URI not found in environment variables")
            
            # Connection with pooling parameters
            self._client = MongoClient(
                mongo_uri,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=10000,          # 10 second connection timeout
                maxPoolSize=50,                  # Connection pool size
                minPoolSize=10                   # Minimum pool size
            )
            
            # Verify connection with ping
            self._client.admin.command('ping')
            
            # Get database instance
            self._db = self._client['budgetsense']
            
            logger.info("✅ Successfully connected to MongoDB Atlas")
            return True
            
        except ConnectionFailure as e:
            logger.error(f"❌ MongoDB Connection Failed: {e}")
            return False
        except ServerSelectionTimeoutError as e: # type: ignore
            logger.error(f"❌ MongoDB Server Selection Timeout: {e}")
            return False
        except ValueError as e:
            logger.error(f"❌ Configuration Error: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error connecting to MongoDB: {e}")
            return False
    
    def get_database(self):
        """Get database instance"""
        if self._db is None:
            self.connect()
        return self._db
    
    def get_client(self):
        """Get MongoDB client instance"""
        if self._client is None:
            self.connect()
        return self._client
    
    def close_connection(self):
        """Close MongoDB connection"""
        try:
            if self._client:
                self._client.close()
                logger.info("✅ MongoDB connection closed")
        except Exception as e:
            logger.error(f"❌ Error closing MongoDB connection: {e}")
    
    def get_collection(self, collection_name):
        """
        Get a specific collection
        
        Args:
            collection_name (str): Name of the collection
            
        Returns:
            pymongo collection object
        """
        db = self.get_database()
        return db[collection_name] # type: ignore

# Create singleton instance
mongodb = MongoDBConnection()

# Export for use in routes
def init_db(app=None):
    """
    Initialize database connection
    Call this in app.py during Flask app initialization
    """
    mongodb.connect()
    

def get_db():
    """Get database instance - use this in your routes"""
    return mongodb.get_database()

def get_collection(collection_name):
    """Get a specific collection - use this in your routes"""
    return mongodb.get_collection(collection_name)