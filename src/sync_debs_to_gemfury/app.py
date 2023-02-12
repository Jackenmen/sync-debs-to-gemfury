import os
import subprocess
import sys
from typing import Literal, Self

import requests

from .base_package import Package, get_package_cls
from .schema import ConfigDict, load

GITHUB_API_BASE = "https://api.github.com"


class App:
    def __init__(
        self,
        *,
        github_repository: str,
        github_token: str,
        gemfury_username: str,
        gemfury_push_token: str,
        config: ConfigDict,
    ) -> None:
        self._github_repository = github_repository
        self._github_token = github_token
        self._gemfury_username = gemfury_username
        self._gemfury_push_token = gemfury_push_token
        self._config = config
        self.packages: list[Package] = []
        self.changed = False
        self.errored = False

    @property
    def exit_code(self) -> Literal[0, 1]:
        if self.errored:
            return 1
        return 0

    @classmethod
    def from_environ(cls) -> Self:
        return cls(
            github_repository=os.environ["GITHUB_REPOSITORY"],
            github_token=os.environ["GITHUB_TOKEN"],
            gemfury_username=os.environ["GEMFURY_USERNAME"],
            gemfury_push_token=os.environ["GEMFURY_PUSH_TOKEN"],
            config=load("config.yaml"),
        )

    def _load_packages(self) -> None:
        for package_name, package_data in self._config["packages"].items():
            cls = get_package_cls(package_data["type"])
            self.packages.append(cls(package_name, package_data["config"]))

    def _create_directories(self) -> None:
        for dirname in ("debs", "package_versions"):
            os.makedirs(dirname, exist_ok=True)

    def run(self) -> int:
        self._create_directories()
        self._load_packages()
        changed_packages: list[Package] = []

        for package in self.packages:
            try:
                deb_file = package.download_deb()
            except (RuntimeError, requests.HTTPError) as exc:
                print(f"{package.name}: {exc}", file=sys.stderr)
                self.errored = True
                continue

            previous_version = package.get_previous_version()
            if deb_file.version == previous_version:
                continue

            try:
                package.push_to_gemfury(
                    username=self._gemfury_username,
                    push_token=self._gemfury_push_token,
                )
            except requests.HTTPError as exc:
                print(f"{package.name}: {exc}", file=sys.stderr)
                self.errored = True
                continue
            package.save_version()
            self.changed = True
            changed_packages.append(package)

            if not previous_version:
                requests.post(
                    f"{GITHUB_API_BASE}/repos/{self._github_repository}/issues",
                    headers={"Authorization": f"Bearer {self._github_token}"},
                    json={"title": f"Make `{package.name}` package public"},
                )

        if changed_packages:
            subprocess.check_call(
                (
                    "git",
                    "add",
                    *(f"package_versions/{pkg.name}" for pkg in changed_packages),
                )
            )
            subprocess.check_call(
                (
                    "git",
                    "-c",
                    "user.name=github-actions[bot]",
                    "-c",
                    "user.email=41898282+github-actions[bot]@users.noreply.github.com",
                    "commit",
                    "-m",
                    "SYNC: " + " ".join(pkg.name for pkg in changed_packages),
                    "-m",
                    "[skip ci]",
                )
            )
            subprocess.check_call(("git", "push"))

        return self.exit_code
