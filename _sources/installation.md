## Installation

```bash
pip install sand-bob
```

Additionally, you need a local [docker](https://docs.docker.com/engine/install/) installation. Sand-Bob was tested on Windows 11 so far only. In this environment, you also need to install WSL2 to get docker to work.

Finally, you need to configure access to an OpenAI-API-compatible language model server. Just sent these environment variables:

```
SANDBOB_LLM_SERVER = https://url/v1
SANDBOB_LLM_API_KEY = sk_...
```

**Note:** It is recommended to use locally hosted language models (e.g. using [ollama](https://ollama.com)) or souvereign institutional infrastructure for this. As many prompts are sent to the LLM-server while optimizing code [potentially in parallel], costs may be high when using pay-per-token LLM-servers.
