import argparse
import json
import os
import re

from tb_gen.enums import QuestionRevisionResult, TestbenchRevisionBranch

LAST_TRY = 3
LOW_CONFIDENCE_BOUND = 5
# type_map = {"TESTBENCH": 0, "SOLUTION": 1}
well_written_type_map = {
    "PASS": 0,
    "DROP": 1,
    "FIXED": 2,
    "ERROR": 3,
    "UNDECIDED": 4,
}
well_written_branch = [0, 0, 0, 0, 0]  # [PASS, DROP, FIXED, ERROR, UNDECIDED]


def main(result_path, dataset_name, log_key, arg_type, output_name):
    if not os.path.exists(result_path):
        raise FileNotFoundError(f"path {result_path} does not exist.")
    ### Testbench Generation Stage Analysis
    with open(result_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        fixed_code_amount = 0  # "question_state": "FIXED"
        pass_tb = [0 for _ in range(LAST_TRY + 1)]  # tb that score = 10
        last_try_low_confidence = [
            0 for _ in range(10 - LOW_CONFIDENCE_BOUND - 1)
        ]  # for LAST_TRY, score > 5 but not 10
        last_try_low_confidence_tag = 0
        first_try_fail = 0  # 0_tb_score = 0

        rows, cols = LAST_TRY, 4  # Tb_count, Sol_count, Tb_pass, Sol_pass
        branch_analysis = [[0 for _ in range(cols)] for _ in range(rows)]

        for per_data in data["dataset"]:
            dict = per_data.get(log_key, {})
            for key, value in dict.items():
                # print(key, value)
                brnach_tag = 0  # 1: TESTBENCH, 2: SOLUTION
                if key == "question_state":
                    well_written_branch[well_written_type_map[value]] += 1
                    if value == "FIXED":
                        fixed_code_amount += 1

                for i in range(LAST_TRY + 1):
                    if key == f"{i}_tb_score":
                        tb_score = value
                        if tb_score == 10:
                            pass_tb[i] += 1
                            if i != 0:
                                branch_analysis[i - 1][branch_tag + 1] += 1
                        elif tb_score == 0 and i == 0:
                            first_try_fail += 1
                        elif (
                            tb_score > LOW_CONFIDENCE_BOUND
                            and tb_score < 10
                            and i == LAST_TRY
                        ):
                            last_try_low_confidence[
                                tb_score - LOW_CONFIDENCE_BOUND - 1
                            ] += 1
                            last_try_low_confidence_tag = 1

                    if key == f"{i}_branch":
                        # print(key, value)
                        if value == "TESTBENCH":
                            branch_tag = 1
                            branch_analysis[i][branch_tag - 1] += 1
                        elif value == "SOLUTION":
                            # (per_data["id"])
                            branch_tag = 2
                            branch_analysis[i][branch_tag - 1] += 1
    # print(well_written_branch)

    with open(output_name, "w", encoding="utf-8") as f:
        f.write(f"==========={dataset_name} Dataset===========\n")
        if arg_type == 0 or arg_type == 1:
            f.write("-----Well Written Stage Analysis-----\n")
            f.write(f"question \tPASS:\t\t{well_written_branch[0]}\n")
            f.write(f"\t\t\tDROP:\t\t{well_written_branch[1]}\n")
            f.write(f"\t\t\tFIXED:\t\t{well_written_branch[2]}\n")
            f.write(f"\t\t\tERROR:\t\t{well_written_branch[3]}\n")
            f.write(f"\t\t\tUNDECIDED:\t{well_written_branch[4]}\n")
            total_amount = well_written_branch[0] + well_written_branch[2]
            f.write(f"final passed: {total_amount}\n")
        if arg_type == 0 or arg_type == 2:
            f.write("------Testbench Stage Analysis-------\n")
            ## stage analysis
            if arg_type == 2:
                total_amount = len(data["dataset"])
            f.write(f"Total: {total_amount} question\n\n")
            f.write("[Testbench Pass Analysis]\n")
            total_pass = 0
            low_conf_pass = 0
            for i, score in enumerate(pass_tb):
                total_pass += score
                f.write(f"{i}_tb_score=10: \t{score}\n")
            f.write("(")
            for i, count in enumerate(pass_tb):
                f.write(f"{count}")
                if i != LAST_TRY:
                    f.write(" + ")
            f.write(
                f" = {total_pass}, {total_pass} / {total_amount} = {total_pass / total_amount * 100}%)\n\n"
            )
            ## low confidence
            if last_try_low_confidence_tag:
                f.write(f"[CONTROVERSIAL, low confidence]\n")
                for i, count in enumerate(last_try_low_confidence):
                    if count == 0:
                        continue
                    f.write(
                        f"{LAST_TRY}_tb_score={i + LOW_CONFIDENCE_BOUND + 1}: \t{count}\n"
                    )
                    low_conf_pass += count
                f.write(
                    f"({low_conf_pass} + {total_pass} / {total_amount} = {(low_conf_pass + total_pass) / total_amount * 100}%)\n\n"
                )
            ## branch analysis
            f.write(f"[Branch Analysis]\n")
            for i in range(LAST_TRY):
                f.write(
                    f"{i + 1}_branch=Tb: \t{branch_analysis[i][0]}, ({branch_analysis[i][2]} passed)\n"
                )
                f.write(
                    f"{i + 1}_branch=Sol: \t{branch_analysis[i][1]}, ({branch_analysis[i][3]} passed)\n"
                )
            ## extra note
            f.write("\nNote:\n")

            f.write(
                f"0_tb_score=0: \t{first_try_fail}, {first_try_fail / total_amount * 100}%\n"
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-path", type=str, default="output.json")
    # parser.add_argument("--logs-path", type=str, default="verbose_logs.json")
    parser.add_argument("--dataset-name", type=str)
    parser.add_argument("--log-key", type=str, default="logs")
    parser.add_argument("--output-name", type=str, default="analysis.log")
    parser.add_argument(
        "--type", type=int, default=0, help="[0:All | 1:well_written | 2:testbench]"
    )
    args = parser.parse_args()

    # main(args.result_path, args.logs_path, args.dataset_name, arg.log_key)
    main(args.result_path, args.dataset_name, args.log_key, args.type, args.output_name)
