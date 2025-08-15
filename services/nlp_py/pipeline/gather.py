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

def gather():
    """
    Gather headlines from all configured RSS feeds.
    
    This function iterates through all configured RSS feeds, parses each one,
    and extracts headline information. Each headline is enriched with metadata
    from the feed configuration (language, source, group, country).
    
    The function includes error handling to ensure that if one feed fails,
    the others can still be processed successfully. It also includes timeout
    protection and blacklist functionality for problematic feeds.
    
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
    headlines = []
    total_feeds = len(feedList)
    
    for feed_index, item in enumerate(feedList, 1):
        try:
            print(f"Processing {feed_index}/{total_feeds}: {item['name']}")
            
            # Skip problematic feeds
            if item['name'] in PROBLEMATIC_FEEDS:
                print(f"Skipping problematic feed: {item['name']}")
                continue
            
            # Use timeout wrapper for feed parsing
            feed = parse_feed_with_timeout(item['url'], timeout=15)
            
            if feed is None:
                print(f"Skipping {item['name']} due to parsing issues")
                continue
            
            # Check if feed parsing was successful
            if hasattr(feed, 'status') and feed.status != 200:
                print(f"Warning: Feed {item['name']} returned status {feed.status}")
            
            # Check if entries exist
            if not hasattr(feed, 'entries') or not feed.entries:
                print(f"Warning: No entries found in {item['name']}")
                continue
            
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
                        'language': item['language'],
                        'source': item['name'],
                        'group': item['group'],
                        'country': item['country'],
                        'published': _extract_published(entry),
                    }
                    headlines.append(headline)
                    entry_count += 1
                    
                except Exception as entry_error:
                    print(f"Error processing entry in {item['name']}: {str(entry_error)}")
                    continue
            
            print(f"Added {entry_count} headlines from {item['name']}")
            
        except Exception as e:
            # Log error but continue processing other feeds
            # This ensures that a single feed failure doesn't stop the entire process
            print(f"Error processing {item['name']}: {str(e)}")
            continue
    
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