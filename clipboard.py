import subprocess


def copy(s: str):
    subprocess.run("clip",
                   creationflags=subprocess.CREATE_NO_WINDOW, shell=True, input=s, text=True)


def paste() -> str:
    # extra \n added at the end by shell call
    return subprocess.run("powershell -command \"get-clipboard\"",
                          creationflags=subprocess.CREATE_NO_WINDOW,
                          capture_output=True, text=True).stdout.removesuffix("\n")
