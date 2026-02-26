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


# =========================
# FONT LOADER
# =========================

def load_fonts():
    try:
        return {
            "title": ImageFont.truetype("anony/helpers/Raleway-Bold.ttf", 38),
            "artist": ImageFont.truetype("anony/helpers/Inter-Light.ttf", 26),
            "small": ImageFont.truetype("anony/helpers/Inter-Light.ttf", 22),
        }
    except:
        return {
            "title": ImageFont.load_default(),
            "artist": ImageFont.load_default(),
            "small": ImageFont.load_default(),
        }


FONTS = load_fonts()


# =========================
# FETCH IMAGE
# =========================

async def fetch_image(url: str) -> Image.Image:
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, timeout=6)
            r.raise_for_status()
            img = Image.open(BytesIO(r.content)).convert("RGBA")
            return ImageOps.fit(img, (1280, 720), Image.Resampling.LANCZOS)
        except:
            return Image.new("RGBA", (1280, 720), (20, 20, 30, 255))


# =========================
# MAIN CLASS
# =========================

class Thumbnail:
    async def generate(self, song: Track) -> str:
        try:
            os.makedirs("cache", exist_ok=True)
            save_path = f"cache/{song.id}_ios.png"

            thumb = await fetch_image(song.thumbnail)

            # ===== HEAVY BLUR BACKGROUND =====
            bg = thumb.filter(ImageFilter.GaussianBlur(55))
            bg = ImageEnhance.Brightness(bg).enhance(0.65)

            width, height = 1280, 720

            # ===== GLASS PANEL =====
            panel_w, panel_h = 920, 480
            panel_x = (width - panel_w) // 2
            panel_y = (height - panel_h) // 2

            panel = bg.crop(
                (panel_x, panel_y, panel_x + panel_w, panel_y + panel_h)
            )
            panel = panel.filter(ImageFilter.GaussianBlur(25))

            overlay = Image.new(
                "RGBA", (panel_w, panel_h), (40, 40, 60, 160)
            )

            mask = Image.new("L", (panel_w, panel_h), 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                (0, 0, panel_w, panel_h), radius=45, fill=255
            )

            panel = Image.alpha_composite(panel.convert("RGBA"), overlay)
            panel.putalpha(mask)

            bg.paste(panel, (panel_x, panel_y), panel)

            draw = ImageDraw.Draw(bg)

            # ===== COVER =====
            cover = ImageOps.fit(
                thumb, (220, 220), Image.Resampling.LANCZOS
            )

            cover_mask = Image.new("L", (220, 220), 0)
            ImageDraw.Draw(cover_mask).rounded_rectangle(
                (0, 0, 220, 220), radius=30, fill=255
            )
            cover.putalpha(cover_mask)

            bg.paste(cover, (panel_x + 70, panel_y + 90), cover)

            # ===== TEXT =====
            title = (song.title or "Unknown")[:35]
            artist = (song.channel_name or "Unknown")[:30]

            draw.text(
                (panel_x + 340, panel_y + 100),
                title,
                fill="white",
                font=FONTS["title"],
            )

            draw.text(
                (panel_x + 340, panel_y + 155),
                artist,
                fill=(200, 200, 200),
                font=FONTS["artist"],
            )

            # ===== PROGRESS BAR =====
            bar_x1 = panel_x + 340
            bar_x2 = panel_x + 820
            bar_y = panel_y + 220

            draw.line(
                [(bar_x1, bar_y), (bar_x2, bar_y)],
                fill=(140, 140, 140),
                width=6,
            )

            progress = bar_x1 + 220
            draw.line(
                [(bar_x1, bar_y), (progress, bar_y)],
                fill="white",
                width=6,
            )

            draw.text(
                (bar_x1, bar_y - 30),
                "0:24",
                fill="white",
                font=FONTS["small"],
            )

            draw.text(
                (bar_x2 - 50, bar_y - 30),
                song.duration or "--:--",
                fill="white",
                font=FONTS["small"],
            )

            # ===== CONTROLS PNG =====
            try:
                controls = Image.open(
                    "anony/assets/controls.png"
                ).convert("RGBA")

                controls = controls.resize(
                    (620, 170), Image.Resampling.LANCZOS
                )

                bg.paste(
                    controls,
                    (panel_x + 150, panel_y + 260),
                    controls,
                )

                controls.close()
            except Exception as e:
                logger.warning("Controls load error: %s", e)

            bg.save(save_path, "PNG", quality=95)
            return save_path

        except Exception as e:
            logger.warning("Thumbnail error: %s", e)
            return config.DEFAULT_THUMB
