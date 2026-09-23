#!/usr/bin/env python3
"""
Polaris Vehicle Demo - Streaming & Metadata Backend API Server

Serves:
- GET /api/health: Health check and GCS status
- GET /api/models: Model catalog with metadata, 360 video info, and static image lists
- GET /api/models/<model_id>/video: Streams sample_360_rotation.mp4 directly from GCS with HTTP 206 Range support
- GET /api/models/<model_id>/images/<filename>: Streams static images from GCS (with local fallback)
- Static files from frontend/dist if built
"""

import base64
import json
import logging
import mimetypes
import os
import re
import subprocess
import sys
import time
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

from PIL import Image
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("PolarisApiServer")

DEFAULT_PROJECT = "polaris-genai-demo"
DEFAULT_BUCKET = "polaris-demo-files"
PORT = int(os.environ.get("PORT", 5001))
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
DEALERS_DIR = PROJECT_ROOT / "dealers"
DIST_DIR = PROJECT_ROOT / "frontend" / "dist"

# Known model metadata enhancements for Polaris vehicles
MODEL_METADATA = {
    "G27G5X99AZ": {
        "title": "2027 XPEDITION XP Crew NorthStar",
        "segment": "Crossover SxS",
        "color": "Matte Mocha",
        "badge": "NorthStar Edition",
        "hp": "114 HP",
        "seating": "5 Seats",
    },
    "G27GXK99AD": {
        "title": "2027 GENERAL XP 1000 Ultimate",
        "segment": "Crossover SxS",
        "color": "Ghost White",
        "badge": "Ultimate Edition",
        "hp": "100 HP",
        "seating": "2 Seats",
    },
    "R27CCA5AE8": {
        "title": "2027 RANGER 500 Tractor",
        "segment": "Utility SxS",
        "color": "Stealth Gray",
        "badge": "Tractor Edition",
        "hp": "32 HP",
        "seating": "2 Seats",
    },
    "R27X6W1RB9": {
        "title": "2027 RANGER XD 1500 Crew NorthStar Ultimate",
        "segment": "Heavy Duty Utility",
        "color": "Polaris Pursuit Camo",
        "badge": "NorthStar Ultimate",
        "hp": "110 HP",
        "seating": "6 Seats",
    },
    "Z27XPE92AH": {
        "title": "2027 RZR Pro XP Sport",
        "segment": "Performance Sport SxS",
        "color": "Matte Granite Gray",
        "badge": "Sport Edition",
        "hp": "181 HP",
        "seating": "2 Seats",
    },
}

class GCSAuthManager:
    """Manages GCP access tokens via Google Cloud metadata server, google-auth, and gcloud CLI with caching."""
    def __init__(self):
        self._cached_token = None
        self._token_expiry = 0

    def get_token(self) -> str:
        now = time.time()
        if self._cached_token and now < self._token_expiry:
            return self._cached_token

        # 1. Try google-auth library if available
        try:
            import google.auth
            import google.auth.transport.requests
            creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req)
            if creds.token:
                self._cached_token = creds.token
                self._token_expiry = now + 1800
                logger.info("Successfully refreshed access token via google-auth")
                return self._cached_token
        except Exception:
            pass

        # 2. Try GCP Compute / Cloud Run Instance Metadata Server
        try:
            import urllib.request
            req = urllib.request.Request(
                "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
                headers={"Metadata-Flavor": "Google"}
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                tok = data.get("access_token")
                if tok:
                    self._cached_token = tok
                    self._token_expiry = now + 1800
                    logger.info("Successfully refreshed access token via GCP metadata server")
                    return self._cached_token
        except Exception:
            pass

        # 3. Fallback to gcloud CLI (local development)
        try:
            res = subprocess.run(
                ["gcloud", "auth", "print-access-token"],
                check=True,
                capture_output=True,
                text=True,
            )
            self._cached_token = res.stdout.strip()
            self._token_expiry = now + 1800  # valid ~30 min
            logger.info("Successfully refreshed GCS access token via gcloud")
            return self._cached_token
        except Exception as exc:
            logger.warning(f"Failed to obtain token via gcloud: {exc}")
            return ""

auth_manager = GCSAuthManager()


def upload_to_gcs(data_or_path, gcs_object_path: str, content_type: str = "image/jpeg") -> bool:
    """Uploads bytes or a local file to GCS."""
    token = auth_manager.get_token()
    if not token:
        logger.warning(f"No token available for GCS upload: {gcs_object_path}")
        return False
    url = f"https://storage.googleapis.com/upload/storage/v1/b/{DEFAULT_BUCKET}/o?uploadType=media&name={quote(gcs_object_path, safe='')}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": content_type,
    }
    if isinstance(data_or_path, (str, Path)):
        with open(data_or_path, "rb") as f:
            data = f.read()
    else:
        data = data_or_path
    try:
        resp = requests.post(url, headers=headers, data=data, timeout=60)
        if resp.status_code in [200, 201]:
            logger.info(f"Successfully uploaded gs://{DEFAULT_BUCKET}/{gcs_object_path} ({len(data)} bytes)")
            return True
        else:
            logger.warning(f"Failed to upload gs://{DEFAULT_BUCKET}/{gcs_object_path}: {resp.status_code} - {resp.text}")
            return False
    except Exception as exc:
        logger.warning(f"Exception during GCS upload gs://{DEFAULT_BUCKET}/{gcs_object_path}: {exc}")
        return False


def classify_angle(filename: str) -> str:
    lower = filename.lower()
    if "frontleft" in lower or "3q" in lower:
        return "3/4 Front View"
    if "leftprofile" in lower or "profile" in lower:
        return "Left Profile View"
    if "topdown" in lower:
        return "Top-Down View"
    if "dash" in lower:
        return "Interior Dashboard"
    if "rear" in lower:
        return "Rear View"
    if "front" in lower:
        return "Front View"
    return "Angle View"


def get_models_catalog():
    """Scans local models folder and GCS to compile list of models and their media."""
    catalog = []
    if not MODELS_DIR.exists():
        logger.error(f"Models directory not found at {MODELS_DIR}")
        return catalog

    model_dirs = sorted([d for d in MODELS_DIR.iterdir() if d.is_dir()])
    for mdir in model_dirs:
        model_id = mdir.name
        meta = MODEL_METADATA.get(model_id, {
            "title": f"Polaris Model {model_id}",
            "segment": "Powersports",
            "color": "Factory Standard",
            "badge": "Standard",
            "hp": "N/A",
            "seating": "N/A",
        })

        # Static images: up to 5 static images (exclude tif and video files)
        image_candidates = [
            f.name for f in mdir.iterdir()
            if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png"]
            and not f.name.startswith(".")
        ]

        # Prioritize angles
        angle_order = [
            "3/4 Front View",
            "Front View",
            "Left Profile View",
            "Rear View",
            "Top-Down View",
            "Interior Dashboard",
            "Angle View",
        ]

        ranked_images = []
        for f_name in image_candidates:
            label = classify_angle(f_name)
            ranked_images.append({
                "filename": f_name,
                "label": label,
                "url": f"/api/models/{model_id}/images/{f_name}",
                "gcs_uri": f"gs://{DEFAULT_BUCKET}/models/{model_id}/{f_name}",
            })

        def sort_key(img):
            lbl = img["label"]
            try:
                return angle_order.index(lbl)
            except ValueError:
                return 99

        ranked_images.sort(key=sort_key)
        # Limit to up to 5 images as requested
        selected_images = ranked_images[:5]

        # Target video name must match sample_360_rotation.mp4 as specified
        video_filename = "sample_360_rotation.mp4"
        gcs_video_uri = f"gs://{DEFAULT_BUCKET}/models/{model_id}/{video_filename}"
        outdoor_video_filename = "outdoor_background_360.mp4"
        gcs_outdoor_video_uri = f"gs://{DEFAULT_BUCKET}/models/{model_id}/{outdoor_video_filename}"

        catalog.append({
            "id": model_id,
            "title": meta["title"],
            "segment": meta["segment"],
            "color": meta["color"],
            "badge": meta["badge"],
            "hp": meta["hp"],
            "seating": meta["seating"],
            "video": {
                "filename": video_filename,
                "url": f"/api/models/{model_id}/video",
                "gcs_uri": gcs_video_uri,
            },
            "outdoor_video": {
                "filename": outdoor_video_filename,
                "url": f"/api/models/{model_id}/video?variant=outdoor",
                "gcs_uri": gcs_outdoor_video_uri,
            },
            "videos": {
                "studio": {
                    "id": "studio",
                    "title": "Studio 360°",
                    "filename": video_filename,
                    "url": f"/api/models/{model_id}/video",
                    "gcs_uri": gcs_video_uri,
                },
                "outdoor": {
                    "id": "outdoor",
                    "title": "Outdoor Background 360°",
                    "filename": outdoor_video_filename,
                    "url": f"/api/models/{model_id}/video?variant=outdoor",
                    "gcs_uri": gcs_outdoor_video_uri,
                },
            },
            "images": selected_images,
        })
    return catalog


def get_dealers_catalog():
    """
    Discovers dealers from the dealers folder in the GCS bucket and local repository.
    Checks whether background image is present, if logo is available, and which models have showroom images.
    """
    dealers_map = {}

    friendly_names = {
        "Malcolm_smith": "Malcolm Smith Motorsports",
        "bills_service": "Bills Service Center",
        "mies_outland": "Mies Outland",
        "power_lodge": "Power Lodge",
        "ridezilla": "Ridezilla",
    }

    # 1. Scan local DEALERS_DIR if present
    if DEALERS_DIR.exists():
        for d in sorted(DEALERS_DIR.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                did = d.name
                has_bg = any(
                    ("background" in f.name.lower() or f.name.lower().startswith("dealer background"))
                    and f.suffix.lower() in [".jpg", ".jpeg", ".png"]
                    for f in d.iterdir() if f.is_file()
                )
                logos = [f.name for f in d.iterdir() if "logo" in f.name.lower() and f.suffix.lower() in [".png", ".jpg", ".jpeg", ".svg"]]
                
                gen_dir = d / "generated"
                gen_models = []
                if gen_dir.exists():
                    for f in gen_dir.iterdir():
                        if f.name.endswith("_showroom.png"):
                            gen_models.append(f.name.replace("_showroom.png", ""))

                dealers_map[did] = {
                    "id": did,
                    "name": friendly_names.get(did, did.replace("_", " ").title()),
                    "folder_name": did,
                    "has_background": has_bg,
                    "background_url": f"/api/dealers/{did}/background" if has_bg else None,
                    "has_logo": len(logos) > 0,
                    "logo_url": f"/api/dealers/{did}/logo" if logos else None,
                    "generated_models": sorted(gen_models),
                }

    # 2. Query GCS objects to ensure all folders and generated assets under gs://polaris-demo-files/dealers/ are included
    token = auth_manager.get_token()
    if token:
        try:
            url = f"https://storage.googleapis.com/storage/v1/b/{DEFAULT_BUCKET}/o?prefix=dealers/"
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get(url, headers=headers, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("items", []):
                    name = item.get("name", "")
                    parts = name.split("/")
                    if len(parts) >= 2 and parts[1]:
                        did = parts[1]
                        if did not in dealers_map:
                            dealers_map[did] = {
                                "id": did,
                                "name": friendly_names.get(did, did.replace("_", " ").title()),
                                "folder_name": did,
                                "has_background": False,
                                "background_url": None,
                                "has_logo": False,
                                "logo_url": None,
                                "generated_models": [],
                            }
                        fname = parts[-1].lower()
                        if "background" in fname or fname.startswith("dealer background"):
                            dealers_map[did]["has_background"] = True
                            dealers_map[did]["background_url"] = f"/api/dealers/{did}/background"
                        if "logo" in fname:
                            dealers_map[did]["has_logo"] = True
                            dealers_map[did]["logo_url"] = f"/api/dealers/{did}/logo"
                        if fname.endswith("_showroom.png"):
                            mid = parts[-1].replace("_showroom.png", "")
                            if mid not in dealers_map[did]["generated_models"]:
                                dealers_map[did]["generated_models"].append(mid)
        except Exception as exc:
            logger.warning(f"Could not query GCS for dealers: {exc}")

    # Return dealers sorted alphabetically by folder name
    for did in dealers_map:
        dealers_map[did]["generated_models"] = sorted(dealers_map[did]["generated_models"])
    return sorted(dealers_map.values(), key=lambda x: x["folder_name"])


class PolarisHandler(BaseHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Range, Content-Type, Authorization")
        self.send_header("Access-Control-Expose-Headers", "Content-Range, Content-Length, Accept-Ranges")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_HEAD(self):
        self.handle_request(is_head=True)

    def do_GET(self):
        self.handle_request(is_head=False)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        # Upload dealer background: /api/dealers/<dealer_id>/upload-background
        upload_match = re.match(r"^/api/dealers/([^/]+)/upload-background/?$", path)
        if upload_match:
            dealer_id = upload_match.group(1)
            self.handle_dealer_upload_background(dealer_id)
            return

        # Generate showroom image: /api/dealers/<dealer_id>/models/<model_id>/generate
        gen_match = re.match(r"^/api/dealers/([^/]+)/models/([^/]+)/generate/?$", path)
        if gen_match:
            dealer_id = gen_match.group(1)
            model_id = gen_match.group(2)
            self.handle_dealer_generate_showroom(dealer_id, model_id)
            return

        # 404 for unknown POST routes
        self.send_response(404)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": "Endpoint not found", "path": path}).encode("utf-8"))

    def handle_request(self, is_head=False):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query)

        # Health endpoint
        if path == "/api/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            if not is_head:
                self.wfile.write(json.dumps({
                    "status": "healthy",
                    "project": DEFAULT_PROJECT,
                    "bucket": DEFAULT_BUCKET,
                    "timestamp": time.time(),
                }).encode("utf-8"))
            return

        # Agents Registry catalog endpoint
        if path == "/api/agents":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            if not is_head:
                agents_data = [
                    {
                        "id": "polaris-vehicle-360-agent",
                        "display_name": "Polaris Vehicle 360 Rotation Agent",
                        "type": "Primary Agent",
                        "model": "veo-3.1-generate-001",
                        "endpoint": "/api/models",
                        "registry_resource": "projects/416490439030/locations/us-central1/agents/agentregistry-00000000-0000-0000-95d5-81ee5412d9e0",
                        "status": "ACTIVE",
                    },
                    {
                        "id": "polaris-dealer-showroom-agent",
                        "display_name": "Polaris Dealer Showroom Staging Agent",
                        "type": "Primary Agent",
                        "model": "gemini-2.5-flash-image + gemini-2.5-flash",
                        "endpoint": "/api/dealers",
                        "registry_resource": "projects/416490439030/locations/us-central1/agents/agentregistry-00000000-0000-0000-fa86-3102a09015a4",
                        "status": "ACTIVE",
                    },
                    {
                        "id": "polaris-showroom-inpainting-agent",
                        "display_name": "Showroom Inpainting & Architectural Clean-Up Sub-Agent",
                        "type": "Sub-Agent (Stage 1)",
                        "model": "gemini-2.5-flash-image",
                        "endpoint": "/api/dealers/clean-plate",
                        "registry_resource": "projects/416490439030/locations/us-central1/agents/agentregistry-00000000-0000-0000-bfba-97cacb358e7f",
                        "status": "ACTIVE",
                    },
                    {
                        "id": "polaris-showroom-staging-agent",
                        "display_name": "Multi-Reference Vehicle Staging & 3D Signage Sub-Agent",
                        "type": "Sub-Agent (Stage 2)",
                        "model": "gemini-2.5-flash-image",
                        "endpoint": "/api/dealers/stage",
                        "registry_resource": "projects/416490439030/locations/us-central1/agents/agentregistry-00000000-0000-0000-855d-31d06b62c0e4",
                        "status": "ACTIVE",
                    },
                    {
                        "id": "polaris-showroom-qa-evaluator",
                        "display_name": "Multimodal QA & Compliance Auditor Sub-Agent",
                        "type": "Sub-Agent (Stage 3)",
                        "model": "gemini-2.5-flash",
                        "endpoint": "/api/dealers/evaluate",
                        "registry_resource": "projects/416490439030/locations/us-central1/agents/agentregistry-00000000-0000-0000-c280-218726c27953",
                        "status": "ACTIVE",
                    },
                ]
                self.wfile.write(json.dumps({
                    "agents": agents_data,
                    "project": DEFAULT_PROJECT,
                    "location": "us-central1",
                    "total": len(agents_data),
                }).encode("utf-8"))
            return

        # Models catalog endpoint
        if path == "/api/models":
            models = get_models_catalog()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            if not is_head:
                self.wfile.write(json.dumps({
                    "models": models,
                    "total": len(models),
                }).encode("utf-8"))
            return

        # Dealers catalog endpoint
        if path == "/api/dealers":
            dealers = get_dealers_catalog()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            if not is_head:
                self.wfile.write(json.dumps({
                    "dealers": dealers,
                    "total": len(dealers),
                }).encode("utf-8"))
            return

        # Dealer logo: /api/dealers/<dealer_id>/logo
        dealer_logo_match = re.match(r"^/api/dealers/([^/]+)/logo/?$", path)
        if dealer_logo_match:
            dealer_id = dealer_logo_match.group(1)
            self.serve_dealer_logo(dealer_id, is_head=is_head)
            return

        # Dealer background: /api/dealers/<dealer_id>/background
        dealer_bg_match = re.match(r"^/api/dealers/([^/]+)/background/?$", path)
        if dealer_bg_match:
            dealer_id = dealer_bg_match.group(1)
            self.serve_dealer_background(dealer_id, is_head=is_head)
            return

        # Dealer showroom image: /api/dealers/<dealer_id>/models/<model_id>/showroom
        showroom_match = re.match(r"^/api/dealers/([^/]+)/models/([^/]+)/showroom/?$", path)
        if showroom_match:
            dealer_id = showroom_match.group(1)
            model_id = showroom_match.group(2)
            self.serve_dealer_showroom(dealer_id, model_id, is_head=is_head)
            return

        # Dealer evaluation JSON: /api/dealers/<dealer_id>/models/<model_id>/evaluation
        eval_match = re.match(r"^/api/dealers/([^/]+)/models/([^/]+)/evaluation/?$", path)
        if eval_match:
            dealer_id = eval_match.group(1)
            model_id = eval_match.group(2)
            self.serve_dealer_evaluation(dealer_id, model_id, is_head=is_head)
            return

        # Model 360 Video streaming: /api/models/<model_id>/video or /api/models/<model_id>/video/<variant>
        video_match = re.match(r"^/api/models/([^/]+)/video(?:/([^/]+))?/?$", path)
        if video_match:
            model_id = video_match.group(1)
            sub_path = video_match.group(2)
            variant_param = query.get("variant", query.get("type", query.get("video", [None])))[0]
            chosen = sub_path or variant_param or "rotation"
            if chosen and any(k in chosen.lower() for k in ["outdoor", "background"]):
                target_video = "outdoor_background_360.mp4"
            else:
                target_video = "sample_360_rotation.mp4"
            self.stream_video(model_id, video_name=target_video, is_head=is_head)
            return

        # Model Static Image: /api/models/<model_id>/images/<filename>
        image_match = re.match(r"^/api/models/([^/]+)/images/([^/]+)$", path)
        if image_match:
            model_id = image_match.group(1)
            filename = image_match.group(2)
            self.serve_image(model_id, filename, is_head=is_head)
            return

        # Serve frontend/dist static files if present
        if DIST_DIR.exists():
            clean_path = path.lstrip("/")
            file_path = DIST_DIR / clean_path
            if file_path.is_file():
                self.serve_static_file(file_path, is_head=is_head)
                return
            index_path = DIST_DIR / "index.html"
            if index_path.is_file():
                self.serve_static_file(index_path, is_head=is_head)
                return

        # 404
        self.send_response(404)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if not is_head:
            self.wfile.write(json.dumps({"error": "Not Found", "path": path}).encode("utf-8"))

    def stream_video(self, model_id: str, video_name: str = "sample_360_rotation.mp4", is_head=False):
        """Streams 360 rotation or outdoor video directly from GCS with HTTP 206 Range support."""
        token = auth_manager.get_token()
        gcs_object = f"models/{model_id}/{video_name}"
        gcs_url = f"https://storage.googleapis.com/storage/v1/b/{DEFAULT_BUCKET}/o/{quote(gcs_object, safe='')}?alt=media"

        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        # Forward client Range header if requested
        range_header = self.headers.get("Range")
        if range_header:
            headers["Range"] = range_header

        try:
            # Stream from GCS
            req_method = requests.head if is_head else requests.get
            resp = req_method(gcs_url, headers=headers, stream=True, timeout=30)

            if resp.status_code in [200, 206]:
                self.send_response(resp.status_code)
                self.send_cors_headers()
                self.send_header("Content-Type", resp.headers.get("Content-Type", "video/mp4"))
                self.send_header("Accept-Ranges", "bytes")
                if "Content-Length" in resp.headers:
                    self.send_header("Content-Length", resp.headers["Content-Length"])
                if "Content-Range" in resp.headers:
                    self.send_header("Content-Range", resp.headers["Content-Range"])
                self.send_header("Cache-Control", "public, max-age=3600")
                self.end_headers()

                if not is_head:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if chunk:
                            self.wfile.write(chunk)
                return
            else:
                logger.warning(f"GCS streaming returned status {resp.status_code}: {resp.text[:200]}")
        except Exception as exc:
            logger.warning(f"Error proxying from GCS: {exc}")

        # Local fallback if GCS fails
        self.stream_local_video_fallback(model_id, video_name=video_name, is_head=is_head)

    def stream_local_video_fallback(self, model_id: str, video_name: str = "sample_360_rotation.mp4", is_head=False):
        """Fallback to stream rotation or outdoor video from local models/ directory."""
        if "outdoor" in video_name:
            candidates = [
                MODELS_DIR / model_id / "outdoor_background_360.mp4",
                MODELS_DIR / model_id / f"{model_id}_outdoor_background_360.mp4",
            ]
        else:
            candidates = [
                MODELS_DIR / model_id / "sample_360_rotation.mp4",
                MODELS_DIR / model_id / "rotation_360.mp4",
                MODELS_DIR / model_id / f"{model_id}_360_rotation.mp4",
            ]
        local_path = None
        for c in candidates:
            if c.is_file():
                local_path = c
                break

        if not local_path:
            self.send_response(404)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            if not is_head:
                self.wfile.write(json.dumps({"error": f"No video {video_name} found for model {model_id}"}).encode("utf-8"))
            return

        file_size = local_path.stat().st_size
        range_header = self.headers.get("Range")

        if range_header:
            m = re.match(r"bytes=(\d+)-(\d*)", range_header)
            if m:
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else file_size - 1
                length = end - start + 1

                self.send_response(206)
                self.send_cors_headers()
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(length))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()

                if not is_head:
                    with open(local_path, "rb") as f:
                        f.seek(start)
                        remaining = length
                        while remaining > 0:
                            chunk = f.read(min(remaining, 65536))
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                            remaining -= len(chunk)
                return

        # Full file response
        self.send_response(200)
        self.send_cors_headers()
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Length", str(file_size))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        if not is_head:
            with open(local_path, "rb") as f:
                while chunk := f.read(65536):
                    self.wfile.write(chunk)

    def serve_image(self, model_id: str, filename: str, is_head=False):
        """Serves static vehicle image from local disk or GCS."""
        local_path = MODELS_DIR / model_id / filename
        if local_path.is_file():
            mime_type, _ = mimetypes.guess_type(str(local_path))
            mime_type = mime_type or "image/jpeg"
            size = local_path.stat().st_size

            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(size))
            self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()

            if not is_head:
                with open(local_path, "rb") as f:
                    while chunk := f.read(65536):
                        self.wfile.write(chunk)
            return

        # If not local, attempt GCS proxy
        token = auth_manager.get_token()
        gcs_object = f"models/{model_id}/{filename}"
        gcs_url = f"https://storage.googleapis.com/storage/v1/b/{DEFAULT_BUCKET}/o/{quote(gcs_object, safe='')}?alt=media"
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        try:
            resp = requests.get(gcs_url, headers=headers, stream=True, timeout=15)
            if resp.status_code == 200:
                self.send_response(200)
                self.send_cors_headers()
                self.send_header("Content-Type", resp.headers.get("Content-Type", "image/jpeg"))
                if "Content-Length" in resp.headers:
                    self.send_header("Content-Length", resp.headers["Content-Length"])
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                if not is_head:
                    for chunk in resp.iter_content(65536):
                        if chunk:
                            self.wfile.write(chunk)
                return
        except Exception as exc:
            logger.warning(f"Failed to fetch image {filename} from GCS: {exc}")

        self.send_response(404)
        self.send_cors_headers()
        self.end_headers()

    def serve_dealer_logo(self, dealer_id: str, is_head=False):
        """Serves dealer logo from local dealers folder or GCS."""
        dealer_dir = DEALERS_DIR / dealer_id
        if dealer_dir.exists():
            logos = [f for f in dealer_dir.iterdir() if "logo" in f.name.lower() and f.suffix.lower() in [".png", ".jpg", ".jpeg"]]
            if logos:
                logo_path = logos[0]
                mime_type, _ = mimetypes.guess_type(str(logo_path))
                mime_type = mime_type or "image/png"
                size = logo_path.stat().st_size
                self.send_response(200)
                self.send_cors_headers()
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Length", str(size))
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                if not is_head:
                    with open(logo_path, "rb") as f:
                        while chunk := f.read(65536):
                            self.wfile.write(chunk)
                return

        # GCS proxy check
        token = auth_manager.get_token()
        if token:
            try:
                url = f"https://storage.googleapis.com/storage/v1/b/{DEFAULT_BUCKET}/o?prefix=dealers/{quote(dealer_id, safe='')}/"
                headers = {"Authorization": f"Bearer {token}"}
                resp = requests.get(url, headers=headers, timeout=8)
                if resp.status_code == 200:
                    for item in resp.json().get("items", []):
                        name = item.get("name", "")
                        fname = name.split("/")[-1].lower()
                        if "logo" in fname and fname.endswith((".png", ".jpg", ".jpeg", ".svg")):
                            gcs_url = f"https://storage.googleapis.com/storage/v1/b/{DEFAULT_BUCKET}/o/{quote(name, safe='')}?alt=media"
                            img_resp = requests.get(gcs_url, headers=headers, stream=True, timeout=15)
                            if img_resp.status_code == 200:
                                self.send_response(200)
                                self.send_cors_headers()
                                self.send_header("Content-Type", img_resp.headers.get("Content-Type", "image/png"))
                                if "Content-Length" in img_resp.headers:
                                    self.send_header("Content-Length", img_resp.headers["Content-Length"])
                                self.send_header("Cache-Control", "public, max-age=86400")
                                self.end_headers()
                                if not is_head:
                                    for chunk in img_resp.iter_content(65536):
                                        if chunk:
                                            self.wfile.write(chunk)
                                return
            except Exception as exc:
                logger.warning(f"Failed to fetch logo for {dealer_id} from GCS: {exc}")

        # 404
        self.send_response(404)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if not is_head:
            self.wfile.write(json.dumps({"error": f"Logo not found for dealer {dealer_id}"}).encode("utf-8"))

    def serve_dealer_background(self, dealer_id: str, is_head=False):
        """Serves raw dealer background photo from local dealers folder or GCS."""
        dealer_dir = DEALERS_DIR / dealer_id
        if dealer_dir.exists():
            bg_files = [
                f for f in dealer_dir.iterdir()
                if f.is_file() and ("background" in f.name.lower() or f.name.lower().startswith("dealer background"))
                and f.suffix.lower() in [".jpg", ".jpeg", ".png"]
            ]
            if bg_files:
                bg_path = bg_files[0]
                mime_type, _ = mimetypes.guess_type(str(bg_path))
                mime_type = mime_type or "image/jpeg"
                size = bg_path.stat().st_size
                self.send_response(200)
                self.send_cors_headers()
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Length", str(size))
                self.send_header("Cache-Control", "no-cache, must-revalidate")
                self.end_headers()
                if not is_head:
                    with open(bg_path, "rb") as f:
                        while chunk := f.read(65536):
                            self.wfile.write(chunk)
                return

        # GCS proxy check
        token = auth_manager.get_token()
        if token:
            try:
                url = f"https://storage.googleapis.com/storage/v1/b/{DEFAULT_BUCKET}/o?prefix=dealers/{quote(dealer_id, safe='')}/"
                headers = {"Authorization": f"Bearer {token}"}
                resp = requests.get(url, headers=headers, timeout=8)
                if resp.status_code == 200:
                    for item in resp.json().get("items", []):
                        name = item.get("name", "")
                        fname = name.split("/")[-1].lower()
                        if ("background" in fname or fname.startswith("dealer background")) and fname.endswith((".jpg", ".jpeg", ".png")):
                            gcs_url = f"https://storage.googleapis.com/storage/v1/b/{DEFAULT_BUCKET}/o/{quote(name, safe='')}?alt=media"
                            img_resp = requests.get(gcs_url, headers=headers, stream=True, timeout=15)
                            if img_resp.status_code == 200:
                                self.send_response(200)
                                self.send_cors_headers()
                                self.send_header("Content-Type", img_resp.headers.get("Content-Type", "image/jpeg"))
                                if "Content-Length" in img_resp.headers:
                                    self.send_header("Content-Length", img_resp.headers["Content-Length"])
                                self.send_header("Cache-Control", "no-cache, must-revalidate")
                                self.end_headers()
                                if not is_head:
                                    for chunk in img_resp.iter_content(65536):
                                        if chunk:
                                            self.wfile.write(chunk)
                                return
            except Exception as exc:
                logger.warning(f"Failed to fetch background for {dealer_id} from GCS: {exc}")

        self.send_response(404)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if not is_head:
            self.wfile.write(json.dumps({"error": f"Background image not found for dealer {dealer_id}"}).encode("utf-8"))

    def parse_post_data(self):
        """Parses multipart/form-data, application/json, or urlencoded POST bodies."""
        content_type = self.headers.get("Content-Type", "")
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)

        fields = {}
        files = {}

        if "application/json" in content_type:
            try:
                data = json.loads(raw_body.decode("utf-8"))
                if isinstance(data, dict):
                    fields = data
                    if "image" in data:
                        img_str = data["image"]
                        if "," in img_str:
                            img_str = img_str.split(",", 1)[1]
                        files["image"] = {
                            "filename": data.get("filename", "dealer background.jpg"),
                            "content": base64.b64decode(img_str),
                        }
            except Exception as e:
                logger.error(f"Error parsing JSON payload: {e}")

        elif "multipart/form-data" in content_type:
            try:
                msg = BytesParser(policy=default).parsebytes(
                    b"Content-Type: " + content_type.encode("latin1") + b"\r\n\r\n" + raw_body
                )
                for part in msg.iter_parts():
                    name = part.get_param("name", header="content-disposition")
                    filename = part.get_filename()
                    payload = part.get_payload(decode=True)
                    if filename:
                        files[name or "file"] = {
                            "filename": filename,
                            "content": payload,
                        }
                    elif name:
                        fields[name] = payload.decode("utf-8", errors="ignore")
            except Exception as e:
                logger.error(f"Error parsing multipart payload: {e}")

        elif "application/x-www-form-urlencoded" in content_type:
            try:
                parsed = parse_qs(raw_body.decode("utf-8", errors="ignore"))
                for k, v in parsed.items():
                    fields[k] = v[0] if v else ""
            except Exception as e:
                logger.error(f"Error parsing urlencoded payload: {e}")

        return fields, files

    def handle_dealer_upload_background(self, dealer_id: str):
        """
        Receives uploaded dealer background image, saves to dealers/<dealer_id>/dealer background.jpg locally and on GCS,
        and executes generate_dealer_showroom.py for the selected model.
        """
        fields, files = self.parse_post_data()
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        model_id = fields.get("model_id") or query.get("model_id", [None])[0] or "G27G5X99AZ"

        # Extract image bytes
        image_data = None
        for key in ["image", "file", "background"]:
            if key in files:
                image_data = files[key]["content"]
                break
        if not image_data and files:
            first_key = next(iter(files))
            image_data = files[first_key]["content"]

        if not image_data:
            self.send_response(400)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "No image file provided in upload"}).encode("utf-8"))
            return

        dealer_dir = DEALERS_DIR / dealer_id
        dealer_dir.mkdir(parents=True, exist_ok=True)

        # Remove existing local background files to avoid conflict
        for f in dealer_dir.iterdir():
            if f.is_file() and ("background" in f.name.lower() or f.name.lower().startswith("dealer background")):
                try:
                    f.unlink()
                except Exception as e:
                    logger.warning(f"Could not remove old background file {f}: {e}")

        # Save new background image as 'dealer background.jpg' locally
        bg_path = dealer_dir / "dealer background.jpg"
        try:
            with Image.open(BytesIO(image_data)) as img:
                img = img.convert("RGB")
                img.save(bg_path, "JPEG", quality=95)
            logger.info(f"Saved background for dealer {dealer_id} to {bg_path} via PIL")
        except Exception as e:
            logger.warning(f"PIL save failed, writing raw bytes: {e}")
            with open(bg_path, "wb") as f:
                f.write(image_data)

        # Upload background image to GCS under gs://<bucket>/dealers/<dealer_id>/dealer background.jpg
        gcs_bg_key = f"dealers/{dealer_id}/dealer background.jpg"
        upload_to_gcs(bg_path, gcs_bg_key, content_type="image/jpeg")

        # Remove old clean_showroom_plate.png if present so clean plate is regenerated
        old_plate = dealer_dir / "clean_showroom_plate.png"
        if old_plate.exists():
            try:
                old_plate.unlink()
            except Exception:
                pass

        # Run generate_dealer_showroom.py script for the model selected
        script_path = PROJECT_ROOT / "scripts" / "generate_dealer_showroom.py"
        cmd = [
            sys.executable,
            str(script_path),
            "--dealer", dealer_id,
            "--model", model_id,
            "--force-clean",
            "--overwrite",
        ]
        logger.info(f"Executing: {' '.join(cmd)}")
        try:
            res = subprocess.run(
                cmd,
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=180,
                env=dict(os.environ),
            )
            if res.returncode != 0:
                logger.error(f"Generation failed:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}")
                self.send_response(500)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": "generation_failed",
                    "message": f"Showroom generation failed: {res.stderr or res.stdout}",
                    "details": res.stdout,
                }).encode("utf-8"))
                return
        except subprocess.TimeoutExpired:
            self.send_response(504)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "timeout",
                "message": "Showroom generation timed out after 180 seconds",
            }).encode("utf-8"))
            return
        except Exception as exc:
            logger.error(f"Failed to execute generation script: {exc}")
            self.send_response(500)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "execution_error",
                "message": str(exc),
            }).encode("utf-8"))
            return

        self.send_response(200)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "success": True,
            "message": f"Successfully uploaded background and staged {model_id} in {dealer_id} showroom.",
            "dealer_id": dealer_id,
            "model_id": model_id,
            "showroom_url": f"/api/dealers/{dealer_id}/models/{model_id}/showroom?t={int(time.time())}",
        }).encode("utf-8"))

    def handle_dealer_generate_showroom(self, dealer_id: str, model_id: str):
        """
        Executes generate_dealer_showroom.py for the given dealer and model
        when background and logo are present.
        """
        dealer_dir = DEALERS_DIR / dealer_id
        if not dealer_dir.exists():
            self.send_response(404)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"Dealer directory '{dealer_id}' not found"}).encode("utf-8"))
            return

        has_bg = any(
            ("background" in f.name.lower() or f.name.lower().startswith("dealer background"))
            and f.suffix.lower() in [".jpg", ".jpeg", ".png"]
            for f in dealer_dir.iterdir() if f.is_file()
        )
        if not has_bg:
            self.send_response(400)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "missing_background",
                "message": f"Dealer '{dealer_id}' is missing a background image."
            }).encode("utf-8"))
            return

        has_logo = any(
            "logo" in f.name.lower() and f.suffix.lower() in [".png", ".jpg", ".jpeg", ".svg"]
            for f in dealer_dir.iterdir() if f.is_file()
        )
        if not has_logo:
            self.send_response(400)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "missing_logo",
                "message": f"Dealer '{dealer_id}' is missing a logo."
            }).encode("utf-8"))
            return

        script_path = PROJECT_ROOT / "scripts" / "generate_dealer_showroom.py"
        cmd = [
            sys.executable,
            str(script_path),
            "--dealer", dealer_id,
            "--model", model_id,
            "--overwrite",
        ]
        logger.info(f"Executing: {' '.join(cmd)}")
        try:
            res = subprocess.run(
                cmd,
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=180,
                env=dict(os.environ),
            )
            if res.returncode != 0:
                logger.error(f"Generation failed:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}")
                self.send_response(500)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": "generation_failed",
                    "message": f"Showroom generation failed: {res.stderr or res.stdout}",
                    "details": res.stdout,
                }).encode("utf-8"))
                return
        except subprocess.TimeoutExpired:
            self.send_response(504)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "timeout",
                "message": "Showroom generation timed out after 180 seconds",
            }).encode("utf-8"))
            return
        except Exception as exc:
            logger.error(f"Failed to execute generation script: {exc}")
            self.send_response(500)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "execution_error",
                "message": str(exc),
            }).encode("utf-8"))
            return

        self.send_response(200)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "success": True,
            "message": f"Successfully generated showroom staging for {model_id} in {dealer_id}.",
            "dealer_id": dealer_id,
            "model_id": model_id,
            "showroom_url": f"/api/dealers/{dealer_id}/models/{model_id}/showroom?t={int(time.time())}",
        }).encode("utf-8"))

    def serve_dealer_showroom(self, dealer_id: str, model_id: str, is_head=False):
        """Serves the generated vehicle showroom image from local disk or GCS."""
        # 1. Local disk check
        local_path = DEALERS_DIR / dealer_id / "generated" / f"{model_id}_showroom.png"
        if local_path.is_file():
            size = local_path.stat().st_size
            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(size))
            self.send_header("Cache-Control", "no-cache, must-revalidate")
            self.end_headers()
            if not is_head:
                with open(local_path, "rb") as f:
                    while chunk := f.read(65536):
                        self.wfile.write(chunk)
            return

        # 2. GCS proxy check
        token = auth_manager.get_token()
        gcs_object = f"dealers/{dealer_id}/generated/{model_id}_showroom.png"
        gcs_url = f"https://storage.googleapis.com/storage/v1/b/{DEFAULT_BUCKET}/o/{quote(gcs_object, safe='')}?alt=media"
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        try:
            resp = requests.get(gcs_url, headers=headers, stream=True, timeout=10)
            if resp.status_code == 200:
                self.send_response(200)
                self.send_cors_headers()
                self.send_header("Content-Type", "image/png")
                if "Content-Length" in resp.headers:
                    self.send_header("Content-Length", resp.headers["Content-Length"])
                self.send_header("Cache-Control", "no-cache, must-revalidate")
                self.end_headers()
                if not is_head:
                    for chunk in resp.iter_content(65536):
                        if chunk:
                            self.wfile.write(chunk)
                return
        except Exception as exc:
            logger.warning(f"Failed to fetch showroom image from GCS: {exc}")

        # Missing image -> Return 404 with exact reason required by user specification
        self.send_response(404)
        self.send_cors_headers()
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if not is_head:
            self.wfile.write(json.dumps({
                "error": "image_not_generated",
                "message": "Image is not generated since dealer background is missing",
                "dealer_id": dealer_id,
                "model_id": model_id,
            }).encode("utf-8"))

    def serve_dealer_evaluation(self, dealer_id: str, model_id: str, is_head=False):
        """Serves QA audit result JSON if available."""
        local_path = DEALERS_DIR / dealer_id / "generated" / f"{model_id}_evaluation.json"
        if local_path.is_file():
            with open(local_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            if not is_head:
                self.wfile.write(content.encode("utf-8"))
            return

        self.send_response(404)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if not is_head:
            self.wfile.write(json.dumps({"error": "No evaluation found"}).encode("utf-8"))

    def serve_static_file(self, file_path: Path, is_head=False):
        mime_type, _ = mimetypes.guess_type(str(file_path))
        mime_type = mime_type or "application/octet-stream"
        if mime_type.startswith("text/") or mime_type in ["application/javascript", "application/json"]:
            mime_type += "; charset=utf-8"
        size = file_path.stat().st_size

        self.send_response(200)
        self.send_cors_headers()
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(size))
        self.end_headers()

        if not is_head:
            with open(file_path, "rb") as f:
                while chunk := f.read(65536):
                    self.wfile.write(chunk)


def run():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), PolarisHandler)
    logger.info(f"Polaris API server listening on http://0.0.0.0:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down API server...")
        server.server_close()


if __name__ == "__main__":
    run()
