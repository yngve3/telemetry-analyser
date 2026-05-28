"""Use case for stopping telemetry stream publication."""


class StopStream:
    async def execute(self, session_id: str) -> None:
        raise NotImplementedError

