import argparse
import json
import pandas as pd
from multiprocessing import Pool
from pathlib import Path


from dotenv import load_dotenv
from llm import get_llm
from schema import RefinementCtx, Problem
from pipeline import RefinementPipeline, TBForQuesRefinementPipeline
from verilog import format_prompts
from logger import setup_output_log_dir, get_logger

# please create a .env file with all the necessary environment variables
load_dotenv(override=True)


def main(
    provider: str,
    model_name: str,
    input_path: str,
    output_dir: str,
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
    else:  # Verireason
        with open(input_path, "r") as f:
            dataset = json.load(f)["dataset"]

    prompts = format_prompts(dataset, n_problems, log_key, dataset_type)
    n_problems = len(prompts)

    problems = [Problem(id=i, question=q, answer=a) for i, q, a in prompts]
    ctxs = [RefinementCtx.from_problem(p) for p in problems]

    pipeline = TBForQuesRefinementPipeline(
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
    for i, ctx in zip(range(n_problems), ctxs):
        org_i, question, answer, tb, feedbacks, logs = (
            ctx.problem.id,
            ctx.problem.question,
            ctx.problem.answer,
            ctx.testbench.code,
            ctx.feedbacks,
            ctx.logs,
        )

        dataset[org_i]["id"] = org_i
        dataset[org_i]["refined_in"] = question
        dataset[org_i]["refined_out"] = answer
        dataset[org_i]["refined_tb"] = tb
        dataset[org_i][log_key] = logs
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
    parser.add_argument("--n-problems", type=int)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--log-key", type=str, default="logs")
    parser.add_argument(
        "--dataset-type",
        type=int,
        default=0,
        help="[0:Verireason | 1:Deepcircuitx | 2:PyraNet]",
    )

    args = parser.parse_args()

    log_dir = setup_output_log_dir(output_dir=args.output_dir)

    main(
        provider=args.provider,
        model_name=args.model_name,
        input_path=args.input_path,
        output_dir=log_dir,
        n_problems=args.n_problems,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        log_key=args.log_key,
        dataset_type=args.dataset_type,
    )
