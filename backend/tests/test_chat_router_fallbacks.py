import httpx
import openai

from routers.chat import _build_openai_fallback


def test_authentication_error_maps_to_invalid_key_message():
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(401, request=request)
    err = openai.AuthenticationError(
        message="invalid key",
        response=response,
        body=None,
    )

    reply, confidence = _build_openai_fallback(err)

    assert "invalid" in reply.lower()
    assert "api key" in reply.lower()
    assert confidence == "low"


def test_connection_error_maps_to_network_message():
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    err = openai.APIConnectionError(message="connection error", request=request)

    reply, confidence = _build_openai_fallback(err)

    assert "unreachable" in reply.lower() or "network" in reply.lower()
    assert confidence == "low"
