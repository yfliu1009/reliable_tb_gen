import sys
import subprocess


def run_gemini_cli(prompt):
    try:
        result = subprocess.run(
            ["gemini", "--prompt", prompt, "--model", "gemini-2.5-pro-preview-06-05"],
            check=True,
            capture_output=True,
            text=True,
        )
        print("Gemini Output:\n", result.stdout)
    except subprocess.CalledProcessError as e:
        print("Error calling gemini CLI:\n", e.stderr)
        sys.exit(1)


if __name__ == "__main__":
    prompt = "白嫖gemini cli"
    print(prompt)
    run_gemini_cli(prompt)
