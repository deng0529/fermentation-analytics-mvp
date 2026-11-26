"""Small Turso SQL-over-HTTP client for dataset snapshots."""

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent


class DatasetError(RuntimeError):
    """An error with a message safe to show in the app."""


class TursoStatementError(DatasetError):
    def __init__(self, code):
        self.code = code
        if code in {"SQLITE_AUTH", "SQLITE_READONLY", "AUTH", "PERMISSION_DENIED"}:
            message = "Turso denied the operation. The initial import requires a database token with write access."
        else:
            message = "Turso could not run a dataset query. Check that the schema migration has been applied."
        super().__init__(message)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, *args, **kwargs):
        return None


def connect(secrets=None):
    def credential(name):
        aliases = (name, f"Fermentation_{name}")
        for settings in (os.environ, secrets or {}, local):
            for alias in aliases:
                if settings.get(alias):
                    return str(settings[alias]).strip()
        return ""

    local = dotenv_values(ROOT / ".env", interpolate=False, verbose=False)
    url = credential("TURSO_DATABASE_URL")
    token = credential("TURSO_AUTH_TOKEN")
    if not url or not token:
        raise DatasetError("Configure TURSO_DATABASE_URL and TURSO_AUTH_TOKEN in the project .env, "
                           "environment variables, or .streamlit/secrets.toml.")
    return Turso(url, token)


def https_base(url):
    try:
        parts = urlsplit(url)
        if (parts.scheme in {"libsql", "turso", "https"} and parts.hostname and not parts.username
                and parts.password is None and parts.path in {"", "/"} and not parts.query and not parts.fragment):
            return f"https://{parts.netloc}"
    except ValueError:
        pass
    raise DatasetError("The Turso database URL must be a libsql://, turso://, or HTTPS base URL.")


def bind(value):
    if value is None:
        return {"type": "null"}
    kind = {int: "integer", float: "float", str: "text"}[type(value)]
    return {"type": kind, "value": value if kind == "float" else str(value)}


def unpack(cell):
    kind = cell["type"]
    if kind == "null":
        return None
    return {"integer": int, "float": float, "text": str}[kind](cell["value"])


class Turso:
    def __init__(self, url, token):
        self.base = https_base(url)
        self._token = token

    def request(self, requests, *, baton=None, base=None):
        body = {"requests": requests}
        if baton is not None:
            body["baton"] = baton
        request = Request(f"{base or self.base}/v2/pipeline", data=json.dumps(body).encode(), headers={
            "Authorization": f"Bearer {self._token}", "Content-Type": "application/json",
        })
        try:
            with build_opener(NoRedirect).open(request, timeout=35) as response:
                return json.load(response)
        except HTTPError as error:
            detail = error.read(2048).lower() if error.code == 400 else b""
            if error.code in {401, 403} or any(word in detail for word in (b"jwt", b"token", b"authenticat")):
                raise DatasetError("Turso rejected the credentials or permissions. Check the database URL and token.") from None
            raise DatasetError(f"Turso is unavailable or rejected the request (HTTP {error.code}).") from None
        except (OSError, URLError, ValueError):
            raise DatasetError("Turso could not be reached or returned an invalid response.") from None

    def execute(self, *statements):
        with self.session() as session:
            return session.execute(*statements, close=True)

    def session(self):
        return TursoSession(self)


class TursoSession:
    def __init__(self, database):
        self.database = database
        self.base = database.base
        self.baton = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        if self.baton:
            try:
                self.execute(close=True)
            except DatasetError:
                if not exc[0]:
                    raise

    def execute(self, *statements, close=False):
        requests = [
            {"type": "execute", "stmt": {"sql": sql, "args": [bind(value) for value in args]}}
            for sql, args in statements
        ]
        if close:
            requests.append({"type": "close"})
        reply = self.database.request(requests, baton=self.baton, base=self.base)
        try:
            self.baton = reply["baton"]
            # Turso may return the replica origin for subsequent requests in a session.
            if reply.get("base_url") and self.baton:
                origin = https_base(reply["base_url"])
                host, initial_host = urlsplit(origin).hostname, urlsplit(self.database.base).hostname
                if host != initial_host and not (host.endswith(".turso.io") and initial_host.endswith(".turso.io")):
                    raise DatasetError("Turso returned an unexpected session endpoint.")
                self.base = origin
            results = reply["results"]
            if len(results) != len(requests):
                raise ValueError
            for result in results:
                if result["type"] == "error":
                    raise TursoStatementError(result["error"].get("code"))
            return [
                [tuple(unpack(cell) for cell in row) for row in item["response"]["result"]["rows"]]
                for item in results[:len(statements)]
            ]
        except (AttributeError, KeyError, TypeError, ValueError):
            raise DatasetError("Turso returned an invalid dataset query response.") from None


def migrate(database):
    statements = [(sql, ()) for path in sorted((ROOT / "migrations").glob("*.sql"))
                  for sql in path.read_text(encoding="utf-8").split(";") if sql.strip()]
    with database.session() as session:
        session.execute(("PRAGMA foreign_keys = ON", ()), ("BEGIN", ()))
        session.execute(*statements)
        session.execute(("COMMIT", ()), close=True)
