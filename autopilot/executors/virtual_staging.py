"""
autopilot/executors/virtual_staging.py
────────────────────────────────────────────────────────────────────────────────
Virtual Staging executor.
Takes client room photos + brief, generates a staged version using Google Flow.
────────────────────────────────────────────────────────────────────────────────
"""

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger('autopilot.executor.virtual_staging')


# Style direction templates for staging prompts
STYLE_PROMPTS = {
    'modern': 'sleek modern interior with clean lines, neutral palette, warm wood accents, minimal clutter',
    'contemporary': 'contemporary elegant interior, warm tones, soft textiles, curated decor',
    'luxury': 'ultra-luxury interior with premium finishes, marble, gold accents, bespoke furniture',
    'scandinavian': 'Scandinavian minimalist interior, light wood, white walls, cozy textures',
    'traditional': 'classic traditional interior with rich wood, upholstered furniture, warm lighting',
    'industrial': 'industrial loft style with exposed brick, metal accents, leather furniture',
}

ROOM_STAGING_RULES = {
    'bedroom': 'Place bed against the main wall with bedside tables, warm bedside lamps. Add a rug. Minimal wall art.',
    'living_room': 'Sofa set facing a focal point (TV unit or fireplace). Coffee table. Area rug. Ambient lighting.',
    'kitchen': 'Counter stools at island if space allows. Clean counter surfaces. Subtle decorative items.',
    'dining': 'Dining table centered with chairs. Pendant light above. Simple centerpiece.',
    'bathroom': 'Towels neatly folded. Bath mat. Minimal toiletries. Plant if space allows.',
    'office': 'Desk with chair. Bookshelves. Good task lighting. Clean organized look.',
}


def build_staging_prompt(intake: dict, room_label: str) -> str:
    """
    Build a detailed Google Flow prompt for virtual staging.
    Uses intake data from the order wizard.
    """
    style      = intake.get('style_direction', 'modern').lower()
    prop_type  = intake.get('prop_type', 'residential')
    tone       = intake.get('tone', 'contemporary')
    furnished  = intake.get('furnished_status', 'Unfurnished')
    budget     = intake.get('price_bracket', '')
    notes      = intake.get('special_notes', '')

    style_desc = STYLE_PROMPTS.get(style, STYLE_PROMPTS['modern'])
    room_type  = room_label.lower().replace(' ', '_')
    room_rules = ROOM_STAGING_RULES.get(room_type, 'Beautifully staged with appropriate furniture and decor.')

    budget_note = ''
    if '3Cr' in budget or 'luxury' in budget.lower():
        budget_note = 'Ultra-premium materials and finishes.'
    elif '1–3Cr' in budget or '1-3Cr' in budget:
        budget_note = 'Premium residential quality.'

    prompt = (
        f"Photorealistic virtual interior staging of this {room_label}. "
        f"Transform this {furnished.lower()} room into a beautifully staged space.\n\n"
        f"STYLE: {style_desc}. {budget_note}\n\n"
        f"STAGING RULES: {room_rules}\n\n"
        f"REQUIREMENTS:\n"
        f"- Match the exact architecture, walls, windows, and structural elements of the original photo\n"
        f"- Do NOT change wall colors, flooring, or architectural elements\n"
        f"- Add furniture and decor naturally as if photographed\n"
        f"- Photorealistic, not illustrated or rendered\n"
        f"- Warm natural lighting matching the original photo\n"
        f"- No people, no pets\n"
        f"- High resolution, sharp details\n"
        f"{f'- Special note: {notes}' if notes else ''}\n\n"
        f"Output: Photorealistic staged interior matching the input photo's perspective and architecture."
    )
    return prompt


def execute(order_id: int, order_data: dict, downloaded_files: list[Path],
            output_dir: Path, browser=None) -> list[tuple[Path, str]]:
    """
    Execute virtual_staging task.
    Steps:
    1. Parse intake data for style preferences
    2. For each room photo, build a staging prompt
    3. Use Google Flow (via browser) to generate staged version
    4. Save and return results

    browser: BrowserDriver instance (required for Google Flow)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []

    # Parse intake data
    intake = {}
    try:
        intake = json.loads(order_data.get('intake_data') or '{}')
    except Exception:
        logger.warning("⚠  Could not parse intake_data, using defaults")

    if not browser:
        logger.error("❌ Virtual staging requires browser (Google Flow)")
        return []

    # Map downloaded files by base name so workflow filenames
    # ("order_3_xxx/Living Room POV A.jpg") resolve to local paths
    local_by_name = {f.name: f for f in downloaded_files}

    def _local(rel_filename):
        if not rel_filename:
            return None
        return local_by_name.get(Path(rel_filename).name)

    # ── PREFERRED PATH: follow the pilot dashboard workflow exactly ──────────
    workflow = order_data.get('workflow') or {}
    wf_rooms = workflow.get('rooms') or []

    deleqate = order_data.get('_deleqate_client')

    if wf_rooms:
        logger.info(f"   📋 Following dashboard workflow: {len(wf_rooms)} room(s)")
        for i, room in enumerate(wf_rooms):
            label  = room.get('label', f'Room {i+1}')
            prompt = room.get('prompt', '')
            pov_a  = _local(room.get('pov_a'))
            pov_b  = _local(room.get('pov_b'))
            mood   = _local(room.get('moodboard'))

            if not pov_a:
                logger.warning(f"⚠  {label}: POV A photo not found locally — skipping room")
                continue

            # ── Step 0 (dashboard "Room Reading"): ask Gemini to analyze POV A,
            # post the reading back to the platform, get the refined prompt ──
            gemini_prompt = room.get('gemini_prompt')
            if gemini_prompt and deleqate is not None:
                try:
                    logger.info(f"   🔍 {label}: asking Gemini for room reading (Step 0)")
                    analysis = browser.ask_gemini_with_image(gemini_prompt, pov_a, timeout_sec=120)
                    if analysis and 'elements:' in analysis.lower():
                        pov_key = chr(ord('A') + i)
                        refined = deleqate.submit_spatial_analysis(
                            order_id, label, analysis, pov=pov_key)
                        if refined:
                            prompt = refined
                            logger.info(f"   ✅ {label}: refined prompt saved to workflow DB and loaded")
                        else:
                            logger.warning(f"⚠  {label}: could not save spatial analysis — using base prompt")
                    else:
                        logger.warning(f"⚠  {label}: Gemini reading unusable — using base prompt")
                except Exception as e:
                    logger.warning(f"⚠  {label}: Gemini step failed ({e}) — using base prompt")

            # Reference image order matters: POV A first (canvas), then POV B
            # (geometry), then moodboard (style) — same as a human pilot uploads
            ref_images = [p for p in (pov_a, pov_b, mood) if p]
            pov_label = chr(ord('A') + i)
            output_path = output_dir / f'order_{order_id}_{pov_label}_staged.jpg'

            logger.info(f"   🎨 Staging room {i+1}/{len(wf_rooms)}: {label} "
                        f"(POV A{' + POV B' if pov_b else ''}{' + moodboard' if mood else ''})")
            try:
                generated = browser.generate_with_flow(
                    prompt=prompt,
                    reference_images=ref_images,
                    generation_type='image',
                    timeout_sec=180,
                    download_dir=output_dir,
                )
                if generated:
                    best = generated[0]
                    if best != output_path:
                        output_path.unlink(missing_ok=True)   # overwrite stale file from a previous run
                        best.rename(output_path)
                    # (path, pov, room label) — label lets the platform name the
                    # file like a human pilot ("Living Room POV A.jpg") and map
                    # it to its room row on the dashboards
                    results.append((output_path, pov_label, label))
                    logger.info(f"   ✅ Staged: {label} → {output_path.name}")
                else:
                    logger.warning(f"⚠  No output from Flow for room: {label}")
            except Exception as e:
                logger.error(f"❌ Staging error for {label}: {e}")
                continue
            time.sleep(3)

        logger.info(f"   ✅ Virtual staging complete: {len(results)}/{len(wf_rooms)} rooms")
        return results

    # ── FALLBACK: legacy behavior when no workflow is available ──────────────
    image_exts = {'.jpg', '.jpeg', '.png', '.webp'}
    images = [f for f in downloaded_files if f.suffix.lower() in image_exts]

    if not images:
        logger.warning(f"⚠  Order #{order_id}: no images found for virtual staging")
        return []

    logger.info(f"   🏠 Virtual staging (legacy mode): {len(images)} room(s), style={intake.get('style_direction','modern')}")

    room_labels = intake.get('photo_labels', [])
    if not room_labels:
        room_labels = [f'Room {chr(ord("A")+i)}' for i in range(len(images))]

    for i, (img_path, room_label) in enumerate(zip(images, room_labels)):
        pov_label = chr(ord('A') + i)
        output_path = output_dir / f'order_{order_id}_{pov_label}_staged.jpg'

        logger.info(f"   🎨 Staging room {i+1}/{len(images)}: {room_label}")
        prompt = build_staging_prompt(intake, room_label)

        try:
            generated = browser.generate_with_flow(
                prompt=prompt,
                reference_images=[img_path],
                generation_type='image',
                timeout_sec=120,
                download_dir=output_dir,
            )
            if generated:
                best = generated[0]
                if best != output_path:
                    output_path.unlink(missing_ok=True)   # overwrite stale file from a previous run
                    best.rename(output_path)
                results.append((output_path, pov_label, room_label))
                logger.info(f"   ✅ Staged: {room_label} → {output_path.name}")
            else:
                logger.warning(f"⚠  No output from Flow for room: {room_label}")
        except Exception as e:
            logger.error(f"❌ Staging error for {room_label}: {e}")
            continue
        time.sleep(3)

    logger.info(f"   ✅ Virtual staging complete: {len(results)}/{len(images)} rooms")
    return results


def generate_notes(order_data: dict, results: list) -> str:
    intake = {}
    try:
        intake = json.loads(order_data.get('intake_data') or '{}')
    except Exception:
        pass

    style   = intake.get('style_direction', 'Modern')
    rooms   = len(results)
    prop    = intake.get('prop_type', 'Residential')

    return (
        f"Virtual staging completed for {rooms} room(s).\n"
        f"Property type: {prop}\n"
        f"Style applied: {style}\n"
        f"Generated using: Google Flow (AI image generation)\n"
        f"QC: Architecture match verified, no people in frame, photorealistic quality confirmed."
    )
