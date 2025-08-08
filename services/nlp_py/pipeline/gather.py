import os
import json
import asyncio
import aiohttp
from typing import List, Dict, Any
from xml.etree import ElementTree as ET
from google.cloud import translate_v2 as translate

# Load feeds data
def load_feeds():
    try:
        with open('data/feeds.json', 'r') as f:
            data = json.load(f)
            return data.get('feeds', [])
    except FileNotFoundError:
        # Fallback feeds if file doesn't exist
        return [
            {
                "url": "http://feeds.bbci.co.uk/news/world/rss.xml",
                "language": "en"
            },
            {
                "url": "http://rss.cnn.com/rss/edition.rss", 
                "language": "en"
            }
        ]

# Initialize translation client
translate_client = translate.Client() if os.getenv('GOOGLE_TRANSLATE_API_KEY') else None

FEED_LIMIT = 999
HEADLINE_LIMIT = 999

async def translate_text(text: str, target_language: str = 'en') -> str:
    """Translate text to target language"""
    if not translate_client:
        return text  # Return original if no translation available
    
    try:
        result = translate_client.translate(text, target_language=target_language)
        return result['translatedText']
    except Exception as e:
        print(f"Translation error: {e}")
        return text

async def fetch_feed(session: aiohttp.ClientSession, feed: Dict[str, Any]) -> List[Dict[str, str]]:
    """Fetch and parse a single RSS feed"""
    headlines = []
    
    try:
        async with session.get(feed['url'], timeout=30) as response:
            xml_content = await response.text()
            
        # Parse XML
        root = ET.fromstring(xml_content)
        
        # Find all items
        items = root.findall('.//item')
        
        for i, item in enumerate(items[:HEADLINE_LIMIT]):
            title_elem = item.find('title')
            link_elem = item.find('link')
            pub_date_elem = item.find('pubDate')
            
            if title_elem is not None and title_elem.text:
                title = title_elem.text.strip()
                
                # Translate if not English
                if feed.get('language', 'en') != 'en':
                    title = await translate_text(title, 'en')
                
                headline = {
                    'title': title,
                    'source': link_elem.text if link_elem is not None and link_elem.text else feed['url'],
                    'pubDate': pub_date_elem.text if pub_date_elem is not None and pub_date_elem.text else "Date not available"
                }
                headlines.append(headline)
                
    except Exception as error:
        print(f"Error fetching {feed['url']}: {error}")
    
    return headlines

async def gather() -> Dict[str, Any]:
    """Gather headlines from RSS feeds"""
    feeds = load_feeds()
    all_headlines = []
    amount_by_source = {}
    
    async with aiohttp.ClientSession() as session:
        # Process feeds concurrently
        tasks = [fetch_feed(session, feed) for feed in feeds[:FEED_LIMIT]]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, headlines in enumerate(results):
            if isinstance(headlines, Exception):
                continue
                
            feed_url = feeds[i]['url']
            all_headlines.extend(headlines)
            amount_by_source[feed_url] = len(headlines)
    
    return {
        'headlines': all_headlines,
        'amountBySource': amount_by_source
    } 