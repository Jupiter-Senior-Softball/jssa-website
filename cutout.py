"""
Automatic background removal for player photos — the "floating over the
stadium" cut-out.

How it fits in:
  * A player uploads an ordinary photo (nothing changes for them).
  * When a card is shown, we ask a background-removal service to erase the
    background and hand back a see-through PNG of just the player.
  * The card template already draws the stadium BEHIND the photo, so a
    see-through cut-out makes the player appear to stand in the ballpark.

Safety by design:
  * OFF unless a REMOVEBG_API_KEY is set in the environment. With no key,
    enabled() is False and the site behaves exactly as before (normal photo).
  * Every failure returns None so the caller falls back to the normal photo —
    a card is never broken by this feature.
  * Results are cached in memory (keyed by the photo's Drive id, which changes
    whenever a player uploads a new photo), so each photo is processed once and
    the service is called as little as possible.

The service is remove.bg (https://www.remove.bg/api). A free key covers a small
league's handful of photos. To use a different provider later, only the small
_call_service() function below needs to change.
"""

import os
import time
import threading

_API_URL = "https://api.remove.bg/v1.0/removebg"

_lock = threading.Lock()
_cache = {}          # file_id -> PNG bytes (successful cut-outs)
_fail_at = {}        # file_id -> timestamp of last failure (don't hammer the API)
_last_error = {}     # file_id -> human-readable reason, for the diagnostic route
_FAIL_COOLDOWN = 600  # seconds to wait before retrying a photo that failed


def api_key():
    return (os.environ.get("REMOVEBG_API_KEY") or "").strip()


def enabled():
    """True only when a background-removal key is configured."""
    return bool(api_key())


def _source_photo_url(file_id):
    """The player's original photo, straight from Google Drive (public link)."""
    return "https://lh3.googleusercontent.com/d/%s=w800" % file_id


def _remember_failure(file_id, reason):
    with _lock:
        _fail_at[file_id] = time.time()
        _last_error[file_id] = reason


def _call_service(file_id):
    """Ask remove.bg to cut out the player. Returns PNG bytes or raises."""
    import requests
    resp = requests.post(
        _API_URL,
        data={
            "image_url": _source_photo_url(file_id),
            "size": "auto",       # best resolution the key's plan allows
            "type": "person",     # tuned for people, not products
            "format": "png",      # transparent background
        },
        headers={"X-Api-Key": api_key()},
        timeout=30,
    )
    if resp.status_code == 200 and resp.content:
        return resp.content
    # remove.bg returns a JSON error body on failure (e.g. bad key, out of
    # credits). Surface a short, readable reason for the diagnostic route.
    detail = (resp.text or "").strip().replace("\n", " ")[:300]
    raise RuntimeError("HTTP %s from remove.bg: %s" % (resp.status_code, detail))


def cutout_png(file_id):
    """Transparent PNG bytes of just the player, or None if unavailable.

    None means "use the normal photo" — never an error the caller must handle.
    """
    if not enabled() or not file_id:
        return None
    with _lock:
        if file_id in _cache:
            return _cache[file_id]
        last_fail = _fail_at.get(file_id)
    if last_fail and (time.time() - last_fail) < _FAIL_COOLDOWN:
        return None
    try:
        png = _call_service(file_id)
    except Exception as e:
        _remember_failure(file_id, "%s: %s" % (type(e).__name__, e))
        return None
    if not png:
        _remember_failure(file_id, "empty response from remove.bg")
        return None
    with _lock:
        _cache[file_id] = png
        _last_error.pop(file_id, None)
    return png


def status(file_id=None):
    """A small snapshot for the diagnostic route (no secrets included)."""
    with _lock:
        info = {
            "enabled": enabled(),
            "key_present": bool(api_key()),
            "cached_count": len(_cache),
        }
        if file_id:
            info["file_id"] = file_id
            info["cached"] = file_id in _cache
            info["last_error"] = _last_error.get(file_id)
    return info
