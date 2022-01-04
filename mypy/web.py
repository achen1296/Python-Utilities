import os
import time
import typing

import requests
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, NoSuchWindowException
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


def download_url(url: str, file: os.PathLike = None,  *, output=True, **kwargs):
    """ kwargs forwarded to requests.get. If file = None, the name is inferred from the last piece of the URL """
    if file is None:
        file = url_filename(url)
    req = requests.get(url, **kwargs)
    if output:
        print(f"Downloading <{url}> -> <{file}>")
    with open(file, "wb") as f:
        f.write(req.content)


def download_urls(src_dst: dict[str, os.PathLike], *, output=True, **kwargs):
    """ src_dst should be a dictionary defining the order to download and the destination filenames. For None values, the filename is determined from the URL.

    Waits for the specified number of seconds, 15 by default, in between downloads to avoid pressuring the server.

    kwargs passed to requests.get. """
    if output:
        counter = 0
        total = len(src_dst)
    for url in src_dst:
        if output:
            counter += 1
            print(f"{counter}/{total}: ", end="")
        download_url(url, src_dst[url], output=output, **kwargs)


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


def scroll_all_elements(driver: WebDriver, css_selector: str, *, interactable_selector: str = None, last_selector: str = None, wait=1) -> list[WebElement]:
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


class PageReader:
    """Reads a webpage to search for links to download or open."""

    def can_read(self, driver: WebDriver) -> bool:
        """Whether or not the current page is readable by this PageReader."""
        return True

    def to_download(self, driver: WebDriver) -> dict[str, os.PathLike]:
        """Returns a dictionary with URLs from the current page to download as keys and the destination filenames as values . The default implementation returns all img element src attributes."""
        images: list[WebElement] = driver.find_elements_by_css_selector(
            "img")
        download_dict = {}
        for i in images:
            if i is not None:
                src = i.get_attribute("src")
                # use default
                download_dict[src] = None
        return download_dict

    def to_open(self, driver: WebDriver) -> list[str]:
        """Returns a list of URLs from the current page to open next. The default implemenation returns all a element href attributes."""
        links: list[WebElement] = driver.find_elements_by_css_selector(
            "a")
        urls = [l.get_attribute("href") for l in links]
        return [u for u in urls if u is not None]


class PageBrowser:
    """Uses a set of PageReaders to browse."""

    def __init__(self, driver: WebDriver, readers: typing.Iterable[PageReader]):
        self.driver = driver
        self.readers = set(readers)

    def open(self):
        """Open all links found on the current page by any PageReader. Returns the number of links opened."""
        count = 0
        current = self.driver.current_window_handle
        for r in self.readers:
            if r.can_read(self.driver):
                for url in r.to_open(self.driver):
                    count += 1
                    self.driver.execute_script("window.open('')")
                    # switch to last, i.e. newest, window
                    self.driver.switch_to.window(
                        self.driver.window_handles[-1])
                    self.driver.get(url)
            self.driver.switch_to.window(current)
        return count

    def download(self, output=True):
        """Download everything on the current page found by any PageReader. Returns the number of downloads."""
        count = 0
        for r in self.readers:
            if r.can_read(self.driver):
                d = r.to_download(self.driver)
                download_urls(d, output=output)
                count += len(d)
        return count

    def download_all(self, output=True, close_tabs: bool = True):
        """Download everything on all open tabs found by any PageReader. Optionally closes each page after doing so if anything was downloaded. Returns the number of downloads."""
        try:
            current = self.driver.current_window_handle
        except NoSuchWindowException:
            # window being controlled was closed
            current = None
        for handle in self.driver.window_handles:
            self.driver.switch_to.window(handle)
            self.download(output)
            if close_tabs and len(self.driver.window_handles) > 1:
                self.driver.close()
        if current in self.driver.window_handles:
            self.driver.switch_to.window(current)
