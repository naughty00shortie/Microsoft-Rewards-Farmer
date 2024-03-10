import argparse
import json
import logging
import logging.handlers as handlers
import random
import sys
import time
import datetime
import os
from pathlib import Path

from src import Browser, DailySet, Login, MorePromotions, PunchCards, Searches, clearCache
from src.constants import VERSION
from src.loggingColoredFormatter import ColoredFormatter
from src.notifier import Notifier

POINTS_COUNTER = 0

def main():
    isFirstTime = True
    iCounter = 0
    setupLogging()
    args = argumentParser()
    notifier = Notifier(args)
    loadedAccounts = setupAccounts()
    toatlArray = [0] * len(loadedAccounts)
    isFinishedArray = [False] * len(loadedAccounts)
    while not all(isFinishedArray):
        if iCounter == 20:
            cleanupChromeProcesses()
            iCounter = 0
            restart_script()
        now = time.time()
        for index, currentAccount in enumerate(loadedAccounts):
            cleanupChromeProcesses()
            try:
                #clearCache.clear_cache_for_account(currentAccount, args)
                if not isFinishedArray[index]:
                    isFinishedArray[index], totalForToday = executeBot(currentAccount, notifier, args, toatlArray[index], isFirstTime)
                    toatlArray[index] += totalForToday
            except Exception as e:
                logging.exception(f"{e.__class__.__name__}: {e}")
        logging.info(f"{isFinishedArray.count(True)} / {len(isFinishedArray)} accounts finished")
        if not all(isFinishedArray):
            elapsed_time = time.time() - now
            if elapsed_time < 15 * 60:
                remaining_time = 15 * 60 - elapsed_time
                logging.info(f"Sleeping for {remaining_time / 60:.2f} minutes...")
                time.sleep(remaining_time)

def cleanupChromeProcesses():
    os.system("taskkill /im chrome.exe /t /f")
    os.system("taskkill /im msedge.exe /t /f")
    time.sleep(1)

def restart_script():
    python = sys.executable
    os.execl(python, python, *sys.argv)


def setupLogging():
    format = "%(asctime)s [%(levelname)s] %(message)s"
    terminalHandler = logging.StreamHandler(sys.stdout)
    terminalHandler.setFormatter(ColoredFormatter(format))

    (Path(__file__).resolve().parent / "logs").mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format=format,
        handlers=[
            handlers.TimedRotatingFileHandler(
                "logs/activity.log",
                when="midnight",
                interval=1,
                backupCount=2,
                encoding="utf-8",
            ),
            terminalHandler,
        ],
    )


def argumentParser() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Microsoft Rewards Farmer")
    parser.add_argument(
        "-v", "--visible", action="store_true", help="Optional: Visible browser"
    )
    parser.add_argument(
        "-l", "--lang", type=str, default=None, help="Optional: Language (ex: en)"
    )
    parser.add_argument(
        "-g", "--geo", type=str, default=None, help="Optional: Geolocation (ex: US)"
    )
    parser.add_argument(
        "-p",
        "--proxy",
        type=str,
        default=None,
        help="Optional: Global Proxy (ex: http://user:pass@host:port)",
    )
    parser.add_argument(
        "-t",
        "--telegram",
        metavar=("TOKEN", "CHAT_ID"),
        nargs=2,
        type=str,
        default=None,
        help="Optional: Telegram Bot Token and Chat ID (ex: 123456789:ABCdefGhIjKlmNoPQRsTUVwxyZ 123456789)",
    )
    parser.add_argument(
        "-d",
        "--discord",
        type=str,
        default=None,
        help="Optional: Discord Webhook URL (ex: https://discord.com/api/webhooks/123456789/ABCdefGhIjKlmNoPQRsTUVwxyZ)",
    )
    return parser.parse_args()


def bannerDisplay():
    farmerBanner = """
    ███╗   ███╗███████╗    ███████╗ █████╗ ██████╗ ███╗   ███╗███████╗██████╗
    ████╗ ████║██╔════╝    ██╔════╝██╔══██╗██╔══██╗████╗ ████║██╔════╝██╔══██╗
    ██╔████╔██║███████╗    █████╗  ███████║██████╔╝██╔████╔██║█████╗  ██████╔╝
    ██║╚██╔╝██║╚════██║    ██╔══╝  ██╔══██║██╔══██╗██║╚██╔╝██║██╔══╝  ██╔══██╗
    ██║ ╚═╝ ██║███████║    ██║     ██║  ██║██║  ██║██║ ╚═╝ ██║███████╗██║  ██║
    ╚═╝     ╚═╝╚══════╝    ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝"""
    logging.error(farmerBanner)
    logging.warning(
        f"        by Charles Bel (@charlesbel)               version {VERSION}\n"
    )


def setupAccounts() -> dict:
    accountPath = Path(__file__).resolve().parent / "accounts.json"
    if not accountPath.exists():
        accountPath.write_text(
            json.dumps(
                [{"username": "Your Email", "password": "Your Password"}], indent=4
            ),
            encoding="utf-8",
        )
        noAccountsNotice = """
    [ACCOUNT] Accounts credential file "accounts.json" not found.
    [ACCOUNT] A new file has been created, please edit with your credentials and save.
    """
        logging.warning(noAccountsNotice)
        exit()
    loadedAccounts = json.loads(accountPath.read_text(encoding="utf-8"))
    random.shuffle(loadedAccounts)
    return loadedAccounts


def executeBot(currentAccount, notifier: Notifier, args: argparse.Namespace, toatlArray: int, isfirstTime: bool):
    logging.info(
        f'********************{currentAccount.get("username", "")}********************'
    )
    with Browser(mobile=False, account=currentAccount, args=args) as desktopBrowser:
        desktopSearchesLeft = 0
        mobileSearchesLeft = 0
        accountPointsCounter = Login(desktopBrowser).login()
        startingPoints = accountPointsCounter
        logging.info(
            f"[POINTS] You have {desktopBrowser.utils.formatNumber(accountPointsCounter)} points on your account !"
        )
        if isfirstTime:
            DailySet(desktopBrowser).completeDailySet()
            PunchCards(desktopBrowser).completePunchCards()
        # MorePromotions(desktopBrowser).completeMorePromotions()
        (
            remainingSearches,
            remainingSearchesM,
        ) = desktopBrowser.utils.getRemainingSearches()
        if remainingSearches != 0:
            accountPointsCounter, desktopSearchesLeft = Searches(desktopBrowser).bingSearches(
                remainingSearches
            )
        else:
            desktopSearchesLeft = 0
        if remainingSearches == 0 and remainingSearchesM != 0:
            desktopBrowser.closeBrowser()
            with Browser(
                    mobile=True, account=currentAccount, args=args
            ) as mobileBrowser:
                accountPointsCounter = Login(mobileBrowser).login()
                accountPointsCounter, mobileSearchesLeft = Searches(mobileBrowser).bingSearches(
                    remainingSearchesM
                )
        else:
            mobileSearchesLeft = 20

        if remainingSearches == 0 and remainingSearchesM == 0:
            localIsFinished = True
        else:
            localIsFinished = False
        logging.info(
            f"[POINTS] You have {desktopSearchesLeft} searches left on desktop !"
        )
        logging.info(
            f"[POINTS] You have {mobileSearchesLeft} searches left on mobile !"
        )
        logging.info(
            f"Points earned in session: {desktopBrowser.utils.formatNumber(accountPointsCounter - startingPoints)}"
        )
        logging.info(
            f"Total points today: {desktopBrowser.utils.formatNumber(toatlArray + accountPointsCounter - startingPoints)}"
        )
        logging.info(
            f"[POINTS] You are now at {desktopBrowser.utils.formatNumber(accountPointsCounter)} points !\n"
        )

        notifier.send(
            "\n".join(
                [
                    f"Account: {currentAccount.get('username', '')}",
                    f"Points earned in session: {desktopBrowser.utils.formatNumber(accountPointsCounter - startingPoints)}",
                    f"Total points today: {desktopBrowser.utils.formatNumber(toatlArray + accountPointsCounter - startingPoints)}",
                    f"Searches left on desktop: {desktopSearchesLeft}",
                    f"Searches left on mobile: {mobileSearchesLeft}",
                    f"Total points: {desktopBrowser.utils.formatNumber(accountPointsCounter)}",
                    "---------------------------------------------------------",
                ]
            )
        )
        return localIsFinished, (accountPointsCounter - startingPoints)


if __name__ == "__main__":
    main()
