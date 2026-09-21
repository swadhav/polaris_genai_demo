"""
Prompt Templates for Polaris Dealer Showroom Agent with Nano Banana Models.
"""

from typing import Dict, Any


def build_clean_plate_prompt(dealer_name: str) -> str:
    """
    Prompt for Nano Banana (gemini-2.5-flash-image) to inpaint and remove competitor
    OEM banners, parked vehicles, and clutter, generating a pristine showroom floor.
    """
    return f"""[SYSTEM: MASTER ARCHITECTURAL VISUALIZATION & INPAINTING ARTIST]

INPUT: Image 1 is a raw powersports dealership showroom photograph for "{dealer_name}".

MODIFICATION TASKS:
1. REMOVE COMPETITOR BRANDING: Thoroughly inpaint and eliminate all competitor brand logos, banners, signs, and flags (including but not limited to Honda, Yamaha, Kawasaki, Can-Am, BRP, Arctic Cat, Suzuki, KTM).
2. REMOVE CLUTTER & VEHICLES: Remove all existing vehicles parked on the showroom floor, loose equipment, sales racks, and foreground clutter.
3. ARCHITECTURAL PRESERVATION:
   - Reconstruct an empty, pristine vehicle display bay in the center of the showroom floor.
   - Retain authentic architectural elements: exposed ceiling trusses, linear overhead LED/fluorescent light fixtures, wood wall wainscoting, and structural pillars.
   - The showroom floor must be clean, polished, sealed concrete or high-gloss epoxy, displaying subtle specular reflections of the overhead ceiling lights.
4. DO NOT alter the camera angle, perspective, or core room geometry.

OUTPUT: An ultra-clean architectural showroom background plate ready for new vehicle staging, 100% free of competitor IP and clutter."""


def build_nano_banana_composite_prompt(
    vehicle_year: str,
    vehicle_title: str,
    vehicle_color: str,
    vehicle_segment: str,
    dealer_name: str,
) -> str:
    """
    Prompt for Nano Banana (gemini-2.5-flash-image) multi-reference compositing:
    - Image 1: Clean Showroom Plate
    - Image 2: Exact Vehicle Reference (cgi-3qFrontLeft)
    - Image 3: Dealer Logo PNG
    """
    return f"""[SYSTEM: COMMERCIAL AUTOMOTIVE CGI PHOTOGRAPHER & MASTER RETOUCHER]

INPUT IMAGES:
- Image 1: Clean architectural dealer showroom plate.
- Image 2: Exact vehicle reference ({vehicle_year} {vehicle_title} in factory {vehicle_color} finish, {vehicle_segment}).
- Image 3: Official dealer logo for "{dealer_name}".

STAGING & COMPOSITING DIRECTIVES:
1. VEHICLE PLACEMENT:
   - Position the vehicle from Image 2 prominently in the center display bay of the showroom floor in Image 1.
   - Maintain the dynamic 3/4 front perspective matching the showroom floor's perspective and horizon lines.
   - CRITICAL VEHICLE ENTITY PRESERVATION: Preserve exact {vehicle_color} paint finish, exact body panel geometry, factory model decals ('{vehicle_title}'), suspension, knobby off-road tires, and roll cage from Image 2 without alteration, deformation, or generic replacement.

2. RAY-TRACED FLOOR REFLECTIONS & LIGHTING:
   - Synthesize physics-based ray-traced floor reflections of the vehicle's underside, knobby tires, and bodywork onto the polished concrete floor.
   - Cast realistic, soft-diffused ambient occlusion contact shadows directly beneath each tire, grounding the vehicle firmly to the floor.
   - Align vehicle specular highlights with the overhead linear ceiling light fixtures and ambient room illumination.

3. PHOTOREALISTIC 3D ARCHITECTURAL DEALER SIGNAGE:
   - DO NOT place Image 3 as a flat 2D corner watermark or floating overlay.
   - Mount the "{dealer_name}" branding from Image 3 directly ONTO the showroom wooden feature wall as a permanent, dimensional 3D architectural sign.
   - Give the signage realistic physical depth, beveling, brushed metal or acrylic finish, and subtle ambient room lighting interaction with cast shadows on the wall behind it.

CONSTRAINTS:
- Absolute zero competitor IP (no Honda, Yamaha, Kawasaki, Can-Am, etc.).
- Crisp commercial advertising quality (photorealistic, high-resolution).
- Produce exactly ONE final hero showcase image."""


def build_qa_eval_prompt(
    vehicle_year: str,
    vehicle_title: str,
    vehicle_color: str,
    dealer_name: str,
) -> str:
    """
    Prompt for Gemini 2.5 Multimodal QA Evaluator with strict scoring rubric.
    """
    return f"""[SYSTEM: STRICT AUTOMOTIVE ADVERTISING COMPLIANCE & QUALITY AUDITOR]

You are inspecting an AI-generated dealer showroom marketing image (Image 1) against the official reference vehicle render (Image 2).
Reference Vehicle: {vehicle_year} {vehicle_title} in factory {vehicle_color} finish.
Target Dealer: {dealer_name}.

AUDIT CRITERIA & SCORING:
1. VEHICLE ENTITY PRESERVATION (0-35 points):
   - Does paint color precisely match factory {vehicle_color}?
   - Are model decals, trim badges, bodywork, wheels, and roll cage 100% faithful to Image 2 with zero hallucination or incorrect badging?
2. COMPETITOR IP REMOVAL (0-25 points):
   - Check all walls, banners, floor, and reflections for any competitor logo (Honda, Yamaha, Kawasaki, Can-Am, Arctic Cat, Suzuki, KTM, BRP, etc.).
   - ANY competitor IP detected = 0 points and immediate FAIL.
3. PHOTOREALISM & FLOOR REFLECTIONS (0-25 points):
   - Are ray-traced floor reflections geometrically accurate to the vehicle?
   - Are soft ambient occlusion contact shadows present under all tires (no floating vehicle)?
   - Is lighting consistent with overhead ceiling fixtures?
4. DEALER BRANDING INTEGRATION (0-15 points):
   - Is the {dealer_name} logo rendered as realistic 3D architectural signage on the showroom wall (not a flat 2D floating watermark)?

OUTPUT FORMAT:
Return ONLY a valid JSON object matching this schema:
{{
  "total_score": <int 0-100>,
  "passed": <bool, true if total_score >= 85 and not competitor_ip_detected>,
  "competitor_ip_detected": <bool>,
  "competitor_ip_details": "<string describing any competitor logo or empty>",
  "vehicle_entity_score": <int 0-35>,
  "vehicle_entity_notes": "<string>",
  "photorealism_score": <int 0-25>,
  "photorealism_notes": "<string>",
  "dealer_branding_score": <int 0-15>,
  "dealer_branding_notes": "<string>",
  "recommendations": "<string>"
}}"""
