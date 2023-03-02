import os
import time
import typing
from pathlib import Path
from urllib.parse import urlparse

import requests
from selenium import webdriver
from selenium.common.exceptions import (NoSuchElementException,
                                        NoSuchWindowException,
                                        StaleElementReferenceException)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

import console
import files
import lists


def url_filename(url: str):
    """ Get filename in a URL pointing to a file -- the last path component. """
    path = urlparse(url).path
    last_slash = path.rfind("/")
    return path[last_slash+1:]


def download_url(url: str, file: os.PathLike = None,  *, output=True, **get_kwargs):
    """ If file = None, the name is inferred from the last piece of the URL. get_kwargs passed to requests.get. """
    if file is None:
        file = url_filename(url)
    file = files.remove_forbidden_chars(str(file))
    req = requests.get(url, **get_kwargs)
    if output:
        print(f"Downloading <{url}> -> <{file}>")
    with open(file, "wb") as f:
        f.write(req.content)


def download_urls(src_dst: dict[str, os.PathLike], *, wait=0, output=True, **get_kwargs):
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


def firefox_driver(**kwargs) -> webdriver.Firefox:
    # discard log output
    service = FirefoxService(log_path="NUL:")
    driver = webdriver.Firefox(service=service, **kwargs)
    driver.implicitly_wait(2)
    return driver


def tor_driver(**kwargs) -> webdriver.Firefox:
    # discard log output
    service = FirefoxService(log_path="NUL:")
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

    driver = webdriver.Firefox(
        firefox_profile=profile, service=service, **kwargs)
    driver.get("http://check.torproject.org")
    return driver


def chrome_driver(profile: str) -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    options.add_argument(
        f"user-data-dir={os.environ['LOCALAPPDATA']}\\Google\\Chrome\\User Data")
    options.add_argument(f"profile-directory={profile}")
    # discard log output
    service = ChromeService(log_path="NUL:")
    driver = webdriver.Chrome(
        executable_path=f"{os.environ['HOMEPATH']}\\Programs\\chromedriver.exe", options=options, service=service)
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

    def __init__(self, download_headers=None):
        self.download_headers: dict[str, str] = download_headers

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

    def new_tab(self, url: str):
        self.driver.execute_script("window.open('')")
        # switch to last, i.e. newest, window
        self.driver.switch_to.window(
            self.driver.window_handles[-1])
        self.driver.get(url)

    def close_tab(self):
        self.driver.close()
        # switch to new last window, somewhat mimicking normal tab close behavior
        self.driver.switch_to.window(
            self.driver.window_handles[-1])

    def open(self) -> int:
        """Open all links found on the current page by any PageReader. Returns the number of links opened."""
        count = 0
        current = self.driver.current_window_handle
        for r in self.readers:
            if r.can_read(self.driver):
                for url in r.to_open(self.driver):
                    count += 1
                    self.new_tab(url)
            self.driver.switch_to.window(current)
        return count

    def download(self, wait=0, output=True, **get_kwargs) -> int:
        """Download everything on the current page found by any PageReader. Returns the number of downloads.

        get_kwargs passed to requests.get.

        If a PageReader claims to be able to read the page, its download headers are combined with any given as arguments to this function."""
        count = 0
        for r in self.readers:
            if r.can_read(self.driver):
                d = r.to_download(self.driver)
                if r.download_headers is not None:
                    if "headers" not in get_kwargs:
                        get_kwargs["headers"] = {}
                    get_kwargs["headers"].update(r.download_headers)
                download_urls(d, wait=wait, output=output, **get_kwargs)
                count += len(d)
        return count

    def open_and_download(self, wait=0, output=True, **get_kwargs) -> int:
        """Open each link found on the current page, downloads, and closes the tab before moving on to the next one. Returns the number of downloads. get_kwargs passed to requests.get."""
        open_count = 0
        download_count = 0
        current = self.driver.current_window_handle
        for r in self.readers:
            if r.can_read(self.driver):
                to_open = r.to_open(self.driver)
                open_total = len(to_open)
                for url in to_open:
                    if output:
                        open_count += 1
                        print(f"{open_count}/{open_total}")
                    self.new_tab(url)
                    download_count += self.download(wait=wait,
                                                    output=output, **get_kwargs)
                    self.close_tab()
            self.driver.switch_to.window(current)
        return download_count

    def iter_tabs(self):
        for handle in self.driver.window_handles:
            self.driver.switch_to.window(handle)
            yield handle

    def download_all(self, close_tabs: bool = True, wait=0, output=True, **get_kwargs) -> int:
        """Download everything on all open tabs found by any PageReader. Optionally closes each page after doing so if anything was downloaded. Returns the number of downloads. get_kwargs passed to requests.get"""
        try:
            current = self.driver.current_window_handle
        except NoSuchWindowException:
            # window being controlled was closed
            current = None
        count = 0
        for _ in self.iter_tabs():
            current_count = self.download(
                wait=wait, output=output, **get_kwargs)
            if current_count > 0 and close_tabs and len(self.driver.window_handles) > 1:
                self.driver.close()
            count += current_count
        if current in self.driver.window_handles:
            self.driver.switch_to.window(current)
        else:
            self.switch_tab(0)
        return count

    def switch_tab(self, tab_index: int):
        """ Specify tab index starting from 0. """
        self.driver.switch_to.window(self.driver.window_handles[tab_index])

    def save_pages(self, file: os.PathLike):
        """Save the current pages to a file"""
        urls = []
        for _ in self.iter_tabs():
            urls.append(self.driver.current_url)
        lists.write_file_list(file, urls)

    def load_pages(self, file: os.PathLike):
        """Load pages from file"""
        urls = lists.read_file_list(file)
        for u in urls:
            self.new_tab(u)


def run_page_browser(browser: PageBrowser, additional_actions: dict[str, typing.Callable] = None):
    actions = {
        "d": browser.download,
        "a": browser.download_all,
        "o": browser.open,
        "od": browser.open_and_download,
        "t": browser.switch_tab,
        "s": browser.save_pages,
        "l": browser.load_pages
    }

    def switch_tab_transform(tab_index: str):
        return [int(tab_index)]

    def download_all_transform(close_tab: str = "true", wait: str = '0'):
        """Transform tab close arg to bool, wait to int."""
        return [not (close_tab.lower() in {"f", "false"}), int(wait)]

    def open_and_download_transform(wait: str = '0'):
        return [int(wait)]

    arg_transform = {"a": download_all_transform,
                     "t": switch_tab_transform, "od": open_and_download_transform}
    if additional_actions is not None:
        actions.update(additional_actions)

    console.repl(actions, arg_transform=arg_transform)
