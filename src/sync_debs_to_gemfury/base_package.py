import abc
import functools
import importlib
import os
import subprocess
from typing import Protocol, runtime_checkable

import requests


class DebFile:
    def __init__(self, path: str) -> None:
        self.path = path

    @functools.cached_property
    def version(self) -> str:
        return subprocess.check_output(
            ("dpkg-deb", "-f", self.path, "Version"), text=True
        ).strip()


class Package(metaclass=abc.ABCMeta):
    def __init__(self, name: str, config: dict[str, str]) -> None:
        self.name = name
        self._config = config
        self.deb_file = DebFile(os.path.join("debs", f"{self.name}.deb"))

    @abc.abstractmethod
    def download_deb(self) -> DebFile:
        raise NotImplementedError()

    def get_previous_version(self) -> str:
        path = os.path.join("package_versions", self.name)
        try:
            with open(path, encoding="utf-8") as fp:
                return fp.read().strip()
        except FileNotFoundError:
            return ""

    def save_version(self) -> None:
        path = os.path.join("package_versions", self.name)
        with open(path, encoding="utf-8") as fp:
            fp.write(f"{self.deb_file.version}\n")

    def push_to_gemfury(self, username: str, push_token: str) -> None:
        resp = requests.post(
            f"https://push.fury.io/{username}/",
            files={"package": open(self.deb_file.path, "rb")},
            auth=(push_token, ""),
        )
        if resp.status_code == 409:
            return
        resp.raise_for_status()


@runtime_checkable
class PackageModule(Protocol):
    __name__: str
    PACKAGE_CLS: type[Package]


def get_package_cls(name: str) -> type[Package]:
    module = importlib.import_module(f"sync_debs_to_gemfury.packages.{name}")
    assert isinstance(module, PackageModule)
    try:
        return module.PACKAGE_CLS
    except StopIteration:
        raise KeyError(
            f"There's no hook named {name!r} in module {module.__name__!r}"
        ) from None
