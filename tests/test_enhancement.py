"""Tests for text enhancement module."""

import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from whossper.enhancement.openai_enhancer import (
    TextEnhancer,
    create_enhancer_from_config,
    resolve_api_key,
    DEFAULT_SYSTEM_PROMPT,
)


class TestResolveApiKey:
    """Tests for API key resolution."""
    
    def test_direct_api_key_priority(self):
        """Direct api_key takes highest priority."""
        result = resolve_api_key(
            api_key="direct-key",
            api_key_helper="echo helper-key",
            api_key_env_var="TEST_KEY"
        )
        assert result == "direct-key"
    
    def test_helper_command_priority(self):
        """api_key_helper takes second priority when api_key is empty."""
        result = resolve_api_key(
            api_key="",
            api_key_helper="echo helper-key",
            api_key_env_var="TEST_KEY"
        )
        assert result == "helper-key"
    
    def test_env_var_priority(self):
        """api_key_env_var takes third priority."""
        with patch.dict(os.environ, {"MY_API_KEY": "env-key"}):
            result = resolve_api_key(
                api_key="",
                api_key_helper=None,
                api_key_env_var="MY_API_KEY"
            )
            assert result == "env-key"
    
    def test_no_key_returns_none(self):
        """Returns None when no key source provides a value."""
        result = resolve_api_key(
            api_key="",
            api_key_helper=None,
            api_key_env_var=None
        )
        assert result is None
    
    def test_helper_command_failure(self):
        """Failed helper command falls through to env var."""
        with patch.dict(os.environ, {"FALLBACK_KEY": "fallback-value"}):
            result = resolve_api_key(
                api_key="",
                api_key_helper="false",  # Command that fails
                api_key_env_var="FALLBACK_KEY"
            )
            assert result == "fallback-value"
    
    def test_whitespace_trimmed(self):
        """Whitespace is trimmed from all sources."""
        result = resolve_api_key(api_key="  trimmed-key  ")
        assert result == "trimmed-key"
    
    def test_empty_env_var_skipped(self):
        """Empty environment variable is treated as not set."""
        with patch.dict(os.environ, {"EMPTY_KEY": ""}):
            result = resolve_api_key(
                api_key="",
                api_key_helper=None,
                api_key_env_var="EMPTY_KEY"
            )
            assert result is None


class TestTextEnhancerInit:
    """Tests for TextEnhancer initialization."""
    
    @patch('whossper.enhancement.openai_enhancer.OpenAI')
    def test_initialization(self, mock_openai):
        """Test basic initialization."""
        enhancer = TextEnhancer(
            api_key="test-key",
            api_base_url="https://api.openai.com/v1",
            model="gpt-4o-mini"
        )
        
        assert enhancer.api_key == "test-key"
        assert enhancer.model == "gpt-4o-mini"
        assert enhancer.system_prompt == DEFAULT_SYSTEM_PROMPT
    
    def test_missing_api_key_raises(self):
        """Test missing API key raises ValueError."""
        with pytest.raises(ValueError, match="API key is required"):
            TextEnhancer(api_key="")
    
    @patch('whossper.enhancement.openai_enhancer.OpenAI')
    def test_custom_system_prompt(self, mock_openai):
        """Test custom system prompt is used."""
        custom_prompt = "You are a custom assistant."
        
        enhancer = TextEnhancer(
            api_key="test-key",
            system_prompt=custom_prompt
        )
        
        assert enhancer.system_prompt == custom_prompt
    
    @patch('whossper.enhancement.openai_enhancer.OpenAI')
    def test_system_prompt_from_file(self, mock_openai, tmp_dir):
        """Test loading system prompt from file."""
        prompt_file = tmp_dir / "prompt.txt"
        prompt_file.write_text("Custom prompt from file")
        
        enhancer = TextEnhancer(
            api_key="test-key",
            system_prompt_file=str(prompt_file)
        )
        
        assert enhancer.system_prompt == "Custom prompt from file"
    
    @patch('whossper.enhancement.openai_enhancer.OpenAI')
    def test_custom_prompt_overrides_file(self, mock_openai, tmp_dir):
        """Test custom prompt overrides file."""
        prompt_file = tmp_dir / "prompt.txt"
        prompt_file.write_text("File prompt")
        
        enhancer = TextEnhancer(
            api_key="test-key",
            system_prompt="Inline prompt",
            system_prompt_file=str(prompt_file)
        )
        
        assert enhancer.system_prompt == "Inline prompt"
    
    @patch('whossper.enhancement.openai_enhancer.OpenAI')
    def test_missing_prompt_file_uses_default(self, mock_openai):
        """Test missing prompt file falls back to default."""
        enhancer = TextEnhancer(
            api_key="test-key",
            system_prompt_file="/nonexistent/path.txt"
        )
        
        assert enhancer.system_prompt == DEFAULT_SYSTEM_PROMPT


class TestTextEnhancerEnhance:
    """Tests for text enhancement."""
    
    @patch('whossper.enhancement.openai_enhancer.OpenAI')
    def test_enhance_text(self, mock_openai):
        """Test basic text enhancement."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Enhanced text"
        mock_client.chat.completions.create.return_value = mock_response
        
        enhancer = TextEnhancer(api_key="test-key")
        result = enhancer.enhance("um hello world")
        
        assert result == "Enhanced text"
        mock_client.chat.completions.create.assert_called_once()
    
    @patch('whossper.enhancement.openai_enhancer.OpenAI')
    def test_enhance_empty_text_raises(self, mock_openai):
        """Test enhancing empty text raises error."""
        enhancer = TextEnhancer(api_key="test-key")
        
        with pytest.raises(ValueError, match="cannot be empty"):
            enhancer.enhance("")
    
    @patch('whossper.enhancement.openai_enhancer.OpenAI')
    def test_enhance_whitespace_only_raises(self, mock_openai):
        """Test enhancing whitespace-only text raises error."""
        enhancer = TextEnhancer(api_key="test-key")
        
        with pytest.raises(ValueError, match="cannot be empty"):
            enhancer.enhance("   ")
    
    @patch('whossper.enhancement.openai_enhancer.OpenAI')
    def test_enhance_with_context(self, mock_openai):
        """Test enhancement with context."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Contextual result"
        mock_client.chat.completions.create.return_value = mock_response
        
        enhancer = TextEnhancer(api_key="test-key")
        result = enhancer.enhance("hello", context="Technical document")
        
        assert result == "Contextual result"
        
        # Verify context was included in messages
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        context_messages = [m for m in messages if "Context" in m.get("content", "")]
        assert len(context_messages) == 1
    
    @patch('whossper.enhancement.openai_enhancer.OpenAI')
    def test_enhance_with_custom_temperature(self, mock_openai):
        """Test enhancement with custom temperature."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Result"
        mock_client.chat.completions.create.return_value = mock_response
        
        enhancer = TextEnhancer(api_key="test-key")
        enhancer.enhance("test", temperature=0.7)
        
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["temperature"] == 0.7


class TestTextEnhancerInstruction:
    """Tests for instruction-based enhancement."""
    
    @patch('whossper.enhancement.openai_enhancer.OpenAI')
    def test_enhance_with_instruction(self, mock_openai):
        """Test enhancement with specific instruction."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Processed result"
        mock_client.chat.completions.create.return_value = mock_response
        
        enhancer = TextEnhancer(api_key="test-key")
        result = enhancer.enhance_with_instruction(
            "hello world",
            "Make it formal"
        )
        
        assert result == "Processed result"
    
    @patch('whossper.enhancement.openai_enhancer.OpenAI')
    def test_instruction_empty_text_raises(self, mock_openai):
        """Test instruction with empty text raises error."""
        enhancer = TextEnhancer(api_key="test-key")
        
        with pytest.raises(ValueError, match="Text cannot be empty"):
            enhancer.enhance_with_instruction("", "instruction")
    
    @patch('whossper.enhancement.openai_enhancer.OpenAI')
    def test_empty_instruction_raises(self, mock_openai):
        """Test empty instruction raises error."""
        enhancer = TextEnhancer(api_key="test-key")
        
        with pytest.raises(ValueError, match="Instruction cannot be empty"):
            enhancer.enhance_with_instruction("text", "")


class TestTextEnhancerBatch:
    """Tests for batch enhancement."""
    
    @patch('whossper.enhancement.openai_enhancer.OpenAI')
    def test_batch_enhance(self, mock_openai):
        """Test batch enhancement of multiple texts."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Enhanced"
        mock_client.chat.completions.create.return_value = mock_response
        
        enhancer = TextEnhancer(api_key="test-key")
        results = enhancer.batch_enhance(["text1", "text2", "text3"])
        
        assert len(results) == 3
        assert all(r == "Enhanced" for r in results)
        assert mock_client.chat.completions.create.call_count == 3
    
    @patch('whossper.enhancement.openai_enhancer.OpenAI')
    def test_batch_keeps_original_on_failure(self, mock_openai):
        """Test batch keeps original text when enhancement fails."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # First call succeeds, second fails, third succeeds
        mock_response_ok = MagicMock()
        mock_response_ok.choices = [MagicMock()]
        mock_response_ok.choices[0].message.content = "Enhanced"
        
        mock_client.chat.completions.create.side_effect = [
            mock_response_ok,
            Exception("API Error"),
            mock_response_ok,
        ]
        
        enhancer = TextEnhancer(api_key="test-key")
        results = enhancer.batch_enhance(["text1", "text2", "text3"])
        
        assert results[0] == "Enhanced"
        assert results[1] == "text2"  # Original kept
        assert results[2] == "Enhanced"


class TestTextEnhancerConnection:
    """Tests for connection testing."""
    
    @patch('whossper.enhancement.openai_enhancer.OpenAI')
    def test_connection_success(self, mock_openai):
        """Test successful connection test."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hi"
        mock_client.chat.completions.create.return_value = mock_response
        
        enhancer = TextEnhancer(api_key="test-key")
        result = enhancer.test_connection()
        
        assert result is True
    
    @patch('whossper.enhancement.openai_enhancer.OpenAI')
    def test_connection_failure(self, mock_openai):
        """Test failed connection test."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("Connection failed")
        
        enhancer = TextEnhancer(api_key="test-key")
        result = enhancer.test_connection()
        
        assert result is False


class TestCreateEnhancerFromConfig:
    """Tests for factory function."""
    
    @patch('whossper.enhancement.openai_enhancer.OpenAI')
    def test_create_with_valid_key(self, mock_openai):
        """Test creating enhancer with valid config."""
        enhancer = create_enhancer_from_config(
            api_key="test-key",
            model="gpt-4"
        )
        
        assert enhancer is not None
        assert enhancer.model == "gpt-4"
    
    def test_create_without_key_returns_none(self):
        """Test creating enhancer without key returns None."""
        enhancer = create_enhancer_from_config(api_key="")
        
        assert enhancer is None
    
    @patch('whossper.enhancement.openai_enhancer.OpenAI')
    def test_create_with_custom_url(self, mock_openai):
        """Test creating enhancer with custom API URL."""
        enhancer = create_enhancer_from_config(
            api_key="test-key",
            api_base_url="http://localhost:8080/v1"
        )
        
        assert enhancer is not None
        assert enhancer.api_base_url == "http://localhost:8080/v1"


class TestDefaultSystemPrompt:
    """Tests for default system prompt."""
    
    def test_default_prompt_content(self):
        """Test default prompt has expected content."""
        assert "grammar" in DEFAULT_SYSTEM_PROMPT.lower()
        assert "punctuation" in DEFAULT_SYSTEM_PROMPT.lower()
        assert "filler" in DEFAULT_SYSTEM_PROMPT.lower()
    
    def test_default_prompt_not_empty(self):
        """Test default prompt is not empty."""
        assert len(DEFAULT_SYSTEM_PROMPT) > 100
