# -*- coding: utf-8 -*-

import os
import threading
import time
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import (
    AF_IDS_PASSWORD,
    AF_IDS_USERNAME,
    AUTOFUN_BASE_URL,
    CATALOG_CHROME_PROFILE_DIR,
    CATALOG_DEBUG_DIR,
    CHROME_BIN,
    CHROMEDRIVER_PATH,
)
from .filter_helpers import (
    SELECTORS,
    clickable_ancestor,
    debug_log,
    find_client_group_field,
    safe_click,
    save_debug_screenshot,
    select_searchable_quasar_option,
    wait_overlay_gone,
)
from .runtime_settings import is_catalog_search_headless


class CrmSession:
    def __init__(self) -> None:
        self._driver = None
        self._wait = None
        self.lock = threading.Lock()
        self.debug_dir = Path(CATALOG_DEBUG_DIR)

    @property
    def driver(self):
        if self._driver is None:
            self._driver = self._create_driver()
            self._wait = WebDriverWait(self._driver, 25)
        return self._driver

    @property
    def wait(self) -> WebDriverWait:
        if self._wait is None:
            self._wait = WebDriverWait(self.driver, 25)
        return self._wait

    def _create_driver(self):
        import sys
        headless = is_catalog_search_headless()
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")

        if sys.platform == "win32":
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-background-networking")
            options.add_argument("--no-zygote")
            options.add_argument("--disable-features=VizDisplayCompositor")

        if headless:
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1920,1600")
            options.add_argument("--force-device-scale-factor=1")

        profile_dir = Path(CATALOG_CHROME_PROFILE_DIR).expanduser()
        if not profile_dir.is_absolute():
            profile_dir = Path.cwd() / profile_dir
        profile_dir.mkdir(parents=True, exist_ok=True)
        options.add_argument(f"--user-data-dir={profile_dir}")

        if CHROME_BIN and os.path.exists(CHROME_BIN):
            options.binary_location = CHROME_BIN

        if CHROMEDRIVER_PATH and os.path.exists(CHROMEDRIVER_PATH):
            service = Service(CHROMEDRIVER_PATH)
            driver = webdriver.Chrome(service=service, options=options)
        else:
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
            except Exception:
                driver = webdriver.Chrome(options=options)

        if headless:
            driver.set_window_size(1920, 1600)

        return driver

    def close(self) -> None:
        if self._driver is not None:
            try:
                self._driver.quit()
            except Exception as exc:
                debug_log(f"Ignore CRM driver close error: {exc}", self.debug_dir)
            finally:
                self._driver = None
                self._wait = None

    def ensure_ready(self) -> None:
        try:
            if self._looks_logged_in():
                return
            self.open_dashboard()
            if self._looks_logged_in():
                return
        except Exception:
            pass

        self.login()
        self.open_dashboard()

    def login(self) -> None:
        if not AF_IDS_PASSWORD:
            raise RuntimeError("AF_IDS_PASSWORD is required for Autofun CRM login")

        driver = self.driver
        wait = self.wait
        login_url = f"{AUTOFUN_BASE_URL.rstrip('/')}/login"

        debug_log(f"Open Autofun login: {login_url}", self.debug_dir)
        driver.get(login_url)
        self._try_accept_cookies()

        af_ids_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, SELECTORS["login"]["af_ids_button"]))
        )
        if not safe_click(driver, af_ids_button):
            raise RuntimeError("AF IDS login button is not clickable")

        username = wait.until(EC.element_to_be_clickable((By.XPATH, SELECTORS["login"]["username"])))
        username.clear()
        username.send_keys(AF_IDS_USERNAME)

        password = wait.until(EC.element_to_be_clickable((By.XPATH, SELECTORS["login"]["password"])))
        password.clear()
        password.send_keys(AF_IDS_PASSWORD)

        submit = wait.until(EC.element_to_be_clickable((By.XPATH, SELECTORS["login"]["submit"])))
        if not safe_click(driver, submit):
            raise RuntimeError("AF IDS submit button is not clickable")

        wait.until(EC.url_contains("/console"))
        wait_overlay_gone(driver, 20)
        debug_log("Autofun login OK", self.debug_dir)
        save_debug_screenshot(driver, self.debug_dir, "login_ok")

    def open_dashboard(self) -> None:
        url = f"{AUTOFUN_BASE_URL.rstrip('/')}/console/dashboard"
        debug_log(f"Open dashboard: {url}", self.debug_dir)
        self.driver.get(url)
        try:
            self.wait.until(
                EC.any_of(
                    EC.presence_of_element_located((By.XPATH, SELECTORS["shell"]["dashboard_ready"])),
                    EC.url_contains("/login"),
                )
            )
        except TimeoutException:
            save_debug_screenshot(self.driver, self.debug_dir, "dashboard_timeout")
            raise
        wait_overlay_gone(self.driver, 15)
        time.sleep(0.5)

    def open_liquids_page_fresh(self) -> None:
        """Navigate directly to the liquids page URL. Always gives a clean filter state.
        Re-authenticates automatically if the session has expired."""
        url = f"{AUTOFUN_BASE_URL.rstrip('/')}/console/liquid"
        debug_log(f"Open liquids page fresh: {url}", self.debug_dir)
        self.driver.get(url)
        try:
            self.wait.until(
                EC.any_of(
                    EC.url_contains("/console/liquid"),
                    EC.url_contains("/login"),
                )
            )
        except TimeoutException:
            save_debug_screenshot(self.driver, self.debug_dir, "liquids_fresh_timeout")
            raise RuntimeError("Timeout navigating to liquids page")

        if "/login" in (self.driver.current_url or ""):
            debug_log("Session expired on liquids navigation, re-authenticating", self.debug_dir)
            self.login()
            self.driver.get(url)
            try:
                self.wait.until(EC.url_contains("/console/liquid"))
            except TimeoutException:
                save_debug_screenshot(self.driver, self.debug_dir, "liquids_fresh_relogin_timeout")
                raise RuntimeError("Timeout opening liquids page after re-login")

        wait_overlay_gone(self.driver, 15)
        time.sleep(0.5)
        save_debug_screenshot(self.driver, self.debug_dir, "liquids_fresh_opened")

    def open_liquids_from_sidebar(self) -> None:
        self.ensure_ready()
        driver = self.driver
        wait = self.wait

        if self._is_liquids_page():
            return

        for xpath in SELECTORS["shell"]["liquids_sidebar"]:
            items = driver.find_elements(By.XPATH, xpath)
            visible = [item for item in items if item.is_displayed()]
            if not visible:
                continue

            previous_url = driver.current_url
            debug_log(f"Click sidebar Liquids via selector: {xpath}", self.debug_dir)
            click_target = clickable_ancestor(driver, visible[0])
            if not safe_click(driver, click_target):
                continue

            try:
                wait.until(
                    EC.any_of(
                        EC.url_contains("/console/liquid"),
                        EC.presence_of_element_located((By.XPATH, SELECTORS["liquids"]["results_area"])),
                        EC.presence_of_element_located((By.XPATH, SELECTORS["liquids"]["search_button"])),
                    )
                )
            except TimeoutException:
                pass

            wait_overlay_gone(driver, 20)
            time.sleep(0.5)
            if self._is_liquids_page():
                save_debug_screenshot(driver, self.debug_dir, "liquids_opened")
                return

            debug_log(
                f"Liquids click did not open /console/liquid. Previous={previous_url}, current={driver.current_url}",
                self.debug_dir,
            )

        if self._click_liquids_tab_if_open():
            save_debug_screenshot(driver, self.debug_dir, "liquids_tab_opened")
            return

        save_debug_screenshot(driver, self.debug_dir, "liquids_sidebar_not_found")
        raise RuntimeError("Не знайшов пункт меню 'Рідини' у sidebar")

    def set_client_group(self, client_group: str) -> None:
        client_group = (client_group or "").strip()
        if not client_group:
            return

        self.ensure_ready()
        driver = self.driver

        debug_log(f"Set Autofun client group: {client_group}", self.debug_dir)
        field = find_client_group_field(driver)
        select_searchable_quasar_option(driver, field, client_group, timeout=12.0)
        if is_catalog_search_headless():
            self._confirm_client_group_update_if_needed()
        wait_overlay_gone(driver, 15)
        time.sleep(0.4)
        debug_log("Set Autofun client group OK", self.debug_dir)

    def _confirm_client_group_update_if_needed(self) -> None:
        driver = self.driver
        labels = SELECTORS["shell"]["client_group_update_buttons"]
        end_at = time.time() + 8

        while time.time() < end_at:
            try:
                clicked = driver.execute_script(
                    """
                    const labels = arguments[0].map((value) => String(value).toLowerCase());
                    const visible = (el) => {
                        if (!el) return false;
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        return rect.width > 0 && rect.height > 0 &&
                            style.display !== 'none' && style.visibility !== 'hidden';
                    };
                    const candidates = Array.from(document.querySelectorAll(
                        '.q-snackbar button, .q-snackbar .q-btn, ' +
                        '.q-notification button, .q-notification .q-btn, ' +
                        '[role="alert"] button, [role="alert"] .q-btn, button, .q-btn'
                    )).filter(visible);
                    const button = candidates.find((el) => {
                        const text = String(el.innerText || el.textContent || '').trim().toLowerCase();
                        return labels.some((label) => text.includes(label));
                    });
                    if (!button) {
                        return false;
                    }
                    button.scrollIntoView({ block: 'center' });
                    for (const eventName of ['pointerdown', 'mousedown', 'mouseup', 'click']) {
                        button.dispatchEvent(new MouseEvent(eventName, {
                            bubbles: true,
                            cancelable: true,
                            view: window
                        }));
                    }
                    return true;
                    """,
                    labels,
                )
                if clicked:
                    debug_log("Confirm Autofun client group update in headless mode", self.debug_dir)
                    wait_overlay_gone(driver, 20)
                    time.sleep(2.0)
                    return
            except Exception as exc:
                debug_log(f"Ignore client group update confirmation error: {exc}", self.debug_dir)
                return
            time.sleep(0.25)

    def _try_accept_cookies(self) -> None:
        try:
            button = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, SELECTORS["login"]["cookies"]))
            )
            safe_click(self.driver, button)
        except Exception:
            pass

    def _looks_logged_in(self) -> bool:
        current_url = self.driver.current_url or ""
        if "/login" in current_url:
            return False
        try:
            self.driver.find_element(By.XPATH, SELECTORS["shell"]["dashboard_ready"])
            return "/console" in current_url
        except Exception:
            return False

    def _is_liquids_page(self) -> bool:
        current_url = self.driver.current_url or ""
        return "/console/liquid" in current_url

    def _click_liquids_tab_if_open(self) -> bool:
        driver = self.driver
        wait = self.wait
        tabs = driver.find_elements(By.XPATH, SELECTORS["shell"]["liquids_tab"])
        visible = [tab for tab in tabs if tab.is_displayed()]

        for tab in visible:
            if not safe_click(driver, tab):
                continue
            try:
                wait.until(EC.url_contains("/console/liquid"))
            except TimeoutException:
                pass
            wait_overlay_gone(driver, 15)
            time.sleep(0.5)
            if self._is_liquids_page():
                return True

        return False


_SESSION: Optional[CrmSession] = None


def get_crm_session() -> CrmSession:
    global _SESSION
    if _SESSION is None:
        _SESSION = CrmSession()
    return _SESSION


def reset_crm_session() -> None:
    global _SESSION
    session = _SESSION
    if session is None:
        return

    with session.lock:
        session.close()
    _SESSION = None
