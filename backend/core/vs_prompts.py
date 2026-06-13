"""
core.vs_prompts — VERBATIM virtual-staging prompt engine from app.py
(lines 4488-4758): Gemini room-analysis prompt, spatial parsing, and the
Google Flow staging prompt builder used by both pilots and AutoPilot.
"""
import re
_VS_INT_LIGHTING = {
    'Modern Luxury': '2700K warm gold light. Recessed ceiling downlights + directional accent lights on key furniture. Soft shadows. Warm glow from windows suggesting late-afternoon sun. Light temperature transitions from warm white near ceiling to golden near floor.',
    'Warm Contemporary': '2800K neutral warm. Pendant light overhead, natural diffuse window light from the north, soft shadow gradients. No harsh highlights.',
    'Minimalist': '3500K clean white. Even diffuse overhead light, no accent clutter, crisp clean shadows on surfaces. Clinical precision.',
    'Traditional Indian': '2700K amber warm. Decorative pendant fixture, layered lamp sources at eye level, soft pools of warm light on carved woodwork.',
    'Scandinavian': '3000K neutral warm. Abundant natural window light, minimal artificial sources, milky diffuse sky glow, soft even shadows.',
    'Bohemian': '2200K amber candlelight-warm. Multiple layered light sources — floor lamp, hanging bulbs, soft glowing pools. Rich warm shadows.',
}
_VS_INT_LIGHTING_DEFAULT = '2800K neutral warm. Soft ambient overhead, natural window light, no harsh shadows.'

_VS_EXT_LIGHTING = {
    'Modern Luxury': 'Golden hour — 5500K warm directional sunlight at 20–25° horizontal angle, long soft shadows across the facade, deep blue gradient sky with slight warm haze at horizon. Magazine-grade photography. No overexposed surfaces.',
    'Warm Contemporary': 'Late afternoon — 5000K neutral warm sun, slight atmospheric haze, soft directional shadows, warm sky gradient.',
    'Minimalist': 'Midday — 5500K neutral clear sky, even crisp light, clean hard shadows, no atmospheric distortion.',
    'Traditional Indian': 'Dusk — 4000K sky transitioning warm, facade accent lights activated, warm golden edge light on architectural details.',
    'Scandinavian': 'Overcast — 7000K soft diffuse light from milky white sky, no harsh shadows, even flat illumination across the entire facade.',
}
_VS_EXT_LIGHTING_DEFAULT = 'Golden hour — 5500K warm, long shadows, atmospheric depth, blue-to-amber sky gradient.'

_VS_SPACE_VOCAB = {
    'Office': 'ergonomic workstations, task lighting, acoustic ceiling panels, glass partitions, corporate reception finish',
    'Restaurant / Café': 'dining tables with chairs, bar or counter seating, warm ambient ceiling lights, F&B materials — wood and stone, atmospheric dining mood',
    'Hotel Room': 'hospitality-grade furnishings, premium bedding, resort-quality finish, blackout curtains, luggage bench at foot of bed',
    'Clinic / Hospital': 'clean clinical white surfaces, hygienic flooring, professional medical-grade furniture, even cool overhead lighting',
    'Retail Store': 'merchandise display shelving, track lighting on product, open customer footpath, brand identity colours on walls',
}
_VS_SPACE_VOCAB_DEFAULT = 'residential furniture, soft furnishings, lifestyle accessories, warm home atmosphere'

_VS_BUYER_CONTEXT = {
    'HNI': 'Target buyer: High Net-Worth Individual. Staging must signal exclusivity — premium imported materials, bespoke furniture proportions, curated art, zero clutter. Every object should look hand-selected.',
    'Young Professional': 'Target buyer: Young Professional. Staging should feel aspirational but functional — clean lines, multi-use furniture, tech-friendly desk nook, urban energy without excess.',
    'Family': 'Target buyer: Family. Staging should feel warm, liveable, and spacious — durable-looking materials, sufficient seating, storage-visible design, soft tones that feel safe and inviting for children.',
    'Investor': 'Target buyer: Real estate investor. Staging should maximise perceived rental yield — neutral palette, durable finishes, broad demographic appeal, nothing too niche or personalised.',
    'NRI': 'Target buyer: Non-Resident Indian. Staging should blend Indian warmth with international finish standards — global material quality, familiar cultural warmth, aspirational lifestyle cues.',
}

_VS_STYLE_MATERIALS = {
    'Modern Luxury': 'Calacatta marble surfaces, brushed brass fixtures, deep charcoal or ivory base palette, velvet upholstery, lacquered cabinetry, statement pendant lighting, symmetrical furniture arrangement.',
    'Warm Contemporary': 'Light oak or walnut wood tones, linen and cotton fabrics, terracotta or sage green accents, rattan or cane details, layered rugs, warm pendant or floor lamps.',
    'Minimalist': 'Monochrome palette — white walls, concrete or light wood floors, hidden storage, no visible clutter, single statement piece per room, negative space is intentional.',
    'Traditional Indian': 'Dark teak wood furniture with carved detailing, brass and copper accents, jewel-tone fabrics (rust, emerald, mustard), jali screens or arched doorways, hand-block printed textiles.',
    'Scandinavian': 'White and grey base, blonde birch wood, sheepskin throws, knitted cushions, simple geometric forms, abundant greenery (fiddle-leaf or monstera), hygge warmth.',
    'Bohemian': 'Layered textiles, macramé wall art, woven rugs over rugs, eclectic plant collection, vintage furniture mix, warm amber and rust palette, globally-sourced decorative objects.',
}
_VS_STYLE_MATERIALS_DEFAULT = 'Balanced furniture selection, neutral base palette with considered accent tones, quality materials, curated decor.'

_VS_EXT_KEYWORDS = ('exterior', 'facade', 'terrace', 'balcony', 'garden',
                    'rooftop', 'parking', 'pool', 'entrance')

# Port of ROOM_ELEMENTS + classifyRoom from pilot_sku_workflow.html
_VS_ROOM_ELEMENTS = {
    'bedroom': ['Large window','Sliding balcony door','French door to balcony','Walk-in closet (WIC)','Fitted wardrobe','Niche / alcove','AC ledge','False ceiling tray','Study nook','Attached bathroom door','Structural column','Beam'],
    'living':  ['Floor-to-ceiling glass','Large sliding door','Main entrance door','Bay window','Fireplace','Column / structural shaft','Half-wall partition','Staircase','Foyer arch','Terrace access door','Sill window','Jali / screen opening'],
    'kitchen': ['Utility balcony door','Service shaft / duct','Chimney / exhaust vent','Breakfast counter','Pantry alcove','Pass-through window','Under-counter storage niche','Corner unit','Beam overhead','Regular window'],
    'bathroom':['Frosted window','Shower shaft / vent','Ventilator glass block','Shower niche','Bathtub ledge','Toilet alcove partition','Linen cabinet niche','Double sink counter','Skylight'],
    'dining':  ['Large window','Bay window','Passage arch to kitchen','Sideboard niche','Chandelier drop point','Sliding door to balcony','Regular window'],
    'study':   ['Window with sill','Built-in bookshelf niche','Cable management shaft','Accent wall niche','Glass partition wall','French door','Regular window'],
    'balcony': ['Railing / parapet wall','Utility outlet point','Water outlet / tap point','Storage cabinet space','Overhead pergola / shade mount','Adjoining room access door','Open view (no railing obstruction)'],
    'other':   ['Large window','Regular window','Door','Column / shaft','Niche / recess','Open wall','Pass-through','Arch','Beam','Skylight'],
}


def _vs_classify_room(label):
    l = (label or '').lower()
    if re.search(r'bedroom|guest\s*room|kid|child|master', l): return 'bedroom'
    if re.search(r'living|drawing|lounge|family', l): return 'living'
    if re.search(r'kitchen', l): return 'kitchen'
    if re.search(r'bath|toilet|wc|washroom', l): return 'bathroom'
    if re.search(r'dining', l): return 'dining'
    if re.search(r'study|office|work', l): return 'study'
    if re.search(r'balcony|terrace|garden|outdoor|deck', l): return 'balcony'
    return 'other'


def build_gemini_room_analysis_prompt(room_label):
    """Exact port of copyGeminiHelperPrompt() — the prompt a pilot pastes into
    Gemini together with the POV A photo to auto-fill the Step 0 room reading."""
    elements = _VS_ROOM_ELEMENTS.get(_vs_classify_room(room_label), _VS_ROOM_ELEMENTS['other'])
    el_lines = '\n'.join(f'- {el}' for el in elements)
    return (
        f"You are an expert architectural analyst and interior designer. Analyze the uploaded photo of the "
        f"{room_label} and provide a precise, objective assessment to help me fill out a room structure form.\n\n"
        "Based on the image, identify and select from the following options only:\n\n"
        "1. Visible Structural Elements (Choose all that apply from this list):\n"
        f"{el_lines}\n"
        "*(If you see any other distinct structural elements like specific columns, beams, niches, windows, "
        "doors not in the list, write them down for Custom Elements)*\n\n"
        "2. Ceiling Height (Select the most accurate estimate based on door frames and proportions):\n"
        "- Standard 9–10 ft (ceiling is slightly above standard door frame)\n"
        "- High 11–14 ft (ceiling is about 1.5x door frame height)\n"
        "- Double height 15 ft+ (equivalent to two floors)\n"
        "- Unknown\n\n"
        "3. Natural Light Direction (from the camera's point of view):\n"
        "- Left (light enters from left side windows/openings)\n"
        "- Right (light enters from right side windows/openings)\n"
        "- Front-facing (light enters from windows/openings facing the camera)\n"
        "- Multiple windows (light enters from windows on different sides)\n"
        "- No windows visible\n\n"
        "4. Structural Anomalies:\n"
        "Identify if there are columns, overhead beams, recessed niches, arches, or recesses in the walls, and "
        "write a brief description of where they are (e.g. \"exposed column on left wall\", \"overhead beam "
        "across ceiling\"). If none, write \"None\".\n\n"
        "Please format your response EXACTLY like this (do not write any conversational intro or outro, just "
        "these 5 lines):\n"
        "Elements: [comma-separated selected elements]\n"
        "Custom Elements: [comma-separated custom elements, or None]\n"
        "Ceiling: [selected option]\n"
        "Light: [selected option]\n"
        "Anomalies: [description, or None]"
    )


def parse_gemini_spatial_response(text):
    """Parse Gemini's 5-line room reading (same parsing as autoFillFromGemini)."""
    data = {'elements': '', 'custom_elements': '', 'ceiling': '', 'light': '', 'anomalies': ''}
    for line in (text or '').split('\n'):
        low = line.lower().strip()
        if low.startswith('elements:'):
            data['elements'] = line.split(':', 1)[1].strip()
        elif low.startswith('custom elements:'):
            data['custom_elements'] = line.split(':', 1)[1].strip()
        elif low.startswith('ceiling:'):
            data['ceiling'] = line.split(':', 1)[1].strip()
        elif low.startswith('light:'):
            data['light'] = line.split(':', 1)[1].strip()
        elif low.startswith('anomalies:'):
            data['anomalies'] = line.split(':', 1)[1].strip()
    return data


def build_spatial_block(data):
    """Exact port of the [SPATIAL CONTEXT] block copyPrompt() injects."""
    elements = data.get('elements', '')
    customs  = data.get('custom_elements', '')
    if customs and customs.lower() != 'none':
        elements = f"{elements}, {customs}" if elements else customs
    anomalies = data.get('anomalies', '')
    anomalies_line = (f"— Structural anomalies: {anomalies}\n"
                      if anomalies and anomalies.lower() != 'none'
                      else "— Structural anomalies: None noted\n")
    return (
        "[SPATIAL CONTEXT]\n"
        f"— Structural elements observed: {elements}\n"
        f"— Ceiling height: {data.get('ceiling', 'Unknown')}\n"
        f"— Natural light direction: {data.get('light', 'Unknown')}\n"
        f"{anomalies_line}"
        "Honour every detail above — do not contradict observed geometry, ceiling height, or light source "
        "position in the output."
    )


def build_virtual_staging_prompt(intake, room_label, has_pov_b=False, has_moodboard=False,
                                 spatial_block=None):
    """Exact Python port of the pilot dashboard's pre-built Google Flow prompt.
    spatial_block: optional [SPATIAL CONTEXT] text (from the Gemini room reading)
    injected exactly where the dashboard's copyPrompt() injects it."""
    style      = intake.get('style') or 'Warm Contemporary'
    prop_type  = intake.get('property_type') or 'Residential'
    prop_stage = intake.get('property_stage') or 'Finished'
    buyer      = intake.get('buyer_profile') or ''
    notes      = intake.get('special_notes') or ''

    is_ext = any(k in room_label.lower() for k in _VS_EXT_KEYWORDS)
    is_uc  = prop_stage in ('Under Construction', 'Shell / Bare Concrete')

    int_lighting   = _VS_INT_LIGHTING.get(style, _VS_INT_LIGHTING_DEFAULT)
    ext_lighting   = _VS_EXT_LIGHTING.get(style, _VS_EXT_LIGHTING_DEFAULT)
    space_vocab    = _VS_SPACE_VOCAB.get(prop_type, _VS_SPACE_VOCAB_DEFAULT)
    buyer_context  = _VS_BUYER_CONTEXT.get(buyer, '')
    style_materials = _VS_STYLE_MATERIALS.get(style, _VS_STYLE_MATERIALS_DEFAULT)

    p = []
    p.append(
        f"You are India's leading {prop_type.lower()} interior designer and architectural "
        f"visualisation expert with 15 years of professional experience. Your renders are "
        f"published in Architectural Digest India. Every image you produce must be "
        f"photorealistic, magazine-ready, and publishable without retouching.\n")
    p.append(f"TASK: Photorealistic {'exterior' if is_ext else 'interior'} virtual staging. "
             f"{prop_type}. Space: {room_label}.\n")

    if has_pov_b:
        p.append(
            f"[INPUT IMAGES — TWO ANGLES PROVIDED] Two photos of the same {room_label} are provided. "
            "POV A is the main staging canvas. POV B is a second angle of the identical space — use it "
            "exclusively to understand geometry that POV A does not fully reveal.\n"
            "— Cross-reference both images to build a complete mental model of the room: wall lengths, "
            "ceiling height, floor plan shape, position of every door, window, archway, and structural opening\n"
            "— POV A is your primary canvas — the final staged image must match POV A's camera angle, "
            "perspective, lens height, and framing exactly\n"
            "— POV B is geometry intelligence only — do not match its camera angle or compose toward it\n"
            "— Any structural element visible in EITHER photo (wall, window, door, column, niche, beam) "
            "must be preserved exactly in the output")
    else:
        p.append(
            f"[INPUT SPACE] The image is the client's actual {room_label}. This is your staging canvas. "
            "Read the space carefully before generating:\n"
            "— Identify the exact wall positions, ceiling height, floor area, and room proportions\n"
            "— Locate every visible door, window, archway, and passage opening\n"
            "— Note the existing surface textures and finishes (bare walls, floor material, ceiling type)\n"
            "— Respect the natural light direction visible in the photo")

    either = ' visible in either photo' if has_pov_b else ''
    p.append(
        f"[GEOMETRY ENFORCEMENT] All walls, floor, ceiling, and every structural opening{either} are fixed. "
        "Do not alter proportions, do not close or relocate any window or door, do not add or remove "
        "architectural elements. Preserve the room geometry, walls, windows, floors and ceiling exactly as "
        "in the source image; place furniture only on the existing floor. The staged result must be "
        "compositable back onto POV A without perspective errors.\n")

    if spatial_block:
        p.append(spatial_block + "\n")

    if is_uc:
        p.append(
            "[UNDER-CONSTRUCTION HANDLING] This is an unfinished space with raw structural surfaces. Apply "
            "finished surface treatments (flooring, wall plaster or cladding, ceiling finish) over the visible "
            "raw concrete/brick. Every door opening, window opening, passage, and archway visible in the input "
            "photo must be strictly preserved — these define the spatial logic. Furniture placement must respect "
            "the floor plan implied by the structure. All light sources must be consistent with window positions "
            "in the input photo.\n")

    if has_moodboard:
        p.append(
            "[STYLE REFERENCE — CLIENT MOODBOARD PROVIDED] A client moodboard image has been provided as a style "
            "reference. Before generating, carefully read and extract from the moodboard:\n"
            "— Color palette: dominant wall color, floor finish color, fabric accent colors, any recurring tones\n"
            "— Material finishes: specific wood grain type (light oak, dark walnut, whitewash), stone or tile type, "
            "metal tone (brass, matte black, chrome, copper), fabric weave and texture\n"
            "— Furniture silhouette: leg style (tapered, metal pin, slab base, turned), seat profile (low-slung, "
            "upright, curved back), arm style, sofa depth\n"
            "— Lighting mood: ambient vs accent ratio, warm vs cool color temperature, presence and style of "
            "decorative fixtures (pendants, sconces, floor lamps)\n"
            "— Decorative language: plant types and scale, art style and framing, rug pattern and layering, cushion "
            "arrangements, books, candles, tabletop objects\n"
            f"Apply ALL of the above exactly to the {room_label}. The moodboard is the primary style authority and "
            f"overrides the style chip ({style}). Every furnishing decision must trace back to something visible or "
            "implied in the moodboard. If an element is not visible in the moodboard, default to complementing its "
            "palette rather than introducing a new direction.\n")
    else:
        p.append(
            f"[STYLE DIRECTION — {style.upper()}] No moodboard provided. Apply the following style vocabulary precisely:\n"
            f"{style_materials}\n"
            f"Maintain strict internal consistency — every material, color, and object must belong to the same "
            f"{style} language. Do not mix styles.\n")

    p.append(
        f"[FURNISHINGS] Add {space_vocab} appropriate for a {room_label}. Specific requirements:\n"
        "— All furniture must physically rest on the floor — no floating objects, no incorrect perspective\n"
        "— Scale every piece to room proportions — no oversized sofas in small rooms, no undersized beds in master bedrooms\n"
        "— Layer the space: primary furniture → secondary pieces (side tables, shelving) → soft furnishings "
        "(rugs, cushions, throws) → decorative objects (plants, art, books)\n"
        "— Leave clear circulation paths — do not block door swings or window access\n")

    lighting = f"Exterior — {ext_lighting}" if is_ext else f"Interior — {int_lighting}"
    p.append(
        f"[LIGHTING] {lighting} Lighting must be photorealistic and match the quality of a professional "
        "architectural photography shoot. Cast light and shadows must be physically consistent with window "
        "positions in the input space photo.\n")

    if not is_ext and buyer_context:
        p.append(f"[BUYER APPEAL] {buyer_context}")
    if notes:
        p.append(f"[CLIENT INSTRUCTIONS] {notes}")

    p.append(
        "[OUTPUT REQUIREMENTS] No people. No watermarks. No AI artifacts. High resolution. Hyperrealistic. "
        "Camera angle must match the original input photo exactly — same lens height, same perspective, same "
        "framing. Final image must be suitable for a premium property brochure or listing portal without any "
        "retouching.")

    return '\n'.join(p)
