import json
import re
from typing import Dict, Any, Optional
from loguru import logger

from app.core.config import settings


class I18nService:
    """
    Internationalization service for loading and managing translations.
    Supports message interpolation with context variables.
    """

    def __init__(self):
        self._translations: Dict[str, Dict[str, Any]] = {}
        self._default_language = settings.default_language
        self._locales_dir = settings.locales_folder
        self._load_translations()

    def _load_translations(self) -> None:
        """Load all translation files from the locales directory."""
        if not self._locales_dir.exists():
            logger.warning(f"Locales directory not found: {self._locales_dir}")
            return

        for file_path in self._locales_dir.glob("*.json"):
            language_code = file_path.stem
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self._translations[language_code] = json.load(f)
                logger.info(f"Loaded translations for language: {language_code}")
            except Exception as e:
                logger.error(f"Failed to load translations for {language_code}: {e}")

    def _get_nested_value(self, data: Dict[str, Any], key: str) -> Optional[str]:
        """
        Get a nested value from a dictionary using dot notation.
        Example: 'global.internalServerError' -> data['global']['internalServerError']
        """
        keys = key.split(".")
        current = data

        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None

        return current if isinstance(current, str) else None

    def _interpolate_message(self, message: str, context: Dict[str, Any]) -> str:
        """
        Interpolate context variables into the message.
        Supports {variable_name} syntax.
        """
        if not context:
            return message

        # Use regex to find all {variable_name} patterns and replace them
        def replace_var(match):
            var_name = match.group(1)
            return str(context.get(var_name, match.group(0)))

        return re.sub(r"\{([^}]+)\}", replace_var, message)

    def get_message(
        self,
        message_key: str,
        language: str = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Get a translated message by key and language.

        Args:
            message_key: The message key in dot notation (e.g., 'global.internalServerError')
            language: The language code (defaults to default language)
            context: Context variables for message interpolation

        Returns:
            The translated and interpolated message
        """
        if language is None:
            language = self._default_language

        if language in self._translations:
            message = self._get_nested_value(self._translations[language], message_key)
            if message:
                return self._interpolate_message(message, context or {})

        if (
            language != self._default_language
            and self._default_language in self._translations
        ):
            message = self._get_nested_value(
                self._translations[self._default_language], message_key
            )
            if message:
                return self._interpolate_message(message, context or {})

        logger.warning(
            f"Translation not found for key '{message_key}' in language '{language}'"
        )
        return message_key

    def parse_accept_language(self, accept_language: Optional[str]) -> str:
        """
        Parse Accept-Language header and return the best matching language.

        Args:
            accept_language: The Accept-Language header value

        Returns:
            The best matching language code
        """
        if not accept_language:
            return self._default_language
        languages = []
        for lang_part in accept_language.split(","):
            lang_part = lang_part.strip()
            if ";" in lang_part:
                lang, quality = lang_part.split(";", 1)
                try:
                    q = float(quality.split("=")[1])
                except (IndexError, ValueError):
                    q = 1.0
            else:
                lang = lang_part
                q = 1.0

            primary_lang = lang.split("-")[0].lower()
            languages.append((primary_lang, q))

        languages.sort(key=lambda x: x[1], reverse=True)

        for lang, _ in languages:
            if lang in self._translations:
                return lang

        return self._default_language

    def get_supported_languages(self) -> list[str]:
        """Get list of supported language codes."""
        return list(self._translations.keys())

    def reload_translations(self) -> None:
        """Reload all translation files."""
        self._translations.clear()
        self._load_translations()


i18n_service = I18nService()
