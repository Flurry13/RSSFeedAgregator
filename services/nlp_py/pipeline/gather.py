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

Dependencies:
- feedparser: For RSS feed parsing
- json: For configuration file loading
- os: For file path operations
- time: For potential rate limiting (future enhancement)

Usage:
    python gather.py                    # Run standalone
    from gather import gather          # Import as module
"""

import json
import os
import feedparser
import time

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

def gather():
    """
    Gather headlines from all configured RSS feeds.
    
    This function iterates through all configured RSS feeds, parses each one,
    and extracts headline information. Each headline is enriched with metadata
    from the feed configuration (language, source, group, country).
    
    The function includes error handling to ensure that if one feed fails,
    the others can still be processed successfully.
    
    Returns:
        list: List of headline dictionaries, each containing:
            - title: The headline text
            - link: URL to the full article
            - language: Language code (e.g., 'en', 'es')
            - source: Name of the RSS feed source
            - group: Category/group of the feed
            - country: Country code for the feed source
            
    Note:
        If a feed fails to parse, an error message is printed but processing
        continues with the remaining feeds. This ensures robustness.
    """
    headlines = []
    
    # Process each configured RSS feed
    for item in feedList:
        try:
            # Parse the RSS feed using feedparser
            # This handles various RSS formats and provides a unified interface
            feed = feedparser.parse(item['url'])
            
            # Extract headlines from each entry in the feed
            for entry in feed.entries:
                # Create a structured headline object with metadata
                # Use getattr with defaults to handle missing attributes gracefully
                headline = {
                    'title': getattr(entry, 'title', 'No title'),      # Headline text
                    'link': getattr(entry, 'link', 'No link'),         # Article URL
                    'language': item['language'],                       # Feed language
                    'source': item['name'],                            # Source name
                    'group': item['group'],                            # Feed category
                    'country': item['country']                         # Source country
                }
                headlines.append(headline)
                
        except Exception as e:
            # Log error but continue processing other feeds
            # This ensures that a single feed failure doesn't stop the entire process
            print(f"Error processing {item['name']}: {str(e)}")
            continue
    
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