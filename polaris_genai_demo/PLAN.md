# Implementation Plan: Polaris Vehicle Showroom & 360° Studio Frontend

## 1. Overview
Build a dedicated web frontend application for the Polaris GenAI Demo in a new `frontend/` directory. The application enables users to select vehicle models via their Model ID (e.g. `G27G5X99AZ`), stream and play the model's exact 360° rotation video (`sample_360_rotation.mp4`) directly from the Google Cloud Storage (GCS) bucket (`gs://polaris-demo-files`), and view up to 5 static angle images (front, rear, profile, 3/4 front, top-down) for the selected model.

---

## 2. Key Architecture & Constraints

1. **GCS Security & Media Streaming**:
   - Bucket `gs://polaris-demo-files` has **Public Access Prevention (PAP)** enforced, preventing direct unauthenticated browser access to `storage.googleapis.com`.
   - A lightweight local API / proxy server (Python standard HTTP/FastAPI or Node) running in `frontend/server/` uses active `gcloud` credentials to stream GCS media directly.
   - The stream server implements HTTP `206 Partial Content` (Range headers) to support seamless HTML5 `<video>` scrubbing, buffering, and infinite looping.
   - It also provides local fallback to `models/` directory if offline.

2. **Video Isolation**:
   - When a model is chosen, **only** the single video matching `sample_360_rotation.mp4` for that specific model is presented. All intermediate artifacts and other models' videos are excluded.

3. **Multi-Angle Static Images**:
   - For each model, display up to 5 clean static images corresponding to standard automotive perspectives:
     - Front View (`cgi-front`)
     - 3/4 Front Left View (`cgi-3qFrontLeft`)
     - Side Profile View (`cgi-leftProfile`)
     - Rear / Dash Interior View (`cgi-rear` / `cgi-dash`)
     - Top-Down View (`cgi-topDown`)
   - Interactive modal lightbox for inspecting full-resolution vehicle details.

---

## 3. Technology Stack

- **Framework**: React 18 + Vite (fast build, hot module replacement, small footprint)
- **Styling**: Tailwind CSS (sleek dark automotive aesthetic, Polaris blue accent highlights `#005CB9`, responsive grid layout)
- **Icons**: Lucide React (automotive, 360 rotation, play/pause, maximize, chevron icons)
- **Backend / Streaming Server**: Python / Node GCS streaming proxy (zero extra dependencies, uses existing `gcloud` authentication)
- **Local Testing**: Automated health checks, GCS video streaming verification, component rendering test

---

## 4. Directory Structure

```
polaris_genai_demo/
├── frontend/                     # Dedicated frontend folder
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── server/                   # GCS streaming & model metadata API
│   │   └── api_server.py
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── index.css
│   │   ├── components/
│   │   │   ├── Header.jsx        # Branding & active project badge
│   │   │   ├── ModelSelector.jsx # Dropdown & badge switcher (Model IDs)
│   │   │   ├── VideoPlayer360.jsx# Seamless 360 rotation video player
│   │   │   ├── ImageGallery.jsx  # 5-angle image grid & lightbox modal
│   │   │   └── VehicleSpecs.jsx  # Model details & metadata viewer
│   │   └── data/
│   │       └── modelsConfig.js   # Extracted model specifications
│   └── tests/
│       └── smoke_test.py         # Local end-to-end test script
```

---

## 5. Models Catalog

| Model ID | Vehicle Name & Trim | Color | 360 Video Target | Static Images (Up to 5) |
|---|---|---|---|---|
| **G27G5X99AZ** | 2027 XPED XP Crew NorthStar | Matte Mocha | `sample_360_rotation.mp4` | Front, 3/4 Front, Profile, Dash, Top-Down |
| **G27GXK99AD** | 2027 General XP 1000 Ultimate | Ghost White | `sample_360_rotation.mp4` | Front, 3/4 Front, Profile, Dash, Top-Down |
| **R27CCA5AE8** | 2027 Ranger 500 Tractor | Stealth Gray | `sample_360_rotation.mp4` | Front, 3/4 Front, Profile, Rear, PNG Front |
| **R27X6W1RB9** | 2027 Ranger XD 1500 Crew NorthStar Ultimate | Polaris Pursuit Camo | `sample_360_rotation.mp4` | Front, 3/4 Front, Profile, Rear, Top-Down |
| **Z27XPE92AH** | 2027 RZR Pro XP Sport | Matte Granite Gray | `sample_360_rotation.mp4` | Front, 3/4 Front, Profile, Rear, Top-Down |

---

## 6. Implementation Steps

1. **Step 1: Set up GCS Media & Metadata Streaming API (`frontend/server/api_server.py`)**
   - Implements endpoints:
     - `GET /api/models`: List available models and metadata.
     - `GET /api/models/<model_id>/video`: Streams `sample_360_rotation.mp4` from GCS with HTTP 206 Partial Content support.
     - `GET /api/models/<model_id>/images/<index>`: Streams specific static images.
     - `GET /api/health`: Health status and GCS bucket connectivity check.

2. **Step 2: Initialize React + Vite Application (`frontend/`)**
   - Scaffold React application with Tailwind CSS and Vite.
   - Configure proxy in `vite.config.js` to route `/api` calls to the streaming server.

3. **Step 3: Build Core Components**
   - **`ModelSelector`**: Dropdown showing Model ID as primary key (`G27G5X99AZ`, etc.), with model title and color chips.
   - **`VideoPlayer360`**: Hero video player loaded with `sample_360_rotation.mp4` for the selected model. Displays 360° indicator badge, auto-looping, speed control, and pause/play overlay.
   - **`ImageGallery`**: Responsive grid showing up to 5 static images with perspective labels (Front, Rear, Profile, etc.) and a full-screen zoom modal.
   - **`VehicleSpecs`**: Displays vehicle model info, storage bucket source, and resolution info.

4. **Step 4: Local Testing & Validation**
   - Run automated smoke test verifying:
     - API health endpoint returns `200 OK`.
     - Model metadata endpoint returns all 5 models.
     - Video streaming endpoint correctly serves `sample_360_rotation.mp4` with audio/video headers and 206 Range responses.
     - Frontend builds cleanly (`npm run build`).
     - Frontend server serves the compiled single-page application.
