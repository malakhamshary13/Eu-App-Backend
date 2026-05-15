"""
core/limiter.py
───────────────
Shared rate-limiter instance (slowapi, no Redis required).

All routers import `limiter` from here; `main.py` mounts the handler.

Key strategy: client real IP  (falls back through X-Forwarded-For → X-Real-IP → direct)
so it works correctly behind Nginx / Render / Railway reverse proxies.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=[])
