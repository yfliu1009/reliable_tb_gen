from multiprocessing import Pool
import argparse

from llm import GeminiCLILLM

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model-name", type=str, default="gemini-2.5-pro-preview-06-05"
    )
    parser.add_argument("--prompt", "-p", type=str)
    args = parser.parse_args()

    llm = GeminiCLILLM(model_name="gemini-2.5-pro-preview-06-05")

    if args.prompt:
        print("Using provided prompt: ", args.prompt)
        response = llm.generate(args.prompt)
        print("response: ", response)

    else:
        print("白嫖gemini cli")
        response = llm.generate("白嫖gemini cli")
        print("response: ", response)

        print("use 32 processes白嫖gemini cli")
        with Pool(32) as executor:
            responses = executor.map(
                llm.generate, ["use 32 processes白嫖gemini cli"] * 32
            )
        print("response: ", responses)
