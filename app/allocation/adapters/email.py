from typing import Any


def send(*args: Any) -> None:
    """Send an email to the user."""
    print("Sending email to user", *args)
