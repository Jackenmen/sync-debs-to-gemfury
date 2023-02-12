import re

import requests

from ..base_package import Package

RELEASES_URL = "https://api.github.com/repos/{repository}/releases/latest"


class GitHubReleasePackage(Package):
    def __init__(self, name: str, config: dict[str, str]) -> None:
        super().__init__(name, config)
        self._asset_name_pattern = re.compile(config["asset_name_pattern"])

    def download_deb(self) -> None:
        resp = requests.get(RELEASES_URL.format(repository=self._config["repository"]))
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
