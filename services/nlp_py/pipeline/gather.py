import json
import os
import feedparser
import time

# Load feeds from JSON file
def load_feeds():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    feeds_path = os.path.join(project_root, 'data', 'feeds.json')
    
    with open(feeds_path, 'r') as f:
        data = json.load(f)
        return data.get('feeds', [])

feedList = load_feeds()

def gather():
    headlines = []
    
    for item in feedList:
        try:
            feed = feedparser.parse(item['url'])
            
            for entry in feed.entries:
                headline = {
                    'title': getattr(entry, 'title', 'No title'),
                    'link': getattr(entry, 'link', 'No link'),
                    'language': item['language'],
                    'source': item['name'],
                    'group': item['group'],
                    'country': item['country']
                }
                headlines.append(headline)
        except Exception as e:
            print(f"Error processing {item['name']}: {str(e)}")
            continue
    
    return headlines

if __name__ == "__main__":
    result = gather()
    print(f"Collected {len(result)} headlines")
    
    # Show first few as examples
    for i, headline in enumerate(result[:5]):
        print(f"{i+1}. {headline['title']} ({headline['source']}, {headline['language']})")