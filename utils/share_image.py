"""Generates the branded 1200x630 share-preview image used as the og:image /
twitter:image for a listing, so WhatsApp, iMessage, Facebook, LinkedIn and X
all unfurl the same price/beds/baths-aware card instead of a raw photo."""

import io
import logging
import os
from typing import Iterable
from urllib.parse import urlparse

import httpx
from PIL import Image, ImageDraw, ImageFont

from config import settings
from models.listing import Listing
from utils.storage import upload_share_image

logger = logging.getLogger(__name__)

CANVAS_SIZE = (1200, 630)
_FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts")
_MAX_PHOTO_BYTES = 20 * 1024 * 1024  # matches the listing upload size limit

_WHITE = (255, 255, 255, 255)
_WHITE_SOFT = (255, 255, 255, 225)
_CORAL = (255, 100, 92, 255)
_TAG_BG = (184, 10, 23, 235)
_PILL_BG = (3, 10, 16, 120)

# Fields that actually appear on the generated image — an edit that doesn't
# touch any of these doesn't need to pay for a re-fetch + re-render.
SHARE_IMAGE_FIELDS = {"price", "transaction", "location", "bedrooms", "bathrooms", "area_sqft", "images"}


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(os.path.join(_FONT_DIR, name), size)


def _is_allowed_photo_url(url: str) -> bool:
    """Listing photos are only ever URLs we ourselves handed back from
    upload_image() — restrict fetches to that exact host so a crafted
    `images[0]` value (from the listing create/update request body) can't
    turn this into a server-side request to an internal or metadata endpoint."""
    supabase_host = urlparse(settings.supabase_url).hostname
    if not supabase_host:
        return False
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname == supabase_host


def _fetch_photo(url: str) -> Image.Image | None:
    if not _is_allowed_photo_url(url):
        logger.warning("share_image: refusing to fetch photo from disallowed host: %s", url)
        return None
    try:
        with httpx.stream("GET", url, timeout=10.0, follow_redirects=False) as resp:
            resp.raise_for_status()
            content_length = resp.headers.get("content-length")
            if content_length and int(content_length) > _MAX_PHOTO_BYTES:
                logger.warning("share_image: source photo exceeds size limit: %s", url)
                return None
            chunks = bytearray()
            for chunk in resp.iter_bytes():
                chunks.extend(chunk)
                if len(chunks) > _MAX_PHOTO_BYTES:
                    logger.warning("share_image: source photo exceeded size limit while streaming: %s", url)
                    return None
        return Image.open(io.BytesIO(bytes(chunks))).convert("RGB")
    except Exception:
        logger.warning("share_image: failed to fetch source photo %s", url, exc_info=True)
        return None


def _cover_crop(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_w, target_h = size
    src_w, src_h = img.size
    target_ratio = target_w / target_h
    src_ratio = src_w / src_h
    if src_ratio > target_ratio:
        new_w = round(src_h * target_ratio)
        left = (src_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, src_h))
    else:
        new_h = round(src_w / target_ratio)
        top = (src_h - new_h) // 2
        img = img.crop((0, top, src_w, top + new_h))
    return img.resize(size, Image.LANCZOS)


def _bottom_scrim(size: tuple[int, int]) -> Image.Image:
    """A vertical gradient, transparent at the top and ~75% black at the
    bottom, so white text stays legible over any photo."""
    w, h = size
    gradient = Image.new("L", (1, h), color=0)
    for y in range(h):
        t = max(0.0, (y / h - 0.32) / 0.68)
        gradient.putpixel((0, y), round(225 * t))
    alpha = gradient.resize((w, h))
    scrim = Image.new("RGBA", size, (3, 10, 16, 255))
    scrim.putalpha(alpha)
    return scrim


def _pill(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font: ImageFont.FreeTypeFont,
          fg: tuple[int, int, int, int], bg: tuple[int, int, int, int],
          pad_x: int = 18, pad_y: int = 11, right_aligned: bool = False) -> None:
    l, t, r, b = draw.textbbox((0, 0), text, font=font)
    w, h = r - l, b - t
    x, y = xy
    if right_aligned:
        x -= w + pad_x * 2
    box = (x, y, x + w + pad_x * 2, y + h + pad_y * 2)
    draw.rounded_rectangle(box, radius=(h + pad_y * 2) // 2, fill=bg)
    draw.text((x + pad_x - l, y + pad_y - t), text, font=font, fill=fg)


def _price_str(listing: Listing) -> str:
    price = f"${int(listing.price):,}"
    return f"{price}/mo" if listing.transaction == "rent" else price


def _facts(listing: Listing) -> str:
    parts = []
    if listing.bedrooms:
        parts.append(f"{listing.bedrooms} BD")
    if listing.bathrooms:
        bath = listing.bathrooms
        bath_str = str(int(bath)) if float(bath).is_integer() else str(bath)
        parts.append(f"{bath_str} BA")
    if listing.area_sqft:
        parts.append(f"{listing.area_sqft:,} FT²")
    return "   ·   ".join(parts)


def generate_share_image(listing: Listing) -> str | None:
    """Compose and upload the branded share image for a listing.
    Returns the new public URL, or None if there's no photo to build it from
    (the caller should leave share_image_url untouched in that case)."""
    if not listing.images:
        return None

    photo = _fetch_photo(listing.images[0])
    if photo is None:
        return None

    canvas = _cover_crop(photo, CANVAS_SIZE).convert("RGBA")
    canvas = Image.alpha_composite(canvas, _bottom_scrim(CANVAS_SIZE))
    draw = ImageDraw.Draw(canvas, "RGBA")

    tag_font = _font("MonaSans-SemiBold.ttf", 22)
    price_font = _font("MonaSans-ExtraBold.ttf", 62)
    facts_font = _font("MonaSans-SemiBold.ttf", 25)
    brand_font = _font("MonaSans-Bold.ttf", 23)

    tag_text = "FOR RENT" if listing.transaction == "rent" else "FOR SALE"
    _pill(draw, (60, 50), tag_text, tag_font, _WHITE, _TAG_BG)

    _pill(draw, (CANVAS_SIZE[0] - 60, 50), listing.location.upper(), tag_font, _WHITE, _PILL_BG, right_aligned=True)

    draw.text((60, 462), _price_str(listing), font=price_font, fill=_WHITE)

    facts_text = _facts(listing)
    if facts_text:
        draw.text((64, 542), facts_text, font=facts_font, fill=_WHITE_SOFT)

    brand_prefix, brand_word, brand_suffix = "I ", "LOVE", " DR REALTY"
    total_w = sum(draw.textlength(part, font=brand_font) for part in (brand_prefix, brand_word, brand_suffix))
    bx = CANVAS_SIZE[0] - 60 - total_w
    by = CANVAS_SIZE[1] - 68
    for part, color in ((brand_prefix, _WHITE), (brand_word, _CORAL), (brand_suffix, _WHITE)):
        draw.text((bx, by), part, font=brand_font, fill=color)
        bx += draw.textlength(part, font=brand_font)

    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, format="JPEG", quality=88)
    return upload_share_image(buf.getvalue(), str(listing.id))


def maybe_regenerate_share_image(listing: Listing, changed_fields: Iterable[str]) -> None:
    """Regenerate the share image only if one of the fields it actually
    displays changed — skips the network/render cost for unrelated edits."""
    if not SHARE_IMAGE_FIELDS.intersection(changed_fields):
        return
    try:
        listing.share_image_url = generate_share_image(listing)
    except Exception:
        logger.exception("Share image generation failed for listing %s", listing.id)
