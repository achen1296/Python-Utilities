""" Common Windows environment variables referring to file locations """

import os
import platform
from pathlib import Path

if platform.system() != "Windows":
    raise NotImplementedError

APP_DATA = Path(os.environ["APPDATA"])
COMMON_PROGRAM_FILES = Path(os.environ["COMMONPROGRAMFILES"])
COMMON_PROGRAM_FILES_x86 = Path(os.environ["COMMONPROGRAMFILES(X86)"])
HOME_DRIVE = Path(os.environ["HOMEDRIVE"])
LOCAL_APP_DATA = Path(os.environ["LOCALAPPDATA"])
PROGRAM_DATA = Path(os.environ["PROGRAMDATA"])
PROGRAM_FILES = Path(os.environ["PROGRAMFILES"])
PROGRAM_FILES_x86 = Path(os.environ["PROGRAMFILES(X86)"])
PUBLIC = Path(os.environ["PUBLIC"])
# os.environ["SYSTEMDRIVE"] is usually "C:" which resolves to the current working directory but on the C: drive (which only does something if the cwd is not already on C:)
SYSTEM_DRIVE = Path(os.environ["SYSTEMDRIVE"] + "/")
SYSTEM_ROOT = Path(os.environ["SYSTEMROOT"])
TEMP = Path(os.environ["TEMP"])
USER_PROFILE = Path(os.environ["USERPROFILE"])

ENVIRONMENT_NAME = {
    APP_DATA: "APPDATA",
    COMMON_PROGRAM_FILES: "COMMONPROGRAMFILES",
    COMMON_PROGRAM_FILES_x86: "COMMONPROGRAMFILES(X86)",
    HOME_DRIVE: "HOMEDRIVE",
    LOCAL_APP_DATA: "LOCALAPPDATA",
    PROGRAM_DATA: "PROGRAMDATA",
    PROGRAM_FILES: "PROGRAMFILES",
    PROGRAM_FILES_x86: "PROGRAMFILES(X86)",
    PUBLIC: "PUBLIC",
    SYSTEM_DRIVE: "SYSTEMDRIVE",
    SYSTEM_ROOT: "SYSTEMROOT",
    TEMP: "TEMP",
    USER_PROFILE: "USERPROFILE",
}


__all__ = ['APP_DATA',
           'COMMON_PROGRAM_FILES_x86',
           'COMMON_PROGRAM_FILES',
           'HOME_DRIVE',
           'LOCAL_APP_DATA',
           'PROGRAM_DATA',
           'PROGRAM_FILES',
           'PROGRAM_FILES_x86',
           'PUBLIC',
           'SYSTEM_DRIVE',
           'SYSTEM_ROOT',
           'TEMP',
           'USER_PROFILE',
           ]


def __dir__():
    return __all__
