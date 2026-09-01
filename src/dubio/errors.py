class DubError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        context: dict | None = None,
        suggested_action: str | None = None,
    ):
        self.code = code
        self.message = message
        self.context = context or {}
        self.suggested_action = suggested_action
        super().__init__(f"[{code}] {message} | {self.context}")
