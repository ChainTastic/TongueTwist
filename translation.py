import os
import aiohttp
import asyncio
import logging
import time
from typing import Dict, Optional, Tuple, List

from config import TRANSLATION_SERVICES, DEFAULT_TRANSLATION_SERVICE, LANGUAGES, CONFIG

logger = logging.getLogger('discord')

class TranslationService:
    """Translation service that handles API requests to translation services"""
    
    def __init__(self):
        self.service = DEFAULT_TRANSLATION_SERVICE
        self.session = None
        self.rate_limits = {
            'google': {
                'calls': 0,
                'reset_time': time.time() + 60,
                'limit': 500  # Google Translate API limit per minute
            },
            'libre': {
                'calls': 0,
                'reset_time': time.time() + 60,
                'limit': 100  # LibreTranslate estimated limit
            }
        }
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Get aiohttp session, creating it if it doesn't exist"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Close aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def translate(self, text: str, target_lang: str, source_lang: Optional[str] = None) -> str:
        """Translate text to the target language"""
        if not text or not target_lang:
            return text
            
        # Update rate limits
        current_time = time.time()
        for service in self.rate_limits:
            if current_time > self.rate_limits[service]['reset_time']:
                self.rate_limits[service]['calls'] = 0
                self.rate_limits[service]['reset_time'] = current_time + 60
        
        # Check if we need to switch services due to rate limits
        if self.rate_limits[self.service]['calls'] >= self.rate_limits[self.service]['limit']:
            # Try to find another service that's not rate limited
            for service in TRANSLATION_SERVICES:
                if TRANSLATION_SERVICES[service]['enabled'] and self.rate_limits[service]['calls'] < self.rate_limits[service]['limit']:
                    self.service = service
                    break
            else:
                # All services are rate limited
                logger.warning("All translation services are rate limited. Translation will be delayed.")
                # Wait until the next reset
                await asyncio.sleep(self.rate_limits[self.service]['reset_time'] - current_time)
                self.rate_limits[self.service]['calls'] = 0
                self.rate_limits[self.service]['reset_time'] = time.time() + 60
        
        # Increment the call counter
        self.rate_limits[self.service]['calls'] += 1
        
        # Call the appropriate translation method
        if self.service == 'google':
            return await self._translate_google(text, target_lang, source_lang)
        elif self.service == 'libre':
            return await self._translate_libre(text, target_lang, source_lang)
        else:
            logger.error(f"Unknown translation service: {self.service}")
            return text
    
    async def _translate_google(self, text: str, target_lang: str, source_lang: Optional[str] = None) -> str:
        """Translate text using Google Translate API"""
        try:
            api_key = TRANSLATION_SERVICES['google']['api_key']
            base_url = TRANSLATION_SERVICES['google']['base_url']
            
            if not api_key:
                logger.error("Google Translate API key not set")
                return text
            
            session = await self.get_session()
            
            params = {
                'key': api_key,
                'q': text,
                'target': target_lang
            }
            
            if source_lang:
                params['source'] = source_lang
            
            async with session.post(base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'data' in data and 'translations' in data['data'] and len(data['data']['translations']) > 0:
                        return data['data']['translations'][0]['translatedText']
                    else:
                        logger.error(f"Unexpected Google Translate API response: {data}")
                        return text
                else:
                    logger.error(f"Google Translate API error: {response.status} - {await response.text()}")
                    return text
        except Exception as e:
            logger.error(f"Error translating with Google Translate: {e}")
            return text
    
    async def _translate_libre(self, text: str, target_lang: str, source_lang: Optional[str] = None) -> str:
        """Translate text using LibreTranslate API"""
        try:
            api_key = TRANSLATION_SERVICES['libre']['api_key']
            base_url = TRANSLATION_SERVICES['libre']['base_url']
            
            # Use a public LibreTranslate instance if none is configured
            if not base_url:
                base_url = "https://libretranslate.de/translate"
                logger.info("Using public LibreTranslate instance")
            
            session = await self.get_session()
            
            payload = {
                'q': text,
                'target': target_lang,
                'format': 'text'
            }
            
            if api_key:
                payload['api_key'] = api_key
                
            if source_lang:
                payload['source'] = source_lang
            else:
                # If auto detection doesn't work, use English as fallback
                payload['source'] = 'en'
            
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with session.post(base_url, json=payload, timeout=timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'translatedText' in data:
                            return data['translatedText']
                        else:
                            logger.error(f"Unexpected LibreTranslate API response: {data}")
                            return f"[Translation format error] {text}"
                    else:
                        error_text = await response.text()
                        logger.error(f"LibreTranslate API error: {response.status} - {error_text}")
                        
                        # Try fallback to simple translation indicator
                        return f"[{target_lang}] {text}"
            except asyncio.TimeoutError:
                logger.warning("LibreTranslate request timed out")
                return f"[Translation timeout] {text}"
            except Exception as req_error:
                logger.error(f"LibreTranslate request error: {req_error}")
                return f"[Translation request error] {text}"
        except Exception as e:
            logger.error(f"Error translating with LibreTranslate: {e}")
            return f"[Translation failed] {text}"
    
    async def detect_language(self, text: str) -> str:
        """Detect the language of the text"""
        try:
            # Default to Google's detection since it's more reliable
            api_key = TRANSLATION_SERVICES['google']['api_key']
            if not api_key:
                return CONFIG['default_language']
                
            base_url = 'https://translation.googleapis.com/language/translate/v2/detect'
            
            session = await self.get_session()
            
            params = {
                'key': api_key,
                'q': text
            }
            
            async with session.post(base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'data' in data and 'detections' in data['data'] and len(data['data']['detections']) > 0:
                        detections = data['data']['detections'][0]
                        if len(detections) > 0 and 'language' in detections[0]:
                            return detections[0]['language']
                    logger.error(f"Unexpected language detection response: {data}")
                    return CONFIG['default_language']
                else:
                    logger.error(f"Language detection API error: {response.status} - {await response.text()}")
                    return CONFIG['default_language']
        except Exception as e:
            logger.error(f"Error detecting language: {e}")
            return CONFIG['default_language']

# Create the translation service instance
translation_service = TranslationService()
