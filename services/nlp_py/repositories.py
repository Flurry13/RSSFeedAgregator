"""
Data access layer for database operations
Repository pattern for clean separation of concerns
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
import hashlib
from database import get_db_cursor

class HeadlineRepository:
    """Repository for headline database operations"""
    
    @staticmethod
    def _generate_url_hash(url: str, feed_id: str) -> str:
        """Generate hash for URL deduplication"""
        combined = f"{url}:{feed_id}"
        return hashlib.sha256(combined.encode()).hexdigest()[:32]
    
    @staticmethod
    def insert_headline(headline: Dict[str, Any], feed_id: str = None) -> Optional[str]:
        """
        Insert a single headline into database
        
        Args:
            headline: Headline dictionary with title, url, language, etc.
            feed_id: Optional feed_id (uses source name if not provided)
            
        Returns:
            UUID of inserted headline or None if duplicate
        """
        try:
            # Use source name as feed_id if not provided
            if feed_id is None:
                feed_id = headline.get('source', 'unknown')
            
            with get_db_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO headlines (
                        feed_id, title, url, language, 
                        published_at, created_at, updated_at
                    ) VALUES (
                        %(feed_id)s, %(title)s, %(url)s, %(language)s,
                        %(published_at)s, NOW(), NOW()
                    )
                    ON CONFLICT (url, feed_id) DO NOTHING
                    RETURNING id
                """, {
                    'feed_id': feed_id,
                    'title': headline.get('title'),
                    'url': headline.get('link'),
                    'language': headline.get('language', 'en'),
                    'published_at': headline.get('published') or None,
                })
                
                result = cursor.fetchone()
                if result:
                    return str(result['id'])
                return None  # Duplicate
                
        except Exception as e:
            print(f"❌ Error inserting headline: {e}")
            return None
    
    @staticmethod
    def bulk_insert_headlines(headlines: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Bulk insert headlines with deduplication
        
        Args:
            headlines: List of headline dictionaries
            
        Returns:
            Dict with 'inserted' and 'duplicates' counts
        """
        inserted = 0
        duplicates = 0
        errors = 0
        
        try:
            with get_db_cursor() as cursor:
                for headline in headlines:
                    try:
                        feed_id = headline.get('source', 'unknown')
                        
                        cursor.execute("""
                            INSERT INTO headlines (
                                feed_id, title, url, language, 
                                published_at, created_at, updated_at
                            ) VALUES (
                                %(feed_id)s, %(title)s, %(url)s, %(language)s,
                                %(published_at)s, NOW(), NOW()
                            )
                            ON CONFLICT (url, feed_id) DO NOTHING
                            RETURNING id
                        """, {
                            'feed_id': feed_id,
                            'title': headline.get('title'),
                            'url': headline.get('link'),
                            'language': headline.get('language', 'en'),
                            'published_at': headline.get('published') or None,
                        })
                        
                        result = cursor.fetchone()
                        if result:
                            inserted += 1
                        else:
                            duplicates += 1
                            
                    except Exception as e:
                        errors += 1
                        print(f"⚠️  Error inserting headline: {e}")
                        continue
            
            print(f"📊 Bulk insert complete: {inserted} new, {duplicates} duplicates, {errors} errors")
            return {'inserted': inserted, 'duplicates': duplicates, 'errors': errors}
            
        except Exception as e:
            print(f"❌ Bulk insert failed: {e}")
            return {'inserted': 0, 'duplicates': 0, 'errors': len(headlines)}
    
    @staticmethod
    def get_recent_headlines(limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Fetch recent headlines from database
        
        Args:
            limit: Maximum number of headlines to return
            offset: Number of headlines to skip
            
        Returns:
            List of headline dictionaries
        """
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        id, feed_id as source, title, url as link,
                        language, published_at as published,
                        translated_title, created_at
                    FROM headlines
                    ORDER BY created_at DESC
                    LIMIT %(limit)s OFFSET %(offset)s
                """, {'limit': limit, 'offset': offset})
                
                results = cursor.fetchall()
                return [dict(row) for row in results]
                
        except Exception as e:
            print(f"❌ Error fetching headlines: {e}")
            return []
    
    @staticmethod
    def get_headline_count() -> int:
        """Get total number of headlines in database"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM headlines")
                result = cursor.fetchone()
                return result['count'] if result else 0
        except Exception as e:
            print(f"❌ Error counting headlines: {e}")
            return 0
    
    @staticmethod
    def update_translation(headline_id: str, translated_title: str) -> bool:
        """
        Update headline with translation
        
        Args:
            headline_id: UUID of headline
            translated_title: Translated text
            
        Returns:
            True if successful
        """
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    UPDATE headlines
                    SET translated_title = %(translated_title)s,
                        updated_at = NOW()
                    WHERE id = %(id)s
                """, {
                    'id': headline_id,
                    'translated_title': translated_title
                })
                return True
        except Exception as e:
            print(f"❌ Error updating translation: {e}")
            return False


class FeedRepository:
    """Repository for feed management operations"""
    
    @staticmethod
    def get_all_feeds() -> List[Dict]:
        """Get all feeds from database"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT id, name, url, country, language, 
                           category, enabled, last_fetched
                    FROM feeds
                    WHERE enabled = true
                    ORDER BY name
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"❌ Error fetching feeds: {e}")
            return []
    
    @staticmethod
    def update_feed_last_fetched(feed_id: str, error_message: str = None) -> bool:
        """Update feed last_fetched timestamp"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    UPDATE feeds
                    SET last_fetched = NOW(),
                        last_error = %(error)s,
                        updated_at = NOW()
                    WHERE id = %(id)s
                """, {'id': feed_id, 'error': error_message})
                return True
        except Exception as e:
            print(f"❌ Error updating feed: {e}")
            return False

