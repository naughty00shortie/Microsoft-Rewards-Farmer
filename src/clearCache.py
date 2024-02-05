import json
from pathlib import Path
from src.browser import Browser

def clear_cache_for_account(account, args):
    with Browser(mobile=False, account=account, args=args) as desktopBrowser:
        desktopBrowser.clear_cache()

    with Browser(mobile=True, account=account, args=args) as mobileBrowser:
        mobileBrowser.clear_cache()

def load_accounts():
    accountPath = Path(__file__).resolve().parent / "accounts.json"
    if not accountPath.exists():
        print("Accounts credential file 'accounts.json' not found.")
        exit()
    return json.loads(accountPath.read_text(encoding="utf-8"))

if __name__ == "__main__":
    args = None  # Replace with your actual args
    accounts = load_accounts()
    for account in accounts:
        clear_cache_for_account(account, args)