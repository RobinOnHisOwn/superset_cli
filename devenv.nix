{ pkgs, ... }:

{
  packages = with pkgs; [ 
    git
  ];

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

  processes.superset.exec = "bash $DEVENV_ROOT/scripts/dev-superset.sh";

  scripts.superset-open.exec = ''
    url="http://localhost:''${SUPERSET_PORT:-8088}/login/"
    if command -v open >/dev/null 2>&1; then
      open "$url"
    elif command -v xdg-open >/dev/null 2>&1; then
      xdg-open "$url"
    else
      echo "No open/xdg-open found. Visit: $url"
      exit 1
    fi
  '';

  enterShell = ''
    echo "superset-cli devenv ready"
    python --version
    uv --version
    echo "Run 'devenv up superset' to start a local Superset on http://localhost:8088 (admin/admin)."
    echo "Run 'superset-open' to open the login page in your default browser."
  '';

  enterTest = ''
    python --version
    uv --version
    uv run pytest -v
  '';
}
