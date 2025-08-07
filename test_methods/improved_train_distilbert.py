import torch
import torch.nn as nn
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification, Trainer, TrainingArguments
from torch.utils.data import Dataset, DataLoader
import numpy as np
import json
import time
import asyncio
import feedparser
import aiohttp
import subprocess
import os
from typing import List, Dict, Any
from translation_service import translate_text

# Your candidate topics
CANDIDATE_TOPICS = [
    'politics', 'economy', 'technology', 'science', 'health', 'environment',
    'sports', 'entertainment', 'lifestyle', 'world', 'local', 'business',
    'education', 'travel', 'food', 'fashion', 'art'
]

# Create topic to index mapping
TOPIC_TO_ID = {topic: idx for idx, topic in enumerate(CANDIDATE_TOPICS)}
ID_TO_TOPIC = {idx: topic for topic, idx in TOPIC_TO_ID.items()}

# Comprehensive keyword rules for accurate labeling
COMPREHENSIVE_KEYWORD_RULES = {
    'politics': [
        # Political figures and leaders
        'trump', 'biden', 'obama', 'clinton', 'bush', 'reagan', 'nixon', 'kennedy', 'johnson', 'ford', 'carter',
        'putin', 'xi jinping', 'kim jong-un', 'erdogan', 'modi', 'macron', 'merkel', 'johnson', 'trudeau',
        'president', 'prime minister', 'chancellor', 'premier', 'governor', 'mayor', 'senator', 'representative',
        
        # Government institutions
        'congress', 'senate', 'house', 'parliament', 'white house', 'capitol', 'kremlin', 'downing street',
        'government', 'administration', 'cabinet', 'ministry', 'department', 'agency', 'commission',
        
        # Political processes
        'election', 'vote', 'campaign', 'primary', 'debate', 'poll', 'ballot', 'inauguration', 'referendum',
        'impeachment', 'censure', 'veto', 'legislation', 'bill', 'law', 'policy', 'executive order',
        
        # Political parties and ideologies
        'democrat', 'republican', 'liberal', 'conservative', 'progressive', 'socialist', 'communist',
        'nationalist', 'populist', 'centrist', 'moderate', 'radical', 'extremist',
        
        # International politics
        'diplomacy', 'ambassador', 'embassy', 'consulate', 'treaty', 'alliance', 'sanctions', 'summit',
        'united nations', 'un', 'nato', 'eu', 'european union', 'brexit', 'trade war', 'tariffs',
        'foreign policy', 'international relations', 'geopolitics', 'diplomatic', 'bilateral', 'multilateral'
    ],
    
    'economy': [
        # Economic indicators
        'economy', 'economic', 'gdp', 'inflation', 'deflation', 'unemployment', 'employment', 'recession',
        'depression', 'growth', 'decline', 'recovery', 'boom', 'bust', 'market', 'financial', 'fiscal',
        'monetary', 'economic policy', 'stimulus', 'austerity', 'deficit', 'surplus', 'budget',
        
        # Financial markets
        'stock market', 'dow jones', 'nasdaq', 's&p 500', 'ftse', 'nikkei', 'trading', 'investor', 'investment',
        'portfolio', 'dividend', 'earnings', 'revenue', 'profit', 'loss', 'quarterly', 'annual', 'fiscal year',
        'bull market', 'bear market', 'market crash', 'rally', 'correction', 'volatility',
        
        # Banking and finance
        'bank', 'banking', 'interest rate', 'federal reserve', 'fed', 'ecb', 'central bank', 'monetary policy',
        'credit', 'loan', 'mortgage', 'debt', 'bond', 'treasury', 'currency', 'exchange rate', 'forex',
        'cryptocurrency', 'bitcoin', 'ethereum', 'blockchain', 'fintech', 'digital currency',
        
        # Business terms
        'business', 'corporate', 'company', 'corporation', 'enterprise', 'startup', 'merger', 'acquisition',
        'bankruptcy', 'layoff', 'hiring', 'job market', 'wages', 'salary', 'income', 'wealth', 'poverty',
        'inequality', 'middle class', 'working class', 'unemployment rate', 'job creation'
    ],
    
    'technology': [
        # Tech companies
        'apple', 'google', 'microsoft', 'amazon', 'facebook', 'meta', 'tesla', 'netflix', 'uber', 'lyft',
        'airbnb', 'twitter', 'instagram', 'tiktok', 'snapchat', 'linkedin', 'youtube', 'spotify',
        'alphabet', 'alibaba', 'tencent', 'baidu', 'samsung', 'sony', 'intel', 'amd', 'nvidia', 'qualcomm',
        
        # Tech terms
        'technology', 'tech', 'digital', 'software', 'hardware', 'app', 'application', 'platform', 'algorithm',
        'artificial intelligence', 'ai', 'machine learning', 'ml', 'deep learning', 'neural network',
        'data science', 'big data', 'cloud computing', 'cybersecurity', 'hacking', 'malware', 'virus',
        'blockchain', 'cryptocurrency', 'nft', 'metaverse', 'virtual reality', 'vr', 'augmented reality', 'ar',
        'internet', 'web', 'website', 'social media', 'digital transformation', 'automation', 'robotics',
        
        # Tech products
        'smartphone', 'iphone', 'android', 'laptop', 'computer', 'tablet', 'wearable', 'smartwatch',
        'drone', 'robot', 'automation', 'innovation', 'startup', 'venture capital', 'silicon valley',
        'semiconductor', 'chip', 'processor', 'cpu', 'gpu', 'memory', 'storage', 'server', 'database'
    ],
    
    'science': [
        # Scientific disciplines
        'science', 'scientific', 'research', 'study', 'experiment', 'laboratory', 'lab', 'scientist',
        'physics', 'chemistry', 'biology', 'medicine', 'genetics', 'dna', 'genome', 'molecular',
        'astronomy', 'space', 'planet', 'galaxy', 'universe', 'cosmos', 'moon', 'mars', 'satellite',
        'climate science', 'environmental science', 'geology', 'archaeology', 'anthropology', 'psychology',
        'neuroscience', 'biotechnology', 'nanotechnology', 'quantum', 'theoretical', 'applied',
        
        # Scientific terms
        'discovery', 'breakthrough', 'hypothesis', 'theory', 'evidence', 'data', 'analysis', 'peer review',
        'publication', 'journal', 'conference', 'professor', 'researcher', 'university', 'institution',
        'grant', 'funding', 'clinical trial', 'experiment', 'observation', 'hypothesis', 'conclusion',
        
        # Medical research
        'medical', 'healthcare', 'treatment', 'therapy', 'vaccine', 'drug', 'pharmaceutical', 'clinical',
        'patient', 'diagnosis', 'symptom', 'disease', 'infection', 'virus', 'bacteria', 'pathogen',
        'immunology', 'epidemiology', 'public health', 'medical research', 'clinical study'
    ],
    
    'health': [
        # Health institutions
        'hospital', 'clinic', 'medical center', 'pharmacy', 'doctor', 'physician', 'nurse', 'surgeon',
        'specialist', 'therapist', 'psychologist', 'psychiatrist', 'dentist', 'veterinarian',
        'emergency room', 'icu', 'operating room', 'laboratory', 'medical device', 'equipment',
        
        # Health conditions
        'health', 'medical', 'disease', 'illness', 'infection', 'virus', 'bacteria', 'pathogen',
        'cancer', 'diabetes', 'heart disease', 'stroke', 'covid', 'coronavirus', 'pandemic', 'epidemic',
        'outbreak', 'symptom', 'diagnosis', 'treatment', 'therapy', 'surgery', 'medication', 'prescription',
        'mental health', 'depression', 'anxiety', 'stress', 'addiction', 'substance abuse',
        
        # Health terms
        'patient', 'care', 'wellness', 'fitness', 'nutrition', 'diet', 'exercise', 'prevention',
        'screening', 'vaccination', 'immunization', 'medication', 'prescription', 'healthcare system',
        'insurance', 'coverage', 'premium', 'deductible', 'copay', 'medical bill', 'healthcare cost'
    ],
    
    'environment': [
        # Environmental issues
        'environment', 'environmental', 'climate', 'climate change', 'global warming', 'greenhouse gas',
        'carbon', 'emissions', 'pollution', 'air quality', 'water quality', 'deforestation', 'extinction',
        'biodiversity', 'conservation', 'sustainability', 'renewable', 'clean energy', 'fossil fuel',
        'ocean', 'marine', 'forest', 'wildlife', 'endangered', 'species', 'ecosystem', 'habitat',
        
        # Natural resources
        'renewable energy', 'solar', 'wind power', 'hydroelectric', 'geothermal', 'nuclear', 'clean energy',
        'green energy', 'fossil fuel', 'oil', 'gas', 'coal', 'natural gas', 'petroleum', 'mining',
        'water', 'freshwater', 'groundwater', 'aquifer', 'drought', 'flood', 'natural disaster',
        
        # Environmental terms
        'recycling', 'waste', 'plastic', 'pollution', 'toxic', 'hazardous', 'organic', 'natural',
        'green', 'eco-friendly', 'carbon footprint', 'carbon neutral', 'carbon offset', 'sustainable',
        'conservation', 'preservation', 'wildlife', 'national park', 'protected area', 'environmental policy'
    ],
    
    'sports': [
        # Sports
        'sports', 'athletic', 'game', 'match', 'tournament', 'championship', 'olympic', 'olympics',
        'world cup', 'super bowl', 'playoff', 'final', 'semifinal', 'quarterfinal', 'league', 'season',
        'team', 'player', 'athlete', 'coach', 'manager', 'referee', 'umpire', 'score', 'win', 'lose',
        
        # Popular sports
        'football', 'soccer', 'basketball', 'baseball', 'tennis', 'golf', 'hockey', 'volleyball',
        'swimming', 'track', 'marathon', 'boxing', 'mma', 'ufc', 'wrestling', 'rugby', 'cricket',
        'cycling', 'skiing', 'snowboarding', 'surfing', 'gymnastics', 'weightlifting', 'running',
        
        # Sports terms
        'victory', 'defeat', 'record', 'statistics', 'stats', 'draft', 'trade', 'contract', 'salary',
        'endorsement', 'sponsorship', 'arena', 'stadium', 'field', 'court', 'track', 'pool', 'gym',
        'fitness', 'training', 'workout', 'exercise', 'performance', 'championship', 'trophy', 'medal'
    ],
    
    'entertainment': [
        # Entertainment industry
        'entertainment', 'hollywood', 'film', 'movie', 'cinema', 'television', 'tv', 'streaming',
        'netflix', 'disney', 'warner', 'paramount', 'universal', 'sony pictures', 'fox', 'amazon prime',
        'hulu', 'apple tv', 'youtube', 'tiktok', 'instagram', 'social media', 'influencer',
        
        # Music
        'music', 'song', 'album', 'concert', 'tour', 'festival', 'grammy', 'billboard', 'spotify',
        'apple music', 'pandora', 'radio', 'playlist', 'hit', 'chart', 'singer', 'musician', 'band',
        'rapper', 'dj', 'producer', 'composer', 'lyrics', 'melody', 'rhythm', 'genre',
        
        # Celebrities
        'celebrity', 'star', 'actor', 'actress', 'director', 'producer', 'singer', 'musician', 'band',
        'rapper', 'dj', 'comedian', 'host', 'presenter', 'influencer', 'youtuber', 'streamer',
        
        # Entertainment terms
        'award', 'oscar', 'emmy', 'golden globe', 'premiere', 'red carpet', 'box office', 'rating',
        'review', 'critic', 'audience', 'fan', 'fandom', 'franchise', 'sequel', 'remake', 'adaptation'
    ],
    
    'lifestyle': [
        # Lifestyle
        'lifestyle', 'life', 'living', 'wellness', 'fitness', 'personal', 'daily', 'routine', 'habits',
        'wellbeing', 'mindfulness', 'meditation', 'yoga', 'workout', 'exercise', 'diet', 'nutrition',
        'sleep', 'stress', 'relaxation', 'self-care', 'mental health', 'work-life balance',
        
        # Personal development
        'personal development', 'self-improvement', 'motivation', 'productivity', 'time management',
        'goal setting', 'success', 'achievement', 'inspiration', 'mindset', 'positive thinking',
        
        # Home and family
        'home', 'family', 'parenting', 'marriage', 'relationship', 'dating', 'friendship', 'community',
        'neighborhood', 'household', 'domestic', 'family life', 'parenting tips', 'childcare'
    ],
    
    'world': [
        # International terms
        'world', 'international', 'global', 'foreign', 'overseas', 'abroad', 'nation', 'country',
        'state', 'province', 'region', 'continent', 'hemisphere', 'international relations',
        
        # Geographic regions
        'europe', 'asia', 'africa', 'america', 'north america', 'south america', 'central america',
        'middle east', 'pacific', 'atlantic', 'mediterranean', 'caribbean', 'baltic', 'arctic',
        
        # International organizations
        'united nations', 'un', 'nato', 'eu', 'european union', 'who', 'world bank', 'imf',
        'international monetary fund', 'g7', 'g20', 'brics', 'asean', 'african union', 'oas',
        
        # International relations
        'diplomacy', 'foreign policy', 'embassy', 'consulate', 'ambassador', 'minister', 'summit',
        'conference', 'treaty', 'agreement', 'alliance', 'partnership', 'sanctions', 'trade',
        'import', 'export', 'tariff', 'embargo', 'war', 'peace', 'conflict', 'resolution'
    ],
    
    'local': [
        # Local terms
        'local', 'city', 'town', 'village', 'community', 'neighborhood', 'regional', 'municipal',
        'county', 'district', 'ward', 'precinct', 'borough', 'suburb', 'urban', 'rural',
        
        # Local government
        'mayor', 'council', 'commissioner', 'sheriff', 'police', 'fire department', 'school board',
        'local government', 'municipal', 'city hall', 'town hall', 'local election',
        
        # Local issues
        'local news', 'community', 'neighborhood', 'local business', 'local economy', 'local politics',
        'local crime', 'local education', 'local health', 'local environment', 'local sports'
    ],
    
    'business': [
        # Business terms
        'business', 'corporate', 'company', 'corporation', 'enterprise', 'firm', 'agency', 'organization',
        'startup', 'venture', 'entrepreneur', 'entrepreneurship', 'small business', 'medium business',
        'large business', 'multinational', 'conglomerate', 'holding company', 'subsidiary',
        
        # Business roles
        'ceo', 'executive', 'manager', 'director', 'president', 'vice president', 'chairman', 'board',
        'shareholder', 'investor', 'stakeholder', 'employee', 'staff', 'workforce', 'human resources',
        'management', 'leadership', 'administration', 'operations', 'strategy', 'marketing',
        
        # Business operations
        'profit', 'revenue', 'sales', 'marketing', 'advertising', 'brand', 'product', 'service',
        'customer', 'client', 'market', 'industry', 'sector', 'competition', 'competitor', 'market share',
        'business model', 'strategy', 'operations', 'logistics', 'supply chain', 'distribution',
        
        # Business events
        'merger', 'acquisition', 'ipo', 'initial public offering', 'stock', 'share', 'dividend',
        'earnings', 'quarterly', 'annual', 'report', 'conference call', 'layoff', 'hiring', 'expansion',
        'restructuring', 'bankruptcy', 'liquidation', 'insolvency', 'receivership'
    ],
    
    'education': [
        # Education institutions
        'education', 'school', 'university', 'college', 'academy', 'institute', 'campus', 'classroom',
        'student', 'teacher', 'professor', 'instructor', 'lecturer', 'faculty', 'staff', 'administration',
        'principal', 'dean', 'chancellor', 'president', 'board of trustees', 'alumni',
        
        # Education terms
        'learning', 'teaching', 'curriculum', 'syllabus', 'course', 'class', 'lecture', 'seminar',
        'workshop', 'tutorial', 'assignment', 'homework', 'exam', 'test', 'quiz', 'grade', 'gpa',
        'degree', 'diploma', 'certificate', 'bachelor', 'master', 'doctorate', 'phd', 'research',
        
        # Education levels
        'elementary', 'primary', 'secondary', 'high school', 'middle school', 'kindergarten',
        'preschool', 'graduate', 'undergraduate', 'postgraduate', 'vocational', 'technical',
        'online education', 'distance learning', 'e-learning', 'virtual classroom'
    ],
    
    'travel': [
        # Travel
        'travel', 'tourism', 'vacation', 'trip', 'journey', 'voyage', 'expedition', 'adventure',
        'destination', 'hotel', 'resort', 'motel', 'hostel', 'airbnb', 'booking', 'reservation',
        'airline', 'airport', 'flight', 'passenger', 'ticket', 'boarding pass', 'luggage', 'baggage',
        
        # Transportation
        'transportation', 'transport', 'vehicle', 'car', 'bus', 'train', 'subway', 'metro', 'taxi',
        'uber', 'lyft', 'bicycle', 'motorcycle', 'boat', 'ship', 'cruise', 'ferry', 'yacht',
        
        # Travel terms
        'tourist', 'visitor', 'traveler', 'backpacker', 'sightseeing', 'attraction', 'landmark',
        'museum', 'gallery', 'park', 'beach', 'mountain', 'city', 'country', 'culture', 'local',
        'international travel', 'domestic travel', 'business travel', 'leisure travel'
    ],
    
    'food': [
        # Food
        'food', 'restaurant', 'cooking', 'chef', 'recipe', 'dining', 'cuisine', 'meal', 'dish',
        'ingredient', 'spice', 'herb', 'flavor', 'taste', 'delicious', 'tasty', 'fresh', 'organic',
        'farm', 'agriculture', 'farming', 'crop', 'harvest', 'produce', 'vegetable', 'fruit',
        
        # Food industry
        'food industry', 'food service', 'catering', 'delivery', 'takeout', 'fast food', 'fine dining',
        'casual dining', 'food truck', 'cafe', 'bistro', 'pub', 'bar', 'brewery', 'winery',
        
        # Food terms
        'nutrition', 'diet', 'healthy', 'unhealthy', 'calories', 'protein', 'carbohydrate', 'fat',
        'vitamin', 'mineral', 'supplement', 'allergy', 'intolerance', 'vegetarian', 'vegan',
        'gluten-free', 'dairy-free', 'organic', 'natural', 'processed', 'fresh', 'frozen'
    ],
    
    'fashion': [
        # Fashion
        'fashion', 'style', 'clothing', 'apparel', 'outfit', 'dress', 'shirt', 'pants', 'jeans',
        'shoes', 'accessories', 'jewelry', 'watch', 'bag', 'purse', 'wallet', 'belt', 'hat',
        'designer', 'brand', 'label', 'trend', 'trendy', 'stylish', 'elegant', 'casual', 'formal',
        
        # Fashion industry
        'fashion industry', 'fashion week', 'runway', 'catwalk', 'model', 'designer', 'stylist',
        'fashion show', 'collection', 'season', 'spring', 'summer', 'fall', 'winter', 'trend',
        
        # Fashion terms
        'style', 'trend', 'fashionable', 'outdated', 'vintage', 'retro', 'modern', 'classic',
        'luxury', 'premium', 'affordable', 'budget', 'sustainable fashion', 'ethical fashion',
        'fast fashion', 'slow fashion', 'second-hand', 'thrift', 'vintage', 'antique'
    ],
    
    'art': [
        # Art
        'art', 'artist', 'painting', 'sculpture', 'drawing', 'photography', 'film', 'music',
        'literature', 'poetry', 'dance', 'theater', 'performance', 'gallery', 'museum', 'exhibition',
        'creative', 'creativity', 'inspiration', 'expression', 'aesthetic', 'beautiful', 'artistic',
        
        # Art forms
        'painting', 'sculpture', 'drawing', 'sketch', 'illustration', 'photography', 'cinematography',
        'architecture', 'design', 'graphic design', 'digital art', 'street art', 'graffiti',
        'installation', 'performance art', 'conceptual art', 'abstract', 'realistic', 'impressionist',
        
        # Art terms
        'masterpiece', 'exhibition', 'gallery', 'museum', 'curator', 'collector', 'auction',
        'art market', 'art history', 'contemporary art', 'modern art', 'classical art', 'renaissance',
        'impressionism', 'cubism', 'surrealism', 'abstract expressionism', 'pop art'
    ]
}

class RSSDataset(Dataset):
    """Custom dataset for RSS headlines"""
    
    def __init__(self, texts, labels, tokenizer, max_length=128):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]
        
        # Tokenize the text
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

async def fetch_rss_feeds_with_translation():
    """Fetch RSS feeds using the feeds from feeds.ts and translate non-English headlines"""
    
    # Import feeds from TypeScript file
    feeds_data = await get_feeds_from_typescript()
    
    all_headlines = []
    
    async with aiohttp.ClientSession() as session:
        for feed in feeds_data:
            try:
                async with session.get(feed['url']) as response:
                    if response.status == 200:
                        content = await response.text()
                        feed_parser = feedparser.parse(content)
                        
                        for entry in feed_parser.entries[:50]:  # Get 50 headlines per feed
                            title = entry.title
                            
                            # Translate non-English headlines
                            if feed['language'] != 'en':
                                print(f"🔄 Translating headline from {feed['language']}: {title[:50]}...")
                                title = await translate_text(title)
                                print(f"✅ Translated: {title[:50]}...")
                            
                            all_headlines.append({
                                'title': title,
                                'source': feed['url'],
                                'language': feed['language'],
                                'group': feed['group']
                            })
                        
                        print(f"✅ Fetched {len(feed_parser.entries[:50])} headlines from {feed['url']}")
                    else:
                        print(f"❌ Failed to fetch {feed['url']}: {response.status}")
            except Exception as e:
                print(f"❌ Error fetching {feed['url']}: {e}")
    
    return all_headlines

async def get_feeds_from_typescript():
    """Get feeds data from the TypeScript bridge"""
    try:
        # Run TypeScript bridge to get feeds data
        result = subprocess.run(
            ['npx', 'tsx', 'src/lib/feeds_bridge.ts'],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        if result.returncode == 0:
            feeds_data = json.loads(result.stdout.strip())
            print(f"✅ Retrieved {feeds_data['totalFeeds']} feeds from TypeScript")
            print(f"   Languages: {', '.join(feeds_data['languages'])}")
            print(f"   Groups: {', '.join(feeds_data['groups'])}")
            return feeds_data['feeds']
        else:
            print(f"❌ Error getting feeds from TypeScript: {result.stderr}")
            return []
    except Exception as e:
        print(f"❌ Error getting feeds: {e}")
        return []

# Translation function is now imported from translation_service

def create_training_data_with_comprehensive_rules(headlines):
    """Create training data with comprehensive keyword-based labeling"""
    
    training_data = []
    
    for headline in headlines:
        text = headline['title'].lower()
        best_topic = 'world'  # Default topic
        best_score = 0
        
        # Find the best matching topic using comprehensive rules
        for topic, keywords in COMPREHENSIVE_KEYWORD_RULES.items():
            score = 0
            
            # Check for exact keyword matches
            for keyword in keywords:
                if keyword in text:
                    # Weight longer keywords more heavily
                    score += len(keyword.split()) * 2
                    
                    # Bonus for important keywords
                    if keyword in ['trump', 'biden', 'apple', 'google', 'tesla', 'covid', 'coronavirus']:
                        score += 5
                    
                    # Bonus for topic name match
                    if topic in text:
                        score += 3
            
            if score > best_score:
                best_score = score
                best_topic = topic
        
        # Only include headlines with clear topic matches
        if best_score >= 2:  # Minimum score threshold
            training_data.append({
                'text': headline['title'],
                'label': best_topic,
                'label_id': TOPIC_TO_ID[best_topic],
                'score': best_score,
                'source': headline['source'],
                'language': headline['language'],
                'group': headline['group']
            })
    
    return training_data

def train_distilbert_improved():
    """Train DistilBERT with improved data collection and labeling"""
    
    print("=" * 60)
    print("🚀 IMPROVED DISTILBERT TRAINING FOR RSS CLASSIFICATION")
    print("=" * 60)
    
    # Step 1: Fetch RSS data with translation
    print("\n📡 Step 1: Fetching RSS feeds with translation...")
    headlines = asyncio.run(fetch_rss_feeds_with_translation())
    print(f"✅ Fetched {len(headlines)} total headlines")
    
    # Step 2: Create training data with comprehensive rules
    print("\n🏷️  Step 2: Creating training data with comprehensive keyword rules...")
    training_data = create_training_data_with_comprehensive_rules(headlines)
    print(f"✅ Created {len(training_data)} labeled training examples")
    
    if len(training_data) < 100:
        print("❌ Not enough training data. Need at least 100 examples.")
        return
    
    # Step 3: Analyze data distribution
    print("\n📊 Step 3: Analyzing data distribution...")
    topic_counts = {}
    for item in training_data:
        topic = item['label']
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
    
    print("   Topic distribution:")
    for topic, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"   {topic}: {count} examples")
    
    # Step 4: Split data
    print("\n📊 Step 4: Splitting data into train/validation sets...")
    np.random.shuffle(training_data)
    split_idx = int(0.8 * len(training_data))
    train_data = training_data[:split_idx]
    val_data = training_data[split_idx:]
    
    print(f"   Training examples: {len(train_data)}")
    print(f"   Validation examples: {len(val_data)}")
    
    # Step 5: Initialize model
    print("\n🔧 Step 5: Initializing DistilBERT model...")
    model_name = "distilbert-base-uncased"
    tokenizer = DistilBertTokenizer.from_pretrained(model_name)
    
    model = DistilBertForSequenceClassification.from_pretrained(
        model_name,
        num_labels=len(CANDIDATE_TOPICS)
    )
    
    # Step 6: Create datasets
    print("\n📚 Step 6: Creating PyTorch datasets...")
    train_texts = [item['text'] for item in train_data]
    train_labels = [item['label_id'] for item in train_data]
    val_texts = [item['text'] for item in val_data]
    val_labels = [item['label_id'] for item in val_data]
    
    train_dataset = RSSDataset(train_texts, train_labels, tokenizer)
    val_dataset = RSSDataset(val_texts, val_labels, tokenizer)
    
    # Step 7: Training arguments
    print("\n⚙️  Step 7: Setting up training arguments...")
    training_args = TrainingArguments(
        output_dir="./distilbert_rss_classifier_improved",
        num_train_epochs=5,  # More epochs for better learning
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        warmup_steps=100,
        weight_decay=0.01,
        logging_dir="./logs_improved",
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=50,
        save_steps=100,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        save_total_limit=3,
        learning_rate=3e-5,  # Slightly lower learning rate
    )
    
    # Step 8: Initialize trainer
    print("\n🎯 Step 8: Initializing trainer...")
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
    )
    
    # Step 9: Train the model
    print("\n🚀 Step 9: Starting training...")
    print("   This may take 15-45 minutes depending on your hardware...")
    
    train_start = time.time()
    trainer.train()
    train_end = time.time()
    
    print(f"\n✅ Training completed in {train_end - train_start:.2f} seconds")
    
    # Step 10: Save the model
    print("\n💾 Step 10: Saving the trained model...")
    model_path = "./distilbert_rss_classifier_improved_final"
    trainer.save_model(model_path)
    tokenizer.save_pretrained(model_path)
    
    # Save comprehensive topic mappings
    with open(f"{model_path}/topic_mappings.json", 'w') as f:
        json.dump({
            'topic_to_id': TOPIC_TO_ID,
            'id_to_topic': ID_TO_TOPIC,
            'candidate_topics': CANDIDATE_TOPICS,
            'keyword_rules': COMPREHENSIVE_KEYWORD_RULES
        }, f, indent=2)
    
    print(f"✅ Model saved to {model_path}")
    
    # Step 11: Evaluate the model
    print("\n📊 Step 11: Evaluating the model...")
    results = trainer.evaluate()
    print(f"   Final validation loss: {results['eval_loss']:.3f}")
    print(f"   Final validation runtime: {results['eval_runtime']:.3f}s")
    print(f"   Evaluation samples per second: {results['eval_samples_per_second']:.1f}")
    
    # Step 12: Test the model
    print("\n🧪 Step 12: Testing the trained model...")
    test_headlines = [
        "Trump Announces New Trade Deal with China",
        "Scientists Discover New Species in Amazon Rainforest",
        "Tech Giant Reports Record Quarterly Profits",
        "Apple Launches New iPhone with AI Features",
        "Olympic Athlete Breaks World Record in Swimming",
        "Hollywood Star Wins Best Actor at Academy Awards",
        "Federal Reserve Raises Interest Rates Again",
        "Climate Summit Reaches Historic Agreement",
        "New Medical Breakthrough Shows Promise for Cancer Treatment",
        "Space Mission Successfully Lands on Mars"
    ]
    
    model.eval()
    device = next(model.parameters()).device
    print(f"   Using device: {device}")
    
    with torch.no_grad():
        for headline in test_headlines:
            inputs = tokenizer(
                headline,
                truncation=True,
                padding=True,
                return_tensors="pt"
            )
            
            # Move inputs to the same device as the model
            inputs = {k: v.to(device) for k, v in inputs.items()}
            
            outputs = model(**inputs)
            predictions = torch.softmax(outputs.logits, dim=-1)
            predicted_id = torch.argmax(predictions, dim=-1).item()
            confidence = predictions[0][predicted_id].item()
            predicted_topic = ID_TO_TOPIC[predicted_id]
            
            print(f"   '{headline}' → {predicted_topic} ({confidence:.1%})")
    
    print("\n🎉 Improved training completed successfully!")
    print(f"📁 Model saved to: {model_path}")
    print(f"📊 Validation loss: {results['eval_loss']:.3f}")

if __name__ == "__main__":
    train_distilbert_improved() 