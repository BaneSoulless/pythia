"""
Tests for Idempotency Middleware

Validates request deduplication and conflict detection.
"""
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from app.core.idempotency import (
    IdempotencyStore,
    CachedResponse,
    get_idempotency_store,
    idempotent,
    IdempotencyKeyError,
    IdempotencyConflictError,
    generate_request_fingerprint
)


class TestCachedResponse:
    """Test cached response behavior."""
    
    def test_not_expired_within_ttl(self):
        """Response should not be expired within TTL."""
        response = CachedResponse(
            status_code=200,
            body={"data": "test"},
            created_at=datetime.utcnow(),
            ttl_seconds=3600
        )
        
        assert not response.is_expired
    
    def test_expired_after_ttl(self):
        """Response should be expired after TTL."""
        response = CachedResponse(
            status_code=200,
            body={"data": "test"},
            created_at=datetime.utcnow() - timedelta(seconds=3700),
            ttl_seconds=3600
        )
        
        assert response.is_expired


class TestIdempotencyStore:
    """Test in-memory idempotency store."""
    
    def test_set_and_get(self):
        """Should store and retrieve cached responses."""
        store = IdempotencyStore()
        
        store.set("key-123", 200, {"result": "success"})
        cached = store.get("key-123")
        
        assert cached is not None
        assert cached.status_code == 200
        assert cached.body["result"] == "success"
    
    def test_get_nonexistent_key(self):
        """Should return None for nonexistent key."""
        store = IdempotencyStore()
        
        cached = store.get("nonexistent")
        
        assert cached is None
    
    def test_expired_entry_returns_none(self):
        """Should return None for expired entries."""
        store = IdempotencyStore()
        
        # Create with very short TTL
        store.set("key-123", 200, {"data": "test"}, ttl=0)
        
        # Wait for expiry
        time.sleep(0.1)
        
        cached = store.get("key-123")
        assert cached is None
    
    def test_delete(self):
        """Should delete cached entry."""
        store = IdempotencyStore()
        
        store.set("key-123", 200, {"data": "test"})
        result = store.delete("key-123")
        
        assert result is True
        assert store.get("key-123") is None
    
    def test_delete_nonexistent(self):
        """Should return False for nonexistent key."""
        store = IdempotencyStore()
        
        result = store.delete("nonexistent")
        
        assert result is False
    
    def test_clear_expired(self):
        """Should clear expired entries."""
        store = IdempotencyStore()
        
        store.set("key-1", 200, {"data": "1"}, ttl=0)
        store.set("key-2", 200, {"data": "2"}, ttl=3600)
        
        time.sleep(0.1)
        
        cleared = store.clear_expired()
        
        assert cleared == 1
        assert store.get("key-1") is None
        assert store.get("key-2") is not None
    
    def test_get_stats(self):
        """Should return store statistics."""
        store = IdempotencyStore()
        
        store.set("key-1", 200, {"data": "1"})
        store.set("key-2", 200, {"data": "2"})
        
        stats = store.get_stats()
        
        assert stats["total_entries"] == 2


class TestRequestFingerprint:
    """Test request fingerprinting."""
    
    def test_same_data_same_fingerprint(self):
        """Same data should produce same fingerprint."""
        data = {"symbol": "AAPL", "quantity": 10, "price": 150.0}
        
        fp1 = generate_request_fingerprint(data)
        fp2 = generate_request_fingerprint(data)
        
        assert fp1 == fp2
    
    def test_different_data_different_fingerprint(self):
        """Different data should produce different fingerprint."""
        data1 = {"symbol": "AAPL", "quantity": 10}
        data2 = {"symbol": "AAPL", "quantity": 20}
        
        fp1 = generate_request_fingerprint(data1)
        fp2 = generate_request_fingerprint(data2)
        
        assert fp1 != fp2
    
    def test_key_order_independent(self):
        """Fingerprint should be independent of key order."""
        data1 = {"a": 1, "b": 2}
        data2 = {"b": 2, "a": 1}
        
        fp1 = generate_request_fingerprint(data1)
        fp2 = generate_request_fingerprint(data2)
        
        assert fp1 == fp2


class TestIdempotentDecorator:
    """Test idempotent decorator."""
    
    def test_first_call_executes(self):
        """First call should execute function."""
        call_count = {"count": 0}
        
        @idempotent(key_param="idem_key")
        def test_func(idem_key: str, value: int):
            call_count["count"] += 1
            return {"result": value * 2}
        
        result = test_func(idem_key="key-123", value=5)
        
        assert result == {"result": 10}
        assert call_count["count"] == 1
    
    def test_duplicate_call_returns_cached(self):
        """Duplicate call should return cached response."""
        call_count = {"count": 0}
        
        @idempotent(key_param="idem_key")
        def test_func(idem_key: str, value: int):
            call_count["count"] += 1
            return {"result": value * 2}
        
        result1 = test_func(idem_key="key-456", value=5)
        result2 = test_func(idem_key="key-456", value=5)
        
        assert result1 == result2
        assert call_count["count"] == 1  # Only called once
    
    def test_different_key_executes_again(self):
        """Different key should execute function again."""
        call_count = {"count": 0}
        
        @idempotent(key_param="idem_key")
        def test_func(idem_key: str, value: int):
            call_count["count"] += 1
            return {"result": value * 2}
        
        test_func(idem_key="key-a", value=5)
        test_func(idem_key="key-b", value=5)
        
        assert call_count["count"] == 2
    
    def test_no_key_executes_normally(self):
        """Missing key should execute normally without caching."""
        call_count = {"count": 0}
        
        @idempotent(key_param="idem_key", required=False)
        def test_func(idem_key: str = None, value: int = 0):
            call_count["count"] += 1
            return {"result": value * 2}
        
        test_func(value=5)
        test_func(value=5)
        
        assert call_count["count"] == 2
    
    def test_required_key_raises_error(self):
        """Required key missing should raise error."""
        @idempotent(key_param="idem_key", required=True)
        def test_func(idem_key: str = None, value: int = 0):
            return {"result": value * 2}
        
        with pytest.raises(IdempotencyKeyError):
            test_func(value=5)
    
    def test_payload_conflict_raises_error(self):
        """Same key with different payload should raise conflict error."""
        @idempotent(key_param="idem_key", check_payload=True)
        def test_func(idem_key: str, value: int):
            return {"result": value * 2}
        
        test_func(idem_key="key-conflict", value=5)
        
        with pytest.raises(IdempotencyConflictError):
            test_func(idem_key="key-conflict", value=10)  # Different value
    
    def test_error_not_cached(self):
        """Errors should not be cached (allow retry)."""
        call_count = {"count": 0}
        
        @idempotent(key_param="idem_key")
        def test_func(idem_key: str, fail: bool):
            call_count["count"] += 1
            if fail:
                raise ValueError("Test error")
            return {"result": "success"}
        
        with pytest.raises(ValueError):
            test_func(idem_key="key-error", fail=True)
        
        # Should be able to retry (not cached)
        result = test_func(idem_key="key-error", fail=False)
        
        assert result == {"result": "success"}
        assert call_count["count"] == 2
