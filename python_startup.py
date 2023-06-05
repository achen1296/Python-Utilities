import json
import math
import os
import platform
import random
import re
import shutil
import sys
import time
from datetime import datetime
from importlib import reload
from pathlib import Path
from pprint import pprint
from urllib.parse import quote, unquote, urlparse

import selenium
from PIL import Image

import byte_operations as bop
import console
import dictionaries
import files
import ftp
import images
import integers
import lists
import mod
import polynomials
import sets
import strings
import tags
import web
from polynomials import Polynomial
from web import By

Poly = Polynomial


if platform.system() == "Windows":
    import clipboard
    import environment
    import windows_settings
