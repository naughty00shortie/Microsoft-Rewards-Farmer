import contextlib
import logging
import time
import urllib.parse

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from src.browser import Browser


class Login:
    def __init__(self, browser: Browser):
        self.browser = browser
        self.webdriver = browser.webdriver
        self.utils = browser.utils

    def login(self):
        logging.info("[LOGIN] " + "Logging-in...")
        try:
            self.webdriver.get("https://login.live.com/")
            time.sleep(5)
            logging.info("[LOGIN] " + "Navigated to login page.")
        except Exception as e:
            logging.error("[LOGIN] " + "Failed to navigate to login page: " + str(e))
            return
        alreadyLoggedIn = False
        while True:
            try:
                self.utils.waitUntilVisible(
                    By.CSS_SELECTOR, 'html[data-role-name="MeePortal"]', 0.1
                )
                alreadyLoggedIn = True
                break
            except Exception:  # pylint: disable=broad-except
                try:
                    self.utils.waitUntilVisible(By.ID, "i0116", 4)
                    break
                except Exception:  # pylint: disable=broad-except
                    if self.utils.tryDismissAllMessages():
                        continue

        if not alreadyLoggedIn:
            self.executeLogin()
        self.utils.tryDismissCookieBanner()

        logging.info("[LOGIN] " + "Logged-in !")

        self.utils.goHome()
        points = self.utils.getAccountPoints()

        logging.info("[LOGIN] " + "Ensuring login on Bing...")
        self.checkBingLogin()
        logging.info("[LOGIN] Logged-in successfully !")
        return points

    def executeLogin(self):
        self.utils.waitUntilVisible(By.ID, "i0116", 10)
        logging.info("[LOGIN] " + "Writing email...")
        self.webdriver.find_element(By.NAME, "loginfmt").send_keys(
            self.browser.username
        )
        self.webdriver.find_element(By.ID, "idSIButton9").click()

        try:
            self.enterPassword(self.browser.password)
        except Exception:  # pylint: disable=broad-except
            logging.error("[LOGIN] " + "2FA required !")
            with contextlib.suppress(Exception):
                code = self.webdriver.find_element(
                    By.ID, "idRemoteNGC_DisplaySign"
                ).get_attribute("innerHTML")
                logging.error("[LOGIN] " + f"2FA code: {code}")
            logging.info("[LOGIN] Press enter when confirmed...")
            input()

        while not (
                urllib.parse.urlparse(self.webdriver.current_url).path == "/"
                and urllib.parse.urlparse(self.webdriver.current_url).hostname
                == "account.microsoft.com"
        ):
            self.utils.tryDismissAllMessages()
            time.sleep(1)

        self.utils.waitUntilVisible(
            By.CSS_SELECTOR, 'html[data-role-name="MeePortal"]', 10
        )

    def enterPassword(self, password):
        self.utils.waitUntilClickable(By.NAME, "passwd", 10)
        time.sleep(5)
        self.utils.waitUntilClickable(By.ID, "idSIButton9", 10)
        time.sleep(5)
        # browser.webdriver.find_element(By.NAME, "passwd").send_keys(password)
        # If password contains special characters like " ' or \, send_keys() will not work
        password = password.replace("\\", "\\\\").replace('"', '\\"')

        logging.info("[LOGIN] " + "Writing password...")
        password_field = self.webdriver.find_element(By.NAME, "passwd")

        while True:
            password_field.send_keys(password)
            time.sleep(3)
            if password_field.get_attribute("value") == password:
                self.webdriver.find_element(By.ID, "idSIButton9").click()
                break

            password_field.clear()
            time.sleep(3)

    def checkBingLogin(self):
        self.webdriver.get(
            "https://www.bing.com/fd/auth/signin?action=interactive&provider=windows_live_id&return_url=https%3A%2F%2Fwww.bing.com%2F"
        )
        while True:
            currentUrl = urllib.parse.urlparse(self.webdriver.current_url)
            if currentUrl.hostname == "www.bing.com" and currentUrl.path == "/":
                time.sleep(3)
                self.utils.tryDismissBingCookieBanner()
                with contextlib.suppress(Exception):
                    if self.utils.checkBingLogin():
                        return
            time.sleep(1)
