import os
from io import BytesIO
import httpx
from PIL import (
    Image,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageFont,
    ImageOps,
)

from anony import logger, config
from anony.helpers import Track


def load_fonts():
    try:
        return {
            "title": ImageFont.truetype("anony/helpers/Raleway-Bold.ttf", 40),
            "artist": ImageFont.truetype("anony/helpers/Inter-Light.ttf", 28),
            "small": ImageFont.truetype("anony/helpers/Inter-Light.ttf", 22),
        }
    except:
        return {
            "title": ImageFont.load_default(),
            "artist": ImageFont.load_default(),
            "small": ImageFont.load_default(),
        }


FONTS = load_fonts()


async def fetch_image(url: str) -> Image.Image:
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, timeout=6)
            r.raise_for_status()
            img = Image.open(BytesIO(r.content)).convert("RGBA")
            return ImageOps.fit(img, (1280, 720), Image.Resampling.LANCZOS)
        except:
            return Image.new("RGBA", (1280, 720), (25, 18, 18, 255))


class Thumbnail:
    async def generate(self, song: Track) -> str:
        try:
            os.makedirs("cache", exist_ok=True)
            save_path = f"cache/{song.id}_final.png"

            thumb = await fetch_image(song.thumbnail)

            width, height = 1280, 720

            # ===== PREMIUM DARK BLUR BACKGROUND =====
            bg = thumb.resize((width, height), Image.Resampling.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(55))
            bg = ImageEnhance.Brightness(bg).enhance(0.45)

            dark_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 70))
            bg = Image.alpha_composite(bg.convert("RGBA"), dark_overlay)

            # ===== PANEL FRAME (Same Old Framing) =====
            panel_x, panel_y = 305, 125
            panel_w = 975 - 305
            panel_h = 595 - 125

            # ===== SHADOW =====
            shadow = Image.new("RGBA", (panel_w, panel_h), (0, 0, 0, 255))
            shadow = shadow.filter(ImageFilter.GaussianBlur(40))
            bg.paste(shadow, (panel_x + 15, panel_y + 25), shadow)

            # ===== GLASS PANEL =====
            glass = Image.new("RGBA", (panel_w, panel_h), (35, 35, 35, 200))
            mask = Image.new("L", (panel_w, panel_h), 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                (0, 0, panel_w, panel_h),
                radius=30,
                fill=255,
            )
            glass.putalpha(mask)
            bg.paste(glass, (panel_x, panel_y), glass)

            draw = ImageDraw.Draw(bg)

            # ===== COVER =====
            cover = ImageOps.fit(
                thumb, (184, 184), Image.Resampling.LANCZOS
            )

            cover_mask = Image.new("L", (184, 184), 0)
            ImageDraw.Draw(cover_mask).rounded_rectangle(
                (0, 0, 184, 184), radius=20, fill=255
            )
            cover.putalpha(cover_mask)

            bg.paste(cover, (325, 155), cover)

            # ===== TEXT =====
            title = (song.title or "Unknown Title")[:45]
            artist = (song.channel_name or "Unknown Artist")[:40]

            draw.text(
                (520, 200),
                title,
                fill="white",
                font=FONTS["title"],
            )

            draw.text(
                (520, 250),
                artist,
                fill=(210, 210, 210),
                font=FONTS["artist"],
            )

            # ===== CONTROLS =====
            try:
                controls = Image.open("anony/assets/controls.png").convert("RGBA")
                controls = controls.resize((600, 160), Image.Resampling.LANCZOS)

                bg.paste(
                    controls,
                    (335, 415),
                    controls,
                )
            except:
                pass

            # ===== VOLUME BAR (Dynamic Centered) =====
            vol_y = 575

            panel_left = 305
            panel_right = 975

            padding = 110

            bar_start = panel_left + padding
            bar_end = panel_right - padding

            draw.line(
                [(bar_start, vol_y),
                 (bar_end, vol_y)],
                fill=(120, 120, 120),
                width=7,
            )

            filled_width = int((bar_end - bar_start) * 0.6)

            draw.line(
                [(bar_start, vol_y),
                 (bar_start + filled_width, vol_y)],
                fill=(240, 240, 240),
                width=7,
            )

            bg.save(save_path, "PNG", quality=95)
            return save_path

        except Exception as e:
            logger.warning("Thumbnail generation failed: %s", e)
            return config.DEFAULT_THUMB
