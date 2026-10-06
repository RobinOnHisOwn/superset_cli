import io
import zipfile

import httpx
import pytest
from typer.testing import CliRunner

from superset_cli.cli import app
from superset_cli.client import SupersetClient


@pytest.mark.parametrize("resource", ["dashboards", "charts", "datasets", "databases"])
@pytest.mark.parametrize("mode", ["success", "overwrite", "force", "non-zip", "not-found", "expired", "network"])
def test_exports(monkeypatch, instance_setup, tmp_path, resource, mode):
    config, state = instance_setup
    output = tmp_path / "assets.zip"
    original = b"original archive"
    if mode in {"overwrite", "force"}:
        output.write_bytes(original)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("metadata.yaml", "version: 1.0.0\n")
    body = archive.getvalue()
    calls = []

    def handle(request):
        calls.append(request)
        assert request.method == "GET"
        assert request.url.path == f"/api/v1/{resource[:-1]}/export/"
        assert request.url.params["q"] == "!(7,8)"
        if mode == "network":
            raise httpx.ConnectError("unreachable", request=request)
        if mode in {"not-found", "expired"}:
            return httpx.Response(404 if mode == "not-found" else 401, json={"message": "denied"})
        return httpx.Response(200, content=b"<html>not an archive</html>" if mode == "non-zip" else body,
                              headers={"Content-Type": "application/zip"})

    def factory(**kwargs):
        client = SupersetClient(**kwargs)
        client.http.close()
        client.http = httpx.Client(base_url=kwargs["base_url"], transport=httpx.MockTransport(handle))
        return client

    monkeypatch.setattr("superset_cli.cli.SupersetClient", factory)
    args = ["--config", str(config), resource, "export", "prod", "7", "8", "--output", str(output),
            "--state-dir", str(state), *(["--force"] if mode == "force" else [])]
    result = CliRunner().invoke(app, args)
    assert result.exit_code == (0 if mode in {"success", "force"} else 1)
    if mode in {"success", "force"}:
        assert output.read_bytes() == body
    elif mode == "overwrite":
        assert output.read_bytes() == original
        assert not calls
    else:
        assert not output.exists()


@pytest.mark.parametrize("ids", [[], ["-1"], ["not-an-id"]])
def test_exports_require_positive_ids(instance_setup, tmp_path, ids):
    config, state = instance_setup
    result = CliRunner().invoke(app, ["--config", str(config), "charts", "export", "prod", *ids,
                                     "--output", str(tmp_path / "out.zip"), "--state-dir", str(state)])
    assert result.exit_code != 0
