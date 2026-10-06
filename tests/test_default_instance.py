import json
import io
import zipfile
import httpx
import pytest
from typer.testing import CliRunner

from superset_cli.cli import app
from superset_cli.config import load_config
from fakes import FakeSupersetClient


@pytest.mark.parametrize("source", ["single","config","env","flag","positional"])
def test_default_instance_precedence(monkeypatch,instance_setup,source):
    config,state=instance_setup
    runner=CliRunner()
    selected=[]
    class Client(FakeSupersetClient):
        def __init__(self,**kwargs):
            selected.append(kwargs["base_url"])
            super().__init__(**kwargs)
    monkeypatch.setattr("superset_cli.cli.SupersetClient",Client)
    args=["--config",str(config)]
    if source!="single":
        assert runner.invoke(app,args+["instances","add","stage","https://superset-staging.example.com"]).exit_code==0
        (state/"stage").mkdir()
        (state/"stage"/"storage-state.json").write_text('{"cookies":[],"origins":[]}')
        used=runner.invoke(app,args+["instances","use","stage"])
        assert used.exit_code==0,used.output
    if source in {"env","flag","positional"}:
        monkeypatch.setenv("SUPERSET_CLI_INSTANCE","prod")
    if source in {"flag","positional"}:
        args += ["--instance","stage"]
    args += ["charts","get", *(["prod"] if source=="positional" else []),"10","--state-dir",str(state),"--json"]
    result=runner.invoke(app,args)
    assert result.exit_code==0,result.output
    assert json.loads(result.stdout)["id"]==10
    expected="https://superset-staging.example.com" if source in {"config","flag"} else "https://superset.example.com"
    assert selected==[expected]


@pytest.mark.parametrize("override",["", "not-configured"])
def test_invalid_global_override_does_not_fall_back(monkeypatch,instance_setup,override):
    config,state=instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient",FakeSupersetClient)
    result=CliRunner().invoke(app,["--config",str(config),"--instance",override,"charts","get","10","--state-dir",str(state),"--json"])
    assert result.exit_code!=0
    assert "not configured" in result.output


@pytest.mark.parametrize("command",[["charts","update","10"],["api","/api/v1/chart/10","--method","PUT"],["api","/api/v1/chart/10","-XPUT"],["api","/api/v1/chart/10","--method=PUT"]])
def test_omitted_instance_keeps_write_guard(instance_setup,command):
    config,state=instance_setup
    result=CliRunner().invoke(app,["--config",str(config),*command,"--state-dir",str(state)])
    assert result.exit_code!=0
    assert "--allow-write" in result.output



def test_default_clear_and_remove(instance_setup):
    config,state=instance_setup
    runner=CliRunner()
    base=["--config",str(config),"instances"]
    assert runner.invoke(app,base+["use","prod"]).exit_code==0
    assert load_config(config).default_instance=="prod"
    listed=runner.invoke(app,base+["list","--json"])
    assert json.loads(listed.stdout)["default_instance"]=="prod"
    assert runner.invoke(app,base+["use","--clear"]).exit_code==0
    assert load_config(config).default_instance is None
    assert runner.invoke(app,base+["use","prod"]).exit_code==0
    assert runner.invoke(app,base+["remove","prod"]).exit_code==0
    assert load_config(config).default_instance is None


def test_multiple_instances_without_default_fail(monkeypatch,instance_setup):
    config,state=instance_setup
    monkeypatch.delenv("SUPERSET_CLI_INSTANCE",raising=False)
    runner=CliRunner()
    runner.invoke(app,["--config",str(config),"instances","add","stage","https://superset-staging.example.com"])
    result=runner.invoke(app,["--config",str(config),"charts","get","10","--state-dir",str(state)])
    assert result.exit_code!=0
    assert "prod" in result.output and "stage" in result.output


@pytest.mark.parametrize("selection",["implicit","explicit","ambiguous","flag"])
def test_variadic_export_selection(monkeypatch,instance_setup,tmp_path,selection):
    from superset_cli.client import SupersetClient
    config,state=instance_setup
    runner=CliRunner()
    prefix=["--config",str(config)]
    if selection in {"ambiguous","flag"}:
        assert runner.invoke(app,prefix+["instances","add","7","https://superset-staging.example.com"]).exit_code==0
    if selection=="flag":
        prefix += ["--instance","prod"]
    archive=io.BytesIO()
    with zipfile.ZipFile(archive,"w") as output:
        output.writestr("metadata.yaml","version: 1.0.0\n")
    calls=[]
    def handle(request):
        calls.append(request)
        return httpx.Response(200,content=archive.getvalue(),headers={"Content-Type":"application/zip"})
    def factory(**kwargs):
        client=SupersetClient(**kwargs)
        client.http.close()
        client.http=httpx.Client(base_url=kwargs["base_url"],transport=httpx.MockTransport(handle))
        return client
    monkeypatch.setattr("superset_cli.cli.SupersetClient",factory)
    output=tmp_path/"export.zip"
    result=runner.invoke(app,prefix+["charts","export",*(["prod"] if selection=="explicit" else []),"7","8","--output",str(output),"--state-dir",str(state)])
    if selection=="ambiguous":
        assert result.exit_code!=0
        assert "Ambiguous numeric" in result.output
        assert not output.exists() and not calls
    else:
        assert result.exit_code==0,result.output
        assert output.read_bytes()==archive.getvalue()
        assert calls[0].url.host=="superset.example.com"
        assert calls[0].url.params["q"]=="!(7,8)"


@pytest.mark.parametrize("command",[["charts","list"],["charts","get","10"],["datasources","column-values","table","21","country"]])
def test_omitted_instance_argument_arity(monkeypatch,instance_setup,command):
    config,state=instance_setup
    monkeypatch.setattr("superset_cli.cli.SupersetClient",FakeSupersetClient)
    result=CliRunner().invoke(app,["--config",str(config),*command,"--state-dir",str(state),"--json"])
    assert result.exit_code==0,result.output
