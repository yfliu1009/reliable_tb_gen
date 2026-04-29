import pandas as pd
import subprocess
import os
from tqdm import tqdm
import concurrent.futures 

def is_valid_verilog(code, idx, timeout_sec=10):
    if pd.isna(code) or str(code).strip() == "":
        return False
    

    tmp_filename = f"temp_check_{idx}.v"
    
    try:
        with open(tmp_filename, "w", encoding="utf-8") as f:
            f.write(code)
        
        result = subprocess.run(
            ["iverilog", "-o", "/dev/null", tmp_filename],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_sec 
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False
    finally:
        if os.path.exists(tmp_filename):
            os.remove(tmp_filename)

def main():
    input_file = "PyraNetOnVeriBest.csv"
    output_file = "cleaned_PyraNet.csv"
    
    print(f"Reading {input_file}...")
    df = pd.read_csv(input_file)

    if 'code' not in df.columns:
        print("Error: 'code' column not found")
        return

    print(f"Starting Verilog compilation verification (total {len(df)} entries)...")

    codes = df['code'].tolist()
    indices = range(len(df))
    
    results = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = [executor.submit(is_valid_verilog, code, i) for i, code in enumerate(codes)]
        for f in tqdm(concurrent.futures.as_completed(futures), total=len(futures)):
            pass
        
        results = list(tqdm(executor.map(is_valid_verilog, codes, indices), total=len(codes)))

    df_cleaned = df[results]
    
    print("\n--- Cleaning Results ---")
    print(f"Original data entries: {len(df)}")
    print(f"Successfully compiled entries: {len(df_cleaned)}")
    print(f"Removed invalid entries: {len(df) - len(df_cleaned)}")
    
    df_cleaned.to_csv(output_file, index=False)
    print(f"Results saved to: {output_file}")

if __name__ == "__main__":
    main()