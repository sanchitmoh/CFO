"""
Shared test fixtures for AI CFO tests.
"""
import sys
import os
import pytest

# Add the backend directory to sys.path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def anyio_backend():
    return "asyncio"
