import json
from pathlib import Path

import httpx
from pydantic import BaseModel, Field


class AuthExpiredError(Exception):
    pass


def build_list_params(*, page: int | None = None, page_size: int | None = None) -> dict:
    q: dict = {}
    if page is not None:
        q["page"] = page
    if page_size is not None:
        q["page_size"] = page_size
    if not q:
        return {}
    return {"q": json.dumps(q)}


class NotFoundError(Exception):
    pass


class Cookie(BaseModel):
    name: str
    value: str
    domain: str
    path: str


class StorageState(BaseModel):
    cookies: list[Cookie] = Field(default_factory=list)
    origins: list[dict] = Field(default_factory=list)


def load_storage_state(path: Path) -> StorageState:
    return StorageState.model_validate(json.loads(path.read_text()))


def build_cookie_header(state: StorageState) -> str:
    return "; ".join(f"{cookie.name}={cookie.value}" for cookie in state.cookies)


class SupersetClient:
    def __init__(self, *, base_url: str, storage_state_path: Path) -> None:
        self.base_url = base_url.rstrip("/")
        self.storage_state_path = storage_state_path
        self.storage_state = load_storage_state(storage_state_path)
        self.http = httpx.Client(
            base_url=self.base_url,
            headers={
                "Cookie": build_cookie_header(self.storage_state),
                "Accept": "application/json",
            },
            follow_redirects=True,
            timeout=30.0,
        )

    def _get(self, path: str, *, params: dict | None = None) -> dict:
        response = self.http.get(path, params=params)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise AuthExpiredError(
                    "Session expired or invalid. Run 'auth login' to re-authenticate."
                ) from exc
            if exc.response.status_code == 404:
                raise NotFoundError(f"Resource not found: {path}") from exc
            raise
        try:
            return response.json()
        except json.JSONDecodeError:
            raise AuthExpiredError(
                "Unexpected non-JSON response — session may have expired. Run 'auth login' to re-authenticate."
            )

    def list_dashboards(self, *, page: int | None = None, page_size: int | None = None) -> dict:
        return self._get("/api/v1/dashboard/", params=build_list_params(page=page, page_size=page_size) or None)

    def get_dashboard(self, id_or_slug: str) -> dict:
        return self._get(f"/api/v1/dashboard/{id_or_slug}").get("result", {})

    def list_charts(self, *, page: int | None = None, page_size: int | None = None) -> dict:
        return self._get("/api/v1/chart/", params=build_list_params(page=page, page_size=page_size) or None)

    def get_chart(self, id_or_uuid: str) -> dict:
        return self._get(f"/api/v1/chart/{id_or_uuid}").get("result", {})

    def list_datasets(self, *, page: int | None = None, page_size: int | None = None) -> dict:
        return self._get("/api/v1/dataset/", params=build_list_params(page=page, page_size=page_size) or None)

    def get_dataset(self, id_or_uuid: str) -> dict:
        return self._get(f"/api/v1/dataset/{id_or_uuid}").get("result", {})

    def list_databases(self, *, page: int | None = None, page_size: int | None = None) -> dict:
        return self._get("/api/v1/database/", params=build_list_params(page=page, page_size=page_size) or None)

    def get_database(self, pk: str) -> dict:
        return self._get(f"/api/v1/database/{pk}").get("result", {})

    def get_current_user(self) -> dict:
        return self._get("/api/v1/me/").get("result", {})

    def close(self) -> None:
        self.http.close()

    def __enter__(self) -> "SupersetClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
