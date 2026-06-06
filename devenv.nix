{ pkgs, ... }:

{
  packages = [ pkgs.git ];

  languages.python = {
    enable = true;
    venv.enable = true;
    uv = {
      enable = true;
      sync = {
        enable = true;
        groups = [ "dev" ];
      };
    };
  };

  enterShell = ''
    echo "superset-agent-cli devenv ready"
    python --version
    uv --version
  '';

  enterTest = ''
    python --version
    uv --version
    uv run pytest -v
  '';
}
