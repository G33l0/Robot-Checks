#!/usr/bin/env python3
"""
Robot-Checks v1.3 - Multi-Checker Tool
Author: IamG2
Features: dynamic checkers, concurrency, proxy rotation, delay, color UI,
          separate output files per checker with timestamps,
          graceful Ctrl+C handling, Python 3.6+ compatible,
          adaptive banner for all screen sizes.
"""
import os
import sys
import json
import time
import random
import threading
import queue
import importlib.util
import traceback
import shutil          # for terminal size
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from typing import Dict, List, Callable, Optional, Tuple

# ---------- Check for required libraries ----------
try:
    import colorama
    from colorama import Fore, Style, init as colorama_init
    import pyfiglet
    import requests
except ImportError as e:
    print("Missing required libraries. Please install:")
    print("  pip install colorama pyfiglet requests")
    sys.exit(1)

colorama_init(autoreset=True)

# ---------- Constants ----------
CONFIG_FILE = "config.json"
CHECKERS_FOLDER = "checkers"
OUTPUT_DIR = "output"
VERSION = "1.3"
DEFAULT_CONFIG = {
    "input_file": "input.txt",
    "threads": 10,
    "timeout": 10,
    "verbose": False,
    "delay": 0.5,
    "proxy_file": "proxies.txt"
}

# ---------- Configuration Manager ----------
class ConfigManager:
    def __init__(self, config_path: str = CONFIG_FILE):
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self) -> Dict:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                print(f"{Fore.YELLOW}Warning: Could not read config. Using defaults.")
        return DEFAULT_CONFIG.copy()

    def save_config(self):
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
        except IOError as e:
            print(f"{Fore.RED}Error saving config: {e}")

    def get(self, key: str, default=None):
        return self.config.get(key, default)

    def set(self, key: str, value):
        self.config[key] = value
        self.save_config()

# ---------- Proxy Manager (thread-safe) ----------
class ProxyManager:
    def __init__(self, proxy_file: str = None):
        self.proxies = []
        self.lock = threading.Lock()
        self.current_index = 0
        if proxy_file and os.path.exists(proxy_file):
            try:
                with open(proxy_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            self.proxies.append(line)
                if self.proxies:
                    print(f"{Fore.GREEN}Loaded {len(self.proxies)} proxies from {proxy_file}")
                else:
                    print(f"{Fore.YELLOW}No valid proxies found in {proxy_file}")
            except Exception as e:
                print(f"{Fore.RED}Error reading proxy file: {e}")

    def get_proxy(self) -> Optional[str]:
        """Return next proxy in round-robin fashion (thread-safe)."""
        if not self.proxies:
            return None
        with self.lock:
            proxy = self.proxies[self.current_index % len(self.proxies)]
            self.current_index += 1
            return proxy

# ---------- Checker Loader ----------
class CheckerLoader:
    def __init__(self, folder: str = CHECKERS_FOLDER):
        self.folder = folder
        self.checkers: Dict[str, Callable] = {}
        self._ensure_folder()
        self.load_checkers()

    def _ensure_folder(self):
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)
            sample_path = os.path.join(self.folder, "example.py")
            with open(sample_path, 'w') as f:
                f.write('''\
"""
Sample checker - replace with real logic.
"""
import time
def check(email: str, password: str):
    # Simulate work
    time.sleep(1)
    if "@" in email and len(password) > 3:
        return True, "Valid (simulated)"
    return False, "Invalid (simulated)"
''')
            print(f"{Fore.GREEN}Created sample checker in {sample_path}")

    def load_checkers(self):
        self.checkers.clear()
        for filename in os.listdir(self.folder):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                filepath = os.path.join(self.folder, filename)
                try:
                    spec = importlib.util.spec_from_file_location(module_name, filepath)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        if hasattr(module, 'check') and callable(module.check):
                            self.checkers[module_name] = module.check
                        else:
                            print(f"{Fore.YELLOW}Warning: {module_name} has no 'check' function.")
                except Exception as e:
                    print(f"{Fore.RED}Error loading {module_name}: {e}")
        if not self.checkers:
            print(f"{Fore.YELLOW}No checkers found. Add .py files to '{self.folder}/' with a 'check' function.")
        else:
            print(f"{Fore.CYAN}Loaded {len(self.checkers)} checker(s): {', '.join(self.checkers.keys())}")

    def list_checkers(self) -> List[str]:
        return list(self.checkers.keys())

    def get_checker(self, name: str) -> Optional[Callable]:
        return self.checkers.get(name)

# ---------- Checker Runner ----------
class CheckerRunner:
    def __init__(self, checker_func: Callable, checker_name: str, config: ConfigManager):
        self.checker_func = checker_func
        self.checker_name = checker_name
        self.config = config
        self.results = []
        self.print_lock = threading.Lock()
        self.total = 0
        self.processed = 0
        self.valid_count = 0
        self.invalid_count = 0
        self.proxy_manager = None
        proxy_file = config.get("proxy_file")
        if proxy_file and os.path.exists(proxy_file):
            self.proxy_manager = ProxyManager(proxy_file)
        elif proxy_file:
            print(f"{Fore.YELLOW}Proxy file '{proxy_file}' not found. Proceeding without proxies.")

        # Create output directory
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)

        # Generate timestamp and file paths
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.valid_file = os.path.join(OUTPUT_DIR, f"valid-{checker_name}-{self.timestamp}.txt")
        self.invalid_file = os.path.join(OUTPUT_DIR, f"invalid-{checker_name}-{self.timestamp}.txt")

        # Open files for writing (thread-safe with lock)
        self.valid_fh = open(self.valid_file, 'w')
        self.invalid_fh = open(self.invalid_file, 'w')
        # Write header
        self.valid_fh.write(f"# Valid results for {checker_name} - {datetime.now().ctime()}\n")
        self.invalid_fh.write(f"# Invalid results for {checker_name} - {datetime.now().ctime()}\n")

    def _print_result(self, email: str, password: str, success: bool, message: str):
        with self.print_lock:
            self.processed += 1
            status = f"{Fore.GREEN}[+] VALID" if success else f"{Fore.RED}[-] INVALID"
            line = f"{status} {email}:{password} -> {message}"
            print(line)

            # Write to appropriate file
            if success:
                self.valid_fh.write(f"{email}:{password} -> {message}\n")
                self.valid_fh.flush()
                self.valid_count += 1
            else:
                self.invalid_fh.write(f"{email}:{password} -> {message}\n")
                self.invalid_fh.flush()
                self.invalid_count += 1

            self.results.append((email, password, success, message))

    def close_files(self):
        """Close output file handles."""
        if hasattr(self, 'valid_fh') and not self.valid_fh.closed:
            self.valid_fh.close()
        if hasattr(self, 'invalid_fh') and not self.invalid_fh.closed:
            self.invalid_fh.close()

    def run(self, credentials: List[Tuple[str, str]]) -> Dict:
        self.total = len(credentials)
        self.processed = 0
        self.valid_count = 0
        self.invalid_count = 0
        self.results = []

        threads = self.config.get("threads", 10)
        timeout = self.config.get("timeout", 10)
        delay = self.config.get("delay", 0)

        print(f"\n{Fore.CYAN}Starting checks with {threads} threads (timeout={timeout}s, delay={delay}s)...")
        print(f"{Fore.CYAN}Total credentials: {self.total}\n")

        executor = ThreadPoolExecutor(max_workers=threads)
        future_to_cred = {}
        try:
            for email, password in credentials:
                future = executor.submit(self._check_one, email, password, timeout, delay)
                future_to_cred[future] = (email, password)

            # Process results as they complete
            for future in as_completed(future_to_cred):
                email, password = future_to_cred[future]
                try:
                    success, message = future.result(timeout=timeout + 5)
                except Exception as e:
                    success, message = False, f"Error: {str(e)}"
                self._print_result(email, password, success, message)

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Interrupted by user. Shutting down gracefully...")
            # Cancel pending futures
            for f in future_to_cred:
                f.cancel()
            # Shutdown executor with compatibility for Python <3.9
            if hasattr(executor, 'shutdown'):
                try:
                    executor.shutdown(wait=False, cancel_futures=True)
                except TypeError:
                    # Python <3.9: cancel_futures not supported
                    executor.shutdown(wait=False)
            else:
                # Very old Python fallback
                executor.shutdown(wait=False)
            raise  # Re-raise to let main handler catch and exit

        except Exception as e:
            # Unexpected error: ensure files are closed before re-raising
            self.close_files()
            raise

        finally:
            self.close_files()

        # Normal completion: show summary
        summary = {
            "total": self.total,
            "valid": self.valid_count,
            "invalid": self.invalid_count,
            "success_rate": f"{self.valid_count/self.total*100:.2f}%" if self.total > 0 else "0%"
        }
        print(f"\n{Fore.CYAN}=== Check Complete ===")
        print(f"{Fore.GREEN}Valid: {self.valid_count}")
        print(f"{Fore.RED}Invalid: {self.invalid_count}")
        print(f"{Fore.YELLOW}Total: {self.total}")
        print(f"{Fore.CYAN}Success rate: {summary['success_rate']}")
        print(f"{Fore.CYAN}Valid results saved to: {self.valid_file}")
        print(f"{Fore.CYAN}Invalid results saved to: {self.invalid_file}")
        return summary

    def _check_one(self, email: str, password: str, timeout: int, delay: float) -> Tuple[bool, str]:
        """Single check with proxy assignment, delay, and timeout enforcement."""
        # Set thread-local proxy
        proxy = self.proxy_manager.get_proxy() if self.proxy_manager else None
        threading.current_thread().proxy = proxy

        # Apply delay with jitter
        if delay > 0:
            jitter = random.uniform(0.8, 1.2)
            time.sleep(delay * jitter)

        result_queue = queue.Queue()

        def target():
            try:
                success, msg = self.checker_func(email, password)
                result_queue.put((success, msg))
            except Exception as e:
                result_queue.put((False, f"Exception: {str(e)}"))

        t = threading.Thread(target=target, daemon=True)
        t.start()
        t.join(timeout)
        if t.is_alive():
            return False, f"Timeout after {timeout}s"
        try:
            return result_queue.get_nowait()
        except queue.Empty:
            return False, "Unknown error"

# ---------- UI ----------
class RobotChecksUI:
    def __init__(self):
        self.config = ConfigManager()
        self.loader = CheckerLoader()
        self.running = True

    def banner(self):
        # Clear screen with fallback
        try:
            os.system('cls' if os.name == 'nt' else 'clear')
        except:
            pass

        # Determine terminal width for adaptive banner
        try:
            term_width = shutil.get_terminal_size().columns
        except:
            term_width = 80  # fallback

        # Choose figlet font based on width
        if term_width < 80:
            font = "standard"   # narrower, more compact
        else:
            font = "slant"      # classic wide

        try:
            fig = pyfiglet.Figlet(font=font, width=term_width)
            banner_text = fig.renderText('Robot-Checks')
        except:
            banner_text = "Robot-Checks\n"

        # Print with colors
        print(Fore.RED + banner_text)
        print(Fore.WHITE + f"                    v{VERSION} - Multi-Checker Tool\n")
        print(Fore.YELLOW + "                              Author: IamG2")
        print(Fore.CYAN + "=" * 60)
        print(Fore.CYAN + "Multi-Checker Tool - Expandable & Colorful")
        print(Fore.CYAN + "=" * 60 + "\n")

    def main_menu(self):
        while self.running:
            self.banner()
            print(f"{Fore.WHITE}Main Menu:")
            print(f"  {Fore.CYAN}1. Checkers")
            print(f"  {Fore.CYAN}2. Config")
            print(f"  {Fore.CYAN}3. Exit")
            choice = input(f"{Fore.YELLOW}Select option [1-3]: ").strip()
            if choice == "1":
                self.checkers_menu()
            elif choice == "2":
                self.config_menu()
            elif choice == "3":
                self.running = False
                print(f"{Fore.GREEN}Goodbye!")
            else:
                print(f"{Fore.RED}Invalid choice.")
                input("Press Enter to continue.")

    def checkers_menu(self):
        while True:
            self.banner()
            checkers = self.loader.list_checkers()
            if not checkers:
                print(f"{Fore.YELLOW}No checkers available. Please add checker modules to '{CHECKERS_FOLDER}/'")
                input("Press Enter to return.")
                return

            print(f"{Fore.WHITE}Available Checkers:")
            for idx, name in enumerate(checkers, 1):
                print(f"  {Fore.CYAN}{idx}. {name}")
            print(f"  {Fore.CYAN}0. Back to Main Menu")
            choice = input(f"{Fore.YELLOW}Select checker [0-{len(checkers)}]: ").strip()
            if choice == "0":
                return
            if choice.isdigit() and 1 <= int(choice) <= len(checkers):
                checker_name = checkers[int(choice)-1]
                self.run_checker(checker_name)
            else:
                print(f"{Fore.RED}Invalid choice.")
                input("Press Enter to continue.")

    def run_checker(self, checker_name: str):
        checker_func = self.loader.get_checker(checker_name)
        if not checker_func:
            print(f"{Fore.RED}Checker '{checker_name}' not found.")
            input("Press Enter to continue.")
            return

        default_input = self.config.get("input_file", "input.txt")
        input_file = input(f"{Fore.YELLOW}Enter input file [{default_input}]: ").strip()
        if not input_file:
            input_file = default_input
        if not os.path.isfile(input_file):
            print(f"{Fore.RED}File not found: {input_file}")
            input("Press Enter to continue.")
            return

        try:
            with open(input_file, 'r') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"{Fore.RED}Error reading file: {e}")
            input("Press Enter to continue.")
            return

        credentials = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if ':' not in line:
                continue
            email, password = line.split(':', 1)
            credentials.append((email.strip(), password.strip()))

        if not credentials:
            print(f"{Fore.YELLOW}No valid credentials found.")
            input("Press Enter to continue.")
            return

        print(f"{Fore.CYAN}Loaded {len(credentials)} credentials.")
        confirm = input(f"{Fore.YELLOW}Start check? (y/n): ").strip().lower()
        if confirm != 'y':
            return

        runner = CheckerRunner(checker_func, checker_name, self.config)
        try:
            runner.run(credentials)
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Check interrupted by user. Exiting...")
            sys.exit(0)
        input("Press Enter to continue.")

    def config_menu(self):
        while True:
            self.banner()
            print(f"{Fore.WHITE}Configuration:")
            print(f"  {Fore.CYAN}1. Input file   : {self.config.get('input_file')}")
            print(f"  {Fore.CYAN}2. Threads      : {self.config.get('threads')}")
            print(f"  {Fore.CYAN}3. Timeout (s)  : {self.config.get('timeout')}")
            print(f"  {Fore.CYAN}4. Verbose      : {self.config.get('verbose')}")
            print(f"  {Fore.CYAN}5. Delay (s)    : {self.config.get('delay')}")
            print(f"  {Fore.CYAN}6. Proxy file   : {self.config.get('proxy_file')}")
            print(f"  {Fore.CYAN}0. Back")
            choice = input(f"{Fore.YELLOW}Select [0-6]: ").strip()
            if choice == "0":
                return
            elif choice == "1":
                val = input("New input file path: ").strip()
                if val:
                    self.config.set("input_file", val)
            elif choice == "2":
                val = input("Number of threads (1-100): ").strip()
                if val.isdigit():
                    self.config.set("threads", int(val))
            elif choice == "3":
                val = input("Timeout in seconds: ").strip()
                if val.isdigit():
                    self.config.set("timeout", int(val))
            elif choice == "4":
                self.config.set("verbose", not self.config.get("verbose", False))
            elif choice == "5":
                val = input("Delay between requests (seconds, e.g., 0.5): ").strip()
                try:
                    if val:
                        self.config.set("delay", float(val))
                except ValueError:
                    print(f"{Fore.RED}Invalid number.")
            elif choice == "6":
                val = input("Proxy file path (leave empty to disable): ").strip()
                self.config.set("proxy_file", val if val else "")
            else:
                print(f"{Fore.RED}Invalid.")
                input("Press Enter.")

# ---------- Entry Point ----------
def main():
    try:
        ui = RobotChecksUI()
        ui.main_menu()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Interrupted. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"{Fore.RED}Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()