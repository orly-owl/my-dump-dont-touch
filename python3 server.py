from flask import Flask, request
import asyncio
from pyppeteer import launch
import pyppeteer

app = Flask(__name__)

async def post_to_facebook(email, password, post_text):
    browser = await launch(
        headless=False,
        args=["--no-sandbox", "--disable-setuid-sandbox"],
        userDataDir="./fb_session",  # ✅ keeps you logged in
        executablePath=pyppeteer.executablePath()  # ✅ bundled Chromium
    )
    page = await browser.newPage()

    # Always go to FB home feed
    await page.goto("https://www.facebook.com/", {"waitUntil": "networkidle2"})
    await asyncio.sleep(3)

    # =========================
    # Login (if needed)
    # =========================
    try:
        email_input = await page.querySelector("#email")
        if email_input:  # login page is showing
            print("🔑 Logging in...")
            await page.type("#email", email)
            await page.type("#pass", password)
            await page.click("button[name='login']")
            await page.waitForNavigation({"waitUntil": "networkidle2"})
        else:
            print("✅ Skipping login: already logged in.")
    except Exception as e:
        print("⚠️ Login step skipped:", e)

    # =========================
    # Create Post
    # =========================
    try:
        print("📝 Trying to open post composer...")

        # Try span first
        try:
            composer_btn = await page.waitForXPath(
                "//span[contains(text(), \"What's on your mind\")]",
                {"timeout": 10000}
            )
        except:
            # Fallback to div if span not found
            composer_btn = await page.waitForXPath(
                "//div[contains(text(), \"What's on your mind\")]",
                {"timeout": 10000}
            )

        await composer_btn.click()
        await asyncio.sleep(3)

        print("⌨️ Waiting for textbox...")
        post_box = await page.waitForSelector(
            "[role='textbox']", {"visible": True, "timeout": 20000}
        )
        await post_box.type(post_text)

        # Post button (multiple possible selectors)
        post_button = await page.waitForSelector(
            "div[aria-label='Post'][role='button'], div[aria-label='Post'], [data-testid='react-composer-post-button']",
            {"visible": True, "timeout": 20000}
        )
        await page.evaluate('(el) => el.click()', post_button)

        print("📢 Post submitted!")

        # Save screenshot proof
        await page.screenshot({'path': 'proof.png'})
        print("📸 Screenshot saved as proof.png")

        await asyncio.sleep(8)

    except Exception as e:
        print("❌ ERROR posting:", e)

    await browser.close()


# =========================
# Flask webhook endpoint
# =========================
@app.route("/new-row", methods=["POST"])
def new_row():
    try:
        data = request.get_json()
        title = data.get("title")
        confession = data.get("confession")
        post_text = f"{title}\n\n{confession}"

        asyncio.run(
            post_to_facebook("your_email_here", "your_password_here", post_text)
        )
        return {"status": "posted!"}, 200

    except Exception as e:
        print("❌ ERROR:", e)
        return {"status": "error", "message": str(e)}, 500


if __name__ == "__main__":
    app.run(port=5000, debug=True, use_reloader=False, threaded=False)
