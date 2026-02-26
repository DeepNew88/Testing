import os
import aiohttp
from io import BytesIO
from PIL import (
    Image,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageFont,
    ImageOps,
)

from anony import config
from anony.helpers import Track


class Thumbnail:
    def __init__(self):
        self.size = (1280, 720)
        self.font_title = ImageFont.truetype(
            "anony/helpers/Raleway-Bold.ttf", 40
        )
        self.font_channel = ImageFont.truetype(
            "anony/helpers/Inter-Light.ttf", 30
        )

    async def fetch_image(self, url: str) -> Image.Image:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.read()
            return Image.open(BytesIO(data)).convert("RGBA")
        except Exception:
            return Image.new("RGBA", self.size, (30, 30, 30, 255))

    def resize_crop(self, img: Image.Image) -> Image.Image:
        img = img.resize(self.size, Image.Resampling.LANCZOS)
        return img

    def rounded_cover(self, image: Image.Image, size=(220, 220)) -> Image.Image:
        image = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
        mask = Image.new("L", size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, size[0], size[1]), radius=25, fill=255
        )
        image.putalpha(mask)
        return image

    async def generate(self, song: Track) -> str:
    try:
        output = f"cache/{song.id}.png"
        if os.path.exists(output):
            return output

        size = (1280, 720)

        # 🔹 Fetch thumbnail
        thumb = await self.fetch_image(song.thumbnail)
        bg = thumb.resize(size, Image.Resampling.LANCZOS)

        # 🔹 Blur + Dark
        bg = bg.filter(ImageFilter.GaussianBlur(35))
        bg = ImageEnhance.Brightness(bg).enhance(0.5)

        # 🔹 Glass Panel
        panel = Image.new("RGBA", (900, 450), (30, 30, 30, 160))
        mask = Image.new("L", panel.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, 900, 450), radius=40, fill=255
        )
        panel.putalpha(mask)

        panel_x = (size[0] - 900) // 2
        panel_y = (size[1] - 450) // 2

        bg.paste(panel, (panel_x, panel_y), panel)

        # 🔹 Rounded Cover
        cover = ImageOps.fit(thumb, (250, 250), Image.Resampling.LANCZOS)
        cover_mask = Image.new("L", (250, 250), 0)
        ImageDraw.Draw(cover_mask).rounded_rectangle(
            (0, 0, 250, 250), radius=30, fill=255
        )
        cover.putalpha(cover_mask)

        bg.paste(
            cover,
            (panel_x + 70, panel_y + 100),
            cover,
        )

        draw = ImageDraw.Draw(bg)

        # 🔹 Title
        title = song.title[:30] if song.title else "Unknown"
        draw.text(
            (panel_x + 360, panel_y + 120),
            title,
            fill="white",
            font=self.font1,
        )

        # 🔹 Artist
        artist = song.channel_name[:30] if song.channel_name else "Unknown"
        draw.text(
            (panel_x + 360, panel_y + 170),
            artist,
            fill=(200, 200, 200),
            font=self.font2,
        )

        # 🔹 Progress Bar
        bar_start = panel_x + 360
        bar_end = panel_x + 800
        bar_y = panel_y + 260

        draw.line(
            [(bar_start, bar_y), (bar_end, bar_y)],
            fill=(180, 180, 180),
            width=6,
        )

        # Fake progress
        progress = bar_start + 200
        draw.line(
            [(bar_start, bar_y), (progress, bar_y)],
            fill="white",
            width=6,
        )

        # 🔹 Controls
        controls = "⏮     ⏯     ⏭"
        draw.text(
            (panel_x + 430, panel_y + 310),
            controls,
            fill="white",
            font=self.font1,
        )

        os.makedirs("cache", exist_ok=True)
        bg.save(output, "PNG")
        return output

    except Exception:
        return config.DEFAULT_THUMB
