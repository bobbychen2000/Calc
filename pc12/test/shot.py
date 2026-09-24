"""Render the dev viewer headless and save screenshots.
usage: python3 test/shot.py out.png "query-string" [more pairs...]"""
import sys, asyncio, time
from playwright.async_api import async_playwright
async def main(pairs):
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--use-angle=swiftshader","--enable-unsafe-swiftshader","--ignore-gpu-blocklist"])
        pg = await b.new_page(viewport={"width":1400,"height":800})
        logs=[]
        pg.on("console", lambda m: logs.append(m.type+": "+m.text))
        pg.on("pageerror", lambda e: logs.append("pageerror: "+str(e)))
        for out, qs in pairs:
            await pg.goto("http://localhost:8765/web/dev.html?"+qs)
            t0=time.time()
            while time.time()-t0 < 60:
                if await pg.evaluate("window.__ready===true"): break
                await asyncio.sleep(0.2)
            info = await pg.evaluate("[window.__info, window.__err]")
            await pg.screenshot(path=out)
            print(out, info)
        for l in logs[:20]: print(l)
        await b.close()
args = sys.argv[1:]
asyncio.run(main(list(zip(args[0::2], args[1::2]))))
