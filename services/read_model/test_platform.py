import pytest
from httpx import ASGITransport, AsyncClient

from app import create_app
from events import CanonicalPlay, InMemoryEventPipeline, OutboxPublisher
from security import CredentialCipher


async def request(app, method: str, path: str, **kwargs):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.request(method, path, **kwargs)


async def register(app, email: str) -> str:
    response = await request(
        app,
        "POST",
        "/accounts/register",
        json={"email": email, "password": "a-secure-test-password"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_dashboard_data_is_isolated_per_account():
    app = create_app(auth_required=True)
    token_a = await register(app, "a@example.com")
    token_b = await register(app, "b@example.com")
    roster = {
        "league_id": "shared-league",
        "season": 2026,
        "team_id": "1",
        "players": [],
    }

    synced = await request(
        app,
        "POST",
        "/sync/espn-roster",
        json=roster,
        headers={"Authorization": f"Bearer {token_a}"},
    )
    dashboard_b = await request(
        app,
        "GET",
        "/dashboard",
        headers={"Authorization": f"Bearer {token_b}"},
    )

    assert synced.status_code == 200
    assert dashboard_b.json() == {"teams": []}


@pytest.mark.asyncio
async def test_protected_route_rejects_missing_token():
    response = await request(create_app(auth_required=True), "GET", "/dashboard")
    assert response.status_code == 401


def test_provider_credentials_are_encrypted_and_round_trip():
    cipher = CredentialCipher("test-provider-encryption-secret")
    plaintext = b'{"api_key":"secret"}'
    ciphertext = cipher.encrypt(plaintext)

    assert ciphertext != plaintext
    assert cipher.decrypt(ciphertext) == plaintext


@pytest.mark.asyncio
async def test_event_inbox_semantics_make_duplicate_delivery_safe():
    pipeline = InMemoryEventPipeline()
    play = CanonicalPlay(
        source="fixture",
        source_event_id="play-1",
        game_id="game-1",
        player_id="player-1",
        event_type="RECEPTION",
        yards=20,
        cursor=1,
        occurred_at="2026-09-27T12:00:00Z",
    )

    first = await pipeline.ingest(play)
    duplicate = await pipeline.ingest(play)

    assert first.accepted is True
    assert pipeline.points["player-1"] == 3.0
    assert duplicate.duplicate is True
    assert len(pipeline.outbox) == 1


@pytest.mark.asyncio
async def test_event_ingest_requires_separate_service_key():
    play = {
        "source": "fixture",
        "source_event_id": "play-1",
        "game_id": "game-1",
        "player_id": "player-1",
        "event_type": "TOUCHDOWN",
        "cursor": 1,
        "occurred_at": "2026-09-27T12:00:00Z",
    }
    app = create_app(ingest_key="expected-key")

    rejected = await request(app, "POST", "/ingest/events", json=play)
    accepted = await request(
        app,
        "POST",
        "/ingest/events",
        json=play,
        headers={"X-Ingest-Key": "expected-key"},
    )

    assert rejected.status_code == 401
    assert accepted.status_code == 200


@pytest.mark.asyncio
async def test_outbox_publisher_decodes_asyncpg_json_text():
    class Pool:
        def __init__(self):
            self.marked = False

        async def fetch(self, _query, _limit):
            return [
                {
                    "outbox_id": 1,
                    "topic": "projection.updated",
                    "payload": '{"user_id":"user-1","points_delta":3}',
                }
            ]

        async def execute(self, _query, _outbox_id):
            self.marked = True

    class Broker:
        def __init__(self):
            self.payload = None

        async def publish(self, _topic, payload):
            self.payload = payload

    pool = Pool()
    broker = Broker()

    published = await OutboxPublisher(lambda: _value(pool), broker).publish_pending()

    assert published == 1
    assert broker.payload == {"user_id": "user-1", "points_delta": 3}
    assert pool.marked is True


async def _value(value):
    return value
