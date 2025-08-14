"""
Translation Module
Multi-language translation using Google Cloud Translate API
"""

import os
import time
from typing import Dict, List, Optional, Any
from google.cloud import translate
from dotenv import load_dotenv
from gather import gather

load_dotenv()

class Translator:
    def __init__(self):
        """Initialize Google Cloud Translate client"""
        # Use the modern TranslationServiceClient
        self.client = translate.TranslationServiceClient()
        self.target_language = 'en'
        
        # Get project ID from gcloud config or environment
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID') or self._get_project_id()
        self.location = "global"
        
        if not self.project_id:
            raise ValueError("Google Cloud project ID not found. Set GOOGLE_CLOUD_PROJECT_ID environment variable or run 'gcloud config set project YOUR_PROJECT_ID'")
    
    def _get_project_id(self):
        """Get project ID from gcloud config"""
        try:
            import subprocess
            result = subprocess.run(['gcloud', 'config', 'get-value', 'project'], 
                                 capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except:
            return None
    
    def translate_text(self, text: str, source_lang: str) -> Optional[str]:
        """Translate text to English using Google Cloud Translate API"""
        if not text or text.strip() == '':
            return None
            
        # If already English, return original
        if source_lang == 'en':
            return text
            
        try:
            # Build the request for the modern API
            request = translate.TranslateTextRequest(
                parent=f"projects/{self.project_id}/locations/{self.location}",
                contents=[text],
                mime_type="text/plain",
                source_language_code=source_lang,
                target_language_code=self.target_language
            )
            
            # Make the translation request
            response = self.client.translate_text(request=request)
            
            # Extract the translated text
            if response.translations:
                return response.translations[0].translated_text
            return None
            
        except Exception as e:
            print(f"Translation failed for text '{text[:50]}...': {str(e)}")
            return None
    
    def translate_headlines(self, headlines: List[Dict]) -> List[Dict]:
        """Translate a list of headlines to English"""
        translated_headlines = []
        
        print(f"Starting translation of {len(headlines)} headlines...")
        
        for i, headline in enumerate(headlines):
            try:
                # Skip if no title
                if not headline.get('title'):
                    continue
                
                original_title = headline['title']
                source_language = headline.get('language', 'unknown')
                
                # Skip if language is unknown
                if source_language == 'unknown':
                    headline['translated'] = False
                    translated_headlines.append(headline)
                    continue
                
                # Translate title if not already in English
                translated_title = self.translate_text(original_title, source_language)
                
                if translated_title and translated_title != original_title:
                    # Create new headline with translated title
                    translated_headline = headline.copy()
                    translated_headline['title'] = translated_title
                    translated_headline['original_title'] = original_title
                    translated_headline['translated'] = True
                    translated_headlines.append(translated_headline)
                    
                    print(f"Translated [{i+1}/{len(headlines)}]: {original_title[:50]}... → {translated_title[:50]}...")
                else:
                    # Keep original if translation failed or not needed
                    headline['translated'] = False
                    translated_headlines.append(headline)
                
                # Rate limiting to avoid hitting API limits
                time.sleep(0.1)  # 100ms delay between requests
                
            except Exception as e:
                print(f"Error processing headline {i+1}: {str(e)}")
                # Keep original headline on error
                headline['translated'] = False
                translated_headlines.append(headline)
        
        print(f"Translation completed. {len([h for h in translated_headlines if h.get('translated')])} headlines translated.")
        return translated_headlines

def main():
    """Main function to test translation"""
    try:
        # Initialize translator
        translator = Translator()
        
        # Get headlines from gather module
        print("Gathering headlines...")
        headlines = gather()
        
        if not headlines:
            print("No headlines to translate")
            return
        
        print(f"Gathered {len(headlines)} headlines")
        
        # Translate headlines
        translated_headlines = translator.translate_headlines(headlines)
        
        # Show some examples
        print("\n=== Translation Examples ===")
        for i, headline in enumerate(translated_headlines[:5]):
            if headline.get('translated'):
                print(f"{i+1}. {headline['title']} (translated from {headline.get('language', 'unknown')})")
            else:
                print(f"{i+1}. {headline['title']} (already in English)")
        
        return translated_headlines
        
    except Exception as e:
        print(f"Translation process failed: {str(e)}")
        return None

if __name__ == "__main__":
    main()

