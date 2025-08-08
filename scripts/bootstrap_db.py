#!/usr/bin/env python3
"""
Database Bootstrap Script
Seeds the News AI database with initial data from configuration files.
"""

import os
import json
import psycopg
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

def get_db_connection():
    """Create database connection"""
    return psycopg.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        dbname=os.getenv('POSTGRES_DB', 'news_ai'),
        user=os.getenv('POSTGRES_USER', 'news_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'news_password')
    )

def load_feeds_data():
    """Load RSS feeds from data/feeds.json"""
    feeds_file = Path('data/feeds.json')
    if not feeds_file.exists():
        print(f"❌ Feeds file not found: {feeds_file}")
        return []
    
    with open(feeds_file, 'r') as f:
        data = json.load(f)
        return data.get('feeds', [])

def seed_feeds(conn):
    """Seed RSS feeds table"""
    feeds = load_feeds_data()
    if not feeds:
        print("⚠️  No feeds data to seed")
        return
    
    print(f"📡 Seeding {len(feeds)} RSS feeds...")
    
    with conn.cursor() as cur:
        # Clear existing feeds (optional)
        cur.execute("DELETE FROM feeds WHERE id LIKE 'seed_%'")
        
        # Insert feeds
        for feed in feeds:
            cur.execute("""
                INSERT INTO feeds (
                    id, name, url, country, language, category, 
                    leaning, weight, enabled, fetch_interval
                ) VALUES (
                    %(id)s, %(name)s, %(url)s, %(country)s, %(language)s, 
                    %(category)s, %(leaning)s, %(weight)s, %(enabled)s, %(fetch_interval)s
                )
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    url = EXCLUDED.url,
                    country = EXCLUDED.country,
                    language = EXCLUDED.language,
                    category = EXCLUDED.category,
                    leaning = EXCLUDED.leaning,
                    weight = EXCLUDED.weight,
                    enabled = EXCLUDED.enabled,
                    fetch_interval = EXCLUDED.fetch_interval,
                    updated_at = NOW()
            """, feed)
        
        conn.commit()
        print(f"✅ Successfully seeded {len(feeds)} feeds")

def seed_sample_headlines(conn):
    """Seed sample headlines for testing"""
    print("📰 Seeding sample headlines...")
    
    sample_headlines = [
        {
            'feed_id': 'bbc_world',
            'title': 'Global Climate Summit Reaches Historic Agreement',
            'description': 'World leaders agree on ambitious climate action plan',
            'url': 'https://example.com/climate-summit',
            'language': 'en',
        },
        {
            'feed_id': 'cnn_world', 
            'title': 'Tech Giants Announce AI Safety Initiative',
            'description': 'Major technology companies collaborate on AI safety standards',
            'url': 'https://example.com/ai-safety',
            'language': 'en',
        },
        {
            'feed_id': 'reuters_world',
            'title': 'Economic Markets Show Strong Recovery Signs',
            'description': 'Global markets demonstrate resilience amid challenges',
            'url': 'https://example.com/market-recovery',
            'language': 'en',
        }
    ]
    
    with conn.cursor() as cur:
        for headline in sample_headlines:
            cur.execute("""
                INSERT INTO headlines (
                    feed_id, title, description, url, language, published_at
                ) VALUES (
                    %(feed_id)s, %(title)s, %(description)s, %(url)s, %(language)s, NOW()
                )
                ON CONFLICT (url, feed_id) DO NOTHING
            """, headline)
        
        conn.commit()
        print(f"✅ Successfully seeded {len(sample_headlines)} sample headlines")

def seed_sample_classifications(conn):
    """Seed sample topic classifications"""
    print("🎯 Seeding sample classifications...")
    
    with conn.cursor() as cur:
        # Get headline IDs
        cur.execute("SELECT id FROM headlines LIMIT 3")
        headline_ids = [row[0] for row in cur.fetchall()]
        
        classifications = [
            # Climate summit - environment, politics, world
            (headline_ids[0] if len(headline_ids) > 0 else None, 'environment', 0.92, 1),
            (headline_ids[0] if len(headline_ids) > 0 else None, 'politics', 0.78, 2),
            (headline_ids[0] if len(headline_ids) > 0 else None, 'world', 0.85, 3),
            
            # AI safety - technology, business, science  
            (headline_ids[1] if len(headline_ids) > 1 else None, 'technology', 0.95, 1),
            (headline_ids[1] if len(headline_ids) > 1 else None, 'business', 0.82, 2),
            (headline_ids[1] if len(headline_ids) > 1 else None, 'science', 0.73, 3),
            
            # Markets - economy, business, world
            (headline_ids[2] if len(headline_ids) > 2 else None, 'economy', 0.91, 1),
            (headline_ids[2] if len(headline_ids) > 2 else None, 'business', 0.88, 2),
            (headline_ids[2] if len(headline_ids) > 2 else None, 'world', 0.65, 3),
        ]
        
        for headline_id, topic, confidence, rank in classifications:
            if headline_id:
                cur.execute("""
                    INSERT INTO topic_classifications (
                        headline_id, topic, confidence, rank, model_version
                    ) VALUES (
                        %s, %s, %s, %s, 'facebook/bart-large-mnli'
                    )
                    ON CONFLICT (headline_id, topic, rank) DO NOTHING
                """, (headline_id, topic, confidence, rank))
        
        conn.commit()
        print(f"✅ Successfully seeded {len(classifications)} classifications")

def check_database_status(conn):
    """Check database tables and content"""
    print("\n📊 Database Status:")
    
    tables = [
        ('feeds', 'RSS feeds'),
        ('headlines', 'news headlines'),
        ('topic_classifications', 'topic classifications'),
        ('events', 'extracted events'),
        ('event_groups', 'event groups'),
        ('embeddings', 'vector embeddings')
    ]
    
    with conn.cursor() as cur:
        for table, description in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                print(f"   📋 {description}: {count} records")
            except psycopg.Error as e:
                print(f"   ❌ {description}: Error - {e}")

def main():
    """Main bootstrap function"""
    print("🚀 Starting News AI Database Bootstrap")
    print("=" * 50)
    
    try:
        # Connect to database
        print("🔌 Connecting to database...")
        with get_db_connection() as conn:
            print("✅ Database connection successful")
            
            # Seed data
            seed_feeds(conn)
            seed_sample_headlines(conn)
            seed_sample_classifications(conn)
            
            # Check status
            check_database_status(conn)
            
        print("\n🎉 Database bootstrap completed successfully!")
        print("\n🎯 Next steps:")
        print("   1. Start the NLP service: make dev-nlp")
        print("   2. Start the API gateway: make dev-api") 
        print("   3. Start the frontend: make dev-frontend")
        print("   4. Visit http://localhost:3000")
        
    except psycopg.Error as e:
        print(f"❌ Database error: {e}")
        print("💡 Make sure PostgreSQL is running and credentials are correct")
        return 1
        
    except Exception as e:
        print(f"❌ Bootstrap error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 