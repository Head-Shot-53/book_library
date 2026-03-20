class BookingValidationError(Exception):
    def __init__(self, message: str, *, code: str = "invalid_booking"):
        self.message = message
        self.code = code

        super().__init__(message)


class BookingConflictError(BookingValidationError):
    def __init__(
        self, message: str = ("Resource is already booked for this time period.")
    ):
        super().__init__(message, code="booking_conflict")


class BookingStateError(BookingValidationError):
    def __init__(self, message: str, *, code: str = "invalid_booking_state"):
        super().__init__(message, code=code)
