import base64
import io
import logging
from PIL import Image

logger = logging.getLogger(__name__)


def generate_avatar_data_uri(image_source, max_size=(80, 80), quality=60):
    """
    Given an UploadedFile, FileField, file-like object, or file path,
    resize it to a compact avatar thumbnail and return a data URI
    (e.g. data:image/jpeg;base64,...) that safely fits in signed session cookies.
    """
    try:
        if hasattr(image_source, 'open'):
            image_source.open('rb')
        if hasattr(image_source, 'seek'):
            image_source.seek(0)

        img = Image.open(image_source)
        img = img.convert('RGB')
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=quality, optimize=True)
        raw_bytes = buf.getvalue()
        b64 = base64.b64encode(raw_bytes).decode('ascii')
        return f"data:image/jpeg;base64,{b64}"
    except Exception as exc:
        logger.debug("Could not generate avatar data URI: %s", exc)
        return ""
