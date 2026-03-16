from unittest.mock import MagicMock, patch


class TestGenerateWhenDisabled:
    @patch("utils.llm_client.genai")
    def test_returns_none_when_disabled(self, _mock_genai):
        with patch("utils.config.LLM_ENABLED", False):
            from utils.llm_client import generate

            assert generate("any prompt") is None

    @patch("utils.llm_client.genai")
    def test_never_calls_api_when_disabled(self, mock_genai):
        with patch("utils.config.LLM_ENABLED", False):
            from utils.llm_client import generate

            generate("any prompt")
            mock_genai.Client.assert_not_called()


class TestGenerateWhenEnabled:
    def _setup_mock_client(self, mock_genai, response_text):
        mock_response = MagicMock()
        mock_response.text = response_text
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        return mock_client

    @patch("utils.llm_client._client", None)
    @patch("utils.llm_client.genai")
    def test_returns_text_on_success(self, mock_genai):
        self._setup_mock_client(mock_genai, "  LLM narrative output  ")

        with (
            patch("utils.config.LLM_ENABLED", True),
            patch("utils.config.LLM_MODEL", "gemini-2.0-flash"),
            patch("utils.config.LLM_TEMPERATURE", 0.3),
            patch("utils.config.GEMINI_API_KEY", "test-key"),
        ):
            from utils.llm_client import generate

            result = generate("test prompt")

        assert result == "LLM narrative output"

    @patch("utils.llm_client._client", None)
    @patch("utils.llm_client.genai")
    def test_returns_none_on_empty_response(self, mock_genai):
        self._setup_mock_client(mock_genai, "")

        with (
            patch("utils.config.LLM_ENABLED", True),
            patch("utils.config.LLM_MODEL", "gemini-2.0-flash"),
            patch("utils.config.LLM_TEMPERATURE", 0.3),
            patch("utils.config.GEMINI_API_KEY", "test-key"),
        ):
            from utils.llm_client import generate

            assert generate("test") is None

    @patch("utils.llm_client._client", None)
    @patch("utils.llm_client.genai")
    def test_returns_none_on_api_error(self, mock_genai):
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError("API error")
        mock_genai.Client.return_value = mock_client

        with (
            patch("utils.config.LLM_ENABLED", True),
            patch("utils.config.LLM_MODEL", "gemini-2.0-flash"),
            patch("utils.config.LLM_TEMPERATURE", 0.3),
            patch("utils.config.GEMINI_API_KEY", "test-key"),
        ):
            from utils.llm_client import generate

            assert generate("test") is None

    @patch("utils.llm_client._client", None)
    @patch("utils.llm_client.genai")
    def test_returns_none_when_response_is_none(self, mock_genai):
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = None
        mock_genai.Client.return_value = mock_client

        with (
            patch("utils.config.LLM_ENABLED", True),
            patch("utils.config.LLM_MODEL", "gemini-2.0-flash"),
            patch("utils.config.LLM_TEMPERATURE", 0.3),
            patch("utils.config.GEMINI_API_KEY", "test-key"),
        ):
            from utils.llm_client import generate

            assert generate("test") is None


class TestGenerateWhenSdkMissing:
    @patch("utils.llm_client._client", None)
    def test_returns_none_when_genai_is_none(self):
        with (
            patch("utils.llm_client.genai", None),
            patch("utils.config.LLM_ENABLED", True),
        ):
            from utils.llm_client import generate

            assert generate("test") is None


class TestGetClient:
    @patch("utils.llm_client._client", None)
    @patch("utils.llm_client.genai")
    def test_creates_client_with_api_key(self, mock_genai):
        with patch("utils.config.GEMINI_API_KEY", "test-key-abc"):
            from utils.llm_client import _get_client

            _get_client()
        mock_genai.Client.assert_called_once_with(api_key="test-key-abc")

    @patch("utils.llm_client.genai")
    def test_returns_existing_client(self, mock_genai):
        sentinel = MagicMock()
        with patch("utils.llm_client._client", sentinel):
            from utils.llm_client import _get_client

            result = _get_client()
        assert result is sentinel
        mock_genai.Client.assert_not_called()

    @patch("utils.llm_client._client", None)
    def test_returns_none_when_genai_missing(self):
        with patch("utils.llm_client.genai", None):
            from utils.llm_client import _get_client

            assert _get_client() is None
