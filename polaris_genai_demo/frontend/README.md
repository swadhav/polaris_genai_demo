# Polaris 360° Studio & Model Showcase Frontend

A React + Vite frontend for exploring Polaris vehicle models, streaming authenticated 360° rotation videos (`sample_360_rotation.mp4`) from Google Cloud Storage (`gs://polaris-demo-files`), and viewing up to 5 static CGI angle perspectives per model.

---

## Features

1. **Model Selector**:
   - Primary dropdown using the **Model ID** (folder name, e.g. `G27G5X99AZ`, `G27GXK99AD`, `R27CCA5AE8`, `R27X6W1RB9`, `Z27XPE92AH`).
   - Quick-switch pill buttons for rapid 1-click model switching.
   - Live vehicle specs (segment, color finish, horsepower, seating capacity).

2. **360° Rotation Video Player**:
   - Strictly displays `sample_360_rotation.mp4` for the selected model. No other video is shown.
   - Streamed directly from GCS (`gs://polaris-demo-files/models/<model_id>/sample_360_rotation.mp4`) with HTTP 206 Partial Content (range requests) for seamless scrubbing and infinite looping.
   - Autoplay, loop, sound toggle, playback speed presets (0.5x, 1x, 1.5x, 2x), and fullscreen support.

3. **Multi-Angle Static Images**:
   - Up to 5 static CGI images per model (Front View, 3/4 Front Left, Left Profile, Rear / Dashboard, Top-Down).
   - High-resolution modal Lightbox for zoomed inspection with previous/next keyboard navigation.

4. **GCS Security & Resilience**:
   - Overcomes Public Access Prevention (PAP) on `gs://polaris-demo-files` by authenticating requests through active `gcloud` credentials.
   - Transparent local fallback to `models/` directory for offline testing.

---

## Quick Start

### 1. Start the Backend API & Streaming Server
```bash
python3 frontend/server/api_server.py
```
*Runs on `http://localhost:5001`. Serves API endpoints and the compiled production SPA.*

### 2. Start the Vite Dev Server (Optional, for development)
```bash
cd frontend
export PATH="$HOME/.local/bin:$PATH"
npm run dev
```
*Runs on `http://localhost:5173` with hot module reloading and proxies `/api` to port 5001.*

### 3. Run Automated Tests
```bash
python3 frontend/tests/test_frontend.py
```
*Executes full test suite validating health checks, model catalog, video range streaming, static images, and production SPA serving.*
