"""
Tests for Idempotency Implementations

Validates request deduplication and conflict detection for both Memory and Redis stores.
"""

import time
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pythia.infrastructure.idempotency.memory_store import (
    IdempotencyLayer,
    InMemoryIdempotencyStore,
)
from pythia.infrastructure.idempotency.redis_store import IdempotencyStore as RedisIdempotencyStore


class TestInMemoryIdempotencyStore:
    """Test in-memory idempotency store."""

    @pytest.mark.asyncio
    async def test_check_and_set_new_key(self):
        """Should return True and store payload for new key."""
        store = InMemoryIdempotencyStore()
        result = await store.check_and_set("key-123", {"data": "test"})
        assert result is True
        assert "key-123" in store._store

    @pytest.mark.asyncio
    async def test_check_and_set_existing_key(self):
        """Should return False when key already exists."""
        store = InMemoryIdempotencyStore()
        await store.check_and_set("key-123", {"data": "test"})
        result = await store.check_and_set("key-123", {"data": "test2"})
        assert result is False

    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """Should clean up expired keys lazily."""
        store = InMemoryIdempotencyStore(ttl_seconds=0)  # Expires immediately
        await store.check_and_set("key-1", {"data": "1"})
        time.sleep(0.1)
        # check_and_set triggers lazy cleanup
        result = await store.check_and_set("key-2", {"data": "2"})
        assert result is True
        assert "key-1" not in store._store
        assert "key-2" in store._store


class TestIdempotencyLayer:
    """Test idempotency layer for async operations."""

    @pytest.mark.asyncio
    async def test_process_executes_once(self):
        """Should execute function only once per key."""
        layer = IdempotencyLayer()
        execution_count = 0

        async def operation():
            nonlocal execution_count
            execution_count += 1
            return "success"

        res1 = await layer.process("key-1", operation)
        res2 = await layer.process("key-1", operation)

        assert res1 == "success"
        assert res2 == "success"
        assert execution_count == 1

    @pytest.mark.asyncio
    async def test_process_different_keys(self):
        """Should execute function for each different key."""
        layer = IdempotencyLayer()
        executions = []

        async def operation(val):
            executions.append(val)
            return val

        await layer.process("key-1", operation, "first")
        await layer.process("key-2", operation, "second")

        assert executions == ["first", "second"]


class TestRedisIdempotencyStore:
    """Test Redis-backed idempotency store."""

    @pytest.mark.asyncio
    @patch("pythia.infrastructure.idempotency.redis_store.redis.from_url")
    async def test_check_and_set(self, mock_from_url):
        """Should check and set idempotency key in Redis."""
        # Setup mock Redis client and script
        mock_client = AsyncMock()
        mock_script = AsyncMock(return_value=1)
        mock_client.register_script = Mock(return_value=mock_script)
        mock_from_url.return_value = mock_client

        store = RedisIdempotencyStore()
        result = await store.check_and_set("key-123", {"data": "test"})

        assert result is True
        mock_script.assert_called_once()
        args, kwargs = mock_script.call_args
        assert "keys" in kwargs
        assert kwargs["keys"] == ["idem:key-123"]

    @pytest.mark.asyncio
    @patch("pythia.infrastructure.idempotency.redis_store.redis.from_url")
    async def test_check_and_set_duplicate(self, mock_from_url):
        """Should return False if key already exists in Redis."""
        mock_client = AsyncMock()
        mock_script = AsyncMock(return_value=0)
        mock_client.register_script = Mock(return_value=mock_script)
        mock_from_url.return_value = mock_client

        store = RedisIdempotencyStore()
        result = await store.check_and_set("key-123", {"data": "test"})

        assert result is False

    @pytest.mark.asyncio
    @patch("pythia.infrastructure.idempotency.redis_store.redis.from_url")
    async def test_get_response(self, mock_from_url):
        """Should retrieve stored response from Redis."""
        import json
        mock_client = AsyncMock()
        mock_client.get.return_value = json.dumps({"response": "ok"}).encode()
        mock_from_url.return_value = mock_client

        store = RedisIdempotencyStore()
        result = await store.get_response("key-123")

        assert result == {"response": "ok"}
        mock_client.get.assert_called_once_with("idem:key-123")
