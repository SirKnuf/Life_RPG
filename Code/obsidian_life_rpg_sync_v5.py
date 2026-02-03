#!/usr/bin/env python3
# obsidian_life_rpg_sync_v5.py

import sys

from obsidian_rpg_sync_v5 import scan_vault


if __name__ == "__main__":
    scan_vault(sys.argv[1] if len(sys.argv) > 1 else ".")
