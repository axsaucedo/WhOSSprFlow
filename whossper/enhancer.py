"""WhOSSper Text Enhancement - Optional LLM-based text improvement.

This module provides optional text enhancement using OpenAI-compatible APIs.
It improves transcribed speech by fixing grammar, punctuation, and formatting.
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

from openai import OpenAI


logger = logging.getLogger(__name__)


DEFAULT_SYSTEM_PROMPT = """You are a helpful assistant that improves transcribed speech text.

Your task is to:
1. Fix any grammar and punctuation errors
2. Add proper capitalization
3. Remove filler words like "um", "uh", "like" (when used as fillers)
4. Format the text for clarity while preserving the original meaning
5. Do NOT add any commentary or explanations - only output the improved text

Keep the text natural and conversational while making it more polished and readable."""


class TextEnhancer:
    """Enhances transcribed text using OpenAI-compatible APIs."""
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        system_prompt: Optional[str] = None,
        prompt_file: Optional[str] = None,
    ):
        """Initialize text enhancer.
        
        Args:
            api_key: API key for authentication.
            base_url: Base URL for OpenAI-compatible API.
            model: Model to use for enhancement.
            system_prompt: Custom system prompt (overrides file).
            prompt_file: Path to system prompt file.
        """
        if not api_key:
            raise ValueError("API key is required for text enhancement")
        
        self.model = model
        self.system_prompt = self._load_prompt(system_prompt, prompt_file)
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        
        logger.info(f"TextEnhancer initialized with model={model}")
    
    def _load_prompt(
        self,
        custom: Optional[str],
        file_path: Optional[str],
    ) -> str:
        """Load system prompt with priority: custom > file > default."""
        if custom:
            return custom
        
        if file_path:
            path = Path(file_path)
            if path.exists():
                logger.debug(f"Loading prompt from {file_path}")
                return path.read_text().strip()
            logger.warning(f"Prompt file not found: {file_path}")
        
        return DEFAULT_SYSTEM_PROMPT
    
    def enhance(
        self,
        text: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str:
        """Enhance transcribed text using LLM.
        
        Args:
            text: Raw transcribed text to enhance.
            temperature: Model temperature (lower = more deterministic).
            max_tokens: Maximum tokens in response.
            
        Returns:
            Enhanced text.
            
        Raises:
            ValueError: If text is empty.
            Exception: If API call fails.
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        logger.info(f"Enhancing text: {len(text)} chars")
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Please improve this transcribed speech:\n\n{text}"},
        ]
        
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            enhanced = response.choices[0].message.content.strip()
            logger.info(f"Enhanced text: {len(enhanced)} chars")
            return enhanced
            
        except Exception as e:
            logger.error(f"Enhancement failed: {e}")
            raise
    
    def __call__(self, text: str) -> str:
        """Callable interface for use as enhancer function."""
        return self.enhance(text)
    
    @property
    def client(self) -> OpenAI:
        """Get the OpenAI client."""
        return self._client


def resolve_api_key(
    api_key: Optional[str] = None,
    api_key_helper: Optional[str] = None,
    api_key_env_var: Optional[str] = None,
) -> Optional[str]:
    """Resolve API key from various sources.
    
    Priority: api_key > api_key_helper command > api_key_env_var
    
    Args:
        api_key: Direct API key value.
        api_key_helper: Shell command to retrieve API key.
        api_key_env_var: Environment variable name.
        
    Returns:
        Resolved API key or None.
    """
    # Direct key
    if api_key and api_key.strip():
        return api_key.strip()
    
    # Helper command
    if api_key_helper and api_key_helper.strip():
        try:
            result = subprocess.run(
                api_key_helper,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                logger.info("API key retrieved from helper command")
                return result.stdout.strip()
        except Exception as e:
            logger.error(f"api_key_helper error: {e}")
    
    # Environment variable
    if api_key_env_var and api_key_env_var.strip():
        value = os.environ.get(api_key_env_var.strip())
        if value and value.strip():
            logger.info(f"API key from {api_key_env_var}")
            return value.strip()
    
    return None


def create_enhancer(
    api_key: Optional[str] = None,
    api_key_helper: Optional[str] = None,
    api_key_env_var: Optional[str] = None,
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-4o-mini",
    system_prompt: Optional[str] = None,
    prompt_file: Optional[str] = None,
) -> Optional[TextEnhancer]:
    """Create a TextEnhancer from configuration.
    
    Returns None if no API key can be resolved.
    """
    key = resolve_api_key(api_key, api_key_helper, api_key_env_var)
    
    if not key:
        logger.warning("No API key resolved, text enhancement disabled")
        return None
    
    return TextEnhancer(
        api_key=key,
        base_url=base_url,
        model=model,
        system_prompt=system_prompt,
        prompt_file=prompt_file,
    )
