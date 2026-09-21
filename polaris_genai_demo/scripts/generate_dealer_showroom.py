#!/usr/bin/env python3
"""
Polaris Dealer Showroom Image Generation Agent using Google Nano Banana Models.

Transforms dealer showroom environments into photorealistic marketing showcases:
1. Inpaints and removes competitor OEM branding (Honda, Yamaha, Kawasaki, etc.) and clutter
2. Inserts Polaris vehicle models from dynamic 3/4 perspective with ray-traced floor reflections
3. Integrates dealer branding as photorealistic 3D architectural signage
4. Enforces cardinality: Exactly ONE hero image per model per dealer showroom
5. Evaluates output with autonomous multimodal QA (Gemini 2.5 Flash)

Note on repository assets:
Only dealers possessing a valid background image in the repository (e.g. Power Lodge)
are processed. Other dealers are skipped until their background image is added.
"""

import argparse
import base64
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
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from PIL import Image

# Import prompt templates & QA evaluator
try:
    from prompt_templates import (
        build_clean_plate_prompt,
        build_nano_banana_composite_prompt,
    )
    from evaluate_showroom_image import ShowroomImageEvaluator
except ImportError:
    from scripts.prompt_templates import (
        build_clean_plate_prompt,
        build_nano_banana_composite_prompt,
    )
    from scripts.evaluate_showroom_image import ShowroomImageEvaluator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("DealerShowroomAgent")

DEFAULT_PROJECT = "polaris-genai-demo"
DEFAULT_LOCATION = "us-central1"
NANO_BANANA_MODEL = "gemini-2.5-flash-image"

# Catalog metadata for Polaris vehicles
MODEL_METADATA_FALLBACKS = {
    "G27G5X99AZ": {
        "title": "XPEDITION XP Crew NorthStar",
        "segment": "Crossover SxS",
        "color": "Matte Mocha",
        "year": "2027",
    },
    "G27GXK99AD": {
        "title": "GENERAL XP 1000 Ultimate",
        "segment": "Crossover SxS",
        "color": "Ghost White",
        "year": "2027",
    },
    "R27CCA5AE8": {
        "title": "RANGER 500 Tractor",
        "segment": "Utility SxS",
        "color": "Stealth Gray",
        "year": "2027",
    },
    "R27X6W1RB9": {
        "title": "RANGER XD 1500 Crew NorthStar Ultimate",
        "segment": "Heavy Duty Utility",
        "color": "Polaris Pursuit Camo",
        "year": "2027",
    },
    "Z27XPE92AH": {
        "title": "RZR Pro XP Sport",
        "segment": "Performance Sport SxS",
        "color": "Matte Granite Gray",
        "year": "2027",
    },
}


@dataclass
class DealerInfo:
    dealer_id: str
    directory: Path
    display_name: str
    logo_path: Optional[Path] = None
    background_path: Optional[Path] = None
    has_background: bool = False
    clean_plate_path: Optional[Path] = None
    output_dir: Path = field(init=False)

    def __post_init__(self):
        self.output_dir = self.directory / "generated"


@dataclass
class VehicleInfo:
    model_id: str
    directory: Path
    model_title: str
    color: str
    year: str
    segment: str
    hero_3q_path: Optional[Path] = None
    profile_path: Optional[Path] = None
    front_path: Optional[Path] = None


class DealerShowroomAgent:
    def __init__(
        self,
        project_root: Optional[Path] = None,
        project_id: str = DEFAULT_PROJECT,
        location: str = DEFAULT_LOCATION,
        nano_banana_model: str = NANO_BANANA_MODEL,
        max_concurrency: int = 2,
    ):
        self.project_root = project_root or Path(__file__).resolve().parent.parent
        self.dealers_dir = self.project_root / "dealers"
        self.models_dir = self.project_root / "models"
        self.project_id = project_id
        self.location = location
        self.nano_banana_model = nano_banana_model
        self.max_concurrency = max_concurrency
        self.evaluator = ShowroomImageEvaluator(
            project_id=project_id,
            location=location,
        )
        self._cached_token = None
        self._token_expiry = 0

    def get_token(self) -> str:
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
            self._token_expiry = now + 1800
            return self._cached_token
        except subprocess.CalledProcessError as exc:
            logger.error(f"Failed to obtain GCP access token: {exc.stderr}")
            raise

    # -------------------------------------------------------------------------
    # Discovery Engine (Scales from 5 up to 300+ Dealers)
    # -------------------------------------------------------------------------
    def discover_dealers(self) -> Dict[str, DealerInfo]:
        """Scans the dealers directory and categorizes each dealer's assets."""
        dealers: Dict[str, DealerInfo] = {}
        if not self.dealers_dir.exists():
            logger.warning(f"Dealers directory not found: {self.dealers_dir}")
            return dealers

        for d in sorted(self.dealers_dir.iterdir()):
            if not d.is_dir() or d.name.startswith("."):
                continue

            dealer_id = d.name
            display_name = dealer_id.replace("_", " ").title()

            logo_path = None
            background_path = None

            for f in sorted(d.iterdir()):
                if not f.is_file():
                    continue
                fname = f.name.lower()
                if "logo" in fname and f.suffix.lower() in [".png", ".jpg", ".jpeg", ".svg"]:
                    logo_path = f
                elif "background" in fname and f.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                    background_path = f

            clean_plate = d / "clean_showroom_plate.png"
            dealers[dealer_id] = DealerInfo(
                dealer_id=dealer_id,
                directory=d,
                display_name=display_name,
                logo_path=logo_path,
                background_path=background_path,
                has_background=(background_path is not None),
                clean_plate_path=clean_plate if clean_plate.exists() else None,
            )

        logger.info(f"Discovered {len(dealers)} dealer directories.")
        eligible = [k for k, v in dealers.items() if v.has_background]
        skipped = [k for k, v in dealers.items() if not v.has_background]
        logger.info(f"  -> Eligible dealers (background present): {eligible}")
        logger.info(f"  -> Skipped dealers (awaiting background upload): {skipped}")
        return dealers

    def discover_models(self) -> Dict[str, VehicleInfo]:
        """Scans the models directory and categorizes angle renders and metadata."""
        models: Dict[str, VehicleInfo] = {}
        if not self.models_dir.exists():
            logger.warning(f"Models directory not found: {self.models_dir}")
            return models

        for d in sorted(self.models_dir.iterdir()):
            if not d.is_dir() or d.name.startswith("."):
                continue

            model_id = d.name
            meta = MODEL_METADATA_FALLBACKS.get(model_id, {
                "title": f"Polaris {model_id}",
                "color": "Standard",
                "year": "2027",
                "segment": "Off-Road Vehicle",
            })

            hero_3q = None
            profile = None
            front = None

            for f in sorted(d.iterdir()):
                if not f.is_file() or f.suffix.lower() not in [".jpg", ".png", ".jpeg"]:
                    continue
                fname = f.name.lower()
                if ("3q" in fname or "threequarter" in fname) and not hero_3q:
                    hero_3q = f
                elif ("profile" in fname or "side" in fname) and not profile:
                    profile = f
                elif "front" in fname and "3q" not in fname and not front:
                    front = f

            # Fallback to profile or front if 3Q not present
            if not hero_3q:
                hero_3q = profile or front

            models[model_id] = VehicleInfo(
                model_id=model_id,
                directory=d,
                model_title=meta["title"],
                color=meta["color"],
                year=meta["year"],
                segment=meta["segment"],
                hero_3q_path=hero_3q,
                profile_path=profile,
                front_path=front,
            )

        logger.info(f"Discovered {len(models)} vehicle models.")
        for mid, m in models.items():
            logger.info(f"  -> [{mid}] {m.year} {m.model_title} ({m.color}) | Hero Angle: {m.hero_3q_path.name if m.hero_3q_path else 'None'}")
        return models

    # -------------------------------------------------------------------------
    # Helper: Image Optimization & Base64 Encoding
    # -------------------------------------------------------------------------
    def _encode_image_b64(self, image_path: Path, max_dimension: int = 1920) -> Tuple[str, str]:
        """Resizes image if larger than max_dimension and returns base64 data and mime."""
        mime_type = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
        with Image.open(image_path) as im:
            # Downscale proportionally if needed to avoid massive API payloads
            w, h = im.size
            if max(w, h) > max_dimension:
                scale = max_dimension / float(max(w, h))
                new_size = (int(w * scale), int(h * scale))
                im = im.resize(new_size, Image.Resampling.LANCZOS)
            
            buf = BytesIO()
            fmt = "PNG" if mime_type == "image/png" else "JPEG"
            im.save(buf, format=fmt, quality=95)
            b64_data = base64.b64encode(buf.getvalue()).decode("utf-8")
            return b64_data, mime_type

    # -------------------------------------------------------------------------
    # Stage 1: Clean Architectural Background Inpainting (Nano Banana)
    # -------------------------------------------------------------------------
    def get_or_generate_clean_plate(self, dealer: DealerInfo, force_clean: bool = False) -> Path:
        """Generates a clean architectural showroom plate stripped of competitor IP."""
        target_path = dealer.directory / "clean_showroom_plate.png"
        if target_path.exists() and not force_clean:
            logger.info(f"[{dealer.dealer_id}] Using existing clean plate: {target_path.name}")
            dealer.clean_plate_path = target_path
            return target_path

        if not dealer.background_path or not dealer.background_path.exists():
            raise ValueError(f"Dealer '{dealer.dealer_id}' has no background photo to clean.")

        logger.info(f"[{dealer.dealer_id}] Generating clean architectural plate using Nano Banana...")
        prompt = build_clean_plate_prompt(dealer.display_name)
        bg_b64, bg_mime = self._encode_image_b64(dealer.background_path)

        token = self.get_token()
        url = (
            f"https://{self.location}-aiplatform.googleapis.com/v1/"
            f"projects/{self.project_id}/locations/{self.location}/"
            f"publishers/google/models/{self.nano_banana_model}:generateContent"
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": self.project_id,
        }
        payload = {
            "contents": [{
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {"inlineData": {"mimeType": bg_mime, "data": bg_b64}},
                ],
            }],
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            logger.error(f"[{dealer.dealer_id}] Nano Banana inpainting failed ({resp.status_code}): {resp.text}")
            raise RuntimeError(f"Nano Banana API error: {resp.status_code} - {resp.text}")

        res_json = resp.json()
        parts = res_json.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        image_bytes = None
        for p in parts:
            if "inlineData" in p:
                image_bytes = base64.b64decode(p["inlineData"]["data"])
                break

        if not image_bytes:
            raise RuntimeError(f"Nano Banana completed without returning image data: {res_json}")

        with open(target_path, "wb") as f:
            f.write(image_bytes)

        logger.info(f"[{dealer.dealer_id}] Clean architectural plate saved: {target_path} ({len(image_bytes)} bytes)")
        dealer.clean_plate_path = target_path
        return target_path

    # -------------------------------------------------------------------------
    # Stage 2: Vehicle Insertion, 3D Signage & Ray-Traced Reflections (Nano Banana)
    # -------------------------------------------------------------------------
    def generate_single_hero_image(
        self,
        dealer: DealerInfo,
        vehicle: VehicleInfo,
        force_clean: bool = False,
        skip_qa: bool = False,
        overwrite: bool = False,
    ) -> Optional[Path]:
        """
        Generates exactly ONE hero showroom image for a given vehicle model and dealer.
        Preserves vehicle entity, renders 3D dealer signage, and synthesizes floor reflections.
        """
        # Enforce requirement: Skip dealers without a background image
        if not dealer.has_background:
            logger.warning(
                f"[SKIP] Dealer '{dealer.dealer_id}' has no background image in repository. "
                f"Skipping until background image is added."
            )
            return None

        dealer.output_dir.mkdir(parents=True, exist_ok=True)
        output_image_path = dealer.output_dir / f"{vehicle.model_id}_showroom.png"
        output_eval_path = dealer.output_dir / f"{vehicle.model_id}_evaluation.json"

        if output_image_path.exists() and not overwrite:
            logger.info(
                f"[{dealer.dealer_id}] Hero image already exists: {output_image_path.name}. "
                f"Skipping (use --overwrite to regenerate)."
            )
            return output_image_path

        # 1. Obtain or generate clean background plate
        clean_plate_path = self.get_or_generate_clean_plate(dealer, force_clean=force_clean)

        # 2. Verify inputs
        if not vehicle.hero_3q_path or not vehicle.hero_3q_path.exists():
            raise FileNotFoundError(f"Model {vehicle.model_id} has no valid hero angle image.")
        if not dealer.logo_path or not dealer.logo_path.exists():
            raise FileNotFoundError(f"Dealer {dealer.dealer_id} has no valid logo file.")

        logger.info(
            f"Staging vehicle [{vehicle.model_id}] {vehicle.year} {vehicle.model_title} "
            f"in {dealer.display_name} showroom..."
        )

        # 3. Prepare multi-reference images
        plate_b64, plate_mime = self._encode_image_b64(clean_plate_path)
        veh_b64, veh_mime = self._encode_image_b64(vehicle.hero_3q_path)
        logo_b64, logo_mime = self._encode_image_b64(dealer.logo_path)

        # 4. Build prompt
        prompt = build_nano_banana_composite_prompt(
            vehicle_year=vehicle.year,
            vehicle_title=vehicle.model_title,
            vehicle_color=vehicle.color,
            vehicle_segment=vehicle.segment,
            dealer_name=dealer.display_name,
        )

        # 5. Call Nano Banana
        token = self.get_token()
        url = (
            f"https://{self.location}-aiplatform.googleapis.com/v1/"
            f"projects/{self.project_id}/locations/{self.location}/"
            f"publishers/google/models/{self.nano_banana_model}:generateContent"
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": self.project_id,
        }
        payload = {
            "contents": [{
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {"inlineData": {"mimeType": plate_mime, "data": plate_b64}},
                    {"inlineData": {"mimeType": veh_mime, "data": veh_b64}},
                    {"inlineData": {"mimeType": logo_mime, "data": logo_b64}},
                ],
            }],
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=90)
        if resp.status_code != 200:
            logger.error(f"[{dealer.dealer_id}][{vehicle.model_id}] Generation failed ({resp.status_code}): {resp.text}")
            raise RuntimeError(f"Nano Banana API error: {resp.status_code} - {resp.text}")

        res_json = resp.json()
        parts = res_json.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        image_bytes = None
        for p in parts:
            if "inlineData" in p:
                image_bytes = base64.b64decode(p["inlineData"]["data"])
                break

        if not image_bytes:
            raise RuntimeError(f"Nano Banana returned no image: {res_json}")

        with open(output_image_path, "wb") as f:
            f.write(image_bytes)
        logger.info(f"[{dealer.dealer_id}] Successfully generated hero image: {output_image_path} ({len(image_bytes)} bytes)")

        # 6. Autonomous Multimodal QA Audit
        if not skip_qa:
            try:
                qa_res = self.evaluator.evaluate_image(
                    generated_image_path=output_image_path,
                    reference_vehicle_path=vehicle.hero_3q_path,
                    vehicle_title=vehicle.model_title,
                    vehicle_color=vehicle.color,
                    dealer_name=dealer.display_name,
                    vehicle_year=vehicle.year,
                )
                with open(output_eval_path, "w") as f:
                    json.dump(qa_res, f, indent=2)
                logger.info(f"[{dealer.dealer_id}] QA Audit saved: {output_eval_path}")
            except Exception as e:
                logger.warning(f"[{dealer.dealer_id}][{vehicle.model_id}] QA Evaluation warning: {e}")

        return output_image_path

    # -------------------------------------------------------------------------
    # Batch Processing & Controller
    # -------------------------------------------------------------------------
    def run_pipeline(
        self,
        dealer_ids: Optional[List[str]] = None,
        model_ids: Optional[List[str]] = None,
        force_clean: bool = False,
        skip_qa: bool = False,
        overwrite: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Runs the showroom generation pipeline for selected or all dealers and models."""
        dealers = self.discover_dealers()
        models = self.discover_models()

        # Filter target dealers
        target_dealers: List[DealerInfo] = []
        if dealer_ids:
            for did in dealer_ids:
                if did in dealers:
                    target_dealers.append(dealers[did])
                else:
                    logger.error(f"Dealer '{did}' not found in {self.dealers_dir}")
        else:
            target_dealers = list(dealers.values())

        # Filter target models
        target_models: List[VehicleInfo] = []
        if model_ids:
            for mid in model_ids:
                if mid in models:
                    target_models.append(models[mid])
                else:
                    logger.error(f"Model '{mid}' not found in {self.models_dir}")
        else:
            target_models = list(models.values())

        logger.info("=== POLARIS DEALER SHOWROOM AGENT EXECUTION PLAN ===")
        logger.info(f"Target Dealers ({len(target_dealers)}): {[d.dealer_id for d in target_dealers]}")
        logger.info(f"Target Models ({len(target_models)}): {[m.model_id for m in target_models]}")

        tasks = []
        skipped_count = 0
        for dealer in target_dealers:
            if not dealer.has_background:
                logger.info(f"  [SKIP] Dealer '{dealer.dealer_id}' has NO background photo. Will NOT generate images.")
                skipped_count += 1
                continue

            for model in target_models:
                tasks.append((dealer, model))
                logger.info(f"  [QUEUE] Dealer '{dealer.dealer_id}' + Model '{model.model_id}' -> 1 Hero Image")

        if dry_run:
            logger.info("Dry run complete. No API calls executed.")
            return {"status": "dry_run_complete", "queued": len(tasks), "skipped": skipped_count}

        if not tasks:
            logger.warning("No eligible dealer-model tasks found. (Check background image availability)")
            return {"status": "no_tasks", "queued": 0, "skipped": skipped_count}

        results = []
        start_time = time.time()

        # Execute generation (sequential or concurrent)
        if self.max_concurrency > 1:
            logger.info(f"Launching batch execution with concurrency={self.max_concurrency}...")
            with ThreadPoolExecutor(max_workers=self.max_concurrency) as executor:
                futures = {
                    executor.submit(
                        self.generate_single_hero_image,
                        d,
                        m,
                        force_clean,
                        skip_qa,
                        overwrite,
                    ): (d.dealer_id, m.model_id)
                    for d, m in tasks
                }
                for f in as_completed(futures):
                    did, mid = futures[f]
                    try:
                        out = f.result()
                        results.append({"dealer": did, "model": mid, "status": "success", "image": str(out)})
                    except Exception as exc:
                        logger.error(f"Failed [{did}][{mid}]: {exc}")
                        results.append({"dealer": did, "model": mid, "status": "error", "error": str(exc)})
        else:
            for dealer, model in tasks:
                try:
                    out = self.generate_single_hero_image(dealer, model, force_clean=force_clean, skip_qa=skip_qa, overwrite=overwrite)
                    results.append({"dealer": dealer.dealer_id, "model": model.model_id, "status": "success", "image": str(out)})
                except Exception as exc:
                    logger.error(f"Failed [{dealer.dealer_id}][{model.model_id}]: {exc}")
                    results.append({"dealer": dealer.dealer_id, "model": model.model_id, "status": "error", "error": str(exc)})

        elapsed = time.time() - start_time
        logger.info(f"=== PIPELINE COMPLETED IN {elapsed:.1f}s ===")
        logger.info(f"Generated: {len([r for r in results if r['status'] == 'success'])} images | Skipped Dealers: {skipped_count}")
        return {"status": "completed", "results": results, "elapsed_seconds": elapsed, "skipped": skipped_count}


def main():
    parser = argparse.ArgumentParser(
        description="Polaris Dealer Showroom Image Generation Agent (Nano Banana)."
    )
    parser.add_argument("--dealer", help="Specific dealer ID (e.g. 'power_lodge')")
    parser.add_argument("--all-dealers", action="store_true", help="Process all dealers in dealers/ folder (up to 300)")
    parser.add_argument("--model", help="Specific vehicle model ID (e.g. 'G27G5X99AZ')")
    parser.add_argument("--all-models", action="store_true", help="Process all models in models/ folder")
    parser.add_argument("--batch", action="store_true", help="Enable multi-threaded batch processing")
    parser.add_argument("--concurrency", type=int, default=2, help="Max concurrency for batch mode (default: 2)")
    parser.add_argument("--force-clean", action="store_true", help="Force regeneration of clean architectural plate")
    parser.add_argument("--overwrite", action="store_true", help="Force overwrite/regeneration of existing hero showroom images")
    parser.add_argument("--skip-qa", action="store_true", help="Skip autonomous multimodal QA evaluation")
    parser.add_argument("--dry-run", action="store_true", help="Inspect and display task queue without running generation")

    args = parser.parse_args()

    dealer_ids = None
    if args.dealer:
        dealer_ids = [args.dealer]
    elif not args.all_dealers:
        # Default to power_lodge if neither specified
        dealer_ids = ["power_lodge"]

    model_ids = None
    if args.model:
        model_ids = [args.model]
    elif not args.all_models:
        # Default to first model if neither specified
        model_ids = ["G27G5X99AZ"]

    agent = DealerShowroomAgent(
        max_concurrency=args.concurrency if args.batch else 1,
    )

    res = agent.run_pipeline(
        dealer_ids=dealer_ids,
        model_ids=model_ids,
        force_clean=args.force_clean,
        skip_qa=args.skip_qa,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )
    if any(r.get("status") == "error" for r in res.get("results", [])):
        logger.error("Showroom generation completed with errors.")
        sys.exit(1)


if __name__ == "__main__":
    main()
