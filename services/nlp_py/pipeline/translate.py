"""
Translation Module
Multi-language translation using MarianMT models and Google Translate API
"""

import os
import time
import asyncio
from typing import Dict, List, Optional, Any
from transformers import MarianMTModel, MarianTokenizer
from google.cloud import translate_v2 as translate
from dotenv import load_dotenv
import torch

load_dotenv()

# Configuration
GOOGLE_API_KEY = os.getenv('GOOGLE_TRANSLATE_API_KEY')
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Language detection patterns (simple heuristics)
LANGUAGE_PATTERNS = {
    'ru': ['а', 'в', 'с', 'и', 'н', 'т', 'р', 'о', 'л', 'к'],
    'de': ['der', 'die', 'das', 'und', 'ist', 'ein', 'zu', 'von'],
    'fr': ['le', 'la', 'les', 'de', 'et', 'un', 'une', 'à', 'dans'],
    'es': ['el', 'la', 'de', 'y', 'en', 'un', 'una', 'con', 'por'],
    'zh': ['的', '了', '在', '是', '我', '有', '和', '就', '不'],
}

class Translator:
    """Multi-language translation service"""
    
    def __init__(self):
        self.google_client = self._init_google_client()
        self.marian_models = {}  # Cache for MarianMT models
        
    def _init_google_client(self):
        """Initialize Google Translate client"""
        try:
            if GOOGLE_API_KEY:
                return translate.Client()
            else:
                print("⚠️  Google Translate API key not found, using local models only")
                return None
        except Exception as e:
            print(f"❌ Failed to initialize Google Translate: {e}")
            return None
    
    def detect_language(self, text: str) -> str:
        """
        Detect language using Google API or simple heuristics
        
        Args:
            text: Text to analyze
            
        Returns:
            Language code (e.g., 'en', 'ru', 'de')
        """
        if self.google_client:
            try:
                result = self.google_client.detect_language(text)
                return result['language']
            except Exception as e:
                print(f"❌ Language detection failed: {e}")
        
        # Fallback to simple pattern matching
        text_lower = text.lower()
        for lang, patterns in LANGUAGE_PATTERNS.items():
            matches = sum(1 for pattern in patterns if pattern in text_lower)
            if matches >= 3:  # Threshold for detection
                return lang
        
        return 'en'  # Default to English
    
    def _get_marian_model(self, source_lang: str, target_lang: str = 'en'):
        """Get or load MarianMT model for language pair"""
        model_key = f"{source_lang}-{target_lang}"
        
        if model_key in self.marian_models:
            return self.marian_models[model_key]
        
        try:
            model_name = f"Helsinki-NLP/opus-mt-{source_lang}-{target_lang}"
            print(f"🔧 Loading MarianMT model: {model_name}")
            
            tokenizer = MarianTokenizer.from_pretrained(model_name)
            model = MarianMTModel.from_pretrained(model_name)
            
            if DEVICE == "cuda":
                model = model.to(DEVICE)
            
            self.marian_models[model_key] = (tokenizer, model)
            print(f"✅ MarianMT model loaded: {model_name}")
            
            return self.marian_models[model_key]
            
        except Exception as e:
            print(f"❌ Failed to load MarianMT model for {source_lang}-{target_lang}: {e}")
            return None
    
    def translate_with_marian(self, text: str, source_lang: str, target_lang: str = 'en') -> Dict[str, Any]:
        """
        Translate using MarianMT local model
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Translation result dictionary
        """
        start_time = time.time()
        
        model_data = self._get_marian_model(source_lang, target_lang)
        if not model_data:
            return {
                'translated_text': text,
                'detected_language': source_lang,
                'confidence': 0.0,
                'processing_time': time.time() - start_time,
                'method': 'fallback'
            }
        
        tokenizer, model = model_data
        
        try:
            # Tokenize and translate
            inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
            if DEVICE == "cuda":
                inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = model.generate(**inputs, max_length=512, num_beams=4)
            
            translated = tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            return {
                'translated_text': translated,
                'detected_language': source_lang,
                'confidence': 0.9,  # MarianMT doesn't provide confidence scores
                'processing_time': time.time() - start_time,
                'method': 'marian'
            }
            
        except Exception as e:
            print(f"❌ MarianMT translation failed: {e}")
            return {
                'translated_text': text,
                'detected_language': source_lang,
                'confidence': 0.0,
                'processing_time': time.time() - start_time,
                'method': 'fallback'
            }
    
    def translate_with_google(self, text: str, source_lang: str = 'auto', target_lang: str = 'en') -> Dict[str, Any]:
        """
        Translate using Google Translate API
        
        Args:
            text: Text to translate
            source_lang: Source language ('auto' for detection)
            target_lang: Target language code
            
        Returns:
            Translation result dictionary
        """
        start_time = time.time()
        
        if not self.google_client:
            return self.translate_with_marian(text, source_lang, target_lang)
        
        try:
            result = self.google_client.translate(
                text,
                source_language=source_lang if source_lang != 'auto' else None,
                target_language=target_lang
            )
            
            return {
                'translated_text': result['translatedText'],
                'detected_language': result.get('detectedSourceLanguage', source_lang),
                'confidence': 0.95,  # Google Translate is generally high confidence
                'processing_time': time.time() - start_time,
                'method': 'google'
            }
            
        except Exception as e:
            print(f"❌ Google Translate failed: {e}")
            # Fallback to MarianMT
            detected_lang = self.detect_language(text)
            return self.translate_with_marian(text, detected_lang, target_lang)
    
    def translate(self, text: str, source_lang: str = 'auto', target_lang: str = 'en', prefer_local: bool = False) -> Dict[str, Any]:
        """
        Translate text with automatic method selection
        
        Args:
            text: Text to translate
            source_lang: Source language ('auto' for detection)
            target_lang: Target language code
            prefer_local: Use local models instead of API
            
        Returns:
            Translation result dictionary
        """
        # Skip translation if already in target language
        if source_lang == target_lang:
            return {
                'translated_text': text,
                'detected_language': source_lang,
                'confidence': 1.0,
                'processing_time': 0.0,
                'method': 'no_translation_needed'
            }
        
        # Detect language if auto
        if source_lang == 'auto':
            source_lang = self.detect_language(text)
            if source_lang == target_lang:
                return {
                    'translated_text': text,
                    'detected_language': source_lang,
                    'confidence': 1.0,
                    'processing_time': 0.0,
                    'method': 'no_translation_needed'
                }
        
        # Choose translation method
        if prefer_local or not self.google_client:
            return self.translate_with_marian(text, source_lang, target_lang)
        else:
            return self.translate_with_google(text, source_lang, target_lang)
    
    async def translate_batch(self, texts: List[str], source_lang: str = 'auto', target_lang: str = 'en', prefer_local: bool = False) -> List[Dict[str, Any]]:
        """
        Translate multiple texts concurrently
        
        Args:
            texts: List of texts to translate
            source_lang: Source language ('auto' for detection)
            target_lang: Target language code
            prefer_local: Use local models instead of API
            
        Returns:
            List of translation results
        """
        if not texts:
            return []
        
        print(f"🌐 Starting batch translation of {len(texts)} texts ({source_lang} → {target_lang})")
        start_time = time.time()
        
        # Process translations concurrently
        tasks = [
            asyncio.create_task(self._translate_async(text, source_lang, target_lang, prefer_local))
            for text in texts
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ Translation {i+1} failed: {result}")
                final_results.append({
                    'translated_text': texts[i],
                    'detected_language': source_lang,
                    'confidence': 0.0,
                    'processing_time': 0.0,
                    'method': 'failed'
                })
            else:
                final_results.append(result)
        
        total_time = time.time() - start_time
        success_rate = len([r for r in final_results if r['method'] != 'failed']) / len(final_results)
        
        print(f"🎉 Batch translation completed: {len(final_results)} texts in {total_time:.2f}s")
        print(f"📊 Success rate: {success_rate:.1%}")
        
        return final_results
    
    async def _translate_async(self, text: str, source_lang: str, target_lang: str, prefer_local: bool) -> Dict[str, Any]:
        """Async wrapper for translation"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.translate, text, source_lang, target_lang, prefer_local)


# Global translator instance
_translator = None

def get_translator() -> Translator:
    """Get or create global translator instance"""
    global _translator
    if _translator is None:
        _translator = Translator()
    return _translator

def translate_text(text: str, source_lang: str = 'auto', target_lang: str = 'en', prefer_local: bool = False) -> Dict[str, Any]:
    """
    Translate text (convenience function)
    
    Args:
        text: Text to translate
        source_lang: Source language ('auto' for detection)
        target_lang: Target language code
        prefer_local: Use local models instead of API
        
    Returns:
        Translation result dictionary
    """
    translator = get_translator()
    return translator.translate(text, source_lang, target_lang, prefer_local)

async def translate_batch(texts: List[str], source_lang: str = 'auto', target_lang: str = 'en', prefer_local: bool = False) -> List[Dict[str, Any]]:
    """
    Translate multiple texts (convenience function)
    
    Args:
        texts: List of texts to translate
        source_lang: Source language ('auto' for detection)
        target_lang: Target language code
        prefer_local: Use local models instead of API
        
    Returns:
        List of translation results
    """
    translator = get_translator()
    return await translator.translate_batch(texts, source_lang, target_lang, prefer_local)

# Example usage
if __name__ == "__main__":
    # Test translation
    test_texts = [
        "Hola, ¿cómo estás?",  # Spanish
        "Bonjour, comment allez-vous?",  # French
        "Guten Tag, wie geht es Ihnen?"  # German
    ]
    
    # Single translation
    result = translate_text(test_texts[0])
    print("Single translation result:", result)
    
    # Batch translation
    async def test_batch():
        results = await translate_batch(test_texts)
        for i, result in enumerate(results):
            print(f"Text {i+1}: {result['translated_text']} (confidence: {result['confidence']:.1%})")
    
    asyncio.run(test_batch()) 