from .app import App


def main() -> None:
    app = App.from_environ()
    raise SystemExit(app.run())


if __name__ == "__main__":
    main()
