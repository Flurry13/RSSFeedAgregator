"""
Translation Module
Supports both real translation (via deep-translator) and mock mode
With batch translation support and LRU caching for performance optimization
"""

import os
import time
from typing import Dict, List, Optional, Any
from functools import lru_cache
from collections import defaultdict
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
        self._translator_cache = {}  # Cache translator instances by language
        self._translation_cache = {}  # Manual cache for translations (key: (text, lang))
        
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
    
    def _get_lang_map(self, source_lang: str) -> str:
        """Map language codes to deep-translator format"""
        lang_map = {
            'es': 'es', 'fr': 'fr', 'de': 'de', 'it': 'it', 'pt': 'pt',
            'ru': 'ru', 'zh': 'zh-CN', 'ja': 'ja', 'ko': 'ko', 'ar': 'ar',
            'nl': 'nl', 'pl': 'pl', 'sv': 'sv', 'da': 'da', 'fi': 'fi',
            'no': 'no', 'cs': 'cs', 'hu': 'hu', 'ro': 'ro', 'el': 'el'
        }
        return lang_map.get(source_lang.lower(), source_lang.lower())
    
    def _get_translator_instance(self, source_lang: str):
        """Get or create cached translator instance for a language"""
        if source_lang not in self._translator_cache:
            self._translator_cache[source_lang] = self.translator(source=source_lang, target='en')
        return self._translator_cache[source_lang]
    
    def translate_text(self, text: str, source_lang: str) -> Optional[str]:
        """Translate text from source language to English with caching"""
        if not text or text.strip() == '':
            return None
            
        # If already English, return original
        if source_lang == 'en' or source_lang == 'unknown':
            return text
        
        # Check cache first
        cache_key = (text, source_lang)
        if cache_key in self._translation_cache:
            return self._translation_cache[cache_key]
        
        try:
            if self.use_real_translation and self.translator:
                # Use real translation
                src_lang = self._get_lang_map(source_lang)
                if src_lang not in ['en', 'unknown']:
                    translator_instance = self._get_translator_instance(src_lang)
                    translated = translator_instance.translate(text)
                    if translated and translated != text:
                        print(f"✅ Translated [{source_lang}] '{text[:50]}...' → '{translated[:50]}...'")
                        # Cache the result
                        self._translation_cache[cache_key] = translated
                        return translated
                    else:
                        # Translation returned same text (might be error)
                        print(f"⚠️  Translation returned same text for [{source_lang}]: {text[:50]}...")
                        self._translation_cache[cache_key] = text
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
    
    def translate_batch(self, texts: List[str], source_langs: List[str], batch_size: int = 50) -> List[Optional[str]]:
        """
        Translate multiple texts in batches grouped by language
        
        Args:
            texts: List of texts to translate
            source_langs: List of source languages (same length as texts)
            batch_size: Maximum number of texts per batch (default: 50)
            
        Returns:
            List of translated texts (or original if translation fails)
        """
        if len(texts) != len(source_langs):
            raise ValueError("texts and source_langs must have the same length")
        
        if not texts:
            return []
        
        print(f"🚀 Starting batch translation of {len(texts)} texts")
        start_time = time.time()
        
        # Group texts by language for efficient batch processing
        lang_groups = defaultdict(list)  # {lang: [(index, text), ...]}
        for idx, (text, lang) in enumerate(zip(texts, source_langs)):
            # Skip empty texts or English
            if not text or not text.strip() or lang in ['en', 'unknown']:
                lang_groups['skip'].append((idx, text))
            else:
                lang_groups[lang].append((idx, text))
        
        # Initialize results array
        results = [None] * len(texts)
        
        # Process skipped items (English or empty)
        for idx, text in lang_groups.get('skip', []):
            results[idx] = text
        
        # Process each language group
        for lang, items in lang_groups.items():
            if lang == 'skip':
                continue
            
            print(f"📝 Processing {len(items)} texts in language: {lang}")
            src_lang = self._get_lang_map(lang)
            
            # Check cache first and separate cached/uncached
            cached_results = {}
            uncached_items = []
            
            for idx, text in items:
                cache_key = (text, lang)
                if cache_key in self._translation_cache:
                    results[idx] = self._translation_cache[cache_key]
                    cached_results[idx] = True
                else:
                    uncached_items.append((idx, text))
            
            if cached_results:
                print(f"✨ Found {len(cached_results)} cached translations for {lang}")
            
            # Process uncached items in batches
            if uncached_items and self.use_real_translation and self.translator:
                try:
                    translator_instance = self._get_translator_instance(src_lang)
                    
                    # Process in chunks to avoid API limits
                    for i in range(0, len(uncached_items), batch_size):
                        chunk = uncached_items[i:i + batch_size]
                        chunk_texts = [text for _, text in chunk]
                        
                        try:
                            # Batch translate
                            translated_texts = translator_instance.translate_batch(chunk_texts)
                            
                            # Store results and cache
                            for (idx, original_text), translated in zip(chunk, translated_texts):
                                if translated:
                                    results[idx] = translated
                                    cache_key = (original_text, lang)
                                    self._translation_cache[cache_key] = translated
                                else:
                                    results[idx] = original_text
                            
                            print(f"✅ Batch translated {len(chunk)} texts for {lang}")
                            
                        except AttributeError:
                            # Fallback: deep-translator might not support batch translation
                            print(f"⚠️  Batch translation not supported, falling back to individual translation")
                            for idx, text in chunk:
                                translated = self.translate_text(text, lang)
                                results[idx] = translated if translated else text
                        
                        except Exception as e:
                            print(f"❌ Batch translation error for {lang}: {str(e)}")
                            # Fallback to individual translation
                            for idx, text in chunk:
                                translated = self.translate_text(text, lang)
                                results[idx] = translated if translated else text
                
                except Exception as e:
                    print(f"❌ Error setting up translator for {lang}: {str(e)}")
                    # Fallback: return original texts
                    for idx, text in uncached_items:
                        results[idx] = text
            
            elif uncached_items:
                # Mock mode - return original texts
                for idx, text in uncached_items:
                    results[idx] = text
                    print(f"🔧 Mock batch: {len(uncached_items)} texts in {lang}")
        
        total_time = time.time() - start_time
        print(f"🎉 Batch translation completed: {len(texts)} texts in {total_time:.2f}s")
        
        return results
    
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

