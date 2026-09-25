# Hardware desta máquina e ajustes ao plano

Máquina: `notebook do laboratorio` · Windows 11 (x64) · verificado em 25/09/2026 com `python -m provador.check --camera`

## Resultado da verificação

| Item | Plano | Esta máquina |
|---|---|---|
| GPU dedicada | NVIDIA | NVIDIA GeForce RTX 3060 Laptop, **6 GB de VRAM dedicada**, driver 610.60 |
| GPU integrada | — | Intel UHD Graphics (notebook híbrido) |
| OpenGL (padrão) | GPU dedicada | **Intel UHD** — precisa ser forçado para a NVIDIA (ver ajuste 1) |
| CPU | — | Intel Core i7-11800H, 8 núcleos / 16 threads, 2,3 GHz |
| RAM | — | 15,7 GB |
| Webcam | 720p, ≥30 FPS | 1280x720 a 29,8 FPS medidos (30 FPS nominais) |
| Python | 3.11/3.12 | 3.11.16 no `.venv`, criado via uv |

Observação: o Windows mostra cerca de 14 GB de "memória de GPU", mas isso inclui memória compartilhada com a RAM.
A VRAM dedicada é de 6 GB. Isso é suficiente para o app, mas apertado para imagem→3D (T12, TRELLIS/Hunyuan3D).

## Ajustes ao plano

1. **Notebook híbrido (Intel + NVIDIA) — resolvido:** o OpenGL abria na Intel UHD. Foi forçada a NVIDIA por chave de
   registro (`HKCU\Software\Microsoft\DirectX\UserGpuPreferences`, valor `GpuPreference=2;`) para o `python.exe` do
   `.venv` **e** para o `python.exe`/`pythonw.exe` base do uv, porque o do venv é só um atalho que executa o base.
   Se recriar o venv ou o Python do uv mudar de versão, repita (ou use *Configurações → Sistema → Tela → Gráficos*).
2. **Python:** o `uv` obteve o 3.11 sem mexer no Python do sistema (máquina corporativa).
3. **MediaPipe na CPU:** a CPU é de classe alta para notebook. Mantemos o plano; a T13 (`rtmlib` + `onnxruntime-gpu`
   com CUDA) só será adiantada se o benchmark da T3 ficar abaixo de 30 Hz.
4. **Webcam:** o driver mede ~30 FPS. Se a redução de tremulação do driver adicionar latência, avaliar desligá-la
   na T2, quando houver métrica de latência.
5. **T12 com 6 GB de VRAM:** pode exigir versões quantizadas ou rodar em nuvem. Decidir só quando a T12 começar.
6. **GIL × vsync (descoberto na T5):** com vsync, o driver NVIDIA bloqueia a thread de render dentro das
   chamadas GL, e o ModernGL segura o GIL nessa espera. A inferência da pose ia de 15 para 33 ms. Corrigido com
   `glFinish` via ctypes logo após o swap (`src/provador/gl_sync.py`), que espera sem o GIL. Regra: nenhuma
   espera longa dentro de chamadas do ModernGL no loop de render.
7. **Segmentação na GPU (T7):** o selfie multiclasse do MediaPipe leva ~82 ms na CPU desta máquina (o plano
   previa 12 ms), em qualquer resolução de entrada. Convertido para ONNX (`tools/convert_seg_model.py`, via
   tf2onnx num ambiente temporário) e rodando em ONNX Runtime + DirectML na NVIDIA: **~5 ms**, com 99,8% de
   concordância de classes com o MediaPipe. Reserva: ONNX Runtime na CPU (~30 ms). Antecipa a ideia da T13 só
   para a segmentação; a pose continua no MediaPipe (15 ms).
