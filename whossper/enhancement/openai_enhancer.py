"""Text enhancement using OpenAI-compatible APIs."""

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

from openai import OpenAI


logger = logging.getLogger(__name__)


# Default system prompt for text enhancement
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
        api_base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        system_prompt: Optional[str] = None,
        system_prompt_file: Optional[str] = None,
    ):
        """Initialize text enhancer.
        
        Args:
            api_key: API key for authentication.
            api_base_url: Base URL for OpenAI-compatible API.
            model: Model to use for enhancement.
            system_prompt: Custom system prompt (overrides file).
            system_prompt_file: Path to system prompt file.
        """
        if not api_key:
            raise ValueError("API key is required for text enhancement")
        
        self.api_key = api_key
        self.api_base_url = api_base_url
        self.model = model
        
        # Load system prompt
        self.system_prompt = self._load_system_prompt(
            system_prompt, 
            system_prompt_file
        )
        
        # Initialize OpenAI client
        self._client = OpenAI(
            api_key=api_key,
            base_url=api_base_url
        )
        
        logger.info(f"TextEnhancer initialized with model={model}")
    
    def _load_system_prompt(
        self,
        custom_prompt: Optional[str],
        prompt_file: Optional[str]
    ) -> str:
        """Load system prompt from various sources.
        
        Priority: custom_prompt > prompt_file > default
        
        Args:
            custom_prompt: Inline custom prompt.
            prompt_file: Path to prompt file.
            
        Returns:
            System prompt string.
        """
        if custom_prompt:
            logger.debug("Using custom system prompt")
            return custom_prompt
        
        if prompt_file:
            path = Path(prompt_file)
            if path.exists():
                logger.debug(f"Loading system prompt from {prompt_file}")
                return path.read_text().strip()
            else:
                logger.warning(f"Prompt file not found: {prompt_file}, using default")
        
        return DEFAULT_SYSTEM_PROMPT
    
    def enhance(
        self,
        text: str,
        context: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str:
        """Enhance transcribed text using LLM.
        
        Args:
            text: Raw transcribed text to enhance.
            context: Optional context to help with enhancement.
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
        
        # Build messages
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        if context:
            messages.append({
                "role": "user",
                "content": f"Context: {context}"
            })
        
        messages.append({
            "role": "user", 
            "content": f"Please improve this transcribed speech:\n\n{text}"
        })
        
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            enhanced_text = response.choices[0].message.content.strip()
            
            logger.info(f"Enhanced text: {len(enhanced_text)} chars")
            return enhanced_text
            
        except Exception as e:
            logger.error(f"Enhancement failed: {e}")
            raise
    
    def enhance_with_instruction(
        self,
        text: str,
        instruction: str,
        temperature: float = 0.5,
        max_tokens: int = 2048,
    ) -> str:
        """Enhance text with a specific instruction.
        
        Args:
            text: Text to process.
            instruction: Specific instruction for processing.
            temperature: Model temperature.
            max_tokens: Maximum tokens in response.
            
        Returns:
            Processed text.
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        if not instruction or not instruction.strip():
            raise ValueError("Instruction cannot be empty")
        
        logger.info(f"Processing text with instruction: {instruction[:50]}...")
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": f"Instruction: {instruction}\n\nText to process:\n{text}"
            }
        ]
        
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            result = response.choices[0].message.content.strip()
            
            logger.info(f"Processed text: {len(result)} chars")
            return result
            
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            raise
    
    def batch_enhance(
        self,
        texts: list[str],
        temperature: float = 0.3,
    ) -> list[str]:
        """Enhance multiple texts in batch.
        
        Args:
            texts: List of texts to enhance.
            temperature: Model temperature.
            
        Returns:
            List of enhanced texts.
        """
        results = []
        
        for i, text in enumerate(texts):
            try:
                enhanced = self.enhance(text, temperature=temperature)
                results.append(enhanced)
                logger.debug(f"Batch item {i+1}/{len(texts)} complete")
            except Exception as e:
                logger.error(f"Batch item {i+1} failed: {e}")
                # Keep original on failure
                results.append(text)
        
        return results
    
    @property
    def client(self) -> OpenAI:
        """Get the OpenAI client."""
        return self._client
    
    def test_connection(self) -> bool:
        """Test API connection.
        
        Returns:
            True if connection works.
        """
        try:
            # Make a minimal API call
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5,
            )
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


def resolve_api_key(
    api_key: Optional[str] = None,
    api_key_helper: Optional[str] = None,
    api_key_env_var: Optional[str] = None,
) -> Optional[str]:
    """Resolve API key from various sources with priority.
    
    Priority order:
    1. Direct api_key value (if non-empty)
    2. api_key_helper command output
    3. api_key_env_var environment variable
    
    Args:
        api_key: Direct API key value.
        api_key_helper: Shell command to retrieve API key.
        api_key_env_var: Environment variable name containing API key.
        
    Returns:
        Resolved API key or None if not found.
    """
    # Priority 1: Direct api_key value
    if api_key and api_key.strip():
        logger.debug("Using direct api_key value")
        return api_key.strip()
    
    # Priority 2: Run helper command
    if api_key_helper and api_key_helper.strip():
        logger.debug(f"Running api_key_helper command: {api_key_helper[:50]}...")
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
            else:
                logger.warning(f"api_key_helper command failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            logger.error("api_key_helper command timed out")
        except Exception as e:
            logger.error(f"api_key_helper command error: {e}")
    
    # Priority 3: Environment variable
    if api_key_env_var and api_key_env_var.strip():
        env_value = os.environ.get(api_key_env_var.strip())
        if env_value and env_value.strip():
            logger.info(f"API key retrieved from environment variable: {api_key_env_var}")
            return env_value.strip()
        else:
            logger.debug(f"Environment variable {api_key_env_var} not set or empty")
    
    return None


def create_enhancer_from_config(
    api_key: Optional[str] = None,
    api_key_helper: Optional[str] = None,
    api_key_env_var: Optional[str] = None,
    api_base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-4o-mini",
    system_prompt_file: Optional[str] = None,
    custom_system_prompt: Optional[str] = None,
) -> Optional[TextEnhancer]:
    """Create a TextEnhancer from configuration.
    
    API key is resolved with priority: api_key > api_key_helper > api_key_env_var
    
    Args:
        api_key: Direct API key value.
        api_key_helper: Shell command to retrieve API key.
        api_key_env_var: Environment variable name for API key.
        api_base_url: API base URL.
        model: Model name.
        system_prompt_file: Path to prompt file.
        custom_system_prompt: Custom prompt override.
        
    Returns:
        TextEnhancer instance or None if no API key resolved.
    """
    resolved_key = resolve_api_key(api_key, api_key_helper, api_key_env_var)
    
    if not resolved_key:
        logger.warning("No API key resolved, text enhancement disabled")
        return None
    
    return TextEnhancer(
        api_key=resolved_key,
        api_base_url=api_base_url,
        model=model,
        system_prompt=custom_system_prompt,
        system_prompt_file=system_prompt_file,
    )

