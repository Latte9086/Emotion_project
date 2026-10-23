"""Configuration paths are relative to the configuration file, never the cwd."""

import argparse
import json
import logging
from pathlib import Path
import yaml
import numpy as np


def config(path=None):
    file = Path(path or Path(__file__).resolve().parents[1] / "config.yaml").resolve()
    c = yaml.safe_load(file.read_text())
    for key in ("confidence", "valid_ratio"):
        if not 0 <= c[key] <= 1:
            raise ValueError(f"{key} must be between 0 and 1")
    if c["max_gap_seconds"] <= 0:
        raise ValueError("max_gap_seconds must be positive")
    c["root"] = file.parent
    for key, value in c["paths"].items():
        c["paths"][key] = (file.parent / value).resolve()
        c["paths"][key].mkdir(parents=True, exist_ok=True)
    c["openface_binary"] = (file.parent / c["openface_binary"]).resolve()
    for sub in ("figures", "tables", "metrics"):
        (c["paths"]["results"] / sub).mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    return c


def parser(description):
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--config")
    return p


def save_json(path, value):
    def default(x):
        if isinstance(x, np.generic):
            return x.item()
        if isinstance(x, Path):
            return str(x)
        raise TypeError(type(x).__name__)

    Path(path).write_text(json.dumps(value, default=default, indent=2, allow_nan=False))
