import os
import re
import random
import tempfile
import subprocess

from tb_gen.prompt import VERIREASON_SUFF, PYRANET_PREF, DEEPX_PREF

RANDOM_SELECT = False  # If True, select random problems from the dataset


def simulate(i: int, code: str, tb: str) -> str:
    if not code or not tb:
        return ""

    with tempfile.TemporaryDirectory() as temp_dir:
        verilog_file = os.path.join(temp_dir, f"test_{i}.v")
        with open(verilog_file, "w") as f:
            f.write(code)

        tb_file = os.path.join(temp_dir, f"test_{i}_tb.v")
        with open(tb_file, "w") as f:
            f.write(tb)

        exec_file = os.path.join(temp_dir, f"test_{i}.out")

        try:
            subprocess.check_output(
                ["iverilog", "-g2012", "-o", exec_file, verilog_file, tb_file],
                text=True,
                stderr=subprocess.STDOUT,
            )
        except subprocess.CalledProcessError as e:
            return e.output

        try:
            return subprocess.check_output(
                ["vvp", exec_file],
                text=True,
                timeout=1.5,
                stderr=subprocess.STDOUT,
            )
        except subprocess.CalledProcessError as e:
            return e.output
        except subprocess.TimeoutExpired as e:
            return e.output.decode("utf-8") if e.output else ""


def get_tb_score(text: str) -> int:
    pattern = r"`+\s*(\d+)\s*`+"
    match = re.search(pattern, text)
    return int(match.group(1)) if match else 0


def extract_verilog_code(
    text: str, begin: str = "[BEGIN]", done: str = "[DONE]"
) -> str:
    if not text:
        return text

    lines = text.splitlines()

    # Step 1: Try extracting from [BEGIN] ... [DONE]
    in_code = False
    code_lines = []
    found_code = False

    for line in lines:
        if begin in line:
            in_code = True
            start_index = line.find(begin) + len(begin)
            after_begin = line[start_index:].strip()
            if after_begin:
                code_lines.append(after_begin)
            continue
        elif done in line and in_code:
            done_index = line.find(done)
            before_done = line[:done_index].strip()
            if before_done:
                code_lines.append(before_done)
            found_code = True
            break
        elif in_code:
            code_lines.append(line)

    if found_code:
        lines = code_lines

    # Step 2: Fallback to last ```verilog``` block
    in_block = False
    current_block = []
    last_block = []

    for line in lines:
        if line.strip().startswith("```verilog"):
            in_block = True
            current_block = []
            continue
        elif line.strip() == "```" and in_block:
            in_block = False
            last_block = current_block.copy()
            continue
        elif in_block:
            current_block.append(line)

    if last_block:
        return "\n".join(last_block)
    elif found_code:
        return "\n".join(code_lines)
    else:
        return ""


def try_compile(i: int, code: str) -> bool:
    with tempfile.TemporaryDirectory() as temp_dir:
        verilog_file = os.path.join(temp_dir, f"test_{i}.v")
        with open(verilog_file, "w") as f:
            f.write(code)

        exec_file = os.path.join(temp_dir, f"test_{i}.out")
        try:
            compile_cmd = ["iverilog", "-g2012", "-o", exec_file, verilog_file]
            subprocess.check_output(compile_cmd, stderr=subprocess.STDOUT)
            return True
        except subprocess.CalledProcessError:
            return False


def format_prompts(
    dataset: list[dict],
    start_index: int,
    n_problems: int,
    log_key: str,
    dataset_type: int,
) -> tuple[list, list]:
    # print(dataset_type)
    # Try parsing; if it fails, return None
    import json

    def safe_json_parse(s):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return None

    prompts = []
    if RANDOM_SELECT:
        random.seed(
            42
        )  # For reproducibility to test accuracy differences between full pipieline and direct testbench generation
        while n_problems > 0:
            org_i = random.randint(0, 100000)
            org_i = org_i % len(dataset)
            prob = dataset[org_i]
            if log_key in prob:
                print(f"skip {org_i}: log_key")
                continue

            question = ""
            answer = ""

            match dataset_type:
                case 0:  # Verireason
                    # print("verireason")
                    question = prob["input"][: -len(VERIREASON_SUFF)].strip()
                    answer = extract_verilog_code(
                        prob["output"], "<answer>", "</answer>"
                    )

                case 1:  # Deepcircuitx
                    # print("deecircuitx")
                    question = DEEPX_PREF + prob["input"]
                    answer = prob["output"]

                case 2:  # PyraNet
                    # print("pyranet")
                    temp = safe_json_parse(prob["description"])
                    if temp is None:
                        print(f"skip {org_i}: no description")
                        continue
                    question = PYRANET_PREF + temp["description"].strip()
                    answer = prob["code"].strip()

            if not try_compile(org_i, answer):
                print(f"skip {org_i}: compile error")
                continue

            prompts.append((org_i, question, answer))
            n_problems -= 1
    else:
        for i, prob in enumerate(dataset):
            if i < start_index:
                continue
            if n_problems == 0:
                break
            if log_key in prob:
                print(f"skip {i}: log_key")
                continue

            question = ""
            answer = ""

            match dataset_type:
                case 0:  # Verireason
                    # print("verireason")
                    question = prob["input"][: -len(VERIREASON_SUFF)].strip()
                    answer = extract_verilog_code(
                        prob["output"], "<answer>", "</answer>"
                    )

                case 1:  # Deepcircuitx
                    # print("deecircuitx")
                    question = prob["input"]
                    answer = prob["output"]

                case 2:  # PyraNet
                    # print("pyranet")
                    temp = safe_json_parse(prob["description"])
                    if temp is None:
                        print(f"skip {i}: no description")
                        continue
                    question = PYRANET_PREF + temp["description"].strip()
                    answer = prob["code"].strip()

                case 4:  #PyraNet json
                    question = prob["input"]
                    answer = prob["output"]
            if not try_compile(i, answer):
                print(f"skip {i}: compile error")
                continue

            prompts.append((i, question, answer))
            n_problems -= 1

    return prompts
