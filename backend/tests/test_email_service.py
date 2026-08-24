import sys
from types import SimpleNamespace

import pytest

from services.email_service import EmailService


class SMTPConnectTimeoutError(Exception):
    pass


@pytest.mark.anyio
async def test_smtp_uses_configured_timeout_and_starttls(monkeypatch):
    calls = {}

    async def fake_send(_message, **kwargs):
        calls.update(kwargs)

    fake_aiosmtplib = SimpleNamespace(
        send=fake_send,
        errors=SimpleNamespace(SMTPConnectTimeoutError=SMTPConnectTimeoutError),
    )
    monkeypatch.setitem(sys.modules, "aiosmtplib", fake_aiosmtplib)

    from config import settings

    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    monkeypatch.setattr(settings, "SMTP_USERNAME", "user@example.com")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "app-password")
    monkeypatch.setattr(settings, "SMTP_USE_TLS", True)
    monkeypatch.setattr(settings, "SMTP_TIMEOUT_SECONDS", 7.0)

    success = await EmailService()._send_smtp(
        ["recipient@example.com"],
        "Subject",
        "<p>Hello</p>",
        "Hello",
    )

    assert success is True
    assert calls["hostname"] == "smtp.gmail.com"
    assert calls["port"] == 587
    assert calls["start_tls"] is True
    assert calls["use_tls"] is False
    assert calls["timeout"] == 7.0


@pytest.mark.anyio
async def test_smtp_uses_direct_tls_on_port_465(monkeypatch):
    calls = {}

    async def fake_send(_message, **kwargs):
        calls.update(kwargs)

    fake_aiosmtplib = SimpleNamespace(
        send=fake_send,
        errors=SimpleNamespace(SMTPConnectTimeoutError=SMTPConnectTimeoutError),
    )
    monkeypatch.setitem(sys.modules, "aiosmtplib", fake_aiosmtplib)

    from config import settings

    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setattr(settings, "SMTP_PORT", 465)
    monkeypatch.setattr(settings, "SMTP_USERNAME", "user@example.com")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "app-password")
    monkeypatch.setattr(settings, "SMTP_USE_TLS", True)
    monkeypatch.setattr(settings, "SMTP_TIMEOUT_SECONDS", 7.0)

    success = await EmailService()._send_smtp(
        ["recipient@example.com"],
        "Subject",
        "<p>Hello</p>",
        "Hello",
    )

    assert success is True
    assert calls["start_tls"] is False
    assert calls["use_tls"] is True


@pytest.mark.anyio
async def test_smtp_timeout_returns_false(monkeypatch):
    async def fake_send(_message, **_kwargs):
        raise SMTPConnectTimeoutError()

    fake_aiosmtplib = SimpleNamespace(
        send=fake_send,
        errors=SimpleNamespace(SMTPConnectTimeoutError=SMTPConnectTimeoutError),
    )
    monkeypatch.setitem(sys.modules, "aiosmtplib", fake_aiosmtplib)

    from config import settings

    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    monkeypatch.setattr(settings, "SMTP_USERNAME", "user@example.com")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "app-password")
    monkeypatch.setattr(settings, "SMTP_USE_TLS", True)
    monkeypatch.setattr(settings, "SMTP_TIMEOUT_SECONDS", 1.0)

    success = await EmailService()._send_smtp(
        ["recipient@example.com"],
        "Subject",
        "<p>Hello</p>",
        "Hello",
    )

    assert success is False
