import time
import web

if __name__ == "__main__":
    driver = web.chrome_driver("Profile 1")
    driver.get("https://www.youtube.com/playlist?list=WL")

    while True:
        try:
            reduce_to = int(input("Reduce Watch Later to: "))
            if reduce_to >= 0:
                break
            else:
                print("Input a positive value")
        except ValueError:
            print("Input an integer")

    # open the sort options
    web.wait_element(driver, "#trigger").click()

    time.sleep(1)

    # sort by date published (oldest)
    web.wait_element(driver, "#menu>a:nth-child(5)").click()

    time.sleep(5)

    # get the current playlist size
    playlist_size = int(web.wait_element(
        driver, "#stats>yt-formatted-string:nth-child(1)>span:nth-child(1)").get_attribute("innerText").replace(",", ""))

    print(
        f"Watch Later contains {playlist_size} videos, the oldest {playlist_size - reduce_to} videos will be removed")

    while playlist_size > reduce_to:
        # open the popup-menu for the first (oldest) video
        web.wait_element(
            driver, "#contents>ytd-playlist-video-renderer:nth-child(1)>#menu").click()

        # click "remove from watch later"
        web.wait_element(
            driver, "#items>ytd-menu-service-item-renderer:nth-child(3)").click()

        playlist_size -= 1

        time.sleep(.5)

    # open the sort options
    web.wait_element(driver, "#trigger").click()

    time.sleep(1)

    # sort by date published (newest)
    web.wait_element(driver, "#menu>a:nth-child(4)").click()

    time.sleep(5)
