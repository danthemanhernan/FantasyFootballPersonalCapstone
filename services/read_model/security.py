from __future__ import annotations

import base64
import hashlib
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProviderConnectionRequest(BaseModel):
    provider: str = Field(pattern=r"^[a-z0-9_-]+$")
    external_account_id: str
    credentials: dict[str, str]


class ProviderConnectionSummary(BaseModel):
    connection_id: str
    provider: str
    external_account_id: str


@dataclass(frozen=True)
class User:
    user_id: str
    email: str
    password_hash: str


class SecurityStore(Protocol):
    async def create_user(self, email: str, password_hash: str) -> User: ...
    async def find_user_by_email(self, email: str) -> User | None: ...
    async def save_connection(
        self, user_id: str, provider: str, external_account_id: str, encrypted: bytes
    ) -> ProviderConnectionSummary: ...
    async def list_connections(self, user_id: str) -> list[ProviderConnectionSummary]: ...


class InMemorySecurityStore(SecurityStore):
    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.connections: dict[str, list[ProviderConnectionSummary]] = {}

    async def create_user(self, email: str, password_hash: str) -> User:
        normalized = email.casefold()
        if normalized in self.users:
            raise ValueError("account already exists")
        user = User(str(uuid.uuid4()), normalized, password_hash)
        self.users[normalized] = user
        return user

    async def find_user_by_email(self, email: str) -> User | None:
        return self.users.get(email.casefold())

    async def save_connection(
        self, user_id: str, provider: str, external_account_id: str, encrypted: bytes
    ) -> ProviderConnectionSummary:
        summary = ProviderConnectionSummary(
            connection_id=str(uuid.uuid4()),
            provider=provider,
            external_account_id=external_account_id,
        )
        self.connections.setdefault(user_id, []).append(summary)
        return summary

    async def list_connections(self, user_id: str) -> list[ProviderConnectionSummary]:
        return list(self.connections.get(user_id, []))


class PostgresSecurityStore(SecurityStore):
    def __init__(self, pool_provider) -> None:
        self.pool_provider = pool_provider

    async def create_user(self, email: str, password_hash: str) -> User:
        normalized = email.casefold()
        try:
            row = await (await self.pool_provider()).fetchrow(
                """INSERT INTO app_users (email, password_hash)
                   VALUES ($1, $2)
                   RETURNING user_id::text, email, password_hash""",
                normalized,
                password_hash,
            )
        except Exception as error:
            if error.__class__.__name__ == "UniqueViolationError":
                raise ValueError("account already exists") from error
            raise
        return User(**dict(row))

    async def find_user_by_email(self, email: str) -> User | None:
        row = await (await self.pool_provider()).fetchrow(
            """SELECT user_id::text, email, password_hash
               FROM app_users WHERE email = $1""",
            email.casefold(),
        )
        return User(**dict(row)) if row else None

    async def save_connection(
        self, user_id: str, provider: str, external_account_id: str, encrypted: bytes
    ) -> ProviderConnectionSummary:
        row = await (await self.pool_provider()).fetchrow(
            """INSERT INTO provider_connections
                   (user_id, provider, external_account_id, encrypted_credentials)
               VALUES ($1::uuid, $2, $3, $4)
               ON CONFLICT (user_id, provider, external_account_id)
               DO UPDATE SET encrypted_credentials = EXCLUDED.encrypted_credentials,
                             updated_at = NOW()
               RETURNING connection_id::text, provider, external_account_id""",
            user_id,
            provider,
            external_account_id,
            encrypted,
        )
        return ProviderConnectionSummary(**dict(row))

    async def list_connections(self, user_id: str) -> list[ProviderConnectionSummary]:
        rows = await (await self.pool_provider()).fetch(
            """SELECT connection_id::text, provider, external_account_id
               FROM provider_connections WHERE user_id = $1::uuid
               ORDER BY provider, external_account_id""",
            user_id,
        )
        return [ProviderConnectionSummary(**dict(row)) for row in rows]


class Passwords:
    def __init__(self) -> None:
        self.hasher = PasswordHasher()

    def hash(self, password: str) -> str:
        return self.hasher.hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        try:
            return self.hasher.verify(password_hash, password)
        except VerifyMismatchError:
            return False


class TokenManager:
    def __init__(self, secret: str, ttl_minutes: int = 60) -> None:
        if len(secret) < 32:
            raise ValueError("AUTH_SECRET must contain at least 32 characters")
        self.secret = secret
        self.ttl_minutes = ttl_minutes

    def issue(self, user: User) -> str:
        now = datetime.now(UTC)
        return jwt.encode(
            {
                "sub": user.user_id,
                "email": user.email,
                "iat": now,
                "exp": now + timedelta(minutes=self.ttl_minutes),
            },
            self.secret,
            algorithm="HS256",
        )

    def verify(self, token: str) -> str:
        payload = jwt.decode(token, self.secret, algorithms=["HS256"])
        return str(payload["sub"])


class CredentialCipher:
    def __init__(self, secret: str) -> None:
        key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
        self.fernet = Fernet(key)

    def encrypt(self, plaintext: bytes) -> bytes:
        return self.fernet.encrypt(plaintext)

    def decrypt(self, ciphertext: bytes) -> bytes:
        return self.fernet.decrypt(ciphertext)


def configured_secrets() -> tuple[TokenManager, CredentialCipher]:
    auth_secret = os.environ["AUTH_SECRET"]
    provider_secret = os.environ["PROVIDER_ENCRYPTION_KEY"]
    return TokenManager(auth_secret), CredentialCipher(provider_secret)
