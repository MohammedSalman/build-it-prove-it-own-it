"""The reference model: what AfterHours should do for ONE event, as plainly as possible.

It knows nothing about HTTP, SQL, threads or payments. Its whole state is a dict.
It was written from docs/requirements.md (R1 to R3), not from the app's code, so when the
app and the model disagree, one of them misread the requirements. Find out which.
"""


class ReferenceModel:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.status = {}  # reservation number (1, 2, 3 ... in the order made) -> "confirmed" or "cancelled"

    def confirmed(self) -> int:
        return sum(1 for s in self.status.values() if s == "confirmed")

    def places_left(self) -> int:
        return self.capacity - self.confirmed()

    def reserve(self) -> int:
        """Returns the HTTP status the app should answer with."""
        if self.confirmed() >= self.capacity:
            return 409                      # R1: never more confirmed than capacity
        self.status[len(self.status) + 1] = "confirmed"
        return 201

    def cancel(self, number: int) -> int:
        """Cancel reservation `number`. Returns the HTTP status the app should answer with."""
        if number not in self.status:
            return 404
        self.status[number] = "cancelled"   # R3: cancelling again changes nothing
        return 200
