import math
import os
import re
import subprocess
import time

import files


def kill_settings():
    MAX_KILLS = 2
    MAX_WAIT = 30

    kills = 0
    wait = 0

    print("Waiting to close settings app...")
    while True:
        if subprocess.run("taskkill /im SystemSettings.exe /f", creationflags=subprocess.CREATE_NO_WINDOW).returncode != 0:
            kills += 1
        if kills >= MAX_KILLS:
            break
        time.sleep(1)
        wait += 1
        if wait >= MAX_WAIT:
            break


def current_theme():
    output = subprocess.run(
        "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe \"Get-ItemProperty -path HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes -Name 'CurrentTheme'\"", capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW).stdout.decode()
    if match := re.search(r"CurrentTheme\s*:.*?\\([^\\]*?)\.theme", output):
        return match.group(1)
    else:
        raise Exception("Theme not found\n"+output)


def change_theme(theme: str):
    """ Changes the theme, but not if the current theme was already set. """
    curr_theme = current_theme()
    if theme != curr_theme:
        print(f"Changing theme to \"{theme}\" from \"{curr_theme}\"")
        os.startfile(files.USER_PROFILE.joinpath("AppData", "Local", "Microsoft",
                                                 "Windows", "Themes", theme + ".theme"))
        # allow time for theme to change
        time.sleep(5)
        kill_settings()


def set_brightness(b: float):
    """ Argument should be float between 0.0 and 1.0 inclusive """
    print(f"Setting brightness to {b}")
    # Monitorian takes ints only
    subprocess.run(["monitorian", "/set", "all", str(math.floor(b*100))],
                   creationflags=subprocess.CREATE_NO_WINDOW)


def set_contrast(c: float):
    """ Argument should be float between 0.0 and 1.0 inclusive """
    print(f"Setting contrast to {c}")
    subprocess.run(["monitorian",  "/set", "contrast", "all", str(math.floor(c*100))],
                   creationflags=subprocess.CREATE_NO_WINDOW)


def set_volume(volume: float):
    """ Argument should be float between 0.0 and 1.0 inclusive """
    subprocess.run(["nircmd", "setsysvolume", str(volume * 65535)],
                   creationflags=subprocess.CREATE_NO_WINDOW)


def set_system_sounds_volume(volume: float):
    """ Argument should be float between 0.0 and 1.0 inclusive """
    subprocess.run(["nircmd", "setappvolume", "systemsounds", str(volume)],
                   creationflags=subprocess.CREATE_NO_WINDOW)


def set_volume_balance(left: float, right: float):
    subprocess.run(["soundvolumeview ", "/setvolumechannels",
                   "Realtek(R) Audio\Device\Speakers/Headphones\Render", str(math.floor(left*100)), str(math.floor(right*100))])
