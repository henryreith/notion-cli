"""Tests for modes.py."""
import os
import pytest
from unittest.mock import patch
from click.testing import CliRunner

from notion.modes import get_mode, confirm


class TestGetMode:
    def test_explicit_flag_takes_priority(self):
        assert get_mode("interactive") == "interactive"
        assert get_mode("ci") == "ci"
        assert get_mode("auto") == "auto"

    def test_env_var_used_when_no_explicit(self, monkeypatch):
        monkeypatch.setenv("NOTION_MODE", "ci")
        assert get_mode() == "ci"

    def test_env_var_interactive(self, monkeypatch):
        monkeypatch.setenv("NOTION_MODE", "interactive")
        assert get_mode() == "interactive"

    def test_explicit_overrides_env(self, monkeypatch):
        monkeypatch.setenv("NOTION_MODE", "ci")
        assert get_mode("interactive") == "interactive"

    def test_invalid_env_falls_through_to_tty(self, monkeypatch):
        monkeypatch.setenv("NOTION_MODE", "invalid_value")
        # With no TTY (test environment), should return "auto"
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.isatty.return_value = False
            result = get_mode()
        assert result == "auto"

    def test_tty_returns_interactive(self, monkeypatch):
        monkeypatch.delenv("NOTION_MODE", raising=False)
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.isatty.return_value = True
            result = get_mode()
        assert result == "interactive"

    def test_no_tty_returns_auto(self, monkeypatch):
        monkeypatch.delenv("NOTION_MODE", raising=False)
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.isatty.return_value = False
            result = get_mode()
        assert result == "auto"


class TestConfirm:
    def test_auto_mode_always_true(self):
        assert confirm("Proceed?", mode="auto") is True

    def test_ci_mode_always_true(self):
        assert confirm("Proceed?", mode="ci") is True

    def test_interactive_mode_prompts(self):
        with patch("click.confirm", return_value=True) as mock_confirm:
            result = confirm("Proceed?", mode="interactive")
            assert result is True
            mock_confirm.assert_called_once()

    def test_interactive_mode_can_cancel(self):
        with patch("click.confirm", return_value=False) as mock_confirm:
            result = confirm("Proceed?", mode="interactive")
            assert result is False

    def test_no_mode_uses_get_mode(self, monkeypatch):
        monkeypatch.setenv("NOTION_MODE", "auto")
        result = confirm("Proceed?")
        assert result is True
