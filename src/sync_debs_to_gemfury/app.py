from typing import Literal, Self


class App:
    def __init__(self) -> None:
        self.errored = False

    @property
    def exit_code(self) -> Literal[0, 1]:
        if self.errored:
            return 1
        return 0

    @classmethod
    def from_environ(cls) -> Self:
        return cls()

    def run(self) -> int:
        return self.exit_code
