from pathlib import Path

from loguru import logger

from utils.logger import setup_logging

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TestLogger:
    """Tests for utils.logger module."""

    def test_setup_logging_creates_log_file(self, tmp_path, monkeypatch):
        """setup_logging should create the dump.log sink."""
        monkeypatch.setattr("utils.logger._LOG_FILE", tmp_path / "dump.log")
        monkeypatch.setattr("utils.logger._PROJECT_ROOT", tmp_path)


        import utils.logger as log_mod

        log_mod._LOG_FILE = tmp_path / "dump.log"
        setup_logging(level="DEBUG")

        logger.info("test message from test_setup_logging_creates_log_file")
        log_file = tmp_path / "dump.log"
        assert log_file.exists()
        contents = log_file.read_text()
        assert "test message from test_setup_logging_creates_log_file" in contents

    def test_setup_logging_respects_level(self, tmp_path, monkeypatch):
        """Log file should capture DEBUG even when stderr level is higher."""
        log_file = tmp_path / "dump.log"
        monkeypatch.setattr("utils.logger._LOG_FILE", log_file)

        import utils.logger as log_mod

        log_mod._LOG_FILE = log_file
        setup_logging(level="WARNING")

        logger.debug("debug-level-message")
        assert log_file.exists()
        contents = log_file.read_text()
        assert "debug-level-message" in contents
