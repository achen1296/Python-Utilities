import json
import math
import os
import random
import re
import shutil
import sys
import time
from importlib import reload
from pathlib import Path
from pprint import pprint
from urllib.parse import quote, unquote, urlparse

import selenium
from PIL import Image

import byte_operations as bop
import console
import dictionaries
import environment
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
from console import signature
from polynomials import Polynomial
from web import By

Poly = Polynomial


def sig(f):
    """ Prints the signature instead of just returning the string, so it looks nicer in the console. """
    print(signature(f))
