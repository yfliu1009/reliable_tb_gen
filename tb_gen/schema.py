from dataclasses import dataclass, field
from typing import Callable

TVerilogParser = Callable[[str], str]


@dataclass
class Problem:
    id: int
    question: str
    answer: str
    refine_answer: str = ""
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def quoted_question(self) -> str:
        return f"problem: '''\n{self.question}\n'''"

    @property
    def quoted_answer(self) -> str:
        return f"solution: '''\n{self.answer}\n'''"

    @property
    def quoted_refine_answer(self) -> str:
        return f"refine_solution: '''\n{self.refine_answer}\n'''"

    def get_quoted_answer_ast(self, parser_func: TVerilogParser) -> str:
        if not parser_func:
            return ""

        try:
            ast = parser_func(self.answer)
        except Exception as e:
            ast = f"Error: {e}"

        return f"solution's ast: '''{ast}'''"

    def get_quoted_refine_answer_ast(self, parser_func: TVerilogParser) -> str:
        if not parser_func:
            return ""

        try:
            ast = parser_func(self.refine_answer)
        except Exception as e:
            ast = f"Error: {e}"

        return f"solution's ast: '''{ast}'''"


@dataclass
class Testbench:
    code: str = ""
    score: int | None = None
    simulation_output: str | None = None

    @property
    def quoted_code(self) -> str:
        return f"testbench: '''\n{self.code}\n'''"

    def get_quoted_code_ast(self, parser_func: TVerilogParser) -> str:
        if not parser_func:
            return ""

        try:
            ast = parser_func(self.code)
        except Exception as e:
            ast = f"Error: {e}"

        return f"testbench's ast: '''{ast}'''"

    @property
    def quoted_simulation_output(self) -> str:
        return f"simulation_output: '''\n{self.simulation_output}\n'''"


@dataclass
class RefinementCtx:
    problem: Problem
    testbench: Testbench = field(default_factory=lambda: Testbench())
    logs: dict[str, str] = field(default_factory=dict)
    # feedback: list[str] = field(default_factory=list)
    feedbacks: dict[str, str] = field(default_factory=dict)
    length: int = 0

    finished: bool = False
    _pipeline_metadata: dict[str, int | str] = field(default_factory=dict)

    @classmethod
    def from_problem(cls, problem: Problem) -> "RefinementCtx":
        return cls(
            problem=problem,
        )
