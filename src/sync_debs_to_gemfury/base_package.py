import abc
import functools
import hashlib
import hmac
import importlib
import json
import os
import subprocess
from typing import NoReturn, Protocol, Self, TypedDict, runtime_checkable

import requests

from .auth_info import AuthInfo


class DebInfoDict(TypedDict):
    name: str
    version: str
    version_counter: int
    hashes: dict[str, str]


class DebInfo(metaclass=abc.ABCMeta):
    _PREFERRED_ALGORITHMS = ("sha256",)

    def __init__(self, *, version_counter: int = 0) -> None:
        self.version_counter: int = version_counter

    @property
    @abc.abstractmethod
    def name(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def version(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def hashes(self) -> dict[str, str]:
        raise NotImplementedError()

    def to_dict(self) -> DebInfoDict:
        return {
            "name": self.name,
            "version": self.version,
            "version_counter": self.version_counter,
            "hashes": self.hashes,
        }

    @property
    def repo_version(self) -> str:
        if not self.version_counter:
            return self.version
        return f"{self.version}-0gemfury{self.version_counter}"

    def verify_hashes(self, hashes: dict[str, str]) -> bool:
        for algorithm in self._PREFERRED_ALGORITHMS:
            try:
                a = self.hashes[algorithm]
                b = hashes[algorithm]
            except KeyError:
                continue
            else:
                return hmac.compare_digest(a, b)

        for algorithm in self.hashes.keys() & hashes.keys():
            try:
                a = self.hashes[algorithm]
                b = hashes[algorithm]
            except KeyError:
                continue
            else:
                return hmac.compare_digest(a, b)

        raise RuntimeError("No matching hashes were found.")


class EmptyDebInfo(DebInfo):
    def __init__(self, name: str) -> None:
        super().__init__()
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return ""

    @property
    def hashes(self) -> NoReturn:
        raise RuntimeError("Can't access hashes property on an empty deb info.")


class StaticDebInfo(DebInfo):
    def __init__(
        self,
        *,
        name: str,
        version: str,
        version_counter: int = 0,
        hashes: dict[str, str],
    ) -> None:
        super().__init__(version_counter=version_counter)
        self._name = name
        self._version = version
        self._hashes = hashes

    @classmethod
    def from_dict(cls, data: DebInfoDict, *, name: str) -> Self:
        return cls(
            name=data.get("name", name),
            version=data["version"],
            version_counter=data["version_counter"],
            hashes=data["hashes"],
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    @property
    def hashes(self) -> dict[str, str]:
        return self._hashes


class DebFile(DebInfo):
    def __init__(self, path: str) -> None:
        super().__init__()
        self.path = path

    @functools.cached_property
    def name(self) -> str:
        return subprocess.check_output(
            ("dpkg-deb", "-f", self.path, "Package"), text=True
        ).strip()

    @functools.cached_property
    def version(self) -> str:
        return subprocess.check_output(
            ("dpkg-deb", "-f", self.path, "Version"), text=True
        ).strip()

    @functools.cached_property
    def hashes(self) -> dict[str, str]:
        ret = {}
        with open(self.path, "rb") as fp:
            for algorithm in ("sha256",):
                fp.seek(0)
                ret[algorithm] = hashlib.file_digest(fp, algorithm).hexdigest()
        return ret


class Package(metaclass=abc.ABCMeta):
    def __init__(
        self,
        auth_info: AuthInfo,
        name: str,
        *,
        download_should_fail: bool,
        config: dict[str, str],
    ) -> None:
        self._auth_info = auth_info
        self.name = name
        self.download_should_fail = download_should_fail
        self._config = config
        self.deb_file = DebFile(os.path.join("debs", f"{self.name}.deb"))

    @abc.abstractmethod
    def _download_deb(self) -> None:
        raise NotImplementedError()

    def download_deb(self) -> None:
        self._download_deb()
        if self.deb_file.name != self.name:
            raise RuntimeError(
                f"The actual package name of {self.name!r} is {self.deb_file.name!r}."
            )

    def get_previous_deb_info(self) -> DebInfo:
        path = os.path.join("metadata", self.name)
        try:
            with open(path, encoding="utf-8") as fp:
                return StaticDebInfo.from_dict(json.load(fp), name=self.name)
        except FileNotFoundError:
            return EmptyDebInfo(self.name)

    def save_deb_info(self) -> None:
        path = os.path.join("metadata", self.name)
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(self.deb_file.to_dict(), fp, indent=4)
            fp.write("\n")

    def push_to_gemfury(self) -> None:
        resp = requests.post(
            f"https://push.fury.io/{self._auth_info.gemfury_username}/",
            files={"package": open(self.deb_file.path, "rb")},
            auth=(self._auth_info.gemfury_push_token, ""),
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
