"""Backend entrypoint for local development."""

from .bootstrap import bootstrap_application


def main() -> None:
    app_state = bootstrap_application()
    print("Local Meeting Notes backend scaffold is ready.")
    print(f"Environment: {app_state.config.app_env}")
    print(f"Database path: {app_state.config.database_path}")


if __name__ == "__main__":
    main()
