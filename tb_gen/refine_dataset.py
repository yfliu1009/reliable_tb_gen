"""
0. Initial dataset score? Score after augmentation?
1. Filter out dataset whose output does not compile
2. Ask LLM whether the Verilog coding question is well written
3. if well written:
    # keep
   else if can be salvaged:
    # revise
    if revision compiles:
     # keep
    else:
     # drop
   else (utterly unsolvable):
    # drop
4a Ask LLM to generate a testbench for the given Verilog coding problem
    note: meaningful debugging information + exactly 10 test cases
    if fails to generate testbench:
     # drop dataset
    else:
     # continue
4b Ask LLM to generate a testbench for the given Verilog coding problem & answer
    * explain how the Verilog code works.
    * check whether answer is valid?
    * provide testbench if answer is valid.
5. iterate over n_trials times:
    * simulate answer with testbench
    if tb_score == 10:
     # early exit
    else:
     * Provide simulation results to LLM & ask it to
        [MAYBE] add AST information
        [MAYBE] ensemble voting
        [MAYBE] multiple versions for the same problem, validate later
        1. determine whether to fix answer or tb
        2. provide fixed code
     * reassign answer or tb to fixed code

Total: 130 questions
0_tb_score=10: 59
1_tb_score=10: 33
2_tb_score=10: 15
(59 + 33 + 15 = 107, 107 / 128 = 83.6%)

[CONTROVERSIAL, low confidence]
2_tb_score=9: 2
2_tb_score=8: 1
2_tb_score=7: 1
1_tb_score=9: 2
1_tb_score=8: 1
(2 + 1 + 1 + 2 + 1 = 7, (107 + 7) / 128 = 89%)

Note:
question_ok=False&Fixed: 90 (90 / 130 = 69.2%) [ensemble voting]
0_tb_score=0: 51 (51 / 130 = 39.2%)
"""

import argparse
import json
import pandas as pd
from multiprocessing import Pool
from pathlib import Path


from dotenv import load_dotenv
from .llm import get_llm
from .schema import RefinementCtx, Problem
from .pipeline import RefinementPipeline
from .verilog.verilog import format_prompts
from .logger import setup_output_log_dir, get_logger

# please create a .env file with all the necessary environment variables
load_dotenv(override=True)


def main(
    provider: str,
    model_name: str,
    input_path: str,
    output_dir: str,
    start_index: int,
    n_problems: int,
    max_tokens: int,
    temperature: float,
    log_key: str,
    dataset_type: int,
):
    output = {"dataset": []}
    input_path = Path(input_path)

    logger = get_logger()

    if dataset_type == 2:  # PyraNet
        df = pd.read_csv(input_path)
        dataset = df.to_dict(orient="records")
    elif dataset_type == 1:  # Deepcircuitx
        with open(input_path, "r") as f:
            dataset = json.load(f)
    elif dataset_type == 3:  # AutoBench
        dataset = []
        with open(input_path, "r") as f:
            for line in f:
                data = json.loads(line)
                dataset.append(data)
    elif dataset_type == 4:  # Pyra json
        with open(input_path, "r") as f:
            dataset = json.load(f)["dataset"]
    else:  # Verireason
        with open(input_path, "r") as f:
            dataset = json.load(f)["dataset"]
    import inspect

    # print(inspect.signature(format_prompts))
    # exit()
    prompts = format_prompts(dataset, start_index, n_problems, log_key, dataset_type)
    n_problems = len(prompts)

    problems = [Problem(id=i, question=q, answer=a) for i, q, a in prompts]
    ctxs = [RefinementCtx.from_problem(p) for p in problems]

    pipeline = RefinementPipeline(
        llm=get_llm(
            provider=provider,
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    )

    print(f"***PROCESSING {n_problems} DATASETS***")
    with Pool(32) as executor:
        ctxs = executor.map(pipeline, ctxs)

    verbose_logs = {}
    print(f"***WRITING OUTPUT TO {output_dir}***")
    for i, ctx in zip(range(n_problems), ctxs):
        if (i % 50) == 0:
            print(f"***{i} / {n_problems}***")
        org_i, question, answer, refine_answer, tb, feedbacks, logs, input_len = (
            # org_i, question, answer, tb, feedbacks, logs, input_len, testcases = (
            ctx.problem.id,
            ctx.problem.question,
            ctx.problem.answer,
            ctx.problem.refine_answer,
            ctx.testbench.code,
            ctx.feedbacks,
            ctx.logs,
            ctx.length,
            # ctx.problem.testcase,
        )

        is_ten = False
        if "0_tb_score" in logs and logs["0_tb_score"] == 1.0:
            is_ten = True
        elif "1_tb_score" in logs and logs["1_tb_score"] == 1.0:
            is_ten = True
        elif "2_tb_score" in logs and logs["2_tb_score"] == 1.0:
            is_ten = True
        elif "3_tb_score" in logs and logs["3_tb_score"] == 1.0:
            is_ten = True

        if is_ten:
            dataset[org_i]["id"] = org_i
            dataset[org_i]["orig_out"] = answer
            dataset[org_i]["refined_in"] = question
            dataset[org_i]["refined_out"] = refine_answer
            dataset[org_i]["refined_tb"] = tb
            dataset[org_i][log_key] = logs
            dataset[org_i]["input_len"] = input_len
            # dataset[org_i]["testcases"] = testcases

            # if ctx.problem.question_reasoning_trace:
            #     dataset[org_i][
            #         "question_reasoning_trace"
            #     ] = ctx.problem.question_reasoning_trace
            # if ctx.problem.solution_reasoning_trace:
            #     dataset[org_i][
            #         "solution_reasoning_trace"
            #     ] = ctx.problem.solution_reasoning_trace
            # if ctx.problem.testcase_reasoning_trace:
            #     dataset[org_i][
            #         "testcase_reasoning_trace"
            #     ] = ctx.problem.testcase_reasoning_trace
            # if ctx.testbench.reasoning_trace:
            #     dataset[org_i]["tb_reasoning_trace"] = ctx.testbench.reasoning_trace

            output["dataset"].append(dataset[org_i])

        verbose_logs[org_i] = feedbacks

        logger.info("=" * 20)
        logger.info(f"[{org_i}]: {logs}")

    # if dataset_type == 2:  # PyraNet
    #     with open('output.json', 'w', encoding='utf-8') as f:
    #         json.dump(output, f, ensure_ascii=False, indent=2)
    # else:  # Verireason or Deepcircuitx
    #     with open(input_path, "w") as f:
    #         json.dump({"dataset": dataset}, f, indent=4)

    output_json_path = Path(output_dir) / "output.json"
    verbose_logs_path = Path(output_dir) / "verbose_logs.json"

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4)
    with open(verbose_logs_path, "w") as f:
        json.dump(verbose_logs, f, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", type=str, default="gemini")
    parser.add_argument("--model-name", type=str, default="gemini-2.5-pro")
    parser.add_argument("--input-path", type=str)
    parser.add_argument("--output-dir", type=str, default="./result")
    parser.add_argument("--log-dir", type=str, default=None)
    parser.add_argument(
        "--start-index",
        type=int,
        default=0,
        help="only when sequencial select, Start index for processing dataset",
    )
    parser.add_argument("--n-problems", type=int)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--log-key", type=str, default="logs")
    parser.add_argument(
        "--dataset-type",
        type=int,
        default=2,
        help="[0:Verireason | 1:Deepcircuitx | 2:PyraNet | 3:AutoBench]",
    )

    args = parser.parse_args()

    log_dir = setup_output_log_dir(output_dir=args.output_dir, log_id=args.log_dir)

    main(
        provider=args.provider,
        model_name=args.model_name,
        input_path=args.input_path,
        output_dir=log_dir,
        start_index=args.start_index,
        n_problems=args.n_problems,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        log_key=args.log_key,
        dataset_type=args.dataset_type,
    )
