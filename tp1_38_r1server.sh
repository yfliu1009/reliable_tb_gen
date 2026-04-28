source /mnt/disk1/kai/.venv/bin/activate

IDX=32000
SIZE=1000
END_IDX=$((IDX + SIZE))

python3 -m tb_gen.refine_dataset \
    --input-path /mnt/disk1/kai/silicon_mind_dataset/prompts/train-qwen-7b_pyranet.json \
    --start-index $IDX \
    --n-problems $SIZE \
    --dataset-type 4 \
    --model-name "/mnt/shared/SINICA_NTU/model_weights/DeepSeek-R1-0528" \
    --provider openai_local_server \
    --output-dir tb_gen/result \
    --log-dir pyra-${IDX}-${END_IDX}
