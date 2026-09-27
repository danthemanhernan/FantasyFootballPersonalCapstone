# Local application stack

The integrated development stack runs Postgres, Redis, the FastAPI service,
and the web dashboard:

```bash
docker compose -f infra/dev/docker-compose.yml up --build
```

Open `http://127.0.0.1:5174`, then load the extension from
`apps/extension/dist`. The extension reads ESPN with the signed-in browser
session and sends only normalized roster data to the local API.

Postgres is the durable source of league and roster state. Redis is the
cache/readiness dependency. The API's in-process WebSocket fan-out is suitable
for one local process; a cloud deployment should replace it with a shared
broker before scaling the API horizontally.

Stop the stack while retaining data:

```bash
docker compose -f infra/dev/docker-compose.yml down
```

Adding `-v` removes the local database and cache volumes and is intentionally
not part of the normal stop command.
