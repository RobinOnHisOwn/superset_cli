import json
import stat

import httpx
import pytest
from typer.testing import CliRunner

from superset_cli import models
from superset_cli.cli import app
from superset_cli.client import SupersetClient, AuthExpiredError
from superset_cli.config import load_config, save_config


def configure(config):
    settings = models.JWTSettings(username_env="EXAMPLE_USER", password_env="EXAMPLE_PASSWORD")
    current = load_config(config)
    current.instances[0].auth = models.AuthConfig(mode="jwt", jwt=settings)
    save_config(current, config)


def install_transport(monkeypatch, handle):
    original = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(handle)))


def test_jwt_cli_login_refresh_status_logout(monkeypatch, instance_setup):
    config, state = instance_setup
    monkeypatch.setenv("EXAMPLE_USER", "reader")
    monkeypatch.setenv("EXAMPLE_PASSWORD", "synthetic-password")
    calls = []
    def handle(request):
        calls.append(request)
        if request.url.path.endswith("/login"):
            assert json.loads(request.content) == {"username":"reader", "password":"synthetic-password", "provider":"db", "refresh":True}
            return httpx.Response(200, json={"access_token":"synthetic-access", "refresh_token":"synthetic-refresh"})
        assert request.url.path.endswith("/refresh")
        assert request.headers["Authorization"] == "Bearer synthetic-refresh"
        return httpx.Response(200, json={"access_token":"new-access"})
    install_transport(monkeypatch, handle)
    base = ["--config",str(config),"auth","jwt"]
    result = CliRunner().invoke(app, base+["login","prod","--username-env","EXAMPLE_USER","--password-env","EXAMPLE_PASSWORD","--state-dir",str(state),"--json"])
    assert result.exit_code == 0, result.output
    path = state / "prod" / "jwt-state.json"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert json.loads(path.read_text())["refresh_token"] == "synthetic-refresh"
    result = CliRunner().invoke(app, base+["refresh","prod","--state-dir",str(state),"--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(path.read_text())["access_token"] == "new-access"
    assert json.loads(path.read_text())["refresh_token"] == "synthetic-refresh"
    status = CliRunner().invoke(app, ["--config",str(config),"auth","status","prod","--state-dir",str(state),"--json"])
    assert status.exit_code == 0, status.output
    assert json.loads(status.stdout)["mode"] == "jwt"
    assert all(secret not in result.output+status.output+config.read_text() for secret in ["synthetic-password","synthetic-access","synthetic-refresh","new-access"])
    result = CliRunner().invoke(app, base+["logout","prod","--state-dir",str(state)])
    assert result.exit_code == 0
    assert not path.exists()
    assert (state/"prod"/"storage-state.json").exists()
    assert len(calls) == 2


@pytest.mark.parametrize("method,refreshed", [("GET",True),("POST",False)])
def test_jwt_read_retry_only(tmp_path, method, refreshed):
    path = tmp_path/"jwt-state.json"
    path.write_text(json.dumps({"mode":"jwt","access_token":"old","refresh_token":"refresh"}))
    calls = []
    def handle(request):
        calls.append(request)
        assert "Cookie" not in request.headers
        if request.url.path.endswith("/csrf_token/"):
            return httpx.Response(200,json={"result":"synthetic-csrf"})
        if request.method == "POST" and not request.url.path.endswith("/refresh"):
            assert request.headers["X-CSRFToken"] == "synthetic-csrf"
        if request.url.path.endswith("/refresh"):
            assert request.headers["Authorization"] == "Bearer refresh"
            return httpx.Response(200,json={"access_token":"new"})
        if request.headers["Authorization"] == "Bearer old":
            return httpx.Response(401,json={"message":"expired"})
        return httpx.Response(200,json={"result":{"id":7}})
    with SupersetClient(base_url="https://superset.example.com", storage_state_path=path) as client:
        client.http.close()
        client.http=httpx.Client(base_url=client.base_url,headers={"Authorization":"Bearer old"},transport=httpx.MockTransport(handle))
        if refreshed:
            assert client.request(method,"/api/v1/dashboard/7")["result"]["id"] == 7
            assert len(calls)==3
        else:
            with pytest.raises(AuthExpiredError,match="auth jwt"):
                client.request(method,"/api/v1/dashboard/7",json_body={})
            assert len(calls)==2


def test_jwt_instance_reads_without_cookie_state(monkeypatch, instance_setup):
    config,state=instance_setup
    configure(config)
    (state/"prod"/"storage-state.json").unlink()
    (state/"prod"/"jwt-state.json").write_text(json.dumps({"mode":"jwt","access_token":"access","refresh_token":"refresh"}))
    def handle(request):
        assert request.headers["Authorization"]=="Bearer access"
        assert "Cookie" not in request.headers
        return httpx.Response(200,json={"count":0,"result":[]})
    install_transport(monkeypatch,handle)
    result=CliRunner().invoke(app,["--config",str(config),"dashboards","list","prod","--state-dir",str(state),"--json"])
    assert result.exit_code==0,result.output
    assert json.loads(result.stdout)=={"count":0,"result":[]}


@pytest.mark.parametrize("provider",["oauth","db"])
def test_jwt_invalid_credentials_do_not_call_network(monkeypatch,instance_setup,provider):
    config,state=instance_setup
    monkeypatch.delenv("MISSING_EXAMPLE_USER",raising=False)
    monkeypatch.delenv("MISSING_EXAMPLE_PASSWORD",raising=False)
    def forbidden(**kwargs):
        raise AssertionError("Invalid credential configuration reached the network")
    monkeypatch.setattr(httpx,"Client",forbidden)
    result=CliRunner().invoke(app,["--config",str(config),"auth","jwt","login","prod","--username-env","MISSING_EXAMPLE_USER","--password-env","MISSING_EXAMPLE_PASSWORD","--provider",provider,"--state-dir",str(state)])
    assert result.exit_code==1
    assert "JWT login needs" in result.stderr
    assert not (state/"prod"/"jwt-state.json").exists()


@pytest.mark.parametrize("refresh_fails",[False,True])
def test_jwt_refresh_retry_is_bounded(tmp_path,refresh_fails):
    path=tmp_path/"jwt-state.json"
    path.write_text(json.dumps({"mode":"jwt","access_token":"old","refresh_token":"refresh"}))
    calls=[]
    def handle(request):
        calls.append(request)
        if request.url.path.endswith("/refresh") and not refresh_fails:
            return httpx.Response(200,json={"access_token":"new"})
        return httpx.Response(401,json={"message":"expired"})
    with SupersetClient(base_url="https://superset.example.com",storage_state_path=path) as client:
        client.http.close()
        client.http=httpx.Client(base_url=client.base_url,headers={"Authorization":"Bearer old"},transport=httpx.MockTransport(handle))
        with pytest.raises(AuthExpiredError,match="auth jwt"):
            client.request("GET","/api/v1/dashboard/7")
    assert len(calls)==(2 if refresh_fails else 3)


def test_failed_token_replacement_preserves_previous_state(tmp_path,monkeypatch):
    from superset_cli.jwt_auth import save_jwt_state
    path=tmp_path/"jwt-state.json"
    save_jwt_state(path,{"access_token":"old","refresh_token":"refresh"})
    previous=path.read_bytes()
    def failed_replace(*args):
        raise OSError("synthetic replacement failure")
    monkeypatch.setattr("superset_cli.jwt_auth.os.replace",failed_replace)
    with pytest.raises(OSError,match="synthetic"):
        save_jwt_state(path,{"access_token":"new","refresh_token":"refresh"})
    assert path.read_bytes()==previous
    assert list(tmp_path.iterdir())==[path]


@pytest.mark.parametrize("token",["access\nsecret", "access secret", "accessé"])
@pytest.mark.parametrize("operation",["save","load"])
def test_invalid_bearer_values_are_rejected_without_echo(tmp_path,token,operation):
    from superset_cli.jwt_auth import load_jwt_state, save_jwt_state
    path=tmp_path/"jwt-state.json"
    state={"mode":"jwt","access_token":token,"refresh_token":"refresh"}
    path.write_text(json.dumps(state))
    with pytest.raises(ValueError) as error:
        if operation=="save":
            save_jwt_state(path,state)
        else:
            load_jwt_state(path)
    assert token not in str(error.value)


@pytest.mark.parametrize("url,allowed",[("https://superset.example.com",True),("http://localhost:8088",True),("http://127.0.0.1:8088",True),("http://[::1]:8088",True),("http://superset.example.com",False)])
def test_jwt_login_requires_secure_transport(monkeypatch,tmp_path,url,allowed):
    from superset_cli.jwt_auth import login_jwt
    calls=[]
    def handle(request):
        calls.append(request)
        return httpx.Response(200,json={"access_token":"access","refresh_token":"refresh"})
    install_transport(monkeypatch,handle)
    path=tmp_path/"jwt-state.json"
    if allowed:
        login_jwt(url,path,username="example",password="synthetic-password")
        assert path.exists() and len(calls)==1
    else:
        with pytest.raises(ValueError,match="HTTPS"):
            login_jwt(url,path,username="example",password="synthetic-password")
        assert not path.exists() and not calls


@pytest.mark.parametrize("operation",["client","refresh"])
def test_existing_jwt_state_cannot_send_over_remote_http(tmp_path,operation):
    from superset_cli.jwt_auth import save_jwt_state,refresh_jwt
    path=tmp_path/"jwt-state.json"
    save_jwt_state(path,{"access_token":"access","refresh_token":"refresh"})
    def forbidden(request):
        pytest.fail("Remote HTTP received a bearer token")
    with pytest.raises(ValueError,match="HTTPS"):
        if operation=="client":
            SupersetClient(base_url="http://superset.example.com",storage_state_path=path)
        else:
            with httpx.Client(base_url="http://superset.example.com",transport=httpx.MockTransport(forbidden)) as http:
                refresh_jwt(http,path)


@pytest.mark.parametrize("response",[None,["access","refresh"],"malformed"])
def test_nonobject_login_responses_fail_cleanly(tmp_path,response):
    from superset_cli.jwt_auth import save_jwt_state
    path=tmp_path/"jwt-state.json"
    with pytest.raises(ValueError,match="JWT response"):
        save_jwt_state(path,response)
    assert not path.exists()


def test_cli_exception_diagnostics_do_not_show_credentials_locals():
    assert app.pretty_exceptions_show_locals is False


def test_instance_url_update_preserves_explicit_auth_selection(instance_setup):
    from superset_cli.config import load_config,save_config
    from superset_cli.models import AuthConfig,JWTSettings
    config,_=instance_setup
    before=load_config(config)
    binding=AuthConfig(mode="jwt",jwt=JWTSettings(provider="ldap",username_env="EXAMPLE_USER",password_env="EXAMPLE_PASSWORD"))
    instance=before.instances[0].model_copy(update={"auth":binding})
    save_config(before.model_copy(update={"instances":[instance],"default_instance":"prod"}),config)
    result=CliRunner().invoke(app,["--config",str(config),"instances","add","prod","https://superset-staging.example.com"])
    assert result.exit_code==0,result.output
    after=load_config(config)
    assert after.instances[0].auth==binding
    assert after.default_instance=="prod"
