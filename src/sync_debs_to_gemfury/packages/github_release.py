import re

import requests

from ..auth_info import AuthInfo
from ..base_package import Package

RELEASES_URL = "https://api.github.com/repos/{repository}/releases/"


class GitHubReleasePackage(Package):
    def __init__(self, auth_info: AuthInfo, name: str, config: dict[str, str]) -> None:
        super().__init__(auth_info, name, config)
        self._asset_name_pattern = re.compile(config["asset_name_pattern"])
        self._url = RELEASES_URL.format(repository=config["repository"])
        if tag := config.get("tag", ""):
            self._url += f"tags/{tag}"
        else:
            self._url += "latest"

    def _download_deb(self) -> None:
        resp = requests.get(
            self._url,
            headers={"Authorization": f"Bearer {self._auth_info.github_token}"},
        )
        resp.raise_for_status()
        release_data = resp.json()
        valid_assets = []
        for asset_data in release_data["assets"]:
            if self._asset_name_pattern.search(asset_data["name"]) is not None:
                valid_assets.append(asset_data["browser_download_url"])

        if not valid_assets:
            raise RuntimeError(
                f"No asset in {release_data['name']} release matches the name pattern."
            )

        if len(valid_assets) != 1:
            raise RuntimeError(
                f"More than one asset in {release_data['name']}"
                " release matches the name pattern."
            )

        resp = requests.get(valid_assets[0], stream=True)
        resp.raise_for_status()
        with open(self.deb_file.path, "wb") as fp:
            for chunk in resp.iter_content(None):
                fp.write(chunk)


PACKAGE_CLS = GitHubReleasePackage
