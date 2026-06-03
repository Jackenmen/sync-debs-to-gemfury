from typing import Any
from urllib.parse import urljoin

import requests
from lxml import etree

from ..auth_info import AuthInfo
from ..base_package import Package

_etree_ns = etree.FunctionNamespace(None)


def _xpath_string(obj: Any) -> str:
    if isinstance(obj, str):
        return obj
    if isinstance(obj, list):
        if not obj:
            return ""
        return str(obj[0])
    return str(obj)


@_etree_ns("ends-with")
def _xpath_endswith(context, hay: Any, needle: Any) -> bool:
    hay = _xpath_string(hay)
    needle = _xpath_string(needle)
    return hay.endswith(needle)


class HtmlPackage(Package):
    def __init__(
        self,
        auth_info: AuthInfo,
        name: str,
        *,
        download_should_fail: bool,
        config: dict[str, str],
    ) -> None:
        super().__init__(
            auth_info, name, download_should_fail=download_should_fail, config=config
        )
        self._url = self._config["url"]
        self._xpath = etree.XPath(self._config["xpath"])

    def _download_deb(self) -> None:
        html_resp = requests.get(self._url)
        html_resp.raise_for_status()
        root = etree.HTML(html_resp.text)
        download_urls = self._xpath(root)
        if not download_urls:
            raise RuntimeError("Did not find any elements matching")
        download_url = urljoin(self._url, _xpath_string(download_urls[0]))

        file_resp = requests.get(download_url, stream=True)
        file_resp.raise_for_status()
        with open(self.deb_file.path, "wb") as fp:
            for chunk in file_resp.iter_content(None):
                fp.write(chunk)


PACKAGE_CLS = HtmlPackage
