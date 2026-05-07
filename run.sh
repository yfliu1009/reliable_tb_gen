#!/bin/bash

#### version for fully execute in several part
# START=0
# STEP=50
# COUNT=50
# MAX_INDEX=100  # Change this as needed

# while [ $START -lt $MAX_INDEX ]; do
#     END=$((START + COUNT - 1))
#     LOG_DIR="pyra-${START}-${END}"

#     echo "Running range ${START}-${END}..."
#     python3 -m tb_gen.refine_dataset --input-path ../../../disk2/llm_team/silicon_mind_dataset/PyraNet-Verilog/PyraNetOnVeriBest.csv \
#         --start-index $START \
#         --n-problems $COUNT \
#         --dataset-type 2 \
#         --provider openai \
#         --model-name "gpt-4.1" \
#         --output-dir tb_gen/result/fullPyra \
#         --log-dir $LOG_DIR

#     START=$((START + STEP))
# done

python3 -m tb_gen.refine_dataset --input-path ./cleaned_PyraNet.csv \
    --n-problems 2 \
    --dataset-type 2 \
    --provider gemini \
    --model-name "gemini-2.5-pro" \
    --output-dir tb_gen/result

# python3 total_unusable_counter.py > total_unusable_counter.log

### experiment of generating testbench from AutoBench dataset
# python3 tb_gen/refine_dataset.py --input-path ../AutoBench_dataset_ques.jsonl \
#     --n-problems 156 \
#     --dataset-type 3 \
#     --provider openai \
#     --model-name "gpt-4.1" \
#     --output-dir tb_gen/result

### result arrangment
# python3 result_arrange.py --result-path tb_gen/result/autobench-onlyTB-testbench/output.json --type 2 --output-name onlyTB-tb_analysis.log
# python3 result_arrange.py --result-path tb_gen/result/autobench-onlyTB-fullpipe/output.json --type 0 --output-name onlyTB-full_analysis.log

# TODO: test pyra-random-100 with same seed, compare accuracy between full pipeline and direct testbench generation