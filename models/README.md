# Pasta de Modelos de Linguagem (SLM)

Esta pasta é utilizada pelo servidor desktop do **Remote Master Pro** para servir modelos locais de inteligência artificial (como Gemma 2B, Phi-3, ou outros modelos convertidos para `.bin` ou `.task` do MediaPipe/Onnx).

## Como utilizar:
1. Baixe o modelo desejado (por exemplo, `gemma-2b-it-cpu-int4.bin` ou modelo MediaPipe LLM).
2. Coloque o arquivo nesta pasta (`server/models/`).
3. O endpoint `/api/models/slm_model.bin` ficará automaticamente disponível para download ou streaming no aplicativo Android conectado pela rede local.

> **Nota:** Arquivos de modelos binários (`.bin`, `.gguf`, `.task`) são ignorados pelo Git devido ao limite de tamanho do GitHub (> 100MB).
