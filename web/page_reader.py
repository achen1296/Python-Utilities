import lists
from .driver import *
from .download import *

class PageReader:
    """Reads a webpage to search for links to download or open."""

    def __init__(self, get_kwargs=None):
        if get_kwargs is None:
            get_kwargs = {}
        self.get_kwargs: dict[str, str | dict[str, str]] = get_kwargs

    def can_read(self, driver: WebDriver) -> bool:
        """Whether or not the current page is readable by this PageReader."""
        return True

    def to_download(self, driver: WebDriver) -> dict[str, files.PathLike]:
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
        """Returns a list of URLs from the current page to open next. The default implementation returns all a element href attributes."""
        links: list[WebElement] = driver.find_elements(By.CSS_SELECTOR, "a")
        urls = [l.get_attribute("href") for l in links]
        return [u for u in urls if u is not None]


class PageBrowser(console.Cmd):
    """Uses a set of PageReaders for browsing under human control."""

    def __init__(self, driver: WebDriver, readers: Iterable[PageReader], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.driver = driver
        self.readers = set(readers)
        self.user_agent = self.driver.execute_script(
            "return navigator.userAgent")
        self.get = self.driver.get

        # --Cmd functions with no argument transformations required--
        self.do_o = self.open
        self.do_s = self.save_pages
        self.do_l = self.load_pages

    def new_tab(self, url: str):
        """ Open a new tab and switch to it """
        self.driver.execute_script("window.open('')")
        # switch to last, i.e. newest, window
        self.driver.switch_to.window(
            self.driver.window_handles[-1])
        self.driver.get(url)

    def close_tab(self):
        """ Close the current tab and switch to the last one """
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

    def _plan_download(self) -> dict[str, tuple[files.PathLike, dict[str, str]]]:
        """ Analyze the current page using PageReaders and return an accumulated dictionary of planned downloads. """
        plan = {}
        for r in self.readers:
            if r.can_read(self.driver):
                d = r.to_download(self.driver)
                get_kwargs = r.get_kwargs
                if "headers" not in get_kwargs:
                    get_kwargs["headers"] = {}
                get_kwargs["headers"]["User-Agent"] = self.user_agent
                plan.update({
                    url: (filename, get_kwargs)
                    for url, filename in d.items()
                })
        return plan

    def download_current_page(self, wait=0, output=True) -> int:
        """Download everything on the current page found by any PageReader (using the keyword arguments to requests.get it specifies; the user agent string is also always included). Returns the number of downloads."""
        plan = self._plan_download()
        download_urls(plan, wait=wait, output=output)
        return len(plan)

    def open_and_download(self, wait=0, output=True) -> int:
        """Open each link found on the current page, analyzes, and closes the tab before moving on to the next one, then downloads everything. Returns the number of downloads. get_kwargs passed to requests.get."""
        download_count = 0
        current = self.driver.current_window_handle
        plan = {}
        for r in self.readers:
            if r.can_read(self.driver):
                to_open = r.to_open(self.driver)
                for url in to_open:
                    self.new_tab(url)
                    plan.update(self._plan_download())
                    self.close_tab()
            self.driver.switch_to.window(current)
        download_urls(plan, wait=wait, output=output)
        return download_count

    def iter_tabs(self):
        for handle in self.driver.window_handles:
            self.driver.switch_to.window(handle)
            yield handle

    def download_all(self, close_tabs: bool = True, wait=0, output=True) -> int:
        """Download everything on all open tabs found by any PageReader. Optionally closes each page after analyzing it if anything was downloaded. Returns the number of downloads. get_kwargs passed to requests.get"""
        try:
            current = self.driver.current_window_handle
        except NoSuchWindowException:
            # window being controlled was closed
            current = None
        plan = {}
        for _ in self.iter_tabs():
            page_plan = self._plan_download()
            if len(page_plan) > 0 and close_tabs and len(self.driver.window_handles) > 1:
                self.driver.close()
            plan.update(page_plan)

        if current in self.driver.window_handles:
            # return to the original active tab
            self.driver.switch_to.window(current)
        else:
            # switch to the first tab
            self.switch_tab(0)

        download_urls(plan, wait=wait, output=output)
        return len(plan)

    def switch_tab(self, tab_index: int):
        """ Specify tab index starting from 0. """
        self.driver.switch_to.window(self.driver.window_handles[tab_index])

    def save_pages(self, file: files.PathLike):
        """Save the current pages to a file"""
        urls = []
        for _ in self.iter_tabs():
            urls.append(self.driver.current_url)
        lists.write_file_list(file, urls)

    def load_pages(self, file: files.PathLike):
        """Load pages from file"""
        urls = lists.read_file_list(file)
        for u in urls:
            self.new_tab(u)

    # -- Cmd functions with argument transformations required --
    def do_d(self, wait: int = 0):
        # assume output True if used as command line
        self.download_current_page(int(wait))

    do_d.__doc__ = download_current_page.__doc__

    def do_a(self, close_tabs: bool = True, wait: int = 0):
        # assume output True if used as command line
        if isinstance(close_tabs, str):
            close_tabs = close_tabs.lower() not in {"f", "false"}
        self.download_all(close_tabs, int(wait))

    do_a.__doc__ = download_all.__doc__

    def do_t(self, tab_index: int):
        self.switch_tab(int(tab_index))
    do_t.__doc__ = switch_tab.__doc__

    def do_od(self, wait: int = 0):
        self.open_and_download(int(wait))
    do_od.__doc__ = open_and_download.__doc__


if __name__ == "__main__":
    import console
    console.traceback_wrap(PageBrowser(
        firefox_driver(), [PageReader()]).cmdloop)
