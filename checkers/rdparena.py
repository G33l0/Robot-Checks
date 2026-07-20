"""
Checker for RDP Arena (www.rdparena.com)
Author: IamG2
"""
import requests
from typing import Tuple

# Service endpoints
BASE_URL = "https://www.rdparena.com/"
LOGIN_URL = BASE_URL + "payments/login"

# Request timeout (seconds)
TIMEOUT = 15

def check(email: str, password: str) -> Tuple[bool, str]:
    """
    Attempt login to RDP Arena via the /payments/login endpoint.
    Returns (success: bool, message: str)
    """
    try:
        # Prepare login payload – adjust field names if needed
        # Common ones: 'email', 'password', 'username', etc.
        payload = {
            "email": email,
            "password": password
        }

        # Optional headers – some services require a User-Agent
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*"
        }

        # POST request with redirects disabled to catch redirection
        response = requests.post(
            LOGIN_URL,
            data=payload,
            headers=headers,
            timeout=TIMEOUT,
            allow_redirects=False
        )

        # --- Determine success based on response ---

        # 1. HTTP 302/301 redirect usually means login success
        if response.status_code in (301, 302):
            # Check if redirect location is a dashboard or home
            location = response.headers.get("Location", "")
            if "dashboard" in location.lower() or "account" in location.lower() or "home" in location.lower():
                return True, "Login successful (redirect to dashboard)"
            else:
                return True, f"Login successful (redirect to {location})"

        # 2. HTTP 200 – examine JSON or HTML
        if response.status_code == 200:
            # Try to parse as JSON
            try:
                data = response.json()
                # Look for success indicator – common keys: 'status', 'success', 'message'
                if data.get("status") == "success" or data.get("success") is True:
                    return True, "Login successful (JSON response)"
                else:
                    # If there is an error message, return it
                    error_msg = data.get("message") or data.get("error") or "Invalid credentials"
                    return False, f"Login failed: {error_msg}"
            except ValueError:
                # Not JSON – check HTML for typical success messages
                html = response.text.lower()
                if "welcome" in html or "dashboard" in html or "logout" in html:
                    return True, "Login successful (HTML content)"
                elif "invalid" in html or "incorrect" in html or "error" in html:
                    return False, "Login failed (HTML indicates error)"
                else:
                    # Ambiguous – we can treat as failure or success based on context
                    # Safer to treat as failure unless we are certain
                    return False, "Login response ambiguous (no clear success indicator)"

        # 3. Other status codes (400, 401, 403, 500, etc.)
        else:
            return False, f"HTTP {response.status_code}: {response.reason}"

    except requests.exceptions.Timeout:
        return False, "Request timed out"
    except requests.exceptions.ConnectionError:
        return False, "Connection error (check network or URL)"
    except requests.exceptions.RequestException as e:
        return False, f"Request error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"