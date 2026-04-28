# enums.py
from enum import Enum


class QuestionRevisionResult(Enum):
    """
    Enum representing the result of a question revision.
    """

    PASS = "PASS"
    DROP = "DROP"
    FIXED = "FIXED"
    ERROR = "ERROR"
    UNDECIDED = "UNDECIDED"


class TestbenchRevisionBranch(Enum):
    """
    Enum representing the result of a testbench revision.
    """

    SOLUTION = "SOLUTION"
    TESTBENCH = "TESTBENCH"
    UNDECIDED = "UNDECIDED"
