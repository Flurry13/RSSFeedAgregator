#!/usr/bin/env python3
"""
RSS Feed Gathering Module
=========================

This module provides functionality to gather news headlines from multiple RSS feeds.
It loads feed configurations from a JSON file, parses RSS feeds, and extracts
structured headline data including titles, links, and metadata.

Features:
- Load RSS feed configurations from JSON
- Parse multiple RSS feeds concurrently
- Extract structured headline data
- Error handling for individual feed failures
- Metadata enrichment (language, source, group, country)
- Timeout protection for problematic feeds
- Blacklist for feeds that cause hanging

Dependencies:
- feedparser: For RSS feed parsing
- json: For configuration file loading
- os: For file path operations
- time: For potential rate limiting (future enhancement)
- threading: For timeout protection

Usage:
    python gather.py                    # Run standalone
    from gather import gather          # Import as module
"""

import json
import os
import feedparser
import time
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen
from urllib.error import URLError

# Load feeds from JSON file
def load_feeds():
    """
    Load RSS feed configurations from the project's data/feeds.json file.
    
    This function navigates from the current pipeline directory to the project root,
    then loads the feeds configuration file. The feeds.json should contain an array
    of feed objects with the following structure:
    
    {
        "feeds": [
            {
                "name": "Feed Display Name",
                "url": "https://example.com/rss",
                "language": "en",
                "group": "news",
                "country": "US"
            }
        ]
    }
    
    Returns:
        list: List of feed configuration dictionaries
        
    Raises:
        FileNotFoundError: If feeds.json doesn't exist
        json.JSONDecodeError: If feeds.json is malformed
    """
    # Get the current file's directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Navigate to project root (3 levels up: pipeline -> nlp_py -> services -> RSSFeed2)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    
    # Construct path to feeds configuration file
    feeds_path = os.path.join(project_root, 'data', 'feeds.json')
    
    # Load and parse the JSON configuration file
    with open(feeds_path, 'r') as f:
        data = json.load(f)
        # Return the feeds array, or empty list if 'feeds' key doesn't exist
        return data.get('feeds', [])

# Load feed configurations at module import time
# This ensures feeds are available immediately when the module is imported
feedList = load_feeds()

def load_feeds_from_db():
    """Load active feed sources from the database."""
    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from repositories import SourceRepository
        sources = SourceRepository.get_all(active_only=True)
        return [
            {
                "id": s["id"],
                "name": s["name"],
                "url": s["url"],
                "language": s.get("language", "en"),
                "country": s.get("country", ""),
                "group": s.get("group_name", ""),
            }
            for s in sources
        ]
    except Exception:
        return None

# Blacklist of problematic feeds that cause hanging
PROBLEMATIC_FEEDS = ['CBC News Politics']

def parse_feed_with_timeout(url, timeout=30):
    """Parse feed with timeout using threading"""
    result = [None]
    exception = [None]
    
    def parse_feed():
        try:
            result[0] = feedparser.parse(url)
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=parse_feed)
    thread.daemon = True
    thread.start()
    thread.join(timeout)
    
    if thread.is_alive():
        print(f"Timeout parsing feed: {url}")
        return None
    
    if exception[0]:
        print(f"Error parsing feed: {url} - {str(exception[0])}")
        return None
    
    return result[0]

def _extract_published(entry) -> str:
    """Return ISO8601-like published timestamp if available, else empty string."""
    try:
        ts = getattr(entry, 'published_parsed', None) or getattr(entry, 'updated_parsed', None)
        if ts:
            return time.strftime('%Y-%m-%dT%H:%M:%SZ', ts)
        s = getattr(entry, 'published', None) or getattr(entry, 'updated', None)
        return s or ''
    except Exception:
        return ''

def process_single_feed(feed_item, feed_index, total_feeds):
    """
    Process a single RSS feed and return headlines.
    Extracted from gather() for parallel processing.
    
    Args:
        feed_item: Feed configuration dictionary
        feed_index: Index of this feed (for progress reporting)
        total_feeds: Total number of feeds being processed
        
    Returns:
        tuple: (headlines_list, feed_name, success_bool)
    """
    headlines = []
    
    try:
        print(f"Processing {feed_index}/{total_feeds}: {feed_item['name']}")
        
        # Skip problematic feeds
        if feed_item['name'] in PROBLEMATIC_FEEDS:
            print(f"Skipping problematic feed: {feed_item['name']}")
            return (headlines, feed_item['name'], False)
        
        # Use timeout wrapper for feed parsing
        feed = parse_feed_with_timeout(feed_item['url'], timeout=15)
        
        if feed is None:
            print(f"Skipping {feed_item['name']} due to parsing issues")
            return (headlines, feed_item['name'], False)
        
        # Check if feed parsing was successful
        if hasattr(feed, 'status') and feed.status != 200:
            print(f"Warning: Feed {feed_item['name']} returned status {feed.status}")
        
        # Check if entries exist
        if not hasattr(feed, 'entries') or not feed.entries:
            print(f"Warning: No entries found in {feed_item['name']}")
            return (headlines, feed_item['name'], False)
        
        entry_count = 0
        for entry in feed.entries:
            try:
                # More robust attribute extraction with CDATA handling
                title = getattr(entry, 'title', None)
                link = getattr(entry, 'link', None)
                
                # Clean CDATA content if present
                if title and isinstance(title, str):
                    title = title.strip()
                    # Remove any remaining CDATA markers
                    if title.startswith('<![CDATA[') and title.endswith(']]>'):
                        title = title[9:-3].strip()
                
                if link and isinstance(link, str):
                    link = link.strip()
                
                # Skip entries without essential data
                if not title or not link:
                    continue
                
                headline = {
                    'title': title,
                    'link': link,
                    'language': feed_item['language'],
                    'source': feed_item['name'],
                    'group': feed_item['group'],
                    'country': feed_item['country'],
                    'published': _extract_published(entry),
                    'source_id': feed_item.get('id'),
                }
                headlines.append(headline)
                entry_count += 1
                
            except Exception as entry_error:
                print(f"Error processing entry in {feed_item['name']}: {str(entry_error)}")
                continue
        
        print(f"Added {entry_count} headlines from {feed_item['name']}")
        return (headlines, feed_item['name'], True)
        
    except Exception as e:
        # Log error but return empty list
        print(f"Error processing {feed_item['name']}: {str(e)}")
        return (headlines, feed_item['name'], False)

async def gather_feed_async(feed_item, feed_index, total_feeds, executor):
    """
    Async wrapper for processing a single feed.
    
    Args:
        feed_item: Feed configuration dictionary
        feed_index: Index of this feed
        total_feeds: Total number of feeds
        executor: ThreadPoolExecutor for running blocking operations
        
    Returns:
        tuple: (headlines_list, feed_name, success_bool)
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor,
        process_single_feed,
        feed_item,
        feed_index,
        total_feeds
    )

async def gather_all_feeds_async(feeds, max_concurrent=20):
    """
    Gather headlines from all feeds concurrently.
    
    Args:
        feeds: List of feed configuration dictionaries
        max_concurrent: Maximum number of concurrent feed fetches
        
    Returns:
        list: Combined list of all headlines
    """
    total_feeds = len(feeds)
    all_headlines = []
    
    print(f"🚀 Starting parallel RSS gathering for {total_feeds} feeds (max {max_concurrent} concurrent)")
    start_time = time.time()
    
    # Create thread pool executor for blocking operations
    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        # Create tasks for all feeds
        tasks = [
            gather_feed_async(feed, idx + 1, total_feeds, executor)
            for idx, feed in enumerate(feeds)
        ]
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    success_count = 0
    error_count = 0
    
    for result in results:
        if isinstance(result, Exception):
            print(f"❌ Task failed with exception: {str(result)}")
            error_count += 1
            continue
        
        headlines, feed_name, success = result
        if success:
            all_headlines.extend(headlines)
            success_count += 1
        else:
            error_count += 1
    
    elapsed_time = time.time() - start_time
    
    print(f"✅ Parallel gathering completed in {elapsed_time:.2f}s")
    print(f"📊 Success: {success_count}/{total_feeds} feeds, Errors: {error_count}")
    print(f"📰 Total headlines collected: {len(all_headlines)}")
    
    return all_headlines

def gather(use_async=True, max_concurrent=20):
    """
    Gather headlines from all configured RSS feeds.
    
    This function processes RSS feeds either sequentially (legacy) or in parallel (optimized).
    Each headline is enriched with metadata from the feed configuration.
    
    Args:
        use_async: If True, use parallel async processing. If False, use sequential (default: True)
        max_concurrent: Maximum number of concurrent feed fetches when using async (default: 20)
    
    Returns:
        list: List of headline dictionaries, each containing:
            - title: The headline text
            - link: URL to the full article
            - language: Language code (e.g., 'en', 'es')
            - source: Name of the RSS feed source
            - group: Category/group of the feed
            - country: Country code for the feed source
            - published: ISO8601 string or feed-provided date string
            
    Note:
        If a feed fails to parse, an error message is printed but processing
        continues with the remaining feeds. This ensures robustness.
    """
    db_feeds = load_feeds_from_db()
    feeds = db_feeds if db_feeds is not None else feedList

    if use_async:
        # Use new parallel async implementation
        try:
            # Check if we're already in an event loop
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, create task
                return asyncio.create_task(gather_all_feeds_async(feeds, max_concurrent))
            except RuntimeError:
                # No event loop, create one
                return asyncio.run(gather_all_feeds_async(feeds, max_concurrent))
        except Exception as e:
            print(f"⚠️  Async gathering failed: {str(e)}, falling back to sequential")
            use_async = False

    # Legacy sequential implementation (fallback)
    if not use_async:
        print("Using sequential RSS gathering (legacy mode)")
        headlines = []
        total_feeds = len(feeds)

        for feed_index, item in enumerate(feeds, 1):
            result_headlines, feed_name, success = process_single_feed(item, feed_index, total_feeds)
            headlines.extend(result_headlines)

        print(f"Total headlines collected: {len(headlines)}")
        return headlines

# Main execution block - runs when script is executed directly
if __name__ == "__main__":
    # Gather headlines from all configured feeds
    result = gather()
    
    # Display summary statistics
    print(f"Collected {len(result)} headlines")
    
    # Show first few headlines as examples for verification
    # This helps users quickly verify that the gathering process worked correctly
    print("\nSample headlines:")
    for i, headline in enumerate(result[:5]):
        print(f"{i+1}. {headline['title']} ({headline['source']}, {headline['language']})")
    
    # Future enhancement: Add more detailed output options
    # - Export to JSON/CSV
    # - Filter by language/group/country
    # - Deduplication
    # - Rate limiting between requests