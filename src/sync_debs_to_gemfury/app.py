import os
import subprocess
import sys
from typing import Literal, Self

import requests

from .auth_info import AuthInfo
from .base_package import Package, get_package_cls
from .schema import ConfigDict, load

GITHUB_API_BASE = "https://api.github.com"


class App:
    def __init__(
        self,
        *,
        auth_info: AuthInfo,
        config: ConfigDict,
    ) -> None:
        self._auth_info = auth_info
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
        return cls(auth_info=AuthInfo.from_environ(), config=load("config.yaml"))

    def _load_packages(self) -> None:
        for package_name, package_data in self._config["packages"].items():
            cls = get_package_cls(package_data["type"])
            self.packages.append(
                cls(
                    self._auth_info,
                    package_name,
                    download_should_fail=package_data["download_should_fail"],
                    config=package_data["config"],
                )
            )

    def _create_directories(self) -> None:
        for dirname in ("debs", "metadata"):
            os.makedirs(dirname, exist_ok=True)

    def run(self) -> int:
        self._create_directories()
        self._load_packages()
        changed_packages: list[Package] = []

        for package in self.packages:
            try:
                package.download_deb()
            except (RuntimeError, requests.HTTPError) as exc:
                print(f"{package.name}: {exc}", file=sys.stderr)
                if package.download_should_fail:
                    print(
                        f"{package.name}: Download failure was expected",
                        file=sys.stderr,
                    )
                else:
                    self.errored = True
                continue

            if package.download_should_fail:
                print(
                    f"{package.name}: Expected download failure but one did not occur",
                    file=sys.stderr,
                )
                self.errored = True
                continue

            previous_deb_info = package.get_previous_deb_info()
            if package.deb_file.version == previous_deb_info.version:
                if package.deb_file.verify_hashes(previous_deb_info.hashes):
                    continue
                package.deb_file.version_counter = previous_deb_info.version_counter + 1
                subprocess.check_call(
                    (
                        "fakeroot",
                        sys.executable,
                        "-m",
                        "sync_debs_to_gemfury.deb_reversion",
                        package.deb_file.path,
                        package.deb_file.repo_version,
                    )
                )

            try:
                package.push_to_gemfury()
            except requests.HTTPError as exc:
                print(f"{package.name}: {exc}", file=sys.stderr)
                self.errored = True
                continue
            package.save_deb_info()
            self.changed = True
            changed_packages.append(package)

            if not previous_deb_info.version:
                requests.post(
                    f"{GITHUB_API_BASE}/repos/{self._auth_info.github_repository}/issues",
                    headers={"Authorization": f"Bearer {self._auth_info.github_token}"},
                    json={"title": f"Make `{package.name}` package public"},
                )

        if changed_packages:
            subprocess.check_call(
                ("git", "add", *(f"metadata/{pkg.name}" for pkg in changed_packages))
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
