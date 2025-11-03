"""
Translation Module
Supports both real translation (via deep-translator) and mock mode
"""

import os
import time
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from gather import gather

load_dotenv()

class Translator:
    def __init__(self, use_real_translation: bool = True):
        """Initialize translator
        
        Args:
            use_real_translation: If True, uses deep-translator library. If False, uses mock.
        """
        self.target_language = 'en'
        self.use_real_translation = use_real_translation
        
        if use_real_translation:
            try:
                from deep_translator import GoogleTranslator
                self.translator = GoogleTranslator
                print("✅ Using Google Translator (via deep-translator)")
            except ImportError:
                print("⚠️  deep-translator not installed. Install with: pip install deep-translator")
                print("   Falling back to mock translation")
                self.use_real_translation = False
                self.translator = None
        else:
            print("Using mock translator - no actual translation will occur")
            self.translator = None
    
    def translate_text(self, text: str, source_lang: str) -> Optional[str]:
        """Translate text from source language to English"""
        if not text or text.strip() == '':
            return None
            
        # If already English, return original
        if source_lang == 'en' or source_lang == 'unknown':
            return text
        
        # Map language codes to deep-translator format
        lang_map = {
            'es': 'es', 'fr': 'fr', 'de': 'de', 'it': 'it', 'pt': 'pt',
            'ru': 'ru', 'zh': 'zh-CN', 'ja': 'ja', 'ko': 'ko', 'ar': 'ar',
            'nl': 'nl', 'pl': 'pl', 'sv': 'sv', 'da': 'da', 'fi': 'fi',
            'no': 'no', 'cs': 'cs', 'hu': 'hu', 'ro': 'ro', 'el': 'el'
        }
        
        try:
            if self.use_real_translation and self.translator:
                # Use real translation
                src_lang = lang_map.get(source_lang.lower(), source_lang.lower())
                if src_lang not in ['en', 'unknown']:
                    translator_instance = self.translator(source=src_lang, target='en')
                    translated = translator_instance.translate(text)
                    if translated and translated != text:
                        print(f"✅ Translated [{source_lang}] '{text[:50]}...' → '{translated[:50]}...'")
                        return translated
                    else:
                        # Translation returned same text (might be error)
                        print(f"⚠️  Translation returned same text for [{source_lang}]: {text[:50]}...")
                        return text
                else:
                    return text
            else:
                # Mock translation - return original but indicate it's processed
                print(f"🔧 Mock translation: '{text[:50]}...' from {source_lang} to {self.target_language}")
                # Return original text for mock mode
                return text
        except Exception as e:
            print(f"❌ Translation error for [{source_lang}]: {str(e)}")
            # Return original text on error
            return text
    
    def translate_headlines(self, headlines: List[Dict]) -> List[Dict]:
        """Translate a list of headlines to English (mock implementation)"""
        translated_headlines = []
        
        print(f"Starting mock translation of {len(headlines)} headlines...")
        
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
                
                # Mock translation - just mark as translated
                translated_headline = headline.copy()
                translated_headline['translated'] = True
                translated_headlines.append(translated_headline)
                
                # Progress update
                if (i + 1) % 10 == 0:
                    print(f"Processed {i + 1}/{len(headlines)} headlines")
                    
            except Exception as e:
                print(f"Error processing headline {i}: {str(e)}")
                headline['translated'] = False
                translated_headlines.append(headline)
        
        print(f"Mock translation completed. {len(translated_headlines)} headlines processed.")
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

