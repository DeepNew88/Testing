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

            # FULL SCREEN COVER (NO BOX, NO BLACK PADDING)
            img = ImageOps.fit(
                img,
                (1280, 720),
                Image.Resampling.LANCZOS
            )

            return img

        except:
            return Image.new("RGBA", (1280, 720), (25, 18, 18, 255))


class Thumbnail:
    async def generate(self, song: Track) -> str:
        try:
            os.makedirs("cache", exist_ok=True)
            save_path = f"cache/{song.id}_final.png"

            thumb = await fetch_image(song.thumbnail)

            width, height = 1280, 720

            # ===== PREMIUM FULL BLUR BACKGROUND =====
            bg = thumb.copy()

            bg = bg.filter(ImageFilter.GaussianBlur(15))
            bg = ImageEnhance.Brightness(bg).enhance(1.0)

            dark_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 30))
            bg = Image.alpha_composite(bg, dark_overlay)

            # ===== PANEL FRAME =====
            # ===== BIGGER GLASS PANEL =====
            panel_margin_x = 180   # left-right spacing
            panel_margin_y = 90    # top-bottom spacing

            panel_x = panel_margin_x
            panel_y = panel_margin_y

            panel_w = width - (panel_margin_x * 2)
            panel_h = height - (panel_margin_y * 2)

            # ===== GLASS PANEL =====
            glass = Image.new("RGBA", (panel_w, panel_h), (35, 35, 35, 190))
            mask = Image.new("L", (panel_w, panel_h), 0)

            ImageDraw.Draw(mask).rounded_rectangle(
                (0, 0, panel_w, panel_h),
                radius=35,
                fill=255,
            )

            glass.putalpha(mask)
            bg.paste(glass, (panel_x, panel_y), glass)

            draw = ImageDraw.Draw(bg)

            # ===== COVER =====
            cover = ImageOps.fit(
                thumb,
                (184, 184),
                Image.Resampling.LANCZOS
            )

            cover_mask = Image.new("L", (184, 184), 0)
            ImageDraw.Draw(cover_mask).rounded_rectangle(
                (0, 0, 184, 184),
                radius=25,
                fill=255
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
                (520, 255),
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

            # ===== VOLUME BAR =====
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
