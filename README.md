# Diffusion Compression Lab

Diffusion Compression Lab is an end-to-end research prototype for lossy image compression with a foundation diffusion model. It combines a learned latent codec, factorized Gaussian entropy modeling, integer arithmetic coding, and one-step Stable Diffusion 2.1 reconstruction in a self-contained FastAPI + React application.

This project is inspired by **Lossy Image Compression with Foundation Diffusion Models**. It is a practical prototype, not a claim of exact reproduction of every component or result in the paper.

## What is implemented

- SD 2.1 VAE encoding into a 4-channel latent representation.
- Strict loading of the supplied `models/paper_style_best.pt` codec checkpoint.
- Lambda-controlled adaptive quantization.
- Factorized Gaussian entropy model and integer arithmetic coding.
- Independently parseable and checksummed DFC2 files.
- One-step SD 2.1 latent diffusion reconstruction.
- Real backend progress events for the ten-stage compression pipeline.
- Measured BPP, compression ratio, MSE, PSNR, optional SSIM, and encode/decode timings.
- A real Lambda sweep at `1, 5, 7, 10, 20` using the same uploaded image.
- A standalone decoder that accepts only a DFC2 bitstream; it does not upload or require the original image.

## Architecture

```text
image
  -> SD 2.1 VAE encode
  -> 4-channel latent
  -> checkpoint-backed parameter estimation
  -> adaptive affine quantization
  -> factorized Gaussian probability tables
  -> integer arithmetic coding
  -> DFC2 container
  -> arithmetic decode
  -> inverse quantization
  -> one-step SD 2.1 diffusion reconstruction
  -> SD 2.1 VAE decode
  -> reconstructed image
```

The current entropy model is a factorized Gaussian model. The project does not claim to implement the paper's Entroformer. The decoder uses the DFC2 metadata, payload, checksum, shared SD 2.1 model, and shared codec checkpoint; it does not use the original image.

## Project layout

```text
backend/
  main.py                  FastAPI routes and WebSocket progress endpoint
  model_manager.py         Lazy, strict loading of SD 2.1 and the codec
  diffusion_codec/         Quantization, entropy, arithmetic coding, DFC2, metrics
  services/                Compression, decompression, and job management
  tests/                   Codec, API, and model-loading tests
frontend/
  src/pages/               Compress, Decode, Experiments, Model, and About pages
  src/components/          Upload, settings, pipeline, metrics, and chart UI
models/
  paper_style_best.pt      Supplied learned codec checkpoint
outputs/
  Generated DFC2 files and reconstructions; ignored by Git
```

## Requirements

- Python 3.10 or newer.
- Node.js 18 or newer.
- A CUDA-capable GPU is recommended. CPU execution works but SD 2.1 inference is slow.
- Hugging Face access to `sd-research/stable-diffusion-2-1-base`.
- Enough disk space for the SD 2.1 model download, which is several gigabytes.

## Installation

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

Copy-Item .env.example .env
```

Put your Hugging Face token in `.env`:

```dotenv
HF_TOKEN=your_huggingface_token
```

Never commit `.env`. It is ignored by Git. The checked-in `.env.example` contains no secret.

The codec checkpoint is expected at:

```text
models/paper_style_best.pt
```

The checkpoint is included in this repository. The SD 2.1 foundation model is downloaded and cached by `diffusers` on first use.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `HF_TOKEN` | empty | Hugging Face access token |
| `DIFFUSIONCOMPRESS_MODEL_ID` | `sd-research/stable-diffusion-2-1-base` | Exact foundation model ID |
| `DIFFUSIONCOMPRESS_CODEC_CHECKPOINT` | `models/paper_style_best.pt` | Codec checkpoint path |
| `DIFFUSIONCOMPRESS_DEVICE` | `cuda` | Requested device; automatically falls back to CPU when CUDA is unavailable |
| `DIFFUSIONCOMPRESS_DTYPE` | `float16` | GPU inference dtype; CPU uses float32 |

Do not substitute another foundation model or checkpoint. The supplied codec checkpoint is tied to the SD 2.1 stack.

## Run locally

Start the backend from the repository root:

```powershell
\.venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

In a second terminal, start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The backend is available at [http://127.0.0.1:8000](http://127.0.0.1:8000).

The model manager loads the codec, VAE, U-Net, and scheduler when the first compression or decode request needs them. Check the loaded state at `/api/model/status`.

## Using the application

### Compress

1. Open the Compress page and upload an image.
2. Select the research codec and choose a Lambda value.
3. Leave the optional bitrate target as `auto` unless you are recording an experiment input. The current codec uses learned quantization and entropy coding; the field is not an exact target-rate optimizer.
4. The reconstruction method is intentionally fixed to one-step diffusion.
5. Click **Compress image**.
6. Inspect the measured metrics, download the DFC2 bitstream, or download the reconstruction.

The live pipeline is reported by the backend. The UI does not simulate progress.

### Real rate-distortion experiment

After uploading an image, click **Run real experiment**. The frontend submits five independent backend compression jobs for Lambda values:

```text
1, 5, 7, 10, 20
```

Each point is measured from the generated DFC2 file and reconstruction. The results are persisted in `outputs/experiments.json`, shown in the Experiments page, and plotted as BPP on the x-axis versus PSNR on the y-axis. Hover a chart point to see Lambda, BPP, PSNR, and compression ratio.

### Decode independently

Open the Decode page and upload only a `.dfc2` file. The original image is not requested or used. The decoder validates the DFC2 checksum, decodes the arithmetic-coded symbols, reconstructs the latent with one-step diffusion, and returns a PNG.

## API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Basic health check |
| `GET` | `/api/model/status` | Model, checkpoint, device, and component status |
| `GET` | `/api/system/status` | Runtime and GPU status |
| `POST` | `/api/compress` | Accepts a multipart image and creates a compression job |
| `GET` | `/api/jobs/{job_id}` | Returns job state, progress, metrics, and output URLs |
| `WS` | `/ws/pipeline/{job_id}` | Streams backend-generated pipeline progress |
| `GET` | `/api/jobs/{job_id}/download/dfc2` | Downloads the generated DFC2 file |
| `GET` | `/api/jobs/{job_id}/download/reconstruction` | Downloads the reconstructed PNG |
| `POST` | `/api/decompress` | Accepts a multipart DFC2 file and returns a PNG |
| `POST` | `/api/decompress/inspect` | Validates a DFC2 file and returns its metadata |
| `GET` | `/api/experiments` | Returns persisted completed experiment records |
| `GET` | `/api/metrics/{experiment_id}` | Returns one stored experiment record |

The compression form accepts `mode`, optional `bitrate`, `lambda_value`, `resolution`, and compatibility fields used internally by the backend. The supported UI reconstruction path is one-step diffusion only.

Example health check:

```powershell
curl.exe http://127.0.0.1:8000/health
```

## DFC2 format

DFC2 version 1 contains:

1. An 18-byte big-endian prefix containing the magic value, version, reserved byte, metadata length, and payload length.
2. Canonical UTF-8 JSON metadata containing image dimensions, latent dimensions, timestep, quantization parameters, entropy parameters, symbol bounds, and diffusion settings.
3. The integer arithmetic-coded payload.
4. A 32-byte SHA-256 checksum over the prefix, metadata, and payload.

The format does not store the original image, original image bytes, raw floating-point latent, or reconstruction. The checksum is verified before decoding.

## Metrics

Compression metrics are measured from the actual input, DFC2 file, and reconstruction:

- Original and compressed file size.
- Payload and header size.
- Bits per pixel and compression ratio.
- MSE and PSNR.
- Optional SSIM.
- Encode and decode time.
- Latent shape, diffusion timestep, and diffusion step metadata.

SSIM is shown as unavailable when it cannot be calculated. Standalone decoding cannot calculate PSNR or SSIM because it has no original image for comparison.

## Validation

The current implementation has been validated with:

```text
5 passed, 1 skipped
```

The skipped test is the opt-in SD 2.1 model download test. The frontend production build also passes with `npm run build`.

A completed real Lambda sweep on the included 256x256 test image produced:

| Lambda | BPP | Compression ratio | PSNR | DFC2 size |
|---:|---:|---:|---:|---:|
| 1 | 0.2174 | 0.94x | 23.84 dB | 1781 B |
| 5 | 0.1974 | 1.03x | 17.93 dB | 1617 B |
| 7 | 0.1932 | 1.06x | 16.94 dB | 1583 B |
| 10 | 0.1896 | 1.08x | 16.87 dB | 1553 B |
| 20 | 0.1677 | 1.22x | 17.46 dB | 1374 B |

These are prototype measurements, not benchmark claims. Results can vary with image content, hardware, library versions, and model cache state.

Run the fast test suite:

```powershell
python -m pytest backend/tests -q
```

Run the opt-in model-loading test only when the SD 2.1 files are available or you intend to download them:

```powershell
$env:RUN_SD21_TESTS = "1"
python -m pytest backend/tests/test_model_loading.py -q
```

## Known limitations

- SD 2.1 inference is slow on CPU and requires several gigabytes of cached model files.
- The reconstruction path is one-step only; the UI does not pretend to provide multi-step or refined sampling.
- The optional bitrate field is informational input to the current API and is not an exact target-rate optimizer.
- The supplied codec checkpoint is a research prototype and is not presented as a paper benchmark.
- SSIM is optional and may be unavailable depending on the installed environment.

## Paper reference

Inspired by “Lossy Image Compression with Foundation Diffusion Models” by Lucas Relic, Roberto Azevedo, Markus Gross, and Christopher Schroers.
