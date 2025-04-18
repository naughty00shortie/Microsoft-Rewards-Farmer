import json
import logging
import random
import time
from datetime import date, timedelta,datetime

import requests
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

from src.browser import Browser


class Searches:
    def __init__(self, browser: Browser):
        self.browser = browser
        self.webdriver = browser.webdriver


    def getGoogleTrends(self, words_count: int) -> list[str]:
        """
        Retrieves Google Trends search terms via the new API (last 48 hours).
        """
        logging.debug("Starting Google Trends fetch (last 48 hours)...")
        search_terms: list[str] = []
        session = requests.Session()
        # Add common headers (you might need to adjust these based on network inspection)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        session.headers.update(headers)

        url = "https://trends.google.com/_/TrendsUi/data/batchexecute"
        payload = f'f.req=[[[i0OFE,"[null, null, \\"{self.browser.localeGeo}\\", 0, null, 48]"]]]'
        headers = {"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"}

        logging.debug(f"Sending POST request to {url}")
        try:
            response = session.post(url, headers=headers, data=payload)
            response.raise_for_status()
            logging.debug("Response received from Google Trends API")
        except requests.RequestException as e:
            logging.error(f"Error fetching Google Trends: {e}")
            return []

        trends_data = self.extract_json_from_response(response.text)
        if not trends_data:
            logging.error("Failed to extract JSON from Google Trends response")
            return []

        logging.debug("JSON successfully extracted. Processing root terms...")

        # Process only the first element in each item
        root_terms = []
        for item in trends_data:
            try:
                topic = item[0]
                root_terms.append(topic)
            except Exception as e:
                logging.warning(f"Error processing an item: {e}")
                continue

        logging.debug(f"Extracted {len(root_terms)} root trend entries")

        # Convert to lowercase and remove duplicates
        search_terms = list(set(term.lower() for term in root_terms))
        logging.debug(f"Found {len(search_terms)} unique search terms")

        if words_count < len(search_terms):
            logging.debug(f"Limiting search terms to {words_count} items")
            search_terms = search_terms[:words_count]

        logging.debug("Google Trends fetch complete")
        return search_terms

    def extract_json_from_response(self, text: str):
        """
        Extracts the nested JSON object from the API response.
        """
        logging.debug("Extracting JSON from API response")
        for line in text.splitlines():
            trimmed = line.strip()
            if trimmed.startswith('[') and trimmed.endswith(']'):
                try:
                    intermediate = json.loads(trimmed)
                    data = json.loads(intermediate[0][2])
                    logging.debug("JSON extraction successful")
                    return data[1]
                except Exception as e:
                    logging.warning(f"Error parsing JSON: {e}")
                    continue
        logging.error("No valid JSON found in response")
        return None

    def getRelatedTerms(self, word: str) -> list:
        try:
            r = requests.get(
                f"https://api.bing.com/osjson.aspx?query={word}",
                headers={"User-agent": self.browser.userAgent},
            )
            return r.json()[1]
        except Exception:  # pylint: disable=broad-except
            return []

    def bingSearches(self, numberOfSearches: int, pointsCounter: int = 0):
        sectionSearches = 3
        logging.info(
            "[BING] "
            + f"Starting {self.browser.browserType.capitalize()} Edge Bing searches...",
        )

        i = 0
        search_terms = self.getGoogleTrends(numberOfSearches)
        for word in search_terms:
            i += 1
            if i < numberOfSearches:
                logging.info("[BING] " + f"{i}/{sectionSearches} still need to search {numberOfSearches-i} time(s)")
            else:
                logging.info("[BING] " + f"{i}/{numberOfSearches+1} still need to search {numberOfSearches-i} time(s)")
            points = self.bingSearch(word)
            time.sleep(60)
            if points <= pointsCounter:
                relatedTerms = self.getRelatedTerms(word)[:2]
                for term in relatedTerms:
                    points = self.bingSearch(term)
                    if not points <= pointsCounter:
                        break
            if points > 0:
                pointsCounter = points
            else:
                time.sleep(100)
                break
            if i >= sectionSearches:
                time.sleep(100)
                return pointsCounter, numberOfSearches - i
        logging.info(
            f"[BING] Finished {self.browser.browserType.capitalize()} Edge Bing searches !"
        )
        return pointsCounter, 0

    def bingSearch(self, word: str):
        errorCounter = 0
        while True:
            try:
                self.webdriver.get("https://bing.com")
                self.browser.utils.waitUntilClickable(By.ID, "sb_form_q")
                searchbar = self.webdriver.find_element(By.ID, "sb_form_q")
                searchbar.send_keys(word)
                searchbar.submit()
                time.sleep(20)
                return self.browser.utils.getBingAccountPoints()
            except TimeoutException:
                logging.error("[BING] " + "Timeout, retrying in 5 seconds...")
                errorCounter += 1
                if errorCounter >= 3:
                    logging.error("[BING] " + "Too many timeouts, exiting.")
                    return
                time.sleep(5)
                continue
