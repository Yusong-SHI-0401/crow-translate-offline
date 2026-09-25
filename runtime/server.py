#!/usr/bin/env python3
"""Configure upstream libraries without editing their installed source files."""
import logging
import os
from functools import partial
from common import ROOT, environment

env = environment()
os.environ.clear()
os.environ.update(env)
os.chdir(ROOT / "state")

import argostranslate.sbd
argostranslate.sbd.SBDetect = partial(argostranslate.sbd.SBDetect, max_threads=2)
# Argos changes this variable during import: override it afterwards.
import minisbd.models
minisbd.models.cache_dir = str(ROOT / "cache/minisbd")
# Upstream logs the user's text at INFO, so retain warnings/errors only.
logging.getLogger("argostranslate.utils").setLevel(logging.WARNING)

from libretranslate.main import main
main()
