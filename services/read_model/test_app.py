import pytest
from app import InMemoryStore, create_app
from httpx import ASGITransport, AsyncClient


async def request(app, method: str, path: str):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.request(method, path)


@pytest.mark.asyncio
async def test_liveness_does_not_require_dependencies():
    store = InMemoryStore()
    store.available = False
    response = await request(create_app(store, store, store), "GET", "/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


@pytest.mark.asyncio
async def test_readiness_reports_dependency_outage():
    store = InMemoryStore()
    store.available = False
    response = await request(create_app(store, store, store), "GET", "/health/ready")
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_matchup_endpoint_uses_cache_and_returns_contract():
    store = InMemoryStore()
    app = create_app(store, store, store)
    first = await request(app, "GET", "/matchups/matchup-demo")
    second = await request(app, "GET", "/matchups/matchup-demo")
    assert first.status_code == second.status_code == 200
    assert first.json()["home_points"] == 7.7
    assert second.json() == first.json()


@pytest.mark.asyncio
async def test_missing_matchup_is_not_a_dependency_failure():
    response = await request(create_app(), "GET", "/matchups/missing")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_events_endpoint_limits_results():
    response = await request(create_app(), "GET", "/games/demo-001/events?limit=1")
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_slow_dependency_is_injected_without_changing_contract():
    store = InMemoryStore()
    store.delay_seconds = 0.001
    response = await request(create_app(store, store, store), "GET", "/health/ready")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_cache_aside_experiment(capsys):
    class TracingStore(InMemoryStore):
        def __init__(self):
            super().__init__()
            self.trace = []

        async def get(self, key):
            value = await super().get(key)
            self.trace.append(("cache.get", key, value is not None))
            return value

        async def get_matchup(self, matchup_id):
            self.trace.append(("repository.get_matchup", matchup_id))
            return await super().get_matchup(matchup_id)

        async def set(self, key, value, ttl_seconds):
            self.trace.append(("cache.set", key, ttl_seconds))
            return await super().set(key, value, ttl_seconds)

    store = TracingStore()
    app = create_app(store, store, store)

    # The cache starts empty.
    assert store.cache == {}

    first = await request(app, "GET", "/matchups/matchup-demo")

    print("After first request:")
    print(store.trace)
    print("Cache:", store.cache)

    second = await request(app, "GET", "/matchups/matchup-demo")

    print("After second request:")
    print(store.trace)

    assert first.status_code == 200
    assert second.status_code == 200
