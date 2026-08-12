class BusinessException(Exception):
    def __init__(self, code: int, message: str, error_code: str | None = None):
        self.code = code
        self.message = message
        self.error_code = error_code
        super().__init__(message)
