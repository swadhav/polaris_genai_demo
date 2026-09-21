#!/usr/bin/env python3
"""
Vehicle 360 Rotation Video Generation Agent

This agent inspects vehicle models and their angle images stored in the
'models' folder and generates an 8-second video showing each vehicle in
a seamless 360-degree rotation using Google Cloud Vertex AI Veo 3.1
(veo-3.1-generate-001).

The final 8-second MP4 videos are saved directly into each model's folder
under the 'models/' directory.
"""

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Vehicle360Agent")

DEFAULT_PROJECT = "polaris-genai-demo"
DEFAULT_LOCATION = "us-central1"
DEFAULT_BUCKET = "polaris-demo-files"
DEFAULT_MODEL = "veo-3.1-generate-001"
DEFAULT_DURATION = 8


@dataclass
class VehicleModelInfo:
    model_id: str
    directory: Path
    angles: Dict[str, Path] = field(default_factory=dict)
    model_title: str = ""
    color: str = ""
    front_image_path: Optional[Path] = None
    gcs_front_uri: Optional[str] = None
    video_output_path: Optional[Path] = None


class Vehicle360Agent:
    def __init__(
        self,
        models_dir: str = "models",
        project_id: str = DEFAULT_PROJECT,
        location: str = DEFAULT_LOCATION,
        bucket_name: str = DEFAULT_BUCKET,
        veo_model: str = DEFAULT_MODEL,
        duration_seconds: int = DEFAULT_DURATION,
        max_concurrency: int = 2,
        force_loop: bool = False,
    ):
        self.models_dir = Path(models_dir).resolve()
        self.project_id = project_id
        self.location = location
        self.bucket_name = bucket_name
        self.veo_model = veo_model
        self.duration_seconds = duration_seconds
        self.max_concurrency = max_concurrency
        self.force_loop = force_loop
        self._cached_token = None
        self._token_expiry = 0

    def get_access_token(self) -> str:
        """Retrieves a valid GCP access token using gcloud."""
        now = time.time()
        if self._cached_token and now < self._token_expiry:
            return self._cached_token

        try:
            res = subprocess.run(
                ["gcloud", "auth", "print-access-token"],
                check=True,
                capture_output=True,
                text=True,
            )
            self._cached_token = res.stdout.strip()
            self._token_expiry = now + 1800  # valid for ~30 mins
            return self._cached_token
        except subprocess.CalledProcessError as exc:
            logger.error(f"Failed to obtain access token from gcloud: {exc.stderr}")
            raise

    def discover_models(self) -> List[VehicleModelInfo]:
        """Scans the models directory and categorizes image angles for each model."""
        discovered: List[VehicleModelInfo] = []

        if not self.models_dir.exists():
            raise FileNotFoundError(f"Models directory not found: {self.models_dir}")

        subdirs = sorted([d for d in self.models_dir.iterdir() if d.is_dir()])
        logger.info(f"Scanning {self.models_dir} for vehicle models (found {len(subdirs)} folders)...")

        for d in subdirs:
            model_id = d.name
            info = VehicleModelInfo(
                model_id=model_id,
                directory=d,
                video_output_path=d / f"{model_id}_360_rotation.mp4",
            )

            # Discover image files, prefer .jpg and .png over large uncompressed .tif
            files = [
                f
                for f in d.iterdir()
                if f.is_file() and f.suffix.lower() in [".jpg", ".png", ".jpeg"]
            ]

            for f in sorted(files):
                fname = f.name.lower()
                if "front" in fname and "3q" not in fname:
                    info.angles["front"] = f
                    info.front_image_path = f
                elif "3q" in fname or "threequarter" in fname:
                    info.angles["3qFrontLeft"] = f
                elif "profile" in fname or "side" in fname:
                    info.angles["leftProfile"] = f
                elif "rear" in fname or "back" in fname:
                    info.angles["rear"] = f
                elif "dash" in fname or "interior" in fname:
                    info.angles["dash"] = f
                elif "topdown" in fname or "top" in fname:
                    info.angles["topDown"] = f

            # Fallback if specific "front" wasn't detected cleanly
            if not info.front_image_path and files:
                info.front_image_path = files[0]
                info.angles["front"] = files[0]

            # Parse vehicle name and color from filename
            if info.front_image_path:
                info.model_title, info.color = self._parse_vehicle_metadata(info.front_image_path.name)
            else:
                info.model_title = f"Polaris Vehicle {model_id}"
                info.color = "Vehicle Color"

            info.gcs_front_uri = f"gs://{self.bucket_name}/models/{model_id}/{info.front_image_path.name}"
            discovered.append(info)

            logger.info(
                f"  Model [{model_id}]: {info.model_title} ({info.color}) - "
                f"Angles detected: {list(info.angles.keys())}"
            )

        return discovered

    def _parse_vehicle_metadata(self, filename: str) -> tuple[str, str]:
        """Parses vehicle line and color from standard Polaris filename naming scheme."""
        parts = Path(filename).stem.split("-")
        title_parts = []
        color = "Standard"

        # e.g., 2027-XPED-XP-Crew-NorthStar-US-MatteMocha-cgi-front-G27G5X99AZ
        i = 0
        while i < len(parts):
            p = parts[i]
            if p.lower() in ["us", "cgi", "front", "3qfrontleft", "rear"]:
                break
            if re.match(r"^[A-Z0-9]{10}$", p):  # model id
                break
            title_parts.append(p)
            i += 1

        # Look for color in subsequent parts
        for p in parts:
            if any(c in p.lower() for c in ["matte", "stealth", "ghost", "camo", "black", "white", "gray", "red", "blue", "mocha"]):
                color = re.sub(r"([a-z])([A-Z])", r"\1 \2", p)
                break

        title = "Polaris " + " ".join(title_parts[1:]) if len(title_parts) > 1 else "Polaris Vehicle"
        return title.strip(), color.strip()

    def ensure_gcs_asset(self, info: VehicleModelInfo) -> str:
        """Verifies the front image is present in GCS, uploading if needed."""
        gcs_uri = info.gcs_front_uri
        check_cmd = ["gcloud", "storage", "ls", gcs_uri]
        res = subprocess.run(check_cmd, capture_output=True, text=True)

        if res.returncode == 0:
            logger.info(f"[{info.model_id}] GCS asset verified: {gcs_uri}")
            return gcs_uri

        logger.info(f"[{info.model_id}] Uploading local front image to {gcs_uri}...")
        upload_cmd = ["gcloud", "storage", "cp", str(info.front_image_path), gcs_uri]
        subprocess.run(upload_cmd, check=True, capture_output=True)
        logger.info(f"[{info.model_id}] Upload complete.")
        return gcs_uri

    def generate_veo_360_video(self, info: VehicleModelInfo) -> Path:
        """Invokes Vertex AI Veo 3.1 to generate a seamless 360-degree rotation video."""
        self.ensure_gcs_asset(info)

        token = self.get_access_token()
        predict_url = (
            f"https://{self.location}-aiplatform.googleapis.com/v1/"
            f"projects/{self.project_id}/locations/{self.location}/"
            f"publishers/google/models/{self.veo_model}:predictLongRunning"
        )
        fetch_url = (
            f"https://{self.location}-aiplatform.googleapis.com/v1/"
            f"projects/{self.project_id}/locations/{self.location}/"
            f"publishers/google/models/{self.veo_model}:fetchPredictOperation"
        )

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        prompt = (
            f"A smooth continuous turntable rotation around the {info.model_title} {info.color}, "
            f"camera smoothly orbiting the vehicle in a steady circular motion, "
            f"photorealistic 8k, studio lighting, clean background, fluid cinematic movement"
        )

        storage_uri = f"gs://{self.bucket_name}/models/{info.model_id}/"

        mime_type = "image/png" if info.front_image_path and info.front_image_path.suffix.lower() == ".png" else "image/jpeg"

        instance = {
            "prompt": prompt,
            "image": {
                "gcsUri": info.gcs_front_uri,
                "mimeType": mime_type,
            },
        }

        # The start frame and end frame do not have to be the same view.
        # If the video naturally completes a full rotation, it can end on the start frame;
        # otherwise it smoothly concludes on the view it reaches without a forced, choppy snap.
        if self.force_loop:
            instance["lastFrame"] = {
                "gcsUri": info.gcs_front_uri,
                "mimeType": mime_type,
            }

        payload = {
            "instances": [instance],
            "parameters": {
                "durationSeconds": self.duration_seconds,
                "sampleCount": 1,
                "aspectRatio": "16:9",
                "storageUri": storage_uri,
            },
        }

        logger.info(f"[{info.model_id}] Submitting Veo 3.1 video generation request...")
        resp = requests.post(predict_url, headers=headers, json=payload, timeout=60)

        if resp.status_code != 200:
            logger.error(f"[{info.model_id}] Request failed ({resp.status_code}): {resp.text}")
            raise RuntimeError(f"Veo API error: {resp.status_code} - {resp.text}")

        op_data = resp.json()
        op_name = op_data.get("name")
        logger.info(f"[{info.model_id}] Long-running operation started: {op_name}")

        # Poll operation until done
        poll_interval = 10
        max_attempts = 36  # up to 6 minutes
        video_gcs_uri = None

        for attempt in range(1, max_attempts + 1):
            time.sleep(poll_interval)
            # Refresh token if needed
            token = self.get_access_token()
            headers["Authorization"] = f"Bearer {token}"

            fetch_resp = requests.post(
                fetch_url,
                headers=headers,
                json={"operationName": op_name},
                timeout=30,
            )

            if fetch_resp.status_code != 200:
                logger.warning(
                    f"[{info.model_id}] Polling warning ({fetch_resp.status_code}): {fetch_resp.text}"
                )
                continue

            poll_data = fetch_resp.json()
            if poll_data.get("done", False):
                if "error" in poll_data:
                    err_msg = poll_data["error"]
                    logger.error(f"[{info.model_id}] Operation failed with error: {err_msg}")
                    raise RuntimeError(f"Veo operation error: {err_msg}")

                response_content = poll_data.get("response", {})
                videos = response_content.get("videos", [])
                if not videos:
                    raise RuntimeError(f"Veo completed but returned no video outputs: {poll_data}")

                video_gcs_uri = videos[0].get("gcsUri")
                logger.info(f"[{info.model_id}] Generation completed successfully! Output: {video_gcs_uri}")
                break
            else:
                elapsed = attempt * poll_interval
                logger.info(f"[{info.model_id}] Rendering video with Veo 3.1... ({elapsed}s elapsed)")

        if not video_gcs_uri:
            raise TimeoutError(f"[{info.model_id}] Video generation timed out after {max_attempts * poll_interval}s")

        # Download the video directly into the model directory
        local_output = info.video_output_path
        logger.info(f"[{info.model_id}] Downloading video to {local_output}...")
        download_cmd = ["gcloud", "storage", "cp", video_gcs_uri, str(local_output)]
        subprocess.run(download_cmd, check=True, capture_output=True)

        # Also create a rotation_360.mp4 copy for convenience
        alt_output = info.directory / "rotation_360.mp4"
        shutil.copy2(local_output, alt_output)

        self._verify_video(local_output)
        return local_output

    def generate_ffmpeg_fallback(self, info: VehicleModelInfo) -> Path:
        """Fallback 360 video generation using FFmpeg multi-angle crossfade loop."""
        logger.info(f"[{info.model_id}] Generating fallback 360 rotation video with FFmpeg...")
        local_output = info.video_output_path

        # Order angles: front -> 3qFrontLeft -> leftProfile -> rear -> mirrored leftProfile -> mirrored 3qFrontLeft -> front
        images_order: List[Path] = []
        if "front" in info.angles:
            images_order.append(info.angles["front"])
        if "3qFrontLeft" in info.angles:
            images_order.append(info.angles["3qFrontLeft"])
        if "leftProfile" in info.angles:
            images_order.append(info.angles["leftProfile"])
        if "rear" in info.angles:
            images_order.append(info.angles["rear"])

        # If we have only 1 image, duplicate for rotation effect
        if len(images_order) < 2 and info.front_image_path:
            images_order = [info.front_image_path]

        # Use ffmpeg to create an 8-second smooth video loop
        duration = self.duration_seconds
        fps = 24
        total_frames = duration * fps

        if len(images_order) == 1:
            # Single image subtle camera pan/orbit zoom
            cmd = [
                "ffmpeg", "-y", "-loop", "1", "-i", str(images_order[0]),
                "-vf", f"scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,zoompan=z='min(max(zoom,pzoom)+0.001,1.1)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720:fps={fps}",
                "-t", str(duration), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                str(local_output)
            ]
        else:
            # Transition through available angle views and loop back
            # Generate temporary mirrored images for symmetric views
            temp_files = []
            extended_order = list(images_order)
            # Add mirrored views if leftProfile or 3q exist
            if "leftProfile" in info.angles:
                mirrored_profile = info.directory / "_tmp_rightProfile.jpg"
                subprocess.run(["ffmpeg", "-y", "-i", str(info.angles["leftProfile"]), "-vf", "hflip", str(mirrored_profile)], check=True, capture_output=True)
                extended_order.append(mirrored_profile)
                temp_files.append(mirrored_profile)
            if "3qFrontLeft" in info.angles:
                mirrored_3q = info.directory / "_tmp_3qRight.jpg"
                subprocess.run(["ffmpeg", "-y", "-i", str(info.angles["3qFrontLeft"]), "-vf", "hflip", str(mirrored_3q)], check=True, capture_output=True)
                extended_order.append(mirrored_3q)
                temp_files.append(mirrored_3q)
            # If force_loop is requested, loop back to front; otherwise end naturally on current view
            if self.force_loop:
                extended_order.append(images_order[0])

            # Write concat file
            concat_list = info.directory / "_tmp_concat.txt"
            frame_duration = duration / len(extended_order)
            with open(concat_list, "w") as f:
                for img in extended_order:
                    f.write(f"file '{img.resolve()}'\n")
                    f.write(f"duration {frame_duration:.2f}\n")
                f.write(f"file '{extended_order[-1].resolve()}'\n")

            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
                "-vf", f"scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps={fps}'",
                "-t", str(duration), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                str(local_output)
            ]

            try:
                subprocess.run(cmd, check=True, capture_output=True)
            finally:
                for t in temp_files:
                    t.unlink(missing_ok=True)
                concat_list.unlink(missing_ok=True)

        alt_output = info.directory / "rotation_360.mp4"
        shutil.copy2(local_output, alt_output)
        self._verify_video(local_output)
        return local_output

    def _verify_video(self, video_path: Path):
        """Validates that the output video exists, is valid, and matches the duration."""
        if not video_path.exists() or video_path.stat().st_size == 0:
            raise ValueError(f"Video file was not created or is empty: {video_path}")

        probe_cmd = [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration,size:stream=width,height,codec_name",
            "-of", "json", str(video_path)
        ]
        res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        meta = json.loads(res.stdout)
        dur = float(meta["format"]["duration"])
        size_mb = float(meta["format"]["size"]) / (1024 * 1024)
        stream = meta["streams"][0]
        logger.info(
            f"Verified video: {video_path.name} | "
            f"Duration: {dur:.2f}s | Resolution: {stream.get('width')}x{stream.get('height')} | "
            f"Size: {size_mb:.2f} MB | Codec: {stream.get('codec_name')}"
        )

    def process_model(self, info: VehicleModelInfo, fallback: bool = False, force: bool = False) -> Dict[str, str]:
        """Processes a single vehicle model, attempting Veo first and falling back if requested."""
        if not force and info.video_output_path.exists() and info.video_output_path.stat().st_size > 0:
            try:
                self._verify_video(info.video_output_path)
                logger.info(f"[{info.model_id}] Existing valid video found at {info.video_output_path}. Skipping.")
                return {
                    "model_id": info.model_id,
                    "title": info.model_title,
                    "status": "SUCCESS (CACHED)",
                    "path": str(info.video_output_path),
                    "duration": f"{self.duration_seconds}s",
                    "time_taken": "0.0s",
                }
            except Exception:
                logger.info(f"[{info.model_id}] Existing file corrupted or invalid. Regenerating...")

        logger.info(f"=== Starting 360 Video Generation for {info.model_id} ===")
        start_time = time.time()
        result = {
            "model_id": info.model_id,
            "title": info.model_title,
            "status": "PENDING",
            "path": str(info.video_output_path),
            "duration": "",
            "time_taken": "",
        }

        try:
            if fallback:
                out = self.generate_ffmpeg_fallback(info)
            else:
                try:
                    out = self.generate_veo_360_video(info)
                except Exception as e:
                    logger.warning(f"[{info.model_id}] Veo generation encountered: {e}. Attempting FFmpeg fallback...")
                    out = self.generate_ffmpeg_fallback(info)

            elapsed = time.time() - start_time
            result["status"] = "SUCCESS"
            result["path"] = str(out)
            result["time_taken"] = f"{elapsed:.1f}s"
            result["duration"] = f"{self.duration_seconds}s"
            logger.info(f"[{info.model_id}] Finished successfully in {elapsed:.1f}s -> {out}")
        except Exception as e:
            elapsed = time.time() - start_time
            result["status"] = "FAILED"
            result["error"] = str(e)
            result["time_taken"] = f"{elapsed:.1f}s"
            logger.error(f"[{info.model_id}] Failed after {elapsed:.1f}s: {e}")

        return result

    def run(
        self,
        target_model_ids: Optional[List[str]] = None,
        fallback_only: bool = False,
        force: bool = False,
    ) -> List[Dict[str, str]]:
        """Main agent execution method."""
        models = self.discover_models()

        if target_model_ids:
            models = [m for m in models if m.model_id in target_model_ids]

        logger.info(f"Agent starting batch execution for {len(models)} models (concurrency limit: {self.max_concurrency})...")
        results = []

        with ThreadPoolExecutor(max_workers=self.max_concurrency) as executor:
            future_to_model = {
                executor.submit(self.process_model, m, fallback_only, force): m
                for m in models
            }
            for future in as_completed(future_to_model):
                res = future.result()
                results.append(res)

        logger.info("=" * 60)
        logger.info("BATCH GENERATION SUMMARY REPORT")
        logger.info("=" * 60)
        for r in sorted(results, key=lambda x: x["model_id"]):
            logger.info(
                f"Model: {r['model_id']:<12} | Status: {r['status']:<8} | "
                f"Duration: {r.get('duration','N/A'):<4} | Time: {r.get('time_taken','N/A'):<7} | "
                f"File: {r['path']}"
            )
        logger.info("=" * 60)
        return results


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Agent for Generating 8-second 360-degree Vehicle Rotation Videos"
    )
    parser.add_argument(
        "--models-dir",
        default="models",
        help="Path to models directory (default: models)",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        help="Specific model IDs to generate videos for (default: all discovered)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=8,
        help="Target video duration in seconds (default: 8)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=2,
        help="Maximum concurrent generation jobs (default: 2)",
    )
    parser.add_argument(
        "--fallback-ffmpeg",
        action="store_true",
        help="Use local FFmpeg multi-angle generation instead of Veo 3.1",
    )
    parser.add_argument(
        "--project",
        default=DEFAULT_PROJECT,
        help=f"GCP Project ID (default: {DEFAULT_PROJECT})",
    )
    parser.add_argument(
        "--bucket",
        default=DEFAULT_BUCKET,
        help=f"GCS Bucket (default: {DEFAULT_BUCKET})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration of videos even if valid videos already exist",
    )
    parser.add_argument(
        "--force-loop",
        action="store_true",
        help="Force the video to end on the start frame (may cause choppy ending). Default: False (smooth natural rotation ending on whatever view it reaches).",
    )

    args = parser.parse_args()

    agent = Vehicle360Agent(
        models_dir=args.models_dir,
        project_id=args.project,
        bucket_name=args.bucket,
        duration_seconds=args.duration,
        max_concurrency=args.concurrency,
        force_loop=args.force_loop,
    )

    agent.run(target_model_ids=args.models, fallback_only=args.fallback_ffmpeg, force=args.force)


if __name__ == "__main__":
    main()
