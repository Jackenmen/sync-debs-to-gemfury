import dataclasses
import os
from typing import Self


@dataclasses.dataclass
class AuthInfo:
    github_repository: str
    github_token: str
    gemfury_username: str
    gemfury_push_token: str

    @classmethod
    def from_environ(cls) -> Self:
        return cls(
            github_repository=os.environ["GITHUB_REPOSITORY"],
            github_token=os.environ["GITHUB_TOKEN"],
            gemfury_username=os.environ["GEMFURY_USERNAME"],
            gemfury_push_token=os.environ["GEMFURY_PUSH_TOKEN"],
        )
