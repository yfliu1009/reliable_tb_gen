from openai import OpenAI
import os
import subprocess
import json
import pandas as pd
from pathlib import Path
import tempfile

TB_GUIDE = """You are a professional verilog expert,
Please generate a testbench for the following Verilog coding problem.
The testbench must include 10 test cases covering a broad range of scenarios.
Also, it must print meaningful information about the failed test cases to help with debugging.
If there are multiple subtasks in one test case, the code must pass all subtasks to be considered a successful test case.
Most importantly, the testbench must print the number of passed test cases enclosed by triple backticks to the terminal.
The number of passed test cases must be in the range of 0 to 10, inclusive.
Enclose your testbench code with [BEGIN] and [DONE]. Only provide me the testbench and nothing else."""
PYRANET_PREF = "Given the detailed specifications of a module, generate the corresponding Verilog code."

current_ques = 0


def safe_json_parse(s):
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return None


df = pd.read_csv(
    Path(
        "/mnt/disk2/llm_team/silicon_mind_dataset/PyraNet-Verilog/PyraNetOnVeriBest.csv"
    )
)
dataset = df.to_dict(orient="records")

temp = safe_json_parse(dataset[current_ques]["description"])
question = PYRANET_PREF + temp["description"].strip()
code = dataset[current_ques]["code"].strip()


prompt = f"""{TB_GUIDE}
Problem:
{question}"""


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

try:
    resp = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        # max_tokens=self.max_tokens,
        temperature=0,
        seed=30,  # can change
    )
except Exception as error:
    print(f"Openai Error: {error}")
# print(resp.choices[0].message.content)
text = resp.choices[0].message.content


lines = text.splitlines()

in_code = False
code_lines = []
found_code = False
begin: str = "[BEGIN]"
done: str = "[DONE]"
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
    tb = "\n".join(code_lines)

print(tb)


with tempfile.TemporaryDirectory() as temp_dir:
    verilog_file = os.path.join(temp_dir, f"test_{current_ques}.v")
    with open(verilog_file, "w") as f:
        f.write(code)

    tb_file = os.path.join(temp_dir, f"test_{current_ques}_tb.v")
    with open(tb_file, "w") as f:
        f.write(tb)

    exec_file = os.path.join(temp_dir, f"test_{current_ques}.out")

    try:
        subprocess.check_output(
            ["iverilog", "-g2012", "-o", exec_file, verilog_file, tb_file],
            text=True,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        print(e.output)

    try:
        print(
            subprocess.check_output(
                ["vvp", exec_file],
                text=True,
                timeout=1.5,
                stderr=subprocess.STDOUT,
            )
        )
    except subprocess.CalledProcessError as e:
        print(e.output)
    except subprocess.TimeoutExpired as e:
        print(e.output.decode("utf-8") if e.output else "")
