# (c) Andrew Chen (https://github.com/achen1296)

""" Common Linux environment variables referring to file locations """

import os
import platform
from pathlib import Path

if platform.system() != "Linux":
    raise NotImplementedError

HOME = Path(os.environ["HOME"])
USER_PROFILE = HOME # windows style

__all__ = [
    "HOME",
    "USER_PROFILE",
]