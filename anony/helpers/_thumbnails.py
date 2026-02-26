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
            "title": ImageFont.truetype("anony/helpers/Raleway-Bold.ttf", 42),
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

            # ===== BACKGROUND =====
            bg = thumb.resize((width, height), Image.Resampling.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(75))
            bg = ImageEnhance.Brightness(bg).enhance(0.65)

            tint = Image.new("RGBA", (width, height), (30, 20, 20, 120))
            bg = Image.alpha_composite(bg.convert("RGBA"), tint)

            # ===== PANEL SIZE (TALLER + BALANCED) =====
            panel_w, panel_h = 980, 600
            panel_x = (width - panel_w) // 2
            panel_y = (height - panel_h) // 2

            # ===== SHADOW =====
            shadow = Image.new("RGBA", (panel_w, panel_h), (0, 0, 0, 255))
            shadow_mask = Image.new("L", (panel_w, panel_h), 0)
            ImageDraw.Draw(shadow_mask).rounded_rectangle(
                (0, 0, panel_w, panel_h),
                radius=70,
                fill=255
            )
            shadow.putalpha(shadow_mask)
            bg.paste(shadow, (panel_x + 35, panel_y + 50), shadow)

            # ===== GLASS PANEL =====
            glass = Image.new("RGBA", (panel_w, panel_h), (40, 40, 40, 155))
            mask = Image.new("L", (panel_w, panel_h), 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                (0, 0, panel_w, panel_h),
                radius=70,
                fill=255
            )
            glass.putalpha(mask)
            bg.paste(glass, (panel_x, panel_y), glass)

            draw = ImageDraw.Draw(bg)

            # ===== COVER =====
            cover = ImageOps.fit(
                thumb, (260, 260), Image.Resampling.LANCZOS
            )

            cover_mask = Image.new("L", (260, 260), 0)
            ImageDraw.Draw(cover_mask).rounded_rectangle(
                (0, 0, 260, 260), radius=45, fill=255
            )
            cover.putalpha(cover_mask)

            bg.paste(cover, (panel_x + 90, panel_y + 150), cover)

            # ===== TEXT =====
            title = (song.title or "Unknown Title")[:45]
            artist = (song.channel_name or "Unknown Artist")[:40]

            draw.text(
                (panel_x + 460, panel_y + 170),
                title,
                fill="white",
                font=FONTS["title"],
            )

            draw.text(
                (panel_x + 460, panel_y + 230),
                artist,
                fill=(210, 210, 210),
                font=FONTS["artist"],
            )

            # ===== MAIN PROGRESS =====
            bar_x1 = panel_x + 460
            bar_x2 = panel_x + 940
            bar_y = panel_y + 310

            draw.line(
                [(bar_x1, bar_y), (bar_x2, bar_y)],
                fill=(180, 180, 180),
                width=7,
            )

            progress = bar_x1 + 280
            draw.line(
                [(bar_x1, bar_y), (progress, bar_y)],
                fill="white",
                width=7,
            )

            draw.text(
                (bar_x1, bar_y - 35),
                "0:24",
                fill="white",
                font=FONTS["small"],
            )

            draw.text(
                (bar_x2 - 70, bar_y - 35),
                song.duration or "--:--",
                fill="white",
                font=FONTS["small"],
            )

            # ===== CONTROLS =====
            try:
                controls = Image.open("anony/assets/controls.png").convert("RGBA")
                controls = controls.resize((740, 210), Image.Resampling.LANCZOS)

                bg.paste(
                    controls,
                    (panel_x + 160, panel_y + 360),
                    controls
                )
            except:
                pass

            # ===== VOLUME BAR =====
            vol_y = panel_y + 560

            draw.line(
                [(panel_x + 220, vol_y),
                 (panel_x + 940, vol_y)],
                fill=(150, 150, 150),
                width=6,
            )

            draw.line(
                [(panel_x + 220, vol_y),
                 (panel_x + 560, vol_y)],
                fill=(230, 230, 230),
                width=6,
            )

            bg.save(save_path, "PNG", quality=95)
            return save_path

        except Exception as e:
            logger.warning("Thumbnail generation failed: %s", e)
            return config.DEFAULT_THUMB
