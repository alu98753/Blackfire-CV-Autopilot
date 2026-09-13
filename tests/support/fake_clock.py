"""FakeClock test double for deterministic time simulation."""


class FakeClock:
    def __init__(self, now: float = 1000.0):
        self.now = float(now)

    def monotonic(self) -> float:
        return self.now

    def advance(self, seconds: float) -> float:
        self.now += float(seconds)
        return self.now

    def sleep(self, seconds: float) -> None:
        self.advance(seconds)
