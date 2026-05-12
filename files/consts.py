# (c) Andrew Chen (https://github.com/achen1296)

import os
import platform

PathLike = str | os.PathLike

WINDOWS = platform.system() == "Windows"
LINUX = platform.system() == "Linux"

if WINDOWS:
    from .windows_env import *

    LONG_PATH_PREFIX = "\\\\?\\"
    """ Prefix to allow reading paths >= 260 characters on Windows  """

elif LINUX:
    from .linux_env import *