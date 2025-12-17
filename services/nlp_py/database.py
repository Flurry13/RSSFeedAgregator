"""
Database connection and session management for PostgreSQL
"""

import os
from contextlib import contextmanager
from typing import Generator
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'news_ai'),
    'user': os.getenv('POSTGRES_USER', 'news_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'news_password'),
}

# Connection pool
connection_pool = None

def init_connection_pool(min_conn=2, max_conn=20):
    """
    Initialize PostgreSQL connection pool
    
    Args:
        min_conn: Minimum number of connections in pool
        max_conn: Maximum number of connections in pool
    """
    global connection_pool
    
    try:
        connection_pool = psycopg2.pool.SimpleConnectionPool(
            min_conn,
            max_conn,
            **DB_CONFIG
        )
        
        if connection_pool:
            print(f"✅ Database connection pool created ({min_conn}-{max_conn} connections)")
            return True
        
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"❌ Error creating connection pool: {error}")
        return False

def close_connection_pool():
    """Close all connections in the pool"""
    global connection_pool
    
    if connection_pool:
        connection_pool.closeall()
        print("✅ Connection pool closed")

@contextmanager
def get_db_connection() -> Generator:
    """
    Context manager for database connections from pool
    
    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM headlines")
    """
    global connection_pool
    
    if connection_pool is None:
        init_connection_pool()
    
    conn = None
    try:
        conn = connection_pool.getconn()
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            connection_pool.putconn(conn)

@contextmanager
def get_db_cursor(dict_cursor=True) -> Generator:
    """
    Context manager for database cursor with automatic connection handling
    
    Args:
        dict_cursor: If True, return RealDictCursor (results as dicts)
    
    Usage:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM headlines")
            results = cursor.fetchall()
    """
    with get_db_connection() as conn:
        cursor_class = RealDictCursor if dict_cursor else None
        cursor = conn.cursor(cursor_factory=cursor_class)
        try:
            yield cursor
        finally:
            cursor.close()

def test_connection():
    """Test database connection"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute('SELECT version()')
            version = cursor.fetchone()
            print(f"✅ Database connection successful")
            print(f"   PostgreSQL version: {version['version']}")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

# Initialize pool on module import
if __name__ != "__main__":
    init_connection_pool()

