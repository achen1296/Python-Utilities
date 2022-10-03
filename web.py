import os
import time
import typing

import requests
from selenium import webdriver
from selenium.common.exceptions import (NoSuchElementException,
                                        NoSuchWindowException)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

import console


def url_filename(url: str):
    """ Get ending filename in a URL pointing to a file"""
    last_slash = url.rfind("/")
    last_q = url.rfind("?")
    if last_q > last_slash:
        return url[last_slash + 1:last_q]
    else:
        return url[last_slash + 1:]


def download_url(url: str, file: os.PathLike = None,  *, output=True, **get_kwargs):
    """ If file = None, the name is inferred from the last piece of the URL. get_kwargs passed to requests.get. """
    if file is None:
        file = url_filename(url)
    req = requests.get(url, **get_kwargs)
    if output:
        print(f"Downloading <{url}> -> <{file}>")
    with open(file, "wb") as f:
        f.write(req.content)


def download_urls(src_dst: dict[str, os.PathLike], *, output=True, wait=0, **get_kwargs):
    """ src_dst should be a dictionary defining the order to download and the destination filenames. For None values, the filename is determined from the URL.

    Waits for the specified number of seconds in between downloads as an option to avoid pressuring the server; by default does not wait.

    get_kwargs passed to requests.get. """
    if output:
        counter = 0
        total = len(src_dst)
    for url in src_dst:
        if wait > 0:
            time.sleep(wait)
        if output:
            counter += 1
            print(f"{counter}/{total}: ", end="")
        download_url(url, src_dst[url], output=output, **get_kwargs)


def firefox_driver(**webdriver_kwargs) -> webdriver.Firefox:
    driver = webdriver.Firefox(**webdriver_kwargs)
    driver.implicitly_wait(2)
    return driver


def tor_driver(**webdriver_kwargs) -> webdriver.Firefox:
    userprofile = os.environ["userprofile"]
    tor = userprofile + r'\Programs\Tor Browser\TorBrowser'
    torexe = os.popen(
        tor+r'\Tor\tor.exe')
    profile = FirefoxProfile(
        tor+r'\Data\Browser\profile.default')
    profile.set_preference('network.proxy.type', 1)
    profile.set_preference('network.proxy.socks', '127.0.0.1')
    profile.set_preference('network.proxy.socks_port', 9050)
    profile.set_preference("network.proxy.socks_remote_dns", False)

    driver = webdriver.Firefox(firefox_profile=profile, **webdriver_kwargs)
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


def wait_element(driver: WebDriver, css_selector: str, timeout: int = 10) -> WebElement:
    return WebDriverWait(driver, timeout).until(
        expected_conditions.presence_of_element_located((By.CSS_SELECTOR, css_selector)))


def wait_url(driver: WebDriver, url_contains: str, timeout: int = 10):
    return WebDriverWait(driver, timeout).until(
        expected_conditions.url_contains(url=url_contains))


def scroll_all_elements(driver: WebDriver, css_selector: str, *, interactable_selector: str = None, last_selector: str = None, wait=1) -> list[WebElement]:
    """Scrolls until no more new elements found by css_selector load or until last_selector is found and returns those elements"""
    last_len = 0
    if interactable_selector != None:
        interactable_element = driver.find_element(
            By.CSS_SELECTOR, interactable_selector)
    while True:
        elements = driver.find_elements(By.CSS_SELECTOR, css_selector)

        # try to find last_selector
        if last_selector != None:
            try:
                driver.find_element(By.CSS_SELECTOR, last_selector)
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
            time.sleep(wait)
        else:
            break

    return elements


class PageReader:
    """Reads a webpage to search for links to download or open."""

    def can_read(self, driver: WebDriver) -> bool:
        """Whether or not the current page is readable by this PageReader."""
        return True

    def to_download(self, driver: WebDriver) -> dict[str, os.PathLike]:
        """Returns a dictionary with URLs from the current page to download as keys and the destination filenames as values. The default implementation returns all img element src attributes."""
        images: list[WebElement] = driver.find_elements(By.CSS_SELECTOR, "img")
        download_dict = {}
        for i in images:
            if i is not None:
                src = i.get_attribute("src")
                # use default
                download_dict[src] = None
        return download_dict

    def to_open(self, driver: WebDriver) -> list[str]:
        """Returns a list of URLs from the current page to open next. The default implemenation returns all a element href attributes."""
        links: list[WebElement] = driver.find_elements(By.CSS_SELECTOR, "a")
        urls = [l.get_attribute("href") for l in links]
        return [u for u in urls if u is not None]


class PageBrowser:
    """Uses a set of PageReaders to browse."""

    def __init__(self, driver: WebDriver, readers: typing.Iterable[PageReader]):
        self.driver = driver
        self.readers = set(readers)

    def open(self) -> int:
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

    def download(self, output=True, **get_kwargs) -> int:
        """Download everything on the current page found by any PageReader. Returns the number of downloads. get_kwargs passed to requests.get."""
        count = 0
        for r in self.readers:
            if r.can_read(self.driver):
                d = r.to_download(self.driver)
                download_urls(d, output=output, **get_kwargs)
                count += len(d)
        return count

    def open_and_download(self, output=True, **get_kwargs) -> int:
        """Open each link found on the current page, downloads, and closes the tab before moving on to the next one. Returns the number of downloads. get_kwargs passed to requests.get."""
        count = 0
        current = self.driver.current_window_handle
        for r in self.readers:
            if r.can_read(self.driver):
                for url in r.to_open(self.driver):
                    self.driver.execute_script("window.open('')")
                    # switch to last, i.e. newest, window
                    self.driver.switch_to.window(
                        self.driver.window_handles[-1])
                    self.driver.get(url)
                    count += self.download(output, **get_kwargs)
                    self.driver.close()
                    # switch to new last window for next script execution
                    self.driver.switch_to.window(
                        self.driver.window_handles[-1])
            self.driver.switch_to.window(current)
        return count

    def download_all(self, output=True, close_tabs: bool = True, **get_kwargs) -> int:
        """Download everything on all open tabs found by any PageReader. Optionally closes each page after doing so if anything was downloaded. Returns the number of downloads. get_kwargs passed to requests.get"""
        try:
            current = self.driver.current_window_handle
        except NoSuchWindowException:
            # window being controlled was closed
            current = None
        count = 0
        for handle in self.driver.window_handles:
            self.driver.switch_to.window(handle)
            current_count = self.download(output, **get_kwargs)
            if current_count > 0 and close_tabs and len(self.driver.window_handles) > 1:
                self.driver.close()
            count += current_count
        if current in self.driver.window_handles:
            self.driver.switch_to.window(current)
        return count


def run_page_browser(browser: PageBrowser, additional_actions: dict[str, typing.Callable]):
    actions = {
        "d": browser.download,
        "a": browser.download_all,
        "o": browser.open,
        "od": browser.open_and_download,
    }
    actions.update(additional_actions)

    console.repl(actions)
