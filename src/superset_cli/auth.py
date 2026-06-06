import shutil
from pathlib import Path

from superset_cli.client import load_storage_state


def get_instance_dir(*, state_dir: Path, instance_name: str) -> Path:
    return state_dir / instance_name


def get_storage_state_path(*, state_dir: Path, instance_name: str) -> Path:
    return get_instance_dir(state_dir=state_dir, instance_name=instance_name) / "storage-state.json"


def get_profile_dir(*, state_dir: Path, instance_name: str) -> Path:
    return get_instance_dir(state_dir=state_dir, instance_name=instance_name) / "profile"


def get_auth_status(*, storage_state_path: Path) -> dict:
    if not storage_state_path.exists():
        return {
            "authenticated": False,
            "storage_state_path": str(storage_state_path),
            "cookie_count": 0,
        }

    state = load_storage_state(storage_state_path)
    return {
        "authenticated": True,
        "storage_state_path": str(storage_state_path),
        "cookie_count": len(state.cookies),
    }


def remove_auth_state(*, state_dir: Path, instance_name: str) -> Path:
    instance_dir = get_instance_dir(state_dir=state_dir, instance_name=instance_name)
    shutil.rmtree(instance_dir, ignore_errors=True)
    return instance_dir


def login_with_browser(*, base_url: str, profile_dir: Path, storage_state_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    profile_dir.mkdir(parents=True, exist_ok=True)
    storage_state_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(base_url, wait_until="domcontentloaded")
        input("Complete Superset login in the browser, then press Enter here to save the session...")
        context.storage_state(path=str(storage_state_path))
        context.close()
