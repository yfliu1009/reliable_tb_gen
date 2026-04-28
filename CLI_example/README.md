# Gemini CLI
## Environment Setup (for Gemini CLI)
* prerequisite
    ```shell
    # you must install Node.js, you may go to [Node.js](https://nodejs.org/en/download) to select OS and version
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
    # Verify the Node.js version:
    node -v 
    # use pnpm for better space usage
    curl -fsSL https://get.pnpm.io/install.sh | sh -
    # To start using pnpm, run:
    source /Users/kylekai/.zshrc
    ```
    ```shell
    # Gemini CLI installation
    pnpm install -g @google/gemini-cli
    # start gemini for color theme & Authentication (can use personal google account)
    # for api key authentication, it will directly read your .env if have one. Variable names "GEMINI_API_KEY"
    gemini
    ```

## How to run Gemini CLI in program
after setup the envirnment and personal information inside CLI

you may run it automatically in Python by calling:
```python
result = subprocess.run(
    ["gemini", "--prompt", prompt],
    check=True,
    capture_output=True,
    text=True,
)
# print result
print(result.stdout)
```
* `--prompt`: the prompt you feed to AI
    * Notice that for python calling, we can't interact with gemini as noramlly in CLI, so you must avoid giving imprecise prompt so that AI will not ask you to elaborate.
* `--model`: the model you use, default to "gemini-2.5-pro"
* type in `gemini -h` for more

## Try the example program
```shell
python example_rawdog.py

# or
python example_pythonic.py
```