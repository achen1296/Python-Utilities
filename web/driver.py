# (c) Andrew Chen (https://github.com/achen1296)

import os
import time
from typing import Iterable, Literal, overload

from selenium import webdriver
from selenium.common.exceptions import (ElementClickInterceptedException,
                                        ElementNotInteractableException,
                                        NoSuchElementException,
                                        NoSuchWindowException,
                                        StaleElementReferenceException,
                                        TimeoutException)
from selenium.types import WaitExcTypes
from selenium.webdriver import FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

import files


def firefox_driver(profile: str | None = None, **kwargs) -> webdriver.Firefox:
    # discard log output
    service = FirefoxService(log_path="NUL:")
    if profile:
        options = FirefoxOptions()
        options.profile = FirefoxProfile(profile)
    else:
        options = None
    driver = webdriver.Firefox(options=options, service=service, **kwargs)
    driver.implicitly_wait(2)
    driver.set_page_load_timeout(15)
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


def chrome_driver(profile: files.PathLike, *, executable_path: files.PathLike | None = None, user_data_dir: files.PathLike = os.environ['LOCALAPPDATA']+"\\Google\\Chrome\\User Data") -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    options.add_argument(
        f"user-data-dir={user_data_dir}")
    options.add_argument(f"profile-directory={profile}")
    # disable (almost all) logs
    options.add_argument("--log-level=3")
    if executable_path:
        options.binary_location=str(executable_path)
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(2)
    driver.set_page_load_timeout(15)
    return driver


@overload
def wait_element(driver: WebDriver, css_selector: str, *, all: Literal[False] = False, timeout: int = 10, index: int = 0, ignored_exceptions: WaitExcTypes =
                 (ElementNotInteractableException,
                  NoSuchElementException, StaleElementReferenceException)) -> WebElement | None:
    pass


@overload
def wait_element(driver: WebDriver, css_selector: str, *, all: Literal[True] = True, timeout: int = 10, index: int = 0, ignored_exceptions: WaitExcTypes =
                 (ElementNotInteractableException,
                  NoSuchElementException, StaleElementReferenceException)) -> Iterable[WebElement] | None:
    pass


def wait_element(driver: WebDriver, css_selector: str, *, all: bool = False, timeout: int = 10, index: int = 0, ignored_exceptions: WaitExcTypes =
                 (ElementNotInteractableException,
                  NoSuchElementException, StaleElementReferenceException)
                 ) -> WebElement | Iterable[WebElement] | None:
    """ Replaces the TimeoutException with the last Exception raised by trying to find element(s). """
    last_exc = None

    def try_find(driver: WebDriver):
        nonlocal last_exc
        try:
            if all:
                return driver.find_elements(By.CSS_SELECTOR, css_selector)
            if index == 0:
                return driver.find_element(By.CSS_SELECTOR, css_selector)
            return driver.find_elements(By.CSS_SELECTOR, css_selector)[index]
        except Exception as exc:
            last_exc = exc

    try:
        return WebDriverWait(driver, timeout, ignored_exceptions=ignored_exceptions).until(try_find)
    except TimeoutException:
        raise last_exc


def wait_url(driver: WebDriver, url_contains: str, timeout: int = 10):
    # only raises TimeoutException
    WebDriverWait(driver, timeout).until(
        expected_conditions.url_contains(url=url_contains))


def find_and_get_attribute(driver: WebDriver, css_selector: str, attribute: str, *, all: bool = False, timeout: int = 10, index: int = 0, ignored_exceptions: WaitExcTypes =
                           (ElementNotInteractableException,
                            NoSuchElementException, StaleElementReferenceException)
                           ) -> str | Iterable[str | None] | None:
    """ Replaces the TimeoutException with the last Exception raised by trying to find element(s) and get attribute(s). If all=True then will return a list of the results for all elements found, or specify an index > 0 to select only that index out of the list of all matching elements. """
    last_exc = None

    def try_get_attribute(driver: WebDriver):
        nonlocal last_exc
        try:
            if all:
                es = driver.find_elements(By.CSS_SELECTOR, css_selector)
                return [e.get_attribute(attribute) for e in es]
            if index == 0:
                e = driver.find_element(By.CSS_SELECTOR, css_selector)
                return e.get_attribute(attribute)
            es = driver.find_elements(By.CSS_SELECTOR, css_selector)
            return es[index].get_attribute(attribute)
        except Exception as exc:
            last_exc = exc
    try:
        return WebDriverWait(driver, timeout, ignored_exceptions=ignored_exceptions).until(try_get_attribute)
    except TimeoutException:
        raise last_exc


def find_and_click(driver: WebDriver, css_selector: str, *, timeout: int = 10,  index: int = 0, ignored_exceptions: WaitExcTypes = (ElementClickInterceptedException, ElementNotInteractableException, NoSuchElementException, StaleElementReferenceException)):
    """ Replaces the TimeoutException with the last Exception raised by trying to find element(s) and click. """
    last_exc = None

    def try_click(driver: WebDriver):
        nonlocal last_exc
        try:
            if index == 0:
                e = driver.find_element(By.CSS_SELECTOR, css_selector)
                e.click()
                return True
            es = driver.find_elements(By.CSS_SELECTOR, css_selector)
            es[index].click()
            return True
        except Exception as exc:
            last_exc = exc
    try:
        WebDriverWait(driver, timeout,
                      ignored_exceptions=ignored_exceptions).until(try_click)
    except TimeoutException:
        raise last_exc


def find_and_send_keys(driver: WebDriver, css_selector: str, *keys, timeout: int = 10, index: int = 0,  ignored_exceptions: WaitExcTypes = (ElementNotInteractableException, NoSuchElementException, StaleElementReferenceException)):
    """ Replaces the TimeoutException with the last Exception raised by trying to find element(s) and send keys. """
    last_exc = None

    def try_send_keys(driver: WebDriver):
        nonlocal last_exc
        try:
            if index == 0:
                e = driver.find_element(By.CSS_SELECTOR, css_selector)
                e.send_keys(*keys)
                return True
            es = driver.find_elements(By.CSS_SELECTOR, css_selector)
            es[index].send_keys(*keys)
            return True
        except Exception as exc:
            last_exc = exc
    try:
        WebDriverWait(driver, timeout, ignored_exceptions=ignored_exceptions).until(
            try_send_keys)
    except TimeoutException:
        raise last_exc


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
