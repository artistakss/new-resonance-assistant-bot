"""
Backward-compatible entrypoint.

Use `python main.py` for the new structure.
"""

from __future__ import annotations

import asyncio

from main import main


if __name__ == "__main__":
    asyncio.run(main())
