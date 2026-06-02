"""Browser lifecycle manager using Playwright."""

import asyncio


class BrowserManager:
    """Manages a persistent Playwright browser instance for the session."""

    def __init__(self):
        self._browser = None
        self._context = None
        self._playwright = None
        self._lock = asyncio.Lock()

    async def get_page(self):
        """Get a new browser page, reusing the browser instance."""
        async with self._lock:
            if self._browser is None:
                try:
                    from playwright.async_api import async_playwright
                except ImportError:
                    raise RuntimeError(
                        "Playwright not installed. Run: pip install playwright && playwright install chromium"
                    )
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(headless=True)
                self._context = await self._browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                )
            return await self._context.new_page()

    async def close_page(self, page):
        """Close a single page."""
        await page.close()

    async def cleanup(self):
        """Clean up all browser resources."""
        async with self._lock:
            if self._browser:
                await self._browser.close()
                await self._playwright.stop()
                self._browser = None
                self._context = None
                self._playwright = None


# Global singleton instance
browser_mgr = BrowserManager()
