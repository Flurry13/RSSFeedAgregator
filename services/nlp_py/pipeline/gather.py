import json
import os
import feedparser
import time
import threading
from urllib.request import urlopen
from urllib.error import URLError

# Load feeds from JSON file
def load_feeds():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    feeds_path = os.path.join(project_root, 'data', 'feeds.json')
    
    with open(feeds_path, 'r') as f:
        data = json.load(f)
        return data.get('feeds', [])

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

def gather():
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
                        'country': item['country']
                    }
                    headlines.append(headline)
                    entry_count += 1
                    
                except Exception as entry_error:
                    print(f"Error processing entry in {item['name']}: {str(entry_error)}")
                    continue
            
            print(f"Added {entry_count} headlines from {item['name']}")
            
        except Exception as e:
            print(f"Error processing {item['name']}: {str(e)}")
            continue
    
    print(f"Total headlines collected: {len(headlines)}")
    return headlines

if __name__ == "__main__":
    result = gather()
    print(f"Collected {len(result)} headlines")
    
    # Show first few as examples
    for i, headline in enumerate(result[:5]):
        print(f"{i+1}. {headline['title']} ({headline['source']}, {headline['language']})")