"""Sample Python file for testing parser."""

import os
from typing import List


def simple_function(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y


async def async_function(name: str) -> str:
    """Async function example."""
    return f"Hello, {name}"


@property
def decorated_function():
    """Function with decorator."""
    return "decorated"


class SampleClass:
    """Sample class with methods."""

    def __init__(self, name: str):
        """Initialize the class."""
        self.name = name

    def instance_method(self, value: int) -> int:
        """Instance method."""
        return value * 2

    @staticmethod
    def static_method():
        """Static method."""
        return "static"

    @classmethod
    def class_method(cls):
        """Class method."""
        return cls.__name__

    async def async_method(self):
        """Async method."""
        return self.name
