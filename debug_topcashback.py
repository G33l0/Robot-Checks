#!/usr/bin/env python3
"""
Debug script for TopCashback login - captures full HTML and network details.
Requires: pip install playwright && playwright install chromium
"""
import asyncio
from playwright.async_api import async_playwright

EMAIL = "melissameckley2019@gmail.com"
PASSWORD = "Password@2026"
LOGIN_URL = "https://www.topcashback.com/logon/?RedirectURL=%2Fhome%2F"

async def debug_login():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Set to True for headless
        context = await browser.new_context()
        page = await context.new_page()

        # Capture network requests
        request_data = {}
        response_data = {}

        page.on("request", lambda request: request_data.update({
            request.url: {
                "method": request.method,
                "headers": request.headers,
                "post_data": request.post_data
            }
        }))

        page.on("response", lambda response: response_data.update({
            response.url: {
                "status": response.status,
                "headers": response.headers,
                "body": None  # Will be filled later
            }
        }))

        # Navigate to login page
        print(f"Navigating to: {LOGIN_URL}")
        await page.goto(LOGIN_URL, wait_until="networkidle")

        # Wait for login form
        await page.wait_for_selector("input[type='email'], input[name='email'], input[name='username'], input#email", timeout=10000)

        # Fill credentials - try common field names
        email_field = await page.query_selector("input[type='email'], input[name='email'], input[name='username'], input#email")
        if email_field:
            await email_field.fill(EMAIL)
        else:
            print("Email field not found!")

        password_field = await page.query_selector("input[type='password']")
        if password_field:
            await password_field.fill(PASSWORD)
        else:
            print("Password field not found!")

        # Click login button - try common selectors
        login_button = await page.query_selector("button[type='submit'], input[type='submit'], button:has-text('Log in'), button:has-text('Sign in')")
        if login_button:
            await login_button.click()
        else:
            print("Login button not found!")

        # Wait for navigation
        await page.wait_for_load_state("networkidle", timeout=15000)

        # Get final URL
        final_url = page.url
        print(f"\nFinal URL: {final_url}")

        # Get full HTML
        html = await page.content()
        print("\n--- FULL HTML ---")
        print(html)

        # Get cookies
        cookies = await context.cookies()
        print("\n--- COOKIES ---")
        for cookie in cookies:
            print(f"{cookie['name']}: {cookie['value']}")

        # Get network request details
        print("\n--- NETWORK REQUESTS ---")
        for url, data in request_data.items():
            if "logon" in url or "login" in url or "auth" in url:
                print(f"\nURL: {url}")
                print(f"Method: {data['method']}")
                print(f"Headers: {data['headers']}")
                print(f"Post Data: {data['post_data']}")

        print("\n--- NETWORK RESPONSES ---")
        for url, data in response_data.items():
            if "logon" in url or "login" in url or "auth" in url:
                print(f"\nURL: {url}")
                print(f"Status: {data['status']}")
                print(f"Headers: {data['headers']}")

        # Save HTML to file
        with open("topcashback_response.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("\nHTML saved to topcashback_response.html")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_login())