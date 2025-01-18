from __future__ import annotations

import pytest
from pydantic import BaseModel
from pydantic import PositiveInt


class Student(BaseModel):
    name: str
    age: PositiveInt
    classes: list[str]


@pytest.fixture
def student_cls() -> type[Student]:
    return Student
