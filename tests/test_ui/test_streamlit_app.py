"""Tests for the Streamlit UI's API-calling and display logic.

These tests exercise the helper functions defined in ui/streamlit_app.py
without launching a Streamlit server. All HTTP calls are mocked.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _patch_streamlit():
    """Replace Streamlit module so importing streamlit_app doesn't start a server."""
    mock_st = MagicMock()
    mock_st.set_page_config = MagicMock()
    mock_st.title = MagicMock()
    mock_st.caption = MagicMock()
    mock_st.markdown = MagicMock()
    mock_st.text_input = MagicMock(return_value="")
    mock_st.text_area = MagicMock(return_value="")
    mock_st.button = MagicMock(return_value=False)
    mock_st.spinner = MagicMock(return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock()))
    mock_st.columns = MagicMock(side_effect=lambda n: [MagicMock() for _ in range(n)])
    mock_st.divider = MagicMock()
    mock_st.metric = MagicMock()
    mock_st.progress = MagicMock()
    mock_st.success = MagicMock()
    mock_st.warning = MagicMock()
    mock_st.error = MagicMock()
    mock_st.info = MagicMock()
    mock_st.write = MagicMock()
    mock_st.subheader = MagicMock()
    mock_st.tabs = MagicMock(return_value=[MagicMock(), MagicMock(), MagicMock()])
    mock_st.expander = MagicMock(return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock()))

    with patch.dict("sys.modules", {"streamlit": mock_st}):
        yield mock_st


def _import_app():
    import importlib

    import ui.streamlit_app as app_mod

    importlib.reload(app_mod)
    return app_mod


class TestApiCall:
    @patch("requests.post")
    def test_success_returns_json(self, mock_post, _patch_streamlit):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"stock": {"ticker": "RELIANCE.NS"}, "summary": "OK"}
        mock_post.return_value = mock_resp

        app = _import_app()
        result = app._api_call("/analyze_stock", {"ticker": "RELIANCE"})

        assert result is not None
        assert result["stock"]["ticker"] == "RELIANCE.NS"
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_api_error_returns_none(self, mock_post, _patch_streamlit):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {"detail": "Invalid ticker"}
        mock_post.return_value = mock_resp

        app = _import_app()
        result = app._api_call("/analyze_stock", {"ticker": "$BAD!"})

        assert result is None

    @patch("requests.post")
    def test_connection_error_returns_none(self, mock_post, _patch_streamlit):
        import requests

        mock_post.side_effect = requests.ConnectionError("refused")

        app = _import_app()
        result = app._api_call("/analyze_stock", {"ticker": "RELIANCE"})

        assert result is None

    @patch("requests.post")
    def test_timeout_returns_none(self, mock_post, _patch_streamlit):
        import requests

        mock_post.side_effect = requests.Timeout("timed out")

        app = _import_app()
        result = app._api_call("/analyze_stock", {"ticker": "RELIANCE"})

        assert result is None


class TestDisplayStock:
    def test_display_stock_renders(self, _patch_streamlit):
        app = _import_app()
        stock = {
            "ticker": "RELIANCE.NS",
            "fundamental_score": 75.0,
            "fundamental_verdict": "Strong",
            "technical_score": 70.0,
            "technical_verdict": "Bullish",
            "sentiment_score": 65.0,
            "sentiment_verdict": "Positive",
            "final_score": 72.0,
            "recommendation": "Buy",
            "errors": {},
        }
        app._display_stock(stock)
        _patch_streamlit.metric.assert_called()
        _patch_streamlit.progress.assert_called()


class TestHelpers:
    def test_score_color_green(self, _patch_streamlit):
        app = _import_app()
        assert app._score_color(80.0) == "green"

    def test_score_color_orange(self, _patch_streamlit):
        app = _import_app()
        assert app._score_color(60.0) == "orange"

    def test_score_color_red(self, _patch_streamlit):
        app = _import_app()
        assert app._score_color(30.0) == "red"

    def test_score_color_none(self, _patch_streamlit):
        app = _import_app()
        assert app._score_color(None) == "gray"

    def test_recommendation_emoji(self, _patch_streamlit):
        app = _import_app()
        assert app._recommendation_emoji("Strong Buy") == "🟢"
        assert app._recommendation_emoji("Buy") == "🟡"
        assert app._recommendation_emoji("Hold") == "🟠"
        assert app._recommendation_emoji("Avoid") == "🔴"
        assert app._recommendation_emoji("Unknown") == "⚪"
