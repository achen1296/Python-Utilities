import os
import time
import typing

import requests
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.remote.webdriver import WebDriver


def url_filename(url: str):
    """ Get ending filename in a URL pointing to a file"""
    last_slash = url.rfind("/")
    last_q = url.rfind("?")
    if last_q > last_slash:
        return url[last_slash + 1:last_q]
    else:
        return url[last_slash + 1:]


def download_url(url: str, file: os.PathLike = None,  **kwargs):
    """ kwargs forwarded to requests.get. If file = None, the name is inferred from the last piece of the URL """
    if file == None:
        file = url_filename(url)
    req = requests.get(url, **kwargs)
    print(f"Downloading {url} -> {file}")
    with open(file, "wb") as f:
        f.write(req.content)


def download_urls(urls: typing.Iterable[str], files: dict[str, os.PathLike] = None, wait: int = 15, **kwargs):
    """ urls should be a list defining the order to download, files a dictionary from none/some/all of the urls to the file names. kwargs passed to requests.get. """
    for url in urls:
        if files == None or url not in files:
            download_url(url, **kwargs)
        else:
            download_url(url, files[url], **kwargs)
        time.sleep(wait)


def firefox_driver(**kwargs) -> webdriver.Firefox:
    driver = webdriver.Firefox(**kwargs)
    driver.implicitly_wait(2)
    return driver


def tor_driver(**kwargs) -> webdriver.Firefox:
    tor = r'C:\Users\RhQNS\Programs\Tor Browser\TorBrowser'
    torexe = os.popen(
        tor+r'\Tor\tor.exe')
    profile = FirefoxProfile(
        tor+r'\Data\Browser\profile.default')
    profile.set_preference('network.proxy.type', 1)
    profile.set_preference('network.proxy.socks', '127.0.0.1')
    profile.set_preference('network.proxy.socks_port', 9050)
    profile.set_preference("network.proxy.socks_remote_dns", False)

    driver = webdriver.Firefox(firefox_profile=profile, **kwargs)
    driver.get("http://check.torproject.org")
    return driver


def chrome_driver(profile: str) -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    options.add_argument(
        f"user-data-dir={os.environ['LOCALAPPDATA']}\\Google\\Chrome\\User Data")
    options.add_argument(f"profile-directory={profile}")
    driver = webdriver.Chrome(
        executable_path=f"{os.environ['HOMEPATH']}\\Programs\\chromedriver.exe", options=options)
    driver.implicitly_wait(2)
    return driver


def wait_element(driver: WebDriver, css_selector: str):
    return WebDriverWait(driver, 10).until(
        expected_conditions.presence_of_element_located((By.CSS_SELECTOR, css_selector)))


def scroll_all_elements(driver: webdriver.Firefox, css_selector: str, *, interactable_selector: str = None, last_selector: str = None, wait=1) -> list[WebElement]:
    """Scrolls until no more new elements found by css_selector load or until last_selector is found and returns those elements"""
    last_len = 0
    if interactable_selector != None:
        interactable_element = driver.find_element_by_css_selector(
            interactable_selector)
    while True:
        elements = driver.find_elements_by_css_selector(
            css_selector)

        # try to find last_selector
        if last_selector != None:
            try:
                driver.find_element_by_css_selector(last_selector)
            except NoSuchElementException:
                pass
            else:
                break

        # see if more loaded
        len_elements = len(elements)
        if last_len < len_elements:
            last_len = len_elements
            if interactable_selector == None:
                elements[0].send_keys(Keys.END)
            else:
                interactable_element.send_keys(Keys.END)
            time.sleep(1)
        else:
            break

    return elements
