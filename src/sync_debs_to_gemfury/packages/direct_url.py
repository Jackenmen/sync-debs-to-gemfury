import requests

from ..base_package import Package


class DirectUrlPackage(Package):
    def _download_deb(self) -> None:
        resp = requests.get(self._config["url"], stream=True)
        resp.raise_for_status()
        with open(self.deb_file.path, "wb") as fp:
            for chunk in resp.iter_content(None):
                fp.write(chunk)


PACKAGE_CLS = DirectUrlPackage
