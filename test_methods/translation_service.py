import os
import asyncio
import aiohttp
from typing import Optional

class TranslationService:
    """Simple translation service for RSS headlines"""
    
    def __init__(self):
        self.google_project_id = os.getenv('GOOGLE_PROJECT_ID')
        self.translate_key = os.getenv('TRANSLATE_KEY')
        
    async def translate_text(self, text: str, target_language: str = 'en') -> str:
        """Translate text using Google Cloud Translate API"""
        
        if not self.google_project_id or not self.translate_key:
            print(f"⚠️  Translation credentials not found. Returning original text: {text[:50]}...")
            return text
        
        try:
            # For now, we'll use a simple approach
            # In production, you'd use the Google Cloud Translate API
            print(f"🔄 Would translate to {target_language}: {text[:50]}...")
            
            # Placeholder for actual translation
            # This would be replaced with actual Google Cloud Translate API call
            return text
            
        except Exception as e:
            print(f"❌ Translation error: {e}")
            return text
    
    async def translate_batch(self, texts: list, target_language: str = 'en') -> list:
        """Translate a batch of texts"""
        translated_texts = []
        
        for text in texts:
            translated = await self.translate_text(text, target_language)
            translated_texts.append(translated)
            
            # Add small delay to avoid rate limiting
            await asyncio.sleep(0.1)
        
        return translated_texts

# Global translation service instance
translation_service = TranslationService()

async def translate_text(text: str, target_language: str = 'en') -> str:
    """Global translation function"""
    return await translation_service.translate_text(text, target_language) 