#  Copyright (c) 2025
#  Production Safe Httpx Client for API-based Downloads

import asyncio
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union
from urllib.parse import unquote

import aiofiles
import httpx

from config import DOWNLOADS_DIR, API_URL, API_KEY
from AnonXMusic.logging import LOGGER


@dataclass
class DownloadResult:
    success: bool
    file_path: Optional[Path] = None
    error: Optional[str] = None


class HttpxClient:
    DEFAULT_TIMEOUT = 120
    DEFAULT_DOWNLOAD_TIMEOUT = 300
    CHUNK_SIZE = 8192
    MAX_RETRIES = 2
    BACKOFF_FACTOR = 1.0

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        download_timeout: int = DEFAULT_DOWNLOAD_TIMEOUT,
        max_redirects: int = 5,
    ) -> None:
        self._timeout = timeout
        self._download_timeout = download_timeout

        self._session = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=timeout,
                read=timeout,
                write=timeout,
                pool=timeout,
            ),
            follow_redirects=True,
            max_redirects=max_redirects,
        )

    async def close(self) -> None:
        try:
            await self._session.aclose()
        except Exception as e:
            LOGGER(__name__).error("Error closing HTTP session: %s", repr(e))

    # ==========================================
    # 🔐 Auto API Key Header Injection
    # ==========================================
    @staticmethod
    def _get_headers(url: str, base_headers: dict[str, str]) -> dict[str, str]:
        headers = base_headers.copy()

        if API_URL and API_KEY and url.startswith(API_URL):
            headers["X-API-Key"] = API_KEY

        headers.setdefault("User-Agent", "AnonXMusicBot/1.0")

        return headers

    # ==========================================
    # 🌐 JSON Request (API Call)
    # ==========================================
    async def make_request(
        self,
        url: str,
        max_retries: int = MAX_RETRIES,
        backoff_factor: float = BACKOFF_FACTOR,
        **kwargs: Any,
    ) -> Optional[dict[str, Any]]:

        if not url:
            LOGGER(__name__).warning("Empty URL provided")
            return None

        headers = self._get_headers(url, kwargs.pop("headers", {}))

        for attempt in range(max_retries):
            try:
                start = time.monotonic()
                response = await self._session.get(url, headers=headers, **kwargs)
                response.raise_for_status()
                duration = time.monotonic() - start

                LOGGER(__name__).debug(
                    "Request to %s succeeded in %.2fs", url, duration
                )

                return response.json()

            except httpx.HTTPStatusError as e:
                LOGGER(__name__).warning(
                    "HTTP %s error for %s: %s",
                    e.response.status_code,
                    url,
                    e.response.text,
                )

            except httpx.RequestError as e:
                LOGGER(__name__).warning(
                    "Request failed for %s: %s", url, repr(e)
                )

            except ValueError:
                LOGGER(__name__).error(
                    "Invalid JSON response from %s", url
                )
                return None

            await asyncio.sleep(backoff_factor * (2 ** attempt))

        LOGGER(__name__).error("All retries failed for URL: %s", url)
        return None

    # ==========================================
    # 📥 File Download (Streaming)
    # ==========================================
    async def download_file(
        self,
        url: str,
        file_path: Optional[Union[str, Path]] = None,
        overwrite: bool = False,
        **kwargs: Any,
    ) -> DownloadResult:

        if not url:
            return DownloadResult(False, error="Empty URL provided")

        headers = self._get_headers(url, kwargs.pop("headers", {}))

        try:
            async with self._session.stream(
                "GET",
                url,
                timeout=self._download_timeout,
                headers=headers,
            ) as response:

                response.raise_for_status()

                if file_path is None:
                    cd = response.headers.get("Content-Disposition", "")
                    match = re.search(r'filename="?([^"]+)"?', cd)

                    filename = (
                        unquote(match.group(1))
                        if match
                        else (Path(url).name or uuid.uuid4().hex)
                    )

                    path = Path(DOWNLOADS_DIR) / filename
                else:
                    path = Path(file_path)

                if path.exists() and not overwrite:
                    return DownloadResult(True, file_path=path)

                path.parent.mkdir(parents=True, exist_ok=True)

                async with aiofiles.open(path, "wb") as f:
                    async for chunk in response.aiter_bytes(self.CHUNK_SIZE):
                        await f.write(chunk)

                LOGGER(__name__).debug("Downloaded file to %s", path)

                return DownloadResult(True, file_path=path)

        except Exception as e:
            error_msg = f"Download failed for {url}: {repr(e)}"
            LOGGER(__name__).error(error_msg)
            return DownloadResult(False, error=error_msg)
