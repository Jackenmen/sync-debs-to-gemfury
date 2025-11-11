import typing

from strictyaml import (
    Bool,
    EmptyDict,
    Map,
    MapPattern,
    Optional,
    Str,
    load as yaml_load,
)

PACKAGE_KEYS = {
    "type": Str(),
    Optional("download_should_fail", default=False): Bool(),
    Optional("config", default={}): EmptyDict() | MapPattern(Str(), Str()),
}

SCHEMA = Map(
    {
        "packages": MapPattern(Str(), Map(PACKAGE_KEYS)),
    }
)


class PackageDict(typing.TypedDict):
    type: str
    download_should_fail: bool
    config: dict[str, str]


class ConfigDict(typing.TypedDict):
    packages: dict[str, PackageDict]


def load(path: str) -> ConfigDict:
    with open(path, encoding="utf-8") as fp:
        return yaml_load(fp.read(), SCHEMA, label="config.yaml").data
