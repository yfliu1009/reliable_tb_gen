from abc import ABC, abstractmethod
from typing import List

from .schema import RefinementCtx, Testbench
from .verilog.verilog import simulate, get_tb_score, extract_verilog_code, try_compile
from .verilog.ast_pyverilog import parse_verilog_string
from .prompt import (
    QUESTION_GUIDE,
    TB_GUIDE,
    TB_FOR_QUESTION_GUIDE,
    FIX_GUIDE,
    TESTCASE_GUIDE,
    TB_TESTCASE_GUIDE,
    FIX_GUIDE_TESTCASE,
    Codev_r1_in_context_prefix,
    Codev_r1_in_context_suffix,
    reason_answer_guide,
    WELL_WRITTEN_GUIDE,
    REASON_ANSWER_GUIDE_V2,
    HINT_FILTER
)
from .llm import LLM
from .enums import QuestionRevisionResult, TestbenchRevisionBranch


QUESTION_REVISION = (
    True  # if false, skip question revision -> directly generate testbench
)


BASE_PIPELINE = False # if true, use base pipeline
HINT_FILTERED_PIPELINE = False  # if true, use hint-filtered pipeline for testbench revision
TESTCASE_PIPELINE = False  # if true, use testcase generation pipeline
PREGENERATION = True  # if true, pre-generate all feedbacks for each step and store in ctx.feedbacks

# base
class Step(ABC):
    """
    Abstract base class for a step in the pipeline.
    Each step should implement the `run` method.
    """

    @abstractmethod
    def run(self, ctx: RefinementCtx):
        """
        Run the step on the provided context
        """
        pass


class TestbenchSilmulation(Step):
    _label = (
        "testbench_simulation"  # used for recording number of simulations performed
    )

    def run(self, ctx: RefinementCtx):
        # increment counter
        _count = ctx._pipeline_metadata.setdefault(f"{self._label}_count", 0)
        ctx._pipeline_metadata[f"{self._label}_count"] += 1

        id, answer, tb = ctx.problem.id, ctx.problem.answer, ctx.testbench.code

        sim_out = simulate(id, answer, tb)
        tb_score = get_tb_score(sim_out)

        ctx.testbench.simulation_output = sim_out
        ctx.testbench.score = tb_score

        ctx.logs[f"{_count}_tb_score"] = tb_score

        if ctx.testbench and ctx.testbench.score == 10:
            ctx.finished = True

        return ctx


class LLMGeneration(Step):
    _generation_id = 0

    def __init__(self, llm: LLM, contexts: List[str] = [], feedback_key: str = None):
        # increment generation id for unique identification
        self.generation_id = LLMGeneration._generation_id
        LLMGeneration._generation_id += 1

        self.llm = llm
        self.context = "\n\n".join(contexts)
        self.feedback_key = feedback_key if feedback_key else f"fb_{self.generation_id}"

    def run(self, ctx: RefinementCtx):
        response = self.llm.generate(self.contexts)
        ctx.feedbacks[self.feedback_key] = response

        return ctx


### DONE
class QuestionRevision(LLMGeneration):
    def __init__(
        self, llm: LLM, contexts: List[str] = [WELL_WRITTEN_GUIDE], feedback_key: str = None
    ):
        super().__init__(llm, contexts, feedback_key)

    def run(self, ctx: RefinementCtx):
        import re

        response = self.llm.generate(
            "\n\n".join([self.context, ctx.problem.quoted_question, ctx.problem.quoted_answer])
        )
        ctx.feedbacks[self.feedback_key] = response

        if response:
            if re.search(r"\*+\s*YES\s*\*+", response) is not None:
                ctx.logs["question_state"] = QuestionRevisionResult.PASS.value
            elif re.search(r"\*+\s*DROP\s*\*+", response) is not None:
                ctx.logs["question_state"] = QuestionRevisionResult.DROP.value
                ctx.finished = True
            elif re.search(r"\*+\s*NO\s*\*+", response) is not None:
                tmp_ques = extract_verilog_code(response, "[BEGIN PROB]", "[END PROB]")
                tmp_ans = extract_verilog_code(response, "[BEGIN SOL]", "[END SOL]")
                if tmp_ques and tmp_ans and try_compile(ctx.problem.id, tmp_ans):
                    ctx.logs["question_state"] = QuestionRevisionResult.FIXED.value
                    ctx.problem.question = tmp_ques
                    ctx.problem.answer = tmp_ans
                else:
                    # TODO: we could try a few more times here
                    ctx.logs["question_state"] = QuestionRevisionResult.ERROR.value
                    ctx.finished = True
        else:
            # TODO: we could try a few more times here
            ctx.logs["question_state"] = QuestionRevisionResult.UNDECIDED.value
            ctx.finished = True

        return ctx


class TBForQuestionRevision(LLMGeneration):
    def __init__(
        self,
        llm: LLM,
        contexts: List[str] = [TB_FOR_QUESTION_GUIDE],
        feedback_key: str = None,
    ):
        super().__init__(llm, contexts, feedback_key)

    def run(self, ctx: RefinementCtx):
        import re

        response = self.llm.generate(
            "\n\n".join(
                [self.context, ctx.problem.quoted_question, ctx.testbench.quoted_code]
            )
        )
        ctx.feedbacks[self.feedback_key] = response

        if response:
            if re.search(r"\*+\s*YES\s*\*+", response) is not None:
                ctx.logs["question_state"] = QuestionRevisionResult.PASS.value
            elif re.search(r"\*+\s*DROP\s*\*+", response) is not None:
                ctx.logs["question_state"] = QuestionRevisionResult.DROP.value
                ctx.finished = True
            elif re.search(r"\*+\s*NO\s*\*+", response) is not None:
                tmp_ques = extract_verilog_code(response, "[BEGIN PROB]", "[END PROB]")
                tmp_ans = extract_verilog_code(response, "[BEGIN SOL]", "[END SOL]")
                if tmp_ques and tmp_ans and try_compile(ctx.problem.id, tmp_ans):
                    ctx.logs["question_state"] = QuestionRevisionResult.FIXED.value
                    ctx.problem.question = tmp_ques
                    ctx.problem.answer = tmp_ans
                else:
                    # TODO: we could try a few more times here
                    ctx.logs["question_state"] = QuestionRevisionResult.ERROR.value
                    ctx.finished = True
        else:
            # TODO: we could try a few more times here
            ctx.logs["question_state"] = QuestionRevisionResult.UNDECIDED.value
            ctx.finished = True

        return ctx

#DONE
class TestbenchGeneration(LLMGeneration):
    def __init__(
        self, llm: LLM, contexts: List[str] = [TB_GUIDE], feedback_key: str = None
    ):
        super().__init__(llm, contexts, feedback_key=feedback_key)

    def run(self, ctx: RefinementCtx):

        # print(ctx.problem.question, "\n###question for tb generation###\n")
        # print(ctx.problem.answer, "\n###answer for tb generation###\n")

        response = self.llm.generate(
            "\n\n".join([self.context, ctx.problem.quoted_question])
        )
        ctx.feedbacks[self.feedback_key] = response

        tb_code = extract_verilog_code(response)
        if tb_code:
            ctx.testbench.code = tb_code
            ctx.logs["init_tb"] = True
        else:
            ctx.logs["init_tb"] = False
            ctx.finished = True

        return ctx

#DONE
class TestbenchRevision(LLMGeneration):
    _label = "testbench_revision"  # used for recording number of revisions performed

    def __init__(
        self,
        llm: LLM,
        contexts: List[str] = [FIX_GUIDE],
        feedback_key: str = None,
        enable_ast: bool = False,
    ):
        super().__init__(llm, contexts, feedback_key)

        self.parser_func = parse_verilog_string if enable_ast else None

    def run(self, ctx: RefinementCtx):
        # increment counter
        _count = ctx._pipeline_metadata.setdefault(f"{self._label}_count", 0)
        ctx._pipeline_metadata[f"{self._label}_count"] += 1

        import re

        response = self.llm.generate(
            "\n\n".join(
                [
                    self.context,
                    ctx.problem.quoted_question,
                    ctx.problem.quoted_answer,
                    ctx.problem.get_quoted_answer_ast(self.parser_func),
                    ctx.testbench.quoted_code,
                    ctx.testbench.get_quoted_code_ast(self.parser_func),
                    ctx.testbench.quoted_simulation_output,
                ]
            )
        )

        # ctx.length += len(prompt)

        ctx.feedbacks[self.feedback_key] = response

        has_sol = re.search(r"\*+\s*SOLUTION\s*\*+", response) is not None
        has_tb = re.search(r"\*+\s*TESTBENCH\s*\*+", response) is not None

        if (has_sol and has_tb) or (not has_sol and not has_tb):
            ctx.logs[f"{_count}_branch"] = TestbenchRevisionBranch.UNDECIDED.value

            return ctx

        fixed_code = extract_verilog_code(response)

        if has_sol:
            ctx.logs[f"{_count}_branch"] = TestbenchRevisionBranch.SOLUTION.value
            if not fixed_code:
                ctx.logs[f"{_count}_fix"] = False
                return ctx
            ctx.logs[f"{_count}_fix"] = True
            ctx.problem.answer = fixed_code
        else:
            ctx.logs[f"{_count}_branch"] = TestbenchRevisionBranch.TESTBENCH.value
            if not fixed_code:
                ctx.logs[f"{_count}_fix"] = False
                return ctx
            ctx.logs[f"{_count}_fix"] = True
            ctx.testbench.code = fixed_code

        return ctx


class RefinementPipeline:
    def __init__(
        self, llm: LLM, steps: List[Step] = None, tb_revision_max_retries: int = 3
    ):
        if TESTCASE_PIPELINE:
            self.steps = (
                [
                    QuestionGeneration(llm, feedback_key="question_generation"),
                    SolutionGeneration(llm, feedback_key="solution_generation"),
                    TestcaseGeneration(llm, feedback_key="testcase_generation"),
                    TestbenchGeneration_TC(
                        llm, feedback_key="testbench_generation_with_testcases"
                    ),
                    TestbenchSilmulation_TC(),
                    *(
                        TestbenchRevision_TC(
                            llm,
                            feedback_key="testbench_revision_with_testcases",
                            enable_ast=True,
                        ),
                        TestbenchSilmulation_TC(),
                    )
                    * tb_revision_max_retries,  # tb revision max retries = 3
                ]
                if steps is None
                else steps
            )

        else:
            self.steps = (
                [
                    *(
                        [QuestionRevision(llm, feedback_key="question_revision")]
                        if QUESTION_REVISION
                        else []
                    ),
                    TestbenchGeneration(llm, feedback_key="testbench_generation"),
                    TestbenchSilmulation_TC(),
                    *(
                        TestbenchRevision(
                            llm, feedback_key="testbench_revision", enable_ast=True
                        ),
                        TestbenchSilmulation_TC(),
                    )
                    * tb_revision_max_retries,  # tb revision max retries = 3
                ]
                if steps is None
                else steps
            )


        print(self.steps)

    def __call__(self, ctx: RefinementCtx) -> RefinementCtx:
        print(f"start running {ctx.problem.id}...")
        for step in self.steps:
            ctx = step.run(ctx)

            if ctx.finished:
                print(f"{ctx.problem.id} finished!")
                break

        return ctx




class NewRefinementPipeline:
    def __init__(
        self, llm: LLM, steps: List[Step] = None, tb_revision_max_retries: int = 6
    ):
        if BASE_PIPELINE:
            self.steps = (
                [
                    *(
                        [QuestionRevision(llm, feedback_key="question_revision")]
                        if QUESTION_REVISION
                        else []
                    ),
                    TestbenchGeneration(llm, feedback_key="testbench_generation"),
                    TestbenchSilmulation_TC(),
                    *(
                        TestbenchRevision(
                            llm, feedback_key="testbench_revision", enable_ast=True
                        ),
                        TestbenchSilmulation_TC(),
                    )
                    * tb_revision_max_retries,  # tb revision max retries = 6
                ]
                if steps is None
                else steps
            )
        elif HINT_FILTERED_PIPELINE:
            self.steps = (
                [
                    QuestionRevision(llm, feedback_key="question_revision"),
                    HintFilter(llm, feedback_key="hint_filter"),
                    TestbenchGeneration(llm, feedback_key="testbench_generation"),
                    TestbenchSilmulation_TC(),
                    *(
                        TestbenchRevision(
                            llm, feedback_key="testbench_revision", enable_ast=True
                        ),
                        TestbenchSilmulation_TC(),
                    )
                    * tb_revision_max_retries,  # tb revision max retries = 6
                ]
                if steps is None
                else steps
            )
        elif TESTCASE_PIPELINE:
            self.steps = (
                [
                    QuestionRevision(llm, feedback_key="question_revision"),
                    HintFilter(llm, feedback_key="hint_filter"),
                    TestcaseGeneration(llm, feedback_key="testcase_generation"),
                    TestbenchGeneration_TC(
                        llm, feedback_key="testbench_generation_with_testcases"
                    ),
                    TestbenchSilmulation_TC(),
                    *(
                        TestbenchRevision_TC(
                            llm,
                            feedback_key="testbench_revision_with_testcases",
                            enable_ast=True,
                        ),
                        TestbenchSilmulation_TC(),
                    )
                    * tb_revision_max_retries,  # tb revision max retries = 6
                ]
                if steps is None
                else steps
            )
        elif PREGENERATION:
            self.steps = (
                [
                    TestcaseGeneration(llm, feedback_key="testcase_generation"),
                    TestbenchGeneration_TC(
                        llm, feedback_key="testbench_generation_with_testcases"
                    ),
                    TestbenchSilmulation_TC(),
                    *(
                        TestbenchRevision_TC(
                            llm,
                            feedback_key="testbench_revision_with_testcases",
                            enable_ast=True,
                        ),
                        TestbenchSilmulation_TC(),
                    )
                    * 3,  # pregen tb revision max retries = 6
                    QuestionGeneration(llm, feedback_key="question_generation"),
                    SolutionGeneration(llm, feedback_key="solution_generation"),
                    HintFilter(llm, feedback_key="hint_filter"),
                    TestcaseGeneration(llm, feedback_key="testcase_generation"),
                    TestbenchGeneration_TC(
                        llm, feedback_key="testbench_generation_with_testcases"
                    ),
                    TestbenchSilmulation_TC(),
                    *(
                        TestbenchRevision_TC(
                            llm,
                            feedback_key="testbench_revision_with_testcases",
                            enable_ast=True,
                        ),
                        TestbenchSilmulation_TC(),
                    )
                    * 3,  # pregen tb revision max retries = 6
                ]
                if steps is None
                else steps
            )
            # self.steps = (
            #     [
            #         QuestionGeneration(llm, feedback_key="question_generation"),
            #         SolutionGeneration(llm, feedback_key="solution_generation"),
            #         TestcaseGeneration(llm, feedback_key="testcase_generation"),
            #         TestbenchGeneration_TC(
            #             llm, feedback_key="testbench_generation_with_testcases"
            #         ),
            #         TestbenchSilmulation_TC(),
            #         *(
            #             TestbenchRevision_TC(
            #                 llm,
            #                 feedback_key="testbench_revision_with_testcases",
            #                 enable_ast=True,
            #             ),
            #             TestbenchSilmulation_TC(),
            #         )
            #         * tb_revision_max_retries,  # tb revision max retries = 6
            #     ]
            #     if steps is None
            #     else steps
            # )

        # else:
        #     self.steps = (
        #         [
        #             *(
        #                 [QuestionRevision(llm, feedback_key="question_revision")]
        #                 if QUESTION_REVISION
        #                 else []
        #             ),
        #             TestbenchGeneration(llm, feedback_key="testbench_generation"),
        #             TestbenchSilmulation(),
        #             *(
        #                 TestbenchRevision(
        #                     llm, feedback_key="testbench_revision", enable_ast=True
        #                 ),
        #                 TestbenchSilmulation(),
        #             )
        #             * tb_revision_max_retries,  # tb revision max retries = 3
        #         ]
        #         if steps is None
        #         else steps
        #     )


        print(self.steps)

    def __call__(self, ctx: RefinementCtx) -> RefinementCtx:
        print(f"start running {ctx.problem.id}...")
        for step in self.steps:
            ctx = step.run(ctx)

            if ctx.finished:
                print(f"{ctx.problem.id} finished!")
                break

        return ctx






### NOTE: sequence correct, not test yet
class TBForQuesRefinementPipeline:
    def __init__(
        self, llm: LLM, steps: List[Step] = None, tb_revision_max_retries: int = 3
    ):
        self.steps = (
            [
                TestbenchGeneration(llm, feedback_key="testbench_generation"),
                TestbenchSilmulation(),
                *(
                    TestbenchRevision(llm, feedback_key="testbench_revision"),
                    TestbenchSilmulation(),
                )
                * tb_revision_max_retries,  # tb revision max retries = 3
                *(
                    [TBForQuestionRevision(llm, feedback_key="question_revision")]
                    if QUESTION_REVISION
                    else []
                ),
                TestbenchGeneration(llm, feedback_key="testbench_generation"),
                TestbenchSilmulation(),
                *(
                    TestbenchRevision(llm, feedback_key="testbench_revision"),
                    TestbenchSilmulation(),
                )
                * tb_revision_max_retries,  # tb revision max retries = 3
            ]
            if steps is None
            else steps
        )

    def __call__(self, ctx: RefinementCtx) -> RefinementCtx:
        for step in self.steps:
            if ctx.finished and (
                step.__class__.__name__ == "TestbenchSilmulation"
                or step.__class__.__name__ == "TestbenchRevision"
            ):
                continue
            if not ctx.finished and step.__class__.__name__ == "QuestionRevision":
                break
            if step.__class__.__name__ == "QuestionRevision":
                ctx.finished = False
                ctx._pipeline_metadata[f"testbench_simulation_count"] = 10
                ctx._pipeline_metadata[f"testbench_revision_count"] = 10

            print("Running step:", step.__class__.__name__)
            ctx = step.run(ctx)

        return ctx

#DONE
class TestcaseGeneration(LLMGeneration):
    def __init__(
        self, llm: LLM, contexts: List[str] = [TESTCASE_GUIDE], feedback_key: str = None
    ):
        super().__init__(llm, contexts, feedback_key=feedback_key)

    def run(self, ctx: RefinementCtx):
        prompt = "\n\n".join([self.context, ctx.problem.quoted_question])
        ctx.length += len(prompt)

        response = self.llm.generate(prompt)

        ctx.feedbacks[self.feedback_key] = response

        reasoning_trace = extract_verilog_code(
            response, begin="<think>", done="</think>"
        )
        ctx.problem.testcase_reasoning_trace = reasoning_trace

        ### remove reasoning trace of R1
        end_tag = "</think>"
        end_index = response.find(end_tag)
        if end_index != -1:
            response = response[end_index + len(end_tag) :]

        testcase = extract_verilog_code(response)

        if testcase:
            ctx.problem.testcase = testcase
            ctx.logs["testcase"] = True
        else:
            ctx.logs["testcase"] = False
            ctx.finished = True
        return ctx

#DONE
class TestbenchGeneration_TC(LLMGeneration):
    def __init__(
        self,
        llm: LLM,
        contexts: List[str] = [TB_TESTCASE_GUIDE],
        feedback_key: str = None,
    ):
        super().__init__(llm, contexts, feedback_key=feedback_key)

    def run(self, ctx: RefinementCtx):
        prompt = "\n\n".join(
            [self.context, ctx.problem.quoted_question, ctx.problem.testcase]
        )
        ctx.length += len(prompt)
        response = self.llm.generate(prompt)

        ctx.feedbacks[self.feedback_key] = response

        ### get reasoning trace of testbench

        # print(response, "\ntb_gen response\n\n")
        reasoning_trace = extract_verilog_code(
            response, begin="<think>", done="</think>"
        )
        # print(reasoning_trace, "\ngen reasoning\n\n\n")
        ctx.testbench.reasoning_trace = reasoning_trace

        ### remove reasoning trace of R1

        end_tag = "</think>"
        end_index = response.find(end_tag)
        if end_index != -1:
            response = response[end_index + len(end_tag) :]

        # print(response, "\ntb_gen_response_extract\n\n")

        tb_code = extract_verilog_code(response)
        # print(tb_code, "\ntb_gen_code extract end\n\n")

        if tb_code:
            ctx.testbench.code = tb_code
            ctx.logs["init_tb"] = True
        else:
            ctx.logs["init_tb"] = False
            ctx.finished = True

        return ctx

#DONE
class TestbenchSilmulation_TC(Step):
    _label = (
        "testbench_simulation"  # used for recording number of simulations performed
    )

    def run(self, ctx: RefinementCtx):
        # increment counter
        _count = ctx._pipeline_metadata.setdefault(f"{self._label}_count", 0)
        ctx._pipeline_metadata[f"{self._label}_count"] += 1

        id, answer, tb = ctx.problem.id, ctx.problem.answer, ctx.testbench.code

        sim_out = simulate(id, answer, tb)


        # print(sim_out, "\nsimulation output\n\n")
        passed_cases = 0
        total_cases = 1

        import re


        passed_pattern = r"```Number of passed test cases:\s*(\d+)\s*```"
        total_pattern = r"```Number of total test cases:\s*(\d+)\s*```"

        passed_match = re.search(passed_pattern, sim_out)
        total_match = re.search(total_pattern, sim_out)

        if passed_match and total_match:
            passed_cases = int(passed_match.group(1))
            total_cases = int(total_match.group(1))
        # pattern = (
        #     r"Number of passed test cases: (\d+).*Number of total test cases: (\d+)"
        # )
        # match = re.search(pattern, sim_out, re.DOTALL)
        # if match:
        #     passed_cases = int(match.group(1))
        #     total_cases = int(match.group(2))

        print(f"Passed test cases: {passed_cases}")
        print(f"Total test cases: {total_cases}")

        tb_score = passed_cases / total_cases if total_cases > 0 else 0

        ctx.testbench.simulation_output = sim_out
        ctx.testbench.score = tb_score

        # print('score: ', ctx.testbench.score)

        ctx.logs[f"{_count}_tb_score"] = tb_score

        if ctx.testbench and ctx.testbench.score == 1.0:
            ctx.finished = True

        return ctx

#DONE
class TestbenchRevision_TC(LLMGeneration):
    _label = "testbench_revision"  # used for recording number of revisions performed

    def __init__(
        self,
        llm: LLM,
        contexts: List[str] = [FIX_GUIDE_TESTCASE],
        feedback_key: str = None,
        enable_ast: bool = False,
    ):
        super().__init__(llm, contexts, feedback_key)

        self.parser_func = parse_verilog_string if enable_ast else None

    def run(self, ctx: RefinementCtx):
        # increment counter
        _count = ctx._pipeline_metadata.setdefault(f"{self._label}_count", 0)
        ctx._pipeline_metadata[f"{self._label}_count"] += 1

        import re

        prompt = "\n\n".join(
            [
                self.context,
                ctx.problem.quoted_question,
                ctx.problem.quoted_answer,
                ctx.problem.get_quoted_answer_ast(self.parser_func),
                ctx.testbench.quoted_code,
                ctx.testbench.get_quoted_code_ast(self.parser_func),
                ctx.testbench.quoted_simulation_output,
            ]
        )
        ctx.length += len(prompt)
        response = self.llm.generate(prompt)

        ctx.feedbacks[self.feedback_key] = response

        has_sol = re.search(r"\*+\s*SOLUTION\s*\*+", response) is not None
        has_tb = re.search(r"\*+\s*TESTBENCH\s*\*+", response) is not None

        if (has_sol and has_tb) or (not has_sol and not has_tb):
            ctx.logs[f"{_count}_branch"] = TestbenchRevisionBranch.UNDECIDED.value

            return ctx

        ###get reasoning trace of testbench

        # print(response, "\ntb_rev response\n\n")
        reasoning_trace = extract_verilog_code(
            response, begin="<think>", done="</think>"
        )
        # print(reasoning_trace, "\nrev reasoning\n\n\n")
        ctx.testbench.reasoning_trace = reasoning_trace

        ### remove reasoning trace of R1

        end_tag = "</think>"
        end_index = response.find(end_tag)
        if end_index != -1:
            response = response[end_index + len(end_tag) :]

        # print(response, "\ntb_gen_response_extract\n\n")

        fixed_code = extract_verilog_code(response)

        if has_sol:
            ctx.logs[f"{_count}_branch"] = TestbenchRevisionBranch.SOLUTION.value
            if not fixed_code:
                ctx.logs[f"{_count}_fix"] = False
                return ctx
            ctx.logs[f"{_count}_fix"] = True
            ctx.problem.answer = fixed_code
        else:
            ctx.logs[f"{_count}_branch"] = TestbenchRevisionBranch.TESTBENCH.value
            if not fixed_code:
                ctx.logs[f"{_count}_fix"] = False
                return ctx
            ctx.logs[f"{_count}_fix"] = True
            ctx.testbench.code = fixed_code

        return ctx

#DONE
class QuestionGeneration(LLMGeneration):
    def __init__(
        self,
        llm: LLM,
        contexts: List[str] = [Codev_r1_in_context_prefix],
        feedback_key: str = None,
    ):
        super().__init__(llm, contexts, feedback_key=feedback_key)

    def run(self, ctx: RefinementCtx):
        prompt = "\n\n".join(
            [self.context, ctx.problem.answer, Codev_r1_in_context_suffix]
        )
        
        # print(ctx.problem.answer)
        
        ctx.length += len(prompt)

        response = self.llm.generate(prompt)

        ctx.feedbacks[self.feedback_key] = response

        reasoning_trace = extract_verilog_code(
            response, begin="<think>", done="</think>"
        )
        ctx.problem.question_reasoning_trace = reasoning_trace

        ### remove reasoning trace of R1

        end_tag = "</think>"
        end_index = response.find(end_tag)
        if end_index != -1:
            response = response[end_index + len(end_tag) :]

        new_question = extract_verilog_code(
            response, begin="<problem>", done="</problem>"
        )

        if new_question:
            ctx.logs["question"] = True
            ctx.problem.question = new_question
        else:
            ctx.logs["question"] = False
            ctx.finished = True

        # print(ctx.problem.question, "\n###new question###\n")

        return ctx

#DONE
class SolutionGeneration(LLMGeneration):
    def __init__(
        self,
        llm: LLM,
        contexts: List[str] = [REASON_ANSWER_GUIDE_V2],
        feedback_key: str = None,
    ):
        super().__init__(llm, contexts, feedback_key=feedback_key)

    def run(self, ctx: RefinementCtx):
        prompt = "\n\n".join([self.context, ctx.problem.quoted_question])
        ctx.length += len(prompt)

        response = self.llm.generate(prompt)

        ctx.feedbacks[self.feedback_key] = response

        reasoning_trace = extract_verilog_code(
            response, begin="<think>", done="</think>"
        )
        ctx.problem.reasoning_trace = reasoning_trace

        # ### remove reasoning trace of R1

        end_tag = "</think>"
        end_index = response.find(end_tag)
        if end_index != -1:
            response = response[end_index + len(end_tag) :]

        # reasoning_trace = extract_verilog_code(
        #     response, begin="<reasoning>", done="</reasoning>"
        # )
        code = extract_verilog_code(response, begin="<solution>", done="</solution>")

        # print(reasoning_trace, '\nreasoning trace\n')
        # print(code, '\nsolution\n')

        if code:
            ctx.problem.solution_reasoning_trace = reasoning_trace
            # ctx.problem.answer = code
            ctx.problem.answer = code
            ctx.logs["solution"] = True
        else:
            ctx.logs["solution"] = False
            ctx.finished = True

        # print(ctx.problem.answer, "\n###new solution###\n")
        # print(ctx.problem.solution_reasoning_trace, "\n###new reasoning trace###\n")

        return ctx


class HintFilter(LLMGeneration):
    def __init__(
        self, llm: LLM, contexts: List[str] = [HINT_FILTER], feedback_key: str = None
    ):
        super().__init__(llm, contexts, feedback_key)

    def run(self, ctx: RefinementCtx):
        import re

        response = self.llm.generate(
            "\n\n".join([self.context, ctx.problem.quoted_question, ctx.problem.quoted_answer])
        )
        ctx.feedbacks[self.feedback_key] = response

        if response:
            if re.search(r"\*+\s*NO\s*\*+", response) is not None:
                ctx.logs["hint_filter"] = "PASS"
            elif re.search(r"\*+\s*YES\s*\*+", response) is not None:
                tmp_ques = extract_verilog_code(response, "[BEGIN PROB]", "[END PROB]")
                if tmp_ques:
                    ctx.logs["hint_filter"] = "FIXED"
                    ctx.problem.question = tmp_ques
                else:
                    ctx.logs["hint_filter"] = "NO_SPEC"
        else:
            # TODO: we could try a few more times here
            ctx.logs["question_state"] = "ERROR"
            ctx.finished = True

        return ctx
