import os
import tempfile
import subprocess
import json
import pandas as pd
from multiprocessing import Pool
from pathlib import Path

input_path = Path(
    "../../../disk2/llm_team/silicon_mind_dataset/PyraNet-Verilog/PyraNetOnVeriBest.csv"
)
df = pd.read_csv(input_path)
dataset = df.to_dict(orient="records")
error_counter = 0
timeout_counter = 0


def try_compile(i: int, code: str) -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        verilog_file = os.path.join(temp_dir, f"test_{i}.v")
        with open(verilog_file, "w") as f:
            f.write(code)

        exec_file = os.path.join(temp_dir, f"test_{i}.out")
        try:
            compile_cmd = ["iverilog", "-g2012", "-o", exec_file, verilog_file]
            subprocess.check_output(compile_cmd, stderr=subprocess.STDOUT, timeout=7)
            # subprocess.check_output(compile_cmd, stderr=subprocess.STDOUT)
            return 0
        except subprocess.CalledProcessError:
            # error_counter += 1
            return 1
        except subprocess.TimeoutExpired:
            # timeout_counter += 1
            return 2


def safe_json_parse(s):
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return None


success_data = []
unusable_counter = 0
for i in range(0, len(dataset)):
    success_counter = 0
    prob = dataset[i]

    print(f"Processing problem {i}... ")
    answer = ""

    temp = safe_json_parse(prob["description"])
    if temp is None:
        continue
    answer = prob["code"].strip()
    i = try_compile(i, answer)
    if i == 1:
        unusable_counter += 1
        error_counter += 1
        error_counter += 1
        continue
    elif i == 2:
        unusable_counter += 1
        timeout_counter += 1
        timeout_counter += 1
        continue
    elif i == 0:
        success_data.append(prob)
        success_counter += 1

        # save the dataset
        continue

print(f"✅ Total success: {success_counter}")
print(f"❌ Total error counter: {error_counter}")
print(f"⏰ Total timeout counter: {timeout_counter}")
print(f"🚫 Total unusable (error + timeout + parse fail): {unusable_counter}")

# 儲存成功的資料為 CSV
output_path = Path("SuccessPyra.csv")
pd.DataFrame(success_data).to_csv(output_path, index=False)
print(f"✅ Saved {len(success_data)} records to {output_path}")


# 61000: 14917
