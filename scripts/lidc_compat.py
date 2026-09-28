"""Importa pylidc de forma compatible con NumPy >= 1.24 y Python >= 3.12."""

from __future__ import annotations

import configparser

import numpy as np

for _alias, _builtin in (("int", int), ("float", float), ("bool", bool)):
    if not hasattr(np, _alias):
        setattr(np, _alias, _builtin)

if not hasattr(configparser, "SafeConfigParser"):
    configparser.SafeConfigParser = configparser.ConfigParser

import pylidc as pl  # noqa: E402

__all__ = ["pl"]
