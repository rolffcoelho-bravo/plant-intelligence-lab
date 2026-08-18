"""Publication-only helpers for Plant Intelligence Lab.

The publication package fixes SVG provenance metadata and ID hashing so the
same frozen scientific inputs and code produce byte-stable SVG assets.
"""
from __future__ import annotations

import os

import matplotlib

# PUB-B1 merge timestamp (2026-08-18T16:59:51Z), used only as a reproducible
# publication-build epoch. It is not a scientific timestamp or outcome date.
os.environ["SOURCE_DATE_EPOCH"] = "1787072391"
matplotlib.rcParams["svg.hashsalt"] = "plant-intelligence-lab-pub-b2-v1"
