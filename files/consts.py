# (c) Andrew Chen (https://github.com/achen1296)

import os
import platform

PathLike = str | os.PathLike

WINDOWS = platform.system() == "Windows"


if WINDOWS:
    from .windows_env import *

    LONG_PATH_PREFIX = "\\\\?\\"
    """ Prefix to allow reading paths >= 260 characters on Windows  """
