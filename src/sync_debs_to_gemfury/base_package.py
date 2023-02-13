import abc
import functools
import importlib
import json
import os
import subprocess
from typing import Protocol, Self, TypedDict, runtime_checkable

import requests


class DebInfoDict(TypedDict):
    version: str


class DebInfo(metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def version(self) -> str:
        raise NotImplementedError()

    def to_dict(self) -> DebInfoDict:
        return {
            "version": self.version,
        }


class EmptyDebInfo(DebInfo):
    @property
    def version(self) -> str:
        return ""


class StaticDebInfo(DebInfo):
    def __init__(self, *, version: str) -> None:
        self._version = version

    @classmethod
    def from_dict(cls, data: DebInfoDict) -> Self:
        return cls(
            version=data["version"],
        )

    @property
    def version(self) -> str:
        return self._version


class DebFile(DebInfo):
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

    def get_previous_deb_info(self) -> DebInfo:
        path = os.path.join("metadata", self.name)
        try:
            with open(path, encoding="utf-8") as fp:
                return StaticDebInfo.from_dict(json.load(fp))
        except FileNotFoundError:
            return EmptyDebInfo()

    def save_deb_info(self) -> None:
        path = os.path.join("metadata", self.name)
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(self.deb_file.to_dict(), fp, indent=4)
            fp.write("\n")

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
