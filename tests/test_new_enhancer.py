"""Tests for whossper.enhancer module."""

import os
import pytest
from unittest.mock import MagicMock, patch

from whossper.enhancer import (
    TextEnhancer,
    resolve_api_key,
    create_enhancer,
    DEFAULT_SYSTEM_PROMPT,
)


# =============================================================================
# TextEnhancer Tests
# =============================================================================

class TestTextEnhancer:
    """Tests for TextEnhancer class."""
    
    def test_init_requires_api_key(self):
        """Test that API key is required."""
        with pytest.raises(ValueError, match="API key is required"):
            TextEnhancer(api_key="")
        
        with pytest.raises(ValueError, match="API key is required"):
            TextEnhancer(api_key=None)
    
    @patch("whossper.enhancer.OpenAI")
    def test_init_success(self, mock_openai_class):
        """Test successful initialization."""
        enhancer = TextEnhancer(api_key="test-key", model="gpt-4")
        
        assert enhancer.model == "gpt-4"
        mock_openai_class.assert_called_once()
    
    @patch("whossper.enhancer.OpenAI")
    def test_default_prompt(self, mock_openai_class):
        """Test default system prompt is used."""
        enhancer = TextEnhancer(api_key="test-key")
        
        assert enhancer.system_prompt == DEFAULT_SYSTEM_PROMPT
    
    @patch("whossper.enhancer.OpenAI")
    def test_custom_prompt(self, mock_openai_class):
        """Test custom system prompt."""
        custom = "You are a test prompt."
        enhancer = TextEnhancer(api_key="test-key", system_prompt=custom)
        
        assert enhancer.system_prompt == custom
    
    @patch("whossper.enhancer.OpenAI")
    def test_prompt_from_file(self, mock_openai_class, tmp_path):
        """Test loading prompt from file."""
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("Custom file prompt.")
        
        enhancer = TextEnhancer(
            api_key="test-key",
            prompt_file=str(prompt_file),
        )
        
        assert enhancer.system_prompt == "Custom file prompt."
    
    @patch("whossper.enhancer.OpenAI")
    def test_prompt_priority(self, mock_openai_class, tmp_path):
        """Test custom prompt takes priority over file."""
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("File prompt.")
        
        enhancer = TextEnhancer(
            api_key="test-key",
            system_prompt="Custom takes priority",
            prompt_file=str(prompt_file),
        )
        
        assert enhancer.system_prompt == "Custom takes priority"
    
    @patch("whossper.enhancer.OpenAI")
    def test_missing_prompt_file(self, mock_openai_class):
        """Test fallback when prompt file doesn't exist."""
        enhancer = TextEnhancer(
            api_key="test-key",
            prompt_file="/nonexistent/path.txt",
        )
        
        assert enhancer.system_prompt == DEFAULT_SYSTEM_PROMPT
    
    @patch("whossper.enhancer.OpenAI")
    def test_enhance_empty_text(self, mock_openai_class):
        """Test enhance rejects empty text."""
        enhancer = TextEnhancer(api_key="test-key")
        
        with pytest.raises(ValueError, match="cannot be empty"):
            enhancer.enhance("")
        
        with pytest.raises(ValueError, match="cannot be empty"):
            enhancer.enhance("   ")
    
    @patch("whossper.enhancer.OpenAI")
    def test_enhance_success(self, mock_openai_class):
        """Test successful text enhancement."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Enhanced text here"
        mock_client.chat.completions.create.return_value = mock_response
        
        enhancer = TextEnhancer(api_key="test-key")
        result = enhancer.enhance("Some raw text")
        
        assert result == "Enhanced text here"
        mock_client.chat.completions.create.assert_called_once()
    
    @patch("whossper.enhancer.OpenAI")
    def test_enhance_api_error(self, mock_openai_class):
        """Test enhance handles API errors."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        enhancer = TextEnhancer(api_key="test-key")
        
        with pytest.raises(Exception, match="API Error"):
            enhancer.enhance("Some text")
    
    @patch("whossper.enhancer.OpenAI")
    def test_callable_interface(self, mock_openai_class):
        """Test enhancer can be called directly."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Result"
        mock_client.chat.completions.create.return_value = mock_response
        
        enhancer = TextEnhancer(api_key="test-key")
        result = enhancer("Some text")  # Call directly
        
        assert result == "Result"
    
    @patch("whossper.enhancer.OpenAI")
    def test_client_property(self, mock_openai_class):
        """Test client property returns OpenAI client."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        enhancer = TextEnhancer(api_key="test-key")
        
        assert enhancer.client is mock_client


# =============================================================================
# resolve_api_key Tests
# =============================================================================

class TestResolveApiKey:
    """Tests for resolve_api_key function."""
    
    def test_direct_key(self):
        """Test direct API key takes priority."""
        result = resolve_api_key(api_key="direct-key")
        assert result == "direct-key"
    
    def test_direct_key_strips_whitespace(self):
        """Test whitespace is stripped."""
        result = resolve_api_key(api_key="  key-with-spaces  ")
        assert result == "key-with-spaces"
    
    def test_empty_direct_key(self):
        """Test empty direct key is skipped."""
        result = resolve_api_key(api_key="", api_key_env_var="TEST_VAR")
        assert result is None
    
    @patch("subprocess.run")
    def test_helper_command(self, mock_run):
        """Test API key from helper command."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="helper-key\n",
        )
        
        result = resolve_api_key(api_key_helper="echo helper-key")
        assert result == "helper-key"
    
    @patch("subprocess.run")
    def test_helper_command_failure(self, mock_run):
        """Test helper command failure falls through."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        
        result = resolve_api_key(api_key_helper="failing-command")
        assert result is None
    
    @patch("subprocess.run")
    def test_helper_command_timeout(self, mock_run):
        """Test helper command timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 30)
        
        result = resolve_api_key(api_key_helper="slow-command")
        assert result is None
    
    def test_env_var(self):
        """Test API key from environment variable."""
        with patch.dict(os.environ, {"MY_API_KEY": "env-key"}):
            result = resolve_api_key(api_key_env_var="MY_API_KEY")
            assert result == "env-key"
    
    def test_env_var_not_set(self):
        """Test missing environment variable."""
        result = resolve_api_key(api_key_env_var="NONEXISTENT_VAR_XYZ")
        assert result is None
    
    def test_priority_order(self):
        """Test priority: direct > helper > env."""
        with patch.dict(os.environ, {"ENV_KEY": "env-value"}):
            # Direct wins
            result = resolve_api_key(
                api_key="direct",
                api_key_helper="echo helper",
                api_key_env_var="ENV_KEY",
            )
            assert result == "direct"
    
    @patch("subprocess.run")
    def test_helper_priority_over_env(self, mock_run):
        """Test helper takes priority over env."""
        mock_run.return_value = MagicMock(returncode=0, stdout="helper-key")
        
        with patch.dict(os.environ, {"ENV_KEY": "env-value"}):
            result = resolve_api_key(
                api_key_helper="get-key",
                api_key_env_var="ENV_KEY",
            )
            assert result == "helper-key"
    
    def test_all_none(self):
        """Test returns None when nothing provided."""
        result = resolve_api_key()
        assert result is None


# =============================================================================
# create_enhancer Tests
# =============================================================================

class TestCreateEnhancer:
    """Tests for create_enhancer function."""
    
    @patch("whossper.enhancer.OpenAI")
    def test_create_with_direct_key(self, mock_openai_class):
        """Test creating enhancer with direct key."""
        enhancer = create_enhancer(api_key="test-key")
        
        assert enhancer is not None
        assert isinstance(enhancer, TextEnhancer)
    
    def test_create_without_key(self):
        """Test returns None without API key."""
        enhancer = create_enhancer()
        assert enhancer is None
    
    @patch("whossper.enhancer.OpenAI")
    def test_create_with_all_options(self, mock_openai_class):
        """Test creating enhancer with all options."""
        enhancer = create_enhancer(
            api_key="key",
            base_url="https://custom.api/v1",
            model="gpt-4",
            system_prompt="Custom prompt",
        )
        
        assert enhancer is not None
        assert enhancer.model == "gpt-4"
        assert enhancer.system_prompt == "Custom prompt"
    
    @patch("subprocess.run")
    @patch("whossper.enhancer.OpenAI")
    def test_create_with_helper(self, mock_openai_class, mock_run):
        """Test creating enhancer with helper command."""
        mock_run.return_value = MagicMock(returncode=0, stdout="helper-key")
        
        enhancer = create_enhancer(api_key_helper="get-key")
        
        assert enhancer is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
