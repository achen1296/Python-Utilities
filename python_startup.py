# (c) Andrew Chen (https://github.com/achen1296)

import asyncio
import base64
import itertools
import json
import math
import os
import platform
import random
import re
import shutil
import socket
import sys
import time
from base64 import b64decode, b64encode
from datetime import datetime, timedelta
from importlib import reload
from itertools import combinations, permutations
from pathlib import Path
from pprint import pprint
from socket import socket as Socket
from urllib.parse import quote, unquote, urlparse

import numpy as np
import requests
import selenium
from PIL import Image

import booleans
import byte_operations as bop
import console
import dictionaries
import file_backed_data
import files
import ftp
import images
import integers
from integers import mod
import lists
import polynomials
import quaternions
import sets
import strings
import tags
import threads
import web
from booleans import BooleanExpression
from file_backed_data import JSONFile
from polynomials import Polynomial
from strings import ALPHABET, alphabet, unicode_literal
from threads import IterAheadThread
from web import By

Poly = Polynomial
BE = BooleanExpression

if platform.system() == "Windows":
    import clipboard
    import environment
    import windows_settings


def ulit(char: str):
    print(unicode_literal(char))
