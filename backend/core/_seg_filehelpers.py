# ── Filename hygiene helpers (S21) ────────────────────────
# Standardise uploaded reference photos and deliverables to human-readable,
# collision-safe names like "Living Room POV A.jpg" so pilots and clients
# never see raw hashes or risky original filenames.
def _file_ext(filename, default='jpg'):
    """Return a safe lowercase extension from an arbitrary uploaded name."""
    fn = secure_filename(filename or '')
    return fn.rsplit('.', 1)[-1].lower() if '.' in fn else default

def _clean_label(label):
    """Human-readable label safe for use in a filename (no path chars)."""
    s = re.sub(r'[^\w\s-]', '', (label or '').strip())
    s = re.sub(r'\s+', ' ', s).strip()
    return s or 'File'

# ── M-3: Central upload validation — one whitelist, every upload route ──
ALLOWED_UPLOAD_EXTS = {
    'jpg','jpeg','png','gif','webp','avif',
    'pdf','docx','doc','txt','csv',   # no html/htm — stored-XSS risk when served back
    'mp3','wav','m4a','aac','ogg',
    'mp4','mov','avi','mkv','webm',
    'zip','rar',
}
_IMAGE_EXTS = {'jpg','jpeg','png','gif','webp'}

def is_allowed_upload(filename, allowed=None):
    """Uniform extension check for every upload endpoint. Pass `allowed`
    to narrow (never widen) the global whitelist for a specific route."""
    fn = filename or ''
    ext = fn.rsplit('.', 1)[-1].lower() if '.' in fn else ''
    return bool(ext) and ext in (allowed if allowed is not None else ALLOWED_UPLOAD_EXTS)

def verify_image_content(file_storage):
    """M-3: content check, not just extension — image uploads must actually
    parse as an image (blocks e.g. an .html payload renamed to .jpg)."""
    try:
        from PIL import Image as _PILImage
        pos = file_storage.stream.tell()
        img = _PILImage.open(file_storage.stream)
        img.verify()
        file_storage.stream.seek(pos)
        return True
    except Exception:
        try:
            file_storage.stream.seek(0)
        except Exception:
            pass
        return False

def _unique_named_path(folder, base, ext):
    """Return (filename, fullpath) that does not collide inside `folder`.
    Appends _1, _2 … instead of overwriting an existing file."""
    candidate = f'{base}.{ext}'
    path = os.path.join(folder, candidate)
    i = 1
    while os.path.exists(path):
        candidate = f'{base}_{i}.{ext}'
        path = os.path.join(folder, candidate)
        i += 1
    return candidate, path
