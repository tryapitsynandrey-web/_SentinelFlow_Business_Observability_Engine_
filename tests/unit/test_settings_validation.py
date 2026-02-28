import pytest
import os
from pydantic import ValidationError

from src.config.settings import AppSettings

def test_app_settings_missing_vars(monkeypatch):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    
    settings = AppSettings()
    
    missing = settings.validate_required_integrations(["slack_webhook", "email"])
    assert "SLACK_WEBHOOK_URL" in missing
    assert "SMTP configuration (HOST, PORT, FROM)" in missing

def test_app_settings_validation_url(monkeypatch):
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "http://insecure.com")

    with pytest.raises(ValidationError):
        AppSettings() # Requires HTTPS exclusively based on after validator

def test_app_settings_valid(monkeypatch):
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/test")
    monkeypatch.setenv("SMTP_HOST", "smtp.test.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_FROM", "test@test.com")
    
    settings = AppSettings()
    missing = settings.validate_required_integrations(["slack_webhook", "email"])
    
    assert len(missing) == 0
    assert str(settings.slack_webhook_url) == "https://hooks.slack.com/services/test"
