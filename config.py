import os

# Bot configuration
CONFIG = {
    'prefix': '!',  # Command prefix
    'support_server': os.getenv('SUPPORT_SERVER', 'https://discord.gg/yoursupportserver'),
    'embed_color': 0x3498db,  # Blue color for embeds
    'max_message_length': 2000,  # Discord message character limit
    'default_language': 'en',  # Default language
    'reaction_timeout': 60 * 60,  # How long to wait for reactions (in seconds)
}

# Language configuration
LANGUAGES = {
    '🇺🇸': 'en',  # English (US)
    '🇬🇧': 'en',  # English (UK)
    '🇪🇸': 'es',  # Spanish
    '🇫🇷': 'fr',  # French
    '🇩🇪': 'de',  # German
    '🇮🇹': 'it',  # Italian
    '🇧🇷': 'pt',  # Portuguese
    '🇷🇺': 'ru',  # Russian
    '🇯🇵': 'ja',  # Japanese
    '🇰🇷': 'ko',  # Korean
    '🇨🇳': 'zh-CN',  # Chinese (Simplified)
    '🇹🇼': 'zh-TW',  # Chinese (Traditional)
    '🇮🇳': 'hi',  # Hindi
    '🇦🇪': 'ar',  # Arabic
    '🇹🇷': 'tr',  # Turkish
    '🇳🇱': 'nl',  # Dutch
    '🇸🇪': 'sv',  # Swedish
    '🇵🇱': 'pl',  # Polish
    '🇮🇩': 'id',  # Indonesian
    '🇹🇭': 'th',  # Thai
    '🇻🇳': 'vi',  # Vietnamese
}

# Reverse mapping for easy lookup (language code to emoji)
LANGUAGE_TO_FLAG = {lang: flag for flag, lang in LANGUAGES.items()}

# Translation API configuration
TRANSLATION_SERVICES = {
    'google': {
        'api_key': os.getenv('GOOGLE_TRANSLATE_API_KEY', ''),
        'base_url': 'https://translation.googleapis.com/language/translate/v2',
        'enabled': os.getenv('GOOGLE_TRANSLATE_API_KEY', '') != '',
    },
    'libre': {
        'api_key': os.getenv('LIBRETRANSLATE_API_KEY', ''),
        'base_url': os.getenv('LIBRETRANSLATE_URL', 'https://libretranslate.de'),
        'enabled': True,
    }
}

# Choose which translation service to use
DEFAULT_TRANSLATION_SERVICE = 'libre'  # Default to free LibreTranslate
if TRANSLATION_SERVICES['google']['api_key']:
    DEFAULT_TRANSLATION_SERVICE = 'google'  # Use Google if API key is available
