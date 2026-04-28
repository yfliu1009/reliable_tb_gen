# Testbench Generation
testbench generation pipeline (inspired by VeriPrefer)

## Environment Setup (via uv)
```shell
uv venv
uv pip install -r requirements.txt
```
> Note: for setting up uv package manager, please refer to:
> * [uv: An Extremely Fast Python Package Manager and Project Manager](https://wiki.paslab.csie.org/books/26337/page/uv-an-extremely-fast-python-package-manager-and-project-manager)
> * [Migrate from conda to uv for group-level Python package sharing](https://wiki.paslab.csie.org/books/26337/page/migrate-from-conda-to-uv-for-group-level-python-package-sharing)

## Environment Setup (for Gemini CLI)
1. prerequisite
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

## `tb_gen` Usage
create a `.env` file under the root folder and enter necessary API keys
```typescript
GEMINI_API_KEY=[YOUR API KEY]
```

```shell
python -m tb_gen.refine_dataset \
    --provider geminiCLI
    --input-path /path/to/dataset
    --n-problems 2
    --dataset-type [see doc]
```
other options:
* `--provider`: LLM provider to use, currently only `gemini`, `geminiCLI`, `anthropic`, `openai`, `deepseek` is supported
    * choices: `gemini`, `geminiCLI`, `openai`, `anthropic`, `deepseek`, `selfhost`
    * default: `gemini`
    * note that you need to install gemini cli tool in order to use provider `geminiCLI`
* `--model-name`: which LLM model to use, note that this option is bound to the provider you choose
    * default: `gemini-2.5-pro`
* `--output-dir`: where the logs and ouput json files are located
    * default: `./result`
* `--log-key`: mark refined data with `log_key`, useful when you want to batch refine the dataset, data entry with key `log_key` will be skipped
    * default: `logs`
* `--n-problems`: number of data entries to be processed. the whole dataset will be processed if not set
* `--dataset-type`: [0:Verireason | 1:Deepcircuitx | 2:PyraNet]
