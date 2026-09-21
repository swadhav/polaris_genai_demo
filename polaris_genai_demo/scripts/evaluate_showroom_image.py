#!/usr/bin/env python3
"""
Autonomous Multimodal QA & Compliance Evaluator for Polaris Dealer Showroom Images.

Uses Gemini 2.5 Flash on Vertex AI to inspect generated showroom images against
reference vehicle specifications and dealer branding, ensuring:
1. Exact vehicle entity preservation (paint, geometry, trim)
2. 100% competitor IP elimination (zero rival OEM logos)
3. Ray-traced floor reflections and photorealistic lighting
4. True 3D architectural dealer signage
"""

import argparse
import base64
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ShowroomEvaluator")

DEFAULT_PROJECT = "polaris-genai-demo"
DEFAULT_LOCATION = "us-central1"
DEFAULT_EVAL_MODEL = "gemini-2.5-flash"


class ShowroomImageEvaluator:
    def __init__(
        self,
        project_id: str = DEFAULT_PROJECT,
        location: str = DEFAULT_LOCATION,
        model_name: str = DEFAULT_EVAL_MODEL,
    ):
        self.project_id = project_id
        self.location = location
        self.model_name = model_name
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

    def evaluate_image(
        self,
        generated_image_path: Path,
        reference_vehicle_path: Path,
        vehicle_title: str,
        vehicle_color: str,
        dealer_name: str,
        vehicle_year: str = "2027",
    ) -> Dict[str, Any]:
        """Evaluates a generated showroom image against official vehicle references."""
        logger.info(f"Auditing showroom image: {generated_image_path.name}")
        logger.info(f"  Reference Vehicle: {vehicle_year} {vehicle_title} ({vehicle_color})")
        logger.info(f"  Dealer: {dealer_name}")

        if not generated_image_path.exists():
            raise FileNotFoundError(f"Generated image not found: {generated_image_path}")
        if not reference_vehicle_path.exists():
            raise FileNotFoundError(f"Reference vehicle not found: {reference_vehicle_path}")

        # Encode images to base64
        with open(generated_image_path, "rb") as f:
            gen_b64 = base64.b64encode(f.read()).decode("utf-8")
        gen_mime = "image/png" if generated_image_path.suffix.lower() == ".png" else "image/jpeg"

        with open(reference_vehicle_path, "rb") as f:
            ref_b64 = base64.b64encode(f.read()).decode("utf-8")
        ref_mime = "image/png" if reference_vehicle_path.suffix.lower() == ".png" else "image/jpeg"

        # Build prompt
        try:
            from prompt_templates import build_qa_eval_prompt
            prompt = build_qa_eval_prompt(vehicle_year, vehicle_title, vehicle_color, dealer_name)
        except ImportError:
            from scripts.prompt_templates import build_qa_eval_prompt
            prompt = build_qa_eval_prompt(vehicle_year, vehicle_title, vehicle_color, dealer_name)

        token = self.get_token()
        url = (
            f"https://{self.location}-aiplatform.googleapis.com/v1/"
            f"projects/{self.project_id}/locations/{self.location}/"
            f"publishers/google/models/{self.model_name}:generateContent"
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
                    {"inlineData": {"mimeType": gen_mime, "data": gen_b64}},
                    {"inlineData": {"mimeType": ref_mime, "data": ref_b64}},
                ],
            }],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2,
            },
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            logger.error(f"Evaluation API failed ({resp.status_code}): {resp.text}")
            raise RuntimeError(f"Gemini API error: {resp.status_code} - {resp.text}")

        res_json = resp.json()
        raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"]
        result = json.loads(raw_text)

        # Log audit summary
        logger.info(f"=== QA AUDIT REPORT: {generated_image_path.name} ===")
        logger.info(f"  Total Score: {result.get('total_score', 0)}/100 | Passed: {result.get('passed', False)}")
        logger.info(f"  Competitor IP Detected: {result.get('competitor_ip_detected', False)}")
        if result.get("competitor_ip_detected"):
            logger.warning(f"  Rival IP Flagged: {result.get('competitor_ip_details')}")
        logger.info(f"  Vehicle Entity: {result.get('vehicle_entity_score', 0)}/35 - {result.get('vehicle_entity_notes')}")
        logger.info(f"  Photorealism: {result.get('photorealism_score', 0)}/25 - {result.get('photorealism_notes')}")
        logger.info(f"  Dealer 3D Signage: {result.get('dealer_branding_score', 0)}/15 - {result.get('dealer_branding_notes')}")
        if result.get("recommendations"):
            logger.info(f"  Recommendations: {result.get('recommendations')}")

        return result


def main():
    parser = argparse.ArgumentParser(description="Audits generated dealer showroom marketing images.")
    parser.add_argument("--image", required=True, help="Path to generated showroom image")
    parser.add_argument("--ref-image", required=True, help="Path to reference vehicle render (cgi-3qFrontLeft)")
    parser.add_argument("--model-title", required=True, help="Vehicle title (e.g. 'XPEDITION XP Crew NorthStar')")
    parser.add_argument("--model-color", required=True, help="Vehicle color (e.g. 'Matte Mocha')")
    parser.add_argument("--dealer-name", required=True, help="Dealer name (e.g. 'Power Lodge')")
    parser.add_argument("--output-json", help="Path to save evaluation JSON result")

    args = parser.parse_args()
    evaluator = ShowroomImageEvaluator()
    res = evaluator.evaluate_image(
        generated_image_path=Path(args.image),
        reference_vehicle_path=Path(args.ref_image),
        vehicle_title=args.model_title,
        vehicle_color=args.model_color,
        dealer_name=args.dealer_name,
    )

    if args.output_json:
        out_p = Path(args.output_json)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w") as f:
            json.dump(res, f, indent=2)
        logger.info(f"Saved evaluation report to {out_p}")

    sys.exit(0 if res.get("passed", False) else 1)


if __name__ == "__main__":
    main()
