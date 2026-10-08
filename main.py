#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOTCHER v9.0 — Instagram Username Generator & Checker
Single-file application.

Requires:
    pip install "httpx[http2]" tenacity PySide6 psutil

Run:
    python main.py
"""
from __future__ import annotations

import asyncio
import csv
import hashlib
import json
import math
import platform
import random
import string
import sys
import threading
import time
from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

from PySide6.QtCore import (
    Qt, QTimer, Signal, QObject, QPropertyAnimation, QEasingCurve,
    QRect, QPoint, Property,
)
from PySide6.QtGui import (
    QColor, QFont, QPainter, QBrush, QLinearGradient, QAction,
    QKeySequence, QShortcut, QPen, QIcon,
)
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFrame,
    QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMenu, QMessageBox, QPushButton,
    QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QHeaderView, QTextEdit, QSplitter, QScrollArea, QTabWidget,
    QDoubleSpinBox, QFormLayout, QGroupBox, QPlainTextEdit,
)


APP_NAME = "BOTCHER"
APP_VERSION = "9.0"
APP_CODENAME = "COMMAND"

CONFIG_PATH = Path.home() / ".botcher_config.json"
AUTOSAVE_PATH = Path.home() / ".botcher_autosave.json"

THEMES = {
    "Dark Cyan": {"bg": "#0a1520", "bg2": "#0f1e2d", "bg3": "#152a3d",
                  "fg": "#e6f2ff", "fg_dim": "#6b8ba3", "accent": "#06b6d4",
                  "accent_hover": "#22d3ee", "border": "#1e3548", "mode": "dark"},
    "Midnight Violet": {"bg": "#0d0a1a", "bg2": "#161225", "bg3": "#1f1a30",
                        "fg": "#ede9fe", "fg_dim": "#8b7ba8", "accent": "#8b5cf6",
                        "accent_hover": "#a78bfa", "border": "#2a1f45", "mode": "dark"},
    "Matrix Green": {"bg": "#000a00", "bg2": "#001400", "bg3": "#001f00",
                     "fg": "#c9f7c9", "fg_dim": "#4d7f4d", "accent": "#22ff44",
                     "accent_hover": "#55ff77", "border": "#003300", "mode": "dark"},
    "Deep Emerald": {"bg": "#061a12", "bg2": "#0a2618", "bg3": "#0f3320",
                     "fg": "#d1fae5", "fg_dim": "#5a8f75", "accent": "#10b981",
                     "accent_hover": "#34d399", "border": "#1a4d33", "mode": "dark"},
    "Forest": {"bg": "#0a1410", "bg2": "#101f18", "bg3": "#162a20",
               "fg": "#d4f0d9", "fg_dim": "#6f9a7a", "accent": "#22c55e",
               "accent_hover": "#4ade80", "border": "#2a4530", "mode": "dark"},
    "Ocean Blue": {"bg": "#071626", "bg2": "#0d2033", "bg3": "#142a40",
                   "fg": "#dbeafe", "fg_dim": "#6b8ba8", "accent": "#3b82f6",
                   "accent_hover": "#60a5fa", "border": "#1e3f5c", "mode": "dark"},
    "Sky Light": {"bg": "#eaf4ff", "bg2": "#f7fbff", "bg3": "#d4e6f7",
                  "fg": "#0a1e35", "fg_dim": "#5a7290", "accent": "#0284c7",
                  "accent_hover": "#0369a1", "border": "#b8d4eb", "mode": "light"},
    "Sunset Orange": {"bg": "#1a0e08", "bg2": "#251810", "bg3": "#352114",
                      "fg": "#fee6d6", "fg_dim": "#a07a5e", "accent": "#f97316",
                      "accent_hover": "#fb923c", "border": "#4d3018", "mode": "dark"},
    "Rose Pink": {"bg": "#1a0812", "bg2": "#251018", "bg3": "#35181f",
                  "fg": "#fce7f3", "fg_dim": "#9a6b7d", "accent": "#ec4899",
                  "accent_hover": "#f472b6", "border": "#4d1f2d", "mode": "dark"},
    "Dracula": {"bg": "#282a36", "bg2": "#2e303e", "bg3": "#383a4c",
                "fg": "#f8f8f2", "fg_dim": "#8b8fa8", "accent": "#bd93f9",
                "accent_hover": "#caa8ff", "border": "#44475a", "mode": "dark"},
    "Nord Light": {"bg": "#eceff4", "bg2": "#f7f9fc", "bg3": "#dde3ec",
                   "fg": "#2e3440", "fg_dim": "#6b7280", "accent": "#5e81ac",
                   "accent_hover": "#4a6d92", "border": "#c0c8d6", "mode": "light"},
    "Paper": {"bg": "#f0efe0", "bg2": "#f8f7ea", "bg3": "#e4e2c9",
              "fg": "#1f2937", "fg_dim": "#6b6355", "accent": "#1f2937",
              "accent_hover": "#374151", "border": "#ccc9a5", "mode": "light"},
}

STATUS_COLORS_DARK = {
    "available": "#22c55e", "taken": "#ef4444",
    "reserved": "#eab308", "rate_limited": "#a855f7",
    "unknown": "#06b6d4", "error": "#dc2626",
    "honeypot": "#f43f5e", "skipped": "#475569",
}
STATUS_COLORS_LIGHT = {
    "available": "#15803d", "taken": "#b91c1c",
    "reserved": "#a16207", "rate_limited": "#7e22ce",
    "unknown": "#0e7490", "error": "#991b1b",
    "honeypot": "#be123c", "skipped": "#64748b",
}


class Availability(str, Enum):
    AVAILABLE = "available"
    TAKEN = "taken"
    RESERVED = "reserved"
    RATE_LIMITED = "rate_limited"
    UNKNOWN = "unknown"
    ERROR = "error"
    HONEYPOT = "honeypot"
    SKIPPED = "skipped"


@dataclass
class CheckResult:
    username: str
    availability: Availability
    status_code: int | None = None
    latency_ms: float | None = None
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    note: str | None = None

    def to_dict(self):
        return {
            "username": self.username,
            "availability": self.availability.value,
            "status_code": self.status_code,
            "latency_ms": self.latency_ms,
            "checked_at": self.checked_at.isoformat(),
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            username=d["username"],
            availability=Availability(d["availability"]),
            status_code=d.get("status_code"),
            latency_ms=d.get("latency_ms"),
            checked_at=datetime.fromisoformat(d["checked_at"]),
            note=d.get("note"),
        )


@dataclass
class Settings:
    concurrency: int = 1
    timeout_s: float = 20.0
    retries: int = 4
    backoff_base_s: float = 5.0
    jitter_lo_ms: int = 2000
    jitter_hi_ms: int = 5000
    autosave_every: int = 25
    notify_sound: bool = True
    notify_toast: bool = True
    notify_on_available: bool = True
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    proxy: str | None = None
    session_id: str | None = None
    csrf_token: str | None = None

    @property
    def jitter_ms(self):
        return (self.jitter_lo_ms, self.jitter_hi_ms)


_VALID_CHARS = set(string.ascii_lowercase + string.digits + "._")


def _is_valid(u):
    if not (1 <= len(u) <= 30):
        return False
    if u.endswith("."):
        return False
    if any(c not in _VALID_CHARS for c in u):
        return False
    if ".." in u or "__" in u or "._" in u or "_." in u:
        return False
    return True


def generate_random(length, count, use_letters, use_digits,
                    use_dots, use_underscores, seed=None):
    rng = random.Random(seed)
    pool = ""
    if use_letters:
        pool += string.ascii_lowercase
    if use_digits:
        pool += string.digits
    if not pool:
        pool = string.ascii_lowercase
    out = set()
    attempts = 0
    max_attempts = max(count * 50, 1000)
    while len(out) < count and attempts < max_attempts:
        attempts += 1
        chars = [rng.choice(pool) for _ in range(length)]
        if length > 3:
            for i in range(1, length - 1):
                r = rng.random()
                if use_dots and r < 0.04:
                    chars[i] = "."
                elif use_underscores and r < 0.08:
                    chars[i] = "_"
        cand = "".join(chars)
        if _is_valid(cand):
            out.add(cand)
    return list(out)


@dataclass
class TokenBucket:
    rate: float
    burst: int
    _tokens: float = field(init=False)
    _last: float = field(init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    def __post_init__(self):
        self._tokens = float(self.burst)
        self._last = time.monotonic()

    async def acquire(self, n=1):
        async with self._lock:
            while True:
                now = time.monotonic()
                self._tokens = min(self.burst, self._tokens + (now - self._last) * self.rate)
                self._last = now
                if self._tokens >= n:
                    self._tokens -= n
                    return
                await asyncio.sleep((n - self._tokens) / self.rate)


_WEB_PROFILE_INFO_URL = "https://i.instagram.com/api/v1/users/web_profile_info/"


def _build_headers(user_agent, csrf_token=None):
    h = {
        "user-agent": user_agent,
        "x-ig-app-id": "936619743392459",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "referer": "https://www.instagram.com/",
        "x-requested-with": "XMLHttpRequest",
        "origin": "https://www.instagram.com",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }
    if csrf_token:
        h["x-csrftoken"] = csrf_token
    return h


class InstagramChecker:
    def __init__(self, settings, log_cb=None):
        self.s = settings
        self._bucket = TokenBucket(rate=0.4, burst=1)
        self._client = None
        self._log = log_cb or (lambda *a, **k: None)

    async def __aenter__(self):
        headers = _build_headers(self.s.user_agent, self.s.csrf_token)
        cookies = {}
        if self.s.session_id:
            cookies["sessionid"] = self.s.session_id
        if self.s.csrf_token:
            cookies["csrftoken"] = self.s.csrf_token
        timeout = httpx.Timeout(connect=10.0, read=self.s.timeout_s,
                                write=10.0, pool=10.0)
        self._client = httpx.AsyncClient(
            http2=False, timeout=timeout, headers=headers,
            cookies=cookies or None, proxy=self.s.proxy,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=20,
                                max_keepalive_connections=10,
                                keepalive_expiry=30.0),
        )
        self._log("info", f"[checker] client started proxy={self.s.proxy or 'direct'}")
        return self

    async def __aexit__(self, *exc):
        if self._client:
            await self._client.aclose()
        self._log("info", "[checker] closed")

    async def check_one(self, username):
        assert self._client is not None
        username = username.strip().lower().lstrip("@")
        await self._bucket.acquire()
        jitter = random.uniform(*self.s.jitter_ms) / 1000.0
        await asyncio.sleep(jitter)
        self._log("info", f"[req] {username} jitter={jitter:.2f}s")

        t0 = time.perf_counter()
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.s.retries + 1),
                wait=wait_exponential_jitter(initial=self.s.backoff_base_s,
                                              max=40.0, jitter=1.0),
                retry=retry_if_exception_type(
                    (httpx.TransportError, httpx.TimeoutException, httpx.HTTPStatusError)
                ),
                reraise=True,
            ):
                with attempt:
                    resp = await self._client.get(
                        _WEB_PROFILE_INFO_URL, params={"username": username},
                    )
                    if resp.status_code == 429:
                        retry_after = resp.headers.get("Retry-After")
                        wait_s = float(retry_after) if (
                            retry_after and retry_after.replace(".", "").isdigit()
                        ) else 12.0
                        self._log("warn", f"[429] {username} retry_after={wait_s}s")
                        await asyncio.sleep(wait_s)
                        raise httpx.HTTPStatusError(
                            "429", request=resp.request, response=resp,
                        )
                    latency = (time.perf_counter() - t0) * 1000
                    self._log("ok", f"[resp] {username} code={resp.status_code} {latency:.0f}ms")
                    return self._classify(username, resp, latency)
        except httpx.TimeoutException:
            self._log("error", f"[timeout] {username}")
            return CheckResult(username=username, availability=Availability.ERROR,
                               latency_ms=(time.perf_counter() - t0) * 1000, note="Timeout")
        except httpx.TransportError as e:
            self._log("error", f"[transport] {username} {type(e).__name__}")
            return CheckResult(username=username, availability=Availability.ERROR,
                               latency_ms=(time.perf_counter() - t0) * 1000,
                               note=f"Transport {type(e).__name__}")
        except httpx.HTTPStatusError as e:
            self._log("warn", f"[http] {username} {e.response.status_code}")
            return CheckResult(username=username, availability=Availability.RATE_LIMITED,
                               status_code=e.response.status_code,
                               latency_ms=(time.perf_counter() - t0) * 1000,
                               note="rate limited")
        except Exception as e:
            self._log("error", f"[err] {username} {type(e).__name__}")
            return CheckResult(username=username, availability=Availability.ERROR,
                               latency_ms=(time.perf_counter() - t0) * 1000,
                               note=f"{type(e).__name__}")
        return CheckResult(username=username, availability=Availability.UNKNOWN,
                           note="retry exited")

    @staticmethod
    def _classify(username, resp, latency_ms):
        code = resp.status_code
        if code == 200:
            try:
                data = resp.json()
            except Exception:
                data = {}
            user = (data.get("data") or {}).get("user")
            if user:
                return CheckResult(username=username, availability=Availability.TAKEN,
                                   status_code=200, latency_ms=latency_ms)
            return CheckResult(username=username, availability=Availability.AVAILABLE,
                               status_code=200, latency_ms=latency_ms)
        if code == 404:
            return CheckResult(username=username, availability=Availability.AVAILABLE,
                               status_code=404, latency_ms=latency_ms)
        if code == 429:
            return CheckResult(username=username, availability=Availability.RATE_LIMITED,
                               status_code=429, latency_ms=latency_ms, note="rate limited")
        if code == 401:
            return CheckResult(username=username, availability=Availability.ERROR,
                               status_code=401, latency_ms=latency_ms, note="invalid session")
        if code == 403:
            return CheckResult(username=username, availability=Availability.RESERVED,
                               status_code=403, latency_ms=latency_ms, note="blocked")
        if code == 400:
            return CheckResult(username=username, availability=Availability.UNKNOWN,
                               status_code=400, latency_ms=latency_ms, note="bad request")
        if 500 <= code < 600:
            return CheckResult(username=username, availability=Availability.ERROR,
                               status_code=code, latency_ms=latency_ms,
                               note=f"IG server error {code}")
        return CheckResult(username=username, availability=Availability.UNKNOWN,
                           status_code=code, latency_ms=latency_ms)


class AsyncRunner(QObject):
    result_ready = Signal(object)
    finished = Signal()
    log_event = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self._stop_flag = threading.Event()
        self._pause_flag = threading.Event()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def submit_check(self, candidates, settings):
        self._stop_flag.clear()
        self._pause_flag.clear()
        asyncio.run_coroutine_threadsafe(self._run(candidates, settings), self.loop)

    def pause(self): self._pause_flag.set()
    def resume(self): self._pause_flag.clear()
    def stop(self):
        self._stop_flag.set()
        self._pause_flag.clear()
    def stop_loop(self):
        try:
            self.loop.call_soon_threadsafe(self.loop.stop)
        except Exception:
            pass

    def _emit_log(self, level, msg):
        self.log_event.emit(level, msg)

    async def _run(self, candidates, settings):
        async with InstagramChecker(settings, log_cb=self._emit_log) as checker:
            sem = asyncio.Semaphore(settings.concurrency)
            async def worker(u):
                if self._stop_flag.is_set():
                    return
                while self._pause_flag.is_set() and not self._stop_flag.is_set():
                    await asyncio.sleep(0.2)
                if self._stop_flag.is_set():
                    return
                async with sem:
                    r = await checker.check_one(u)
                    if not self._stop_flag.is_set():
                        self.result_ready.emit(r)
            await asyncio.gather(*(worker(u) for u in candidates))
        self.finished.emit()


def load_config():
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_config(data):
    try:
        CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def load_autosave():
    if AUTOSAVE_PATH.exists():
        try:
            return json.loads(AUTOSAVE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def save_autosave(results):
    try:
        AUTOSAVE_PATH.write_text(
            json.dumps([r.to_dict() for r in results], indent=2), encoding="utf-8")
    except Exception:
        pass


def clear_autosave():
    try:
        if AUTOSAVE_PATH.exists():
            AUTOSAVE_PATH.unlink()
    except Exception:
        pass


class WaveBanner(QWidget):
    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setFixedHeight(150)
        self._t = 0.0
        self._particles = [
            {"x": random.uniform(0, 1), "y": random.uniform(0, 1),
             "vx": random.uniform(-0.001, 0.001),
             "vy": random.uniform(-0.0015, 0.0015),
             "size": random.uniform(1.0, 2.5),
             "alpha": random.uniform(30, 130)}
            for _ in range(50)
        ]
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)

    def set_theme(self, theme):
        self.theme = theme
        self.update()

    def _tick(self):
        self._t += 0.04
        for p in self._particles:
            p["x"] += p["vx"]; p["y"] += p["vy"]
            if p["x"] < 0 or p["x"] > 1: p["vx"] *= -1
            if p["y"] < 0 or p["y"] > 1: p["vy"] *= -1
        self.update()

    def paintEvent(self, event):
        try:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing)
            t = self.theme
            w, h = self.width(), self.height()
            grad = QLinearGradient(0, 0, w, 0)
            c1 = QColor(t["accent"]); c1.setAlpha(0)
            c2 = QColor(t["accent"]); c2.setAlpha(50)
            c3 = QColor(t["accent"]); c3.setAlpha(0)
            grad.setColorAt(0.0, c1); grad.setColorAt(0.5, c2); grad.setColorAt(1.0, c3)
            p.fillRect(0, 25, w, 95, QBrush(grad))
            for offset in range(3):
                c = QColor(t["accent"])
                c.setAlpha(max(20, 120 - offset * 30))
                pen = QPen(c); pen.setWidth(1); p.setPen(pen)
                points = [(x, 70 + math.sin((x / 60.0) + self._t + offset * 0.7) * 7)
                          for x in range(0, w, 8)]
                for i in range(len(points) - 1):
                    p.drawLine(points[i][0], int(points[i][1]),
                               points[i + 1][0], int(points[i + 1][1]))
            p.setPen(Qt.NoPen)
            for part in self._particles:
                c = QColor(t["accent"]); c.setAlpha(int(part["alpha"]))
                p.setBrush(QBrush(c))
                p.drawEllipse(QPoint(int(part["x"] * w), int(part["y"] * h)),
                              int(part["size"]), int(part["size"]))
            font = QFont("Arial Black", 48, QFont.Black)
            font.setLetterSpacing(QFont.AbsoluteSpacing, 6)
            p.setFont(font)
            p.setPen(QColor(t["accent"]))
            p.drawText(QRect(0, 20, w, h - 55), Qt.AlignHCenter | Qt.AlignVCenter, APP_NAME)
            font2 = QFont("Consolas", 10)
            font2.setLetterSpacing(QFont.AbsoluteSpacing, 4)
            p.setFont(font2)
            p.setPen(QColor(t["fg_dim"]))
            p.drawText(QRect(0, h - 42, w, 22), Qt.AlignHCenter | Qt.AlignVCenter,
                       f"v{APP_VERSION} {APP_CODENAME}")
        except Exception:
            pass


class PulseDot(QWidget):
    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setFixedSize(18, 18)
        self._phase = 0.0
        self._active = False
        self._color = QColor(theme["fg_dim"])
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)

    def set_theme(self, theme):
        self.theme = theme; self.update()

    def set_active(self, active, color=None):
        self._active = active
        if color: self._color = QColor(color)
        self.update()

    def _tick(self):
        if self._active:
            self._phase = (self._phase + 0.08) % 1.0
            self.update()

    def paintEvent(self, event):
        try:
            p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
            cx, cy = 9, 9
            if self._active:
                r = 4 + 4 * (1 + math.sin(self._phase * 2 * math.pi)) / 2
                c = QColor(self._color); c.setAlpha(80)
                p.setBrush(QBrush(c)); p.setPen(Qt.NoPen)
                p.drawEllipse(QPoint(cx, cy), int(r), int(r))
            p.setBrush(QBrush(self._color)); p.setPen(Qt.NoPen)
            p.drawEllipse(QPoint(cx, cy), 4, 4)
        except Exception:
            pass


class AnimatedProgressBar(QWidget):
    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setFixedHeight(10)
        self._value = 0.0
        self._maximum = 1.0
        self._shimmer = 0.0
        self._active = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(25)
        self._anim = QPropertyAnimation(self, b"animatedValue")
        self._anim.setDuration(400)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    def get_animated_value(self): return self._value
    def set_animated_value(self, v):
        self._value = v; self.update()
    animatedValue = Property(float, get_animated_value, set_animated_value)

    def set_theme(self, theme):
        self.theme = theme; self.update()

    def set_value(self, value, maximum, animated=True):
        self._maximum = max(1.0, maximum)
        if animated:
            self._anim.stop()
            self._anim.setStartValue(self._value)
            self._anim.setEndValue(float(value))
            self._anim.start()
        else:
            self._value = float(value); self.update()

    def set_active(self, active): self._active = active

    def _tick(self):
        if self._active:
            self._shimmer = (self._shimmer + 0.025) % 1.0
            self.update()

    def paintEvent(self, event):
        try:
            p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
            w, h = self.width(), self.height()
            t = self.theme
            p.setBrush(QBrush(QColor(t["bg3"]))); p.setPen(Qt.NoPen)
            p.drawRoundedRect(0, 0, w, h, h / 2, h / 2)
            ratio = min(1.0, self._value / self._maximum) if self._maximum > 0 else 0
            fill_w = int(w * ratio)
            if fill_w > 0:
                grad = QLinearGradient(0, 0, fill_w, 0)
                grad.setColorAt(0.0, QColor(t["accent"]))
                grad.setColorAt(1.0, QColor(t["accent_hover"]))
                p.setBrush(QBrush(grad))
                p.drawRoundedRect(0, 0, fill_w, h, h / 2, h / 2)
                if self._active and fill_w > 20:
                    sx = int(fill_w * self._shimmer)
                    grad2 = QLinearGradient(sx - 40, 0, sx + 40, 0)
                    grad2.setColorAt(0.0, QColor(255, 255, 255, 0))
                    grad2.setColorAt(0.5, QColor(255, 255, 255, 110))
                    grad2.setColorAt(1.0, QColor(255, 255, 255, 0))
                    p.setBrush(QBrush(grad2))
                    p.drawRoundedRect(0, 0, fill_w, h, h / 2, h / 2)
        except Exception:
            pass


class CircularProgress(QWidget):
    def __init__(self, theme, size=86, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setFixedSize(size, size)
        self._value = 0.0
        self._maximum = 1.0
        self._anim = QPropertyAnimation(self, b"animatedValue")
        self._anim.setDuration(400)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    def get_animated_value(self): return self._value
    def set_animated_value(self, v):
        self._value = v; self.update()
    animatedValue = Property(float, get_animated_value, set_animated_value)

    def set_theme(self, theme):
        self.theme = theme; self.update()

    def set_value(self, value, maximum, animated=True):
        self._maximum = max(1.0, maximum)
        if animated:
            self._anim.stop()
            self._anim.setStartValue(self._value)
            self._anim.setEndValue(float(value))
            self._anim.start()
        else:
            self._value = float(value); self.update()

    def paintEvent(self, event):
        try:
            p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
            t = self.theme
            s = min(self.width(), self.height())
            pad = 7
            rect = QRect(pad, pad, s - 2 * pad, s - 2 * pad)
            pen = QPen(QColor(t["bg3"])); pen.setWidth(7); pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen); p.drawArc(rect, 0, 360 * 16)
            ratio = min(1.0, self._value / self._maximum) if self._maximum > 0 else 0
            pen2 = QPen(QColor(t["accent"])); pen2.setWidth(7); pen2.setCapStyle(Qt.RoundCap)
            p.setPen(pen2); p.drawArc(rect, 90 * 16, -int(360 * 16 * ratio))
            f = QFont("Consolas", 13, QFont.Bold)
            p.setFont(f)
            p.setPen(QColor(t["fg"]))
            p.drawText(rect, Qt.AlignCenter, f"{int(ratio * 100)}%")
        except Exception:
            pass


class StatCard(QFrame):
    def __init__(self, label, color, theme, parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.color = color
        self.theme = theme
        self._value = 0
        self.setFixedHeight(66)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(0)
        self.value_label = QLabel("0")
        self.value_label.setObjectName("statValue")
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet(f"color: {color};")
        layout.addWidget(self.value_label)
        self.name_label = QLabel(label.upper())
        self.name_label.setObjectName("statName")
        self.name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.name_label)
        self._anim = QPropertyAnimation(self, b"value")
        self._anim.setDuration(450)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.finished.connect(self._commit_value)

    def get_value(self): return self._value
    def set_value_prop(self, v): self._value = v
    value = Property(int, get_value, set_value_prop)

    def _commit_value(self):
        self.value_label.setText(str(self._value))

    def set_value(self, v):
        self._anim.stop()
        self._anim.setStartValue(self._value)
        self._anim.setEndValue(int(v))
        self._anim.start()
        QTimer.singleShot(480, self._commit_value)


class Toast(QWidget):
    def __init__(self, parent, text, theme, color, slot, duration_ms=3000):
        super().__init__(parent)
        self.theme = theme
        self.setFixedHeight(46)
        self.setFixedWidth(320)
        self.setStyleSheet(f"""
            Toast {{
                background-color: {theme['bg2']};
                border: 1px solid {color};
                border-radius: 8px;
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        self.label = QLabel(text)
        self.label.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 600;")
        layout.addWidget(self.label)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(22)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
        parent_rect = parent.rect()
        self.target_x = parent_rect.width() - 320 - 26
        self.target_y = 26 + slot * (46 + 8)
        self.move(parent_rect.width() + 20, self.target_y)
        self.show(); self.raise_()
        self.anim_in = QPropertyAnimation(self, b"pos")
        self.anim_in.setDuration(300)
        self.anim_in.setStartValue(QPoint(parent_rect.width() + 20, self.target_y))
        self.anim_in.setEndValue(QPoint(self.target_x, self.target_y))
        self.anim_in.setEasingCurve(QEasingCurve.OutCubic)
        self.anim_in.start()
        QTimer.singleShot(duration_ms, self._fade_out)

    def _fade_out(self):
        try:
            parent = self.parent()
            if parent is None:
                self.deleteLater(); return
            self.anim_out = QPropertyAnimation(self, b"pos")
            self.anim_out.setDuration(240)
            self.anim_out.setStartValue(self.pos())
            self.anim_out.setEndValue(QPoint(parent.width() + 20, self.pos().y()))
            self.anim_out.setEasingCurve(QEasingCurve.InCubic)
            self.anim_out.finished.connect(self._notify_close)
            self.anim_out.start()
        except Exception:
            self.deleteLater()

    def _notify_close(self):
        try:
            parent = self.parent()
            if parent is not None and hasattr(parent, "_on_toast_closed"):
                parent._on_toast_closed(self)
        except Exception:
            pass
        self.deleteLater()


class CollapsibleSection(QWidget):
    def __init__(self, title, theme, expanded=True, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.expanded = expanded
        self._title = title
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.header = QPushButton(self._header_text())
        self.header.setObjectName("sectionToggle")
        self.header.setCursor(Qt.PointingHandCursor)
        self.header.clicked.connect(self.toggle)
        layout.addWidget(self.header)
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        self.content_layout.setSpacing(6)
        self.content.setVisible(expanded)
        layout.addWidget(self.content)

    def _header_text(self):
        marker = "v" if self.expanded else ">"
        return f"{marker}  {self._title}"

    def add(self, widget):
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        self.content_layout.addLayout(layout)

    def set_theme(self, theme):
        self.theme = theme

    def toggle(self):
        self.expanded = not self.expanded
        self.header.setText(self._header_text())
        self.content.setVisible(self.expanded)


def play_sound(kind="info"):
    try:
        if platform.system() == "Windows":
            import winsound
            if kind == "error":
                winsound.MessageBeep(winsound.MB_ICONHAND)
            elif kind == "warn":
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            else:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
        else:
            sys.stdout.write("\a"); sys.stdout.flush()
    except Exception:
        pass


class ResourceMonitor:
    def __init__(self):
        self._proc = None
        if _HAS_PSUTIL:
            try:
                self._proc = psutil.Process()
                self._proc.cpu_percent(interval=None)
            except Exception:
                self._proc = None
        self._rps_window = deque(maxlen=20)
        self._last_count = 0
        self._last_time = time.time()

    def update_rps(self, done_count):
        now = time.time()
        dt = now - self._last_time
        if dt >= 0.5:
            rps = (done_count - self._last_count) / dt
            self._rps_window.append(rps)
            self._last_count = done_count
            self._last_time = now

    def snapshot(self):
        cpu = 0.0
        ram_mb = 0.0
        if self._proc:
            try:
                cpu = self._proc.cpu_percent(interval=None)
                ram_mb = self._proc.memory_info().rss / 1024 / 1024
            except Exception:
                pass
        rps = sum(self._rps_window) / len(self._rps_window) if self._rps_window else 0.0
        return cpu, ram_mb, rps


class BotcherApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION} {APP_CODENAME}")
        self.setMinimumSize(1200, 780)
        self.resize(1420, 900)

        cfg = load_config()
        self.theme_name = cfg.get("theme", "Dark Cyan")
        if self.theme_name not in THEMES:
            self.theme_name = "Dark Cyan"
        self.theme = THEMES[self.theme_name]

        self.user_settings = Settings(
            concurrency=cfg.get("concurrency", 1),
            timeout_s=cfg.get("timeout_s", 20.0),
            retries=cfg.get("retries", 4),
            backoff_base_s=cfg.get("backoff_base_s", 5.0),
            jitter_lo_ms=cfg.get("jitter_lo_ms", 2000),
            jitter_hi_ms=cfg.get("jitter_hi_ms", 5000),
            autosave_every=cfg.get("autosave_every", 25),
            notify_sound=cfg.get("notify_sound", True),
            notify_toast=cfg.get("notify_toast", True),
            notify_on_available=cfg.get("notify_on_available", True),
        )

        self.results = []
        self.candidates = []
        self.checked_set = set()
        self.checking = False
        self.paused = False
        self.stopped = False
        self.total = 0
        self.done_count = 0
        self.start_time = None

        self._toast_queue = deque(maxlen=4)
        self._active_toasts = []
        self._toast_processing = False

        self.resource_monitor = ResourceMonitor()

        self.runner = AsyncRunner()
        self.runner.result_ready.connect(self.on_result)
        self.runner.finished.connect(self.on_finished)
        self.runner.log_event.connect(self.on_log_event)

        self._build_ui()
        self._apply_theme()
        self._setup_shortcuts()
        self._start_timer()
        self._restore_layout()
        QTimer.singleShot(150, self._check_autosave_on_start)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+G"), self, self.on_generate)
        QShortcut(QKeySequence("Ctrl+K"), self, self.on_check)
        QShortcut(QKeySequence("Ctrl+S"), self, self.on_export)
        QShortcut(QKeySequence("Ctrl+L"), self, self.on_clear)
        QShortcut(QKeySequence("Ctrl+P"), self, self.on_pause_resume)
        QShortcut(QKeySequence("Ctrl+R"), self, self.on_retry_failed)
        QShortcut(QKeySequence("F5"), self, self.on_reload_autosave)

    def _restore_layout(self):
        try:
            cfg = load_config()
            size = cfg.get("window_size")
            if size and len(size) == 2 and size[0] >= 1200:
                self.resize(size[0], size[1])
            splitter_sizes = cfg.get("splitter")
            if splitter_sizes and len(splitter_sizes) == 2 and hasattr(self, "splitter"):
                self.splitter.setSizes(splitter_sizes)
        except Exception:
            pass

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 7, 14, 14)
        root.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(10)
        title = QLabel(f"{APP_NAME} v{APP_VERSION} {APP_CODENAME}")
        title.setObjectName("appTitle")
        title.setFixedHeight(32)
        top.addWidget(title)
        self.status_dot = PulseDot(self.theme)
        top.addWidget(self.status_dot)
        top.addStretch()
        hint = QLabel("Ctrl+G · Ctrl+K · Ctrl+P · Ctrl+R · Ctrl+S · Ctrl+L · F5")
        hint.setObjectName("shortcutHint")
        top.addWidget(hint)
        lbl = QLabel("THEME")
        lbl.setObjectName("dimLabel")
        top.addWidget(lbl)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(THEMES.keys())
        self.theme_combo.setCurrentText(self.theme_name)
        self.theme_combo.currentTextChanged.connect(self.on_theme_change)
        self.theme_combo.setFixedWidth(160)
        top.addWidget(self.theme_combo)
        root.addLayout(top)

        self.banner = WaveBanner(self.theme)
        root.addWidget(self.banner)

        stats = QHBoxLayout()
        stats.setSpacing(8)
        self.stat_available = StatCard("available", "#22c55e", self.theme)
        self.stat_taken = StatCard("taken", "#ef4444", self.theme)
        self.stat_reserved = StatCard("reserved", "#eab308", self.theme)
        self.stat_rate = StatCard("rate limited", "#a855f7", self.theme)
        self.stat_honeypot = StatCard("honeypot", "#f43f5e", self.theme)
        for c in (self.stat_available, self.stat_taken, self.stat_reserved,
                  self.stat_rate, self.stat_honeypot):
            stats.addWidget(c, 1)
        root.addLayout(stats)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(8)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self._make_sidebar())
        self.splitter.addWidget(self._make_main())
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([340, 1080])
        root.addWidget(self.splitter, 1)

        self.status_bar = self.statusBar()
        self.resource_label = QLabel("CPU --%  ·  RAM -- MB  ·  RPS --")
        self.resource_label.setObjectName("monoDimLabel")
        self.status_bar.addPermanentWidget(self.resource_label)
        self.eta_label = QLabel("idle")
        self.eta_label.setObjectName("monoDimLabel")
        self.status_bar.addPermanentWidget(self.eta_label)

    def _make_sidebar(self):
        box = QFrame()
        box.setObjectName("sidebar")
        box.setMinimumWidth(300)
        box.setMaximumWidth(460)

        outer = QVBoxLayout(box)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(6)

        status_block = QWidget()
        sb_layout = QVBoxLayout(status_block)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        sb_layout.setSpacing(2)
        sb_layout.addWidget(self._section_label("STATUS"))
        self.status_label = QLabel("Ready.")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setWordWrap(True)
        sb_layout.addWidget(self.status_label)
        outer.addWidget(status_block)
        outer.addWidget(self._divider())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(6)

        gen = CollapsibleSection("GENERATOR", self.theme, expanded=True)
        self.length_input = QSpinBox()
        self.length_input.setRange(1, 30); self.length_input.setValue(5)
        gen.add_layout(self._field("Length", self.length_input))
        self.count_input = QSpinBox()
        self.count_input.setRange(1, 100000); self.count_input.setValue(50)
        gen.add_layout(self._field("Count", self.count_input))
        self.seed_input = QLineEdit()
        self.seed_input.setPlaceholderText("optional")
        gen.add_layout(self._field("Seed", self.seed_input))
        self.cb_letters = QCheckBox("Use letters"); self.cb_letters.setChecked(True)
        self.cb_digits = QCheckBox("Use digits"); self.cb_digits.setChecked(True)
        self.cb_dots = QCheckBox("Allow dots")
        self.cb_under = QCheckBox("Allow underscores")
        for cb in (self.cb_letters, self.cb_digits, self.cb_dots, self.cb_under):
            gen.add(cb)
        self.btn_generate = QPushButton("GENERATE  (Ctrl+G)")
        self.btn_generate.setObjectName("accentButton")
        self.btn_generate.setMinimumHeight(38)
        self.btn_generate.clicked.connect(self.on_generate)
        gen.add(self.btn_generate)
        inner_layout.addWidget(gen)

        chk = CollapsibleSection("CHECKER", self.theme, expanded=True)
        self.conc_input = QSpinBox()
        self.conc_input.setRange(1, 8); self.conc_input.setValue(self.user_settings.concurrency)
        chk.add_layout(self._field("Concurrency", self.conc_input))
        self.session_input = QLineEdit()
        self.session_input.setEchoMode(QLineEdit.Password)
        self.session_input.setPlaceholderText("optional")
        chk.add_layout(self._field("sessionid", self.session_input))
        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText("http://user:pass@host:port")
        chk.add_layout(self._field("Proxy", self.proxy_input))
        self.csrf_input = QLineEdit()
        self.csrf_input.setEchoMode(QLineEdit.Password)
        self.csrf_input.setPlaceholderText("optional")
        chk.add_layout(self._field("csrftoken", self.csrf_input))

        row = QHBoxLayout()
        row.setSpacing(6)
        self.btn_test_proxy = QPushButton("TEST PROXY")
        self.btn_test_proxy.setObjectName("ghostButton")
        self.btn_test_proxy.setMinimumHeight(32)
        self.btn_test_proxy.clicked.connect(self.on_test_proxy)
        row.addWidget(self.btn_test_proxy)
        self.btn_test_session = QPushButton("TEST SESSION")
        self.btn_test_session.setObjectName("ghostButton")
        self.btn_test_session.setMinimumHeight(32)
        self.btn_test_session.clicked.connect(self.on_test_session)
        row.addWidget(self.btn_test_session)
        chk.add_layout(row)

        self.btn_check = QPushButton("CHECK  (Ctrl+K)")
        self.btn_check.setObjectName("accentButton")
        self.btn_check.setMinimumHeight(38)
        self.btn_check.clicked.connect(self.on_check)
        chk.add(self.btn_check)
        inner_layout.addWidget(chk)

        act = CollapsibleSection("ACTIONS", self.theme, expanded=True)
        self.btn_import = QPushButton("IMPORT FILE")
        self.btn_import.setObjectName("ghostButton")
        self.btn_import.setMinimumHeight(32)
        self.btn_import.clicked.connect(self.on_import)
        act.add(self.btn_import)
        self.btn_export = QPushButton("EXPORT  (Ctrl+S)")
        self.btn_export.setObjectName("ghostButton")
        self.btn_export.setMinimumHeight(32)
        self.btn_export.clicked.connect(self.on_export)
        act.add(self.btn_export)
        self.btn_clear = QPushButton("CLEAR  (Ctrl+L)")
        self.btn_clear.setObjectName("ghostButton")
        self.btn_clear.setMinimumHeight(32)
        self.btn_clear.clicked.connect(self.on_clear)
        act.add(self.btn_clear)
        inner_layout.addWidget(act)

        inner_layout.addStretch()
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)

        outer.addWidget(self._divider())
        stats_block = QWidget()
        st_layout = QVBoxLayout(stats_block)
        st_layout.setContentsMargins(0, 0, 0, 0)
        st_layout.setSpacing(2)
        st_layout.addWidget(self._section_label("STATS"))
        self.stats_label = QLabel("no data")
        self.stats_label.setObjectName("statusLabel")
        self.stats_label.setWordWrap(True)
        st_layout.addWidget(self.stats_label)
        outer.addWidget(stats_block)

        return box

    def _make_main(self):
        box = QFrame()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("mainTabs")

        results_tab = QWidget()
        rl = QVBoxLayout(results_tab)
        rl.setContentsMargins(0, 8, 0, 0)
        rl.setSpacing(8)

        prog = QHBoxLayout()
        prog.setSpacing(10)
        self.circ_progress = CircularProgress(self.theme, size=86)
        prog.addWidget(self.circ_progress, 0)
        info = QVBoxLayout()
        info.setSpacing(4)
        self.summary_label = QLabel("Ready.")
        self.summary_label.setObjectName("summaryLabel")
        info.addWidget(self.summary_label)
        self.shimmer_bar = AnimatedProgressBar(self.theme)
        info.addWidget(self.shimmer_bar)
        self.progress_label = QLabel("0 / 0")
        self.progress_label.setObjectName("monoDimLabel")
        info.addWidget(self.progress_label)
        prog.addLayout(info, 1)
        rl.addLayout(prog)

        filt = QHBoxLayout()
        filt.setSpacing(6)
        filt.addWidget(QLabel("Filter:"))
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("type to filter")
        self.filter_input.textChanged.connect(self.apply_filter)
        filt.addWidget(self.filter_input, 1)
        self.btn_retry_failed = QPushButton("RETRY FAILED")
        self.btn_retry_failed.setObjectName("ghostButton")
        self.btn_retry_failed.setMinimumHeight(32)
        self.btn_retry_failed.clicked.connect(self.on_retry_failed)
        filt.addWidget(self.btn_retry_failed)
        self.btn_pause = QPushButton("PAUSE")
        self.btn_pause.setObjectName("ghostButton")
        self.btn_pause.setMinimumHeight(32)
        self.btn_pause.clicked.connect(self.on_pause_resume)
        self.btn_pause.setEnabled(False)
        filt.addWidget(self.btn_pause)
        self.btn_stop = QPushButton("STOP")
        self.btn_stop.setObjectName("ghostButton")
        self.btn_stop.setMinimumHeight(32)
        self.btn_stop.clicked.connect(self.on_stop)
        self.btn_stop.setEnabled(False)
        filt.addWidget(self.btn_stop)
        rl.addLayout(filt)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Username", "Status", "Code", "ms", "Note", "Checked at"])
        hh = self.table.horizontalHeader()
        for i in range(6):
            hh.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.Stretch)
        hh.setSectionsClickable(True)
        hh.sectionClicked.connect(self.on_header_clicked)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.on_table_context_menu)
        rl.addWidget(self.table, 1)

        self.tabs.addTab(results_tab, "Results")

        logs_tab = QWidget()
        ll = QVBoxLayout(logs_tab)
        ll.setContentsMargins(0, 8, 0, 0)
        ll.setSpacing(6)
        log_tools = QHBoxLayout()
        log_tools.addWidget(QLabel("Detailed logs:"))
        log_tools.addStretch()
        self.btn_clear_logs = QPushButton("CLEAR LOGS")
        self.btn_clear_logs.setObjectName("ghostButton")
        self.btn_clear_logs.setMinimumHeight(32)
        self.btn_clear_logs.clicked.connect(self.on_clear_logs)
        log_tools.addWidget(self.btn_clear_logs)
        self.btn_export_logs = QPushButton("EXPORT LOGS")
        self.btn_export_logs.setObjectName("ghostButton")
        self.btn_export_logs.setMinimumHeight(32)
        self.btn_export_logs.clicked.connect(self.on_export_logs)
        log_tools.addWidget(self.btn_export_logs)
        ll.addLayout(log_tools)
        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("detailedLogView")
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(5000)
        ll.addWidget(self.log_view, 1)
        self.tabs.addTab(logs_tab, "Logs")

        settings_tab = QWidget()
        sl = QVBoxLayout(settings_tab)
        sl.setContentsMargins(0, 8, 0, 0)
        sl.setSpacing(10)

        req_group = QGroupBox("Requests")
        req_form = QFormLayout(req_group)
        self.set_timeout = QDoubleSpinBox()
        self.set_timeout.setRange(1.0, 120.0)
        self.set_timeout.setValue(self.user_settings.timeout_s)
        req_form.addRow("Timeout (s):", self.set_timeout)
        self.set_retries = QSpinBox()
        self.set_retries.setRange(0, 10)
        self.set_retries.setValue(self.user_settings.retries)
        req_form.addRow("Retries:", self.set_retries)
        self.set_backoff = QDoubleSpinBox()
        self.set_backoff.setRange(0.5, 60.0)
        self.set_backoff.setValue(self.user_settings.backoff_base_s)
        req_form.addRow("Backoff base (s):", self.set_backoff)
        self.set_jitter_lo = QSpinBox()
        self.set_jitter_lo.setRange(100, 60000)
        self.set_jitter_lo.setValue(self.user_settings.jitter_lo_ms)
        req_form.addRow("Jitter min (ms):", self.set_jitter_lo)
        self.set_jitter_hi = QSpinBox()
        self.set_jitter_hi.setRange(100, 120000)
        self.set_jitter_hi.setValue(self.user_settings.jitter_hi_ms)
        req_form.addRow("Jitter max (ms):", self.set_jitter_hi)
        sl.addWidget(req_group)

        data_group = QGroupBox("Data")
        data_form = QFormLayout(data_group)
        self.set_autosave = QSpinBox()
        self.set_autosave.setRange(5, 1000)
        self.set_autosave.setValue(self.user_settings.autosave_every)
        data_form.addRow("Auto-save every N:", self.set_autosave)
        sl.addWidget(data_group)

        notif_group = QGroupBox("Notifications")
        notif_layout = QVBoxLayout(notif_group)
        self.cb_notify_sound = QCheckBox("Play sound on completion / available")
        self.cb_notify_sound.setChecked(self.user_settings.notify_sound)
        notif_layout.addWidget(self.cb_notify_sound)
        self.cb_notify_toast = QCheckBox("Show toast notifications")
        self.cb_notify_toast.setChecked(self.user_settings.notify_toast)
        notif_layout.addWidget(self.cb_notify_toast)
        self.cb_notify_available = QCheckBox("Notify when AVAILABLE found")
        self.cb_notify_available.setChecked(self.user_settings.notify_on_available)
        notif_layout.addWidget(self.cb_notify_available)
        sl.addWidget(notif_group)

        btn_row = QHBoxLayout()
        self.btn_save_settings = QPushButton("SAVE SETTINGS")
        self.btn_save_settings.setObjectName("accentButton")
        self.btn_save_settings.setMinimumHeight(38)
        self.btn_save_settings.clicked.connect(self.on_save_settings)
        btn_row.addWidget(self.btn_save_settings)
        self.btn_reset_settings = QPushButton("RESET DEFAULTS")
        self.btn_reset_settings.setObjectName("ghostButton")
        self.btn_reset_settings.setMinimumHeight(38)
        self.btn_reset_settings.clicked.connect(self.on_reset_settings)
        btn_row.addWidget(self.btn_reset_settings)
        sl.addLayout(btn_row)
        sl.addStretch()
        self.tabs.addTab(settings_tab, "Settings")

        layout.addWidget(self.tabs, 1)
        return box

    def _section_label(self, text):
        lbl = QLabel(text); lbl.setObjectName("sectionLabel"); return lbl

    def _divider(self):
        f = QFrame(); f.setFrameShape(QFrame.HLine)
        f.setObjectName("divider"); f.setFixedHeight(1); return f

    def _field(self, label_text, widget):
        row = QHBoxLayout(); row.setSpacing(6)
        lbl = QLabel(label_text); lbl.setObjectName("dimLabel")
        lbl.setFixedWidth(92)
        row.addWidget(lbl); row.addWidget(widget, 1)
        return row

    def _start_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_eta)
        self.timer.start(500)

    def _update_eta(self):
        cpu, ram, rps = self.resource_monitor.snapshot()
        self.resource_monitor.update_rps(self.done_count)
        if _HAS_PSUTIL:
            self.resource_label.setText(
                f"CPU {cpu:.0f}%  ·  RAM {ram:.0f} MB  ·  RPS {rps:.2f}")
        else:
            self.resource_label.setText(f"RPS {rps:.2f}  (install psutil for CPU/RAM)")
        if self.checking and not self.paused and self.start_time:
            elapsed = time.time() - self.start_time
            rate = self.done_count / elapsed if elapsed > 0 else 0
            remaining = (self.total - self.done_count) / rate if rate > 0 else 0
            self.eta_label.setText(
                f"elapsed {int(elapsed)}s · rate {rate:.2f}/s · eta {int(remaining)}s")
        elif self.paused: self.eta_label.setText("PAUSED")
        elif self.stopped: self.eta_label.setText("STOPPED")
        else: self.eta_label.setText("idle")

    def on_log_event(self, level, msg):
        colors = {"info": self.theme["accent"], "warn": "#eab308",
                  "error": "#ef4444", "ok": "#22c55e"}
        c = colors.get(level, self.theme["accent"])
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_view.appendPlainText(f"[{ts}] [{level.upper()}] {msg}")
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def on_clear_logs(self):
        self.log_view.clear()

    def on_export_logs(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export logs", "botcher_logs.txt",
                                               "Text (*.txt);;All (*)")
        if not path: return
        try:
            Path(path).write_text(self.log_view.toPlainText(), encoding="utf-8")
            self._toast(f"Logs saved to {path}", "ok")
        except Exception as e:
            self._toast(f"Export failed: {e}", "error")

    def on_save_settings(self):
        self.user_settings.timeout_s = self.set_timeout.value()
        self.user_settings.retries = self.set_retries.value()
        self.user_settings.backoff_base_s = self.set_backoff.value()
        self.user_settings.jitter_lo_ms = self.set_jitter_lo.value()
        self.user_settings.jitter_hi_ms = self.set_jitter_hi.value()
        self.user_settings.autosave_every = self.set_autosave.value()
        self.user_settings.notify_sound = self.cb_notify_sound.isChecked()
        self.user_settings.notify_toast = self.cb_notify_toast.isChecked()
        self.user_settings.notify_on_available = self.cb_notify_available.isChecked()
        cfg = load_config()
        cfg.update({
            "timeout_s": self.user_settings.timeout_s,
            "retries": self.user_settings.retries,
            "backoff_base_s": self.user_settings.backoff_base_s,
            "jitter_lo_ms": self.user_settings.jitter_lo_ms,
            "jitter_hi_ms": self.user_settings.jitter_hi_ms,
            "autosave_every": self.user_settings.autosave_every,
            "notify_sound": self.user_settings.notify_sound,
            "notify_toast": self.user_settings.notify_toast,
            "notify_on_available": self.user_settings.notify_on_available,
        })
        save_config(cfg)
        self._toast("Settings saved", "ok")

    def on_reset_settings(self):
        self.set_timeout.setValue(20.0)
        self.set_retries.setValue(4)
        self.set_backoff.setValue(5.0)
        self.set_jitter_lo.setValue(2000)
        self.set_jitter_hi.setValue(5000)
        self.set_autosave.setValue(25)
        self.cb_notify_sound.setChecked(True)
        self.cb_notify_toast.setChecked(True)
        self.cb_notify_available.setChecked(True)
        self._toast("Reset to defaults (click SAVE)", "warn")

    def _toast(self, text, level="info"):
        if not self.user_settings.notify_toast:
            return
        self._toast_queue.append((text, level))
        self._process_toast_queue()

    def _process_toast_queue(self):
        if self._toast_processing:
            return
        self._active_toasts = [t for t in self._active_toasts if t.isVisible()]
        if len(self._active_toasts) >= 3:
            return
        if not self._toast_queue:
            return
        self._toast_processing = True
        text, level = self._toast_queue.popleft()
        colors = {"info": self.theme["accent"], "warn": "#eab308",
                  "error": "#ef4444", "ok": "#22c55e"}
        color = colors.get(level, self.theme["accent"])
        slot = len(self._active_toasts)
        try:
            t = Toast(self, text, self.theme, color, slot=slot)
            self._active_toasts.append(t)
        except Exception:
            pass
        QTimer.singleShot(200, self._release_toast_lock)

    def _release_toast_lock(self):
        self._toast_processing = False
        self._process_toast_queue()

    def _on_toast_closed(self, toast):
        self._active_toasts = [t for t in self._active_toasts if t is not toast]
        for i, t in enumerate(self._active_toasts):
            try:
                target_y = 26 + i * (46 + 8)
                anim = QPropertyAnimation(t, b"pos")
                anim.setDuration(180)
                anim.setStartValue(t.pos())
                anim.setEndValue(QPoint(t.pos().x(), target_y))
                anim.start()
                t._repos_anim = anim
            except Exception:
                pass
        QTimer.singleShot(150, self._process_toast_queue)

    def _check_autosave_on_start(self):
        try:
            data = load_autosave()
            if data:
                reply = QMessageBox.question(
                    self, "Autosave found",
                    f"Found autosave with {len(data)} results.\nLoad it?",
                    QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self.results = [CheckResult.from_dict(d) for d in data]
                    self.checked_set = {r.username for r in self.results}
                    self._render_all_results()
                    self.on_log_event("ok", f"Loaded {len(self.results)} results from autosave")
                    self._toast(f"Loaded {len(self.results)} results", "ok")
        except Exception:
            pass

    def on_reload_autosave(self):
        self._check_autosave_on_start()

    def on_theme_change(self, name):
        if name not in THEMES: return
        self.theme_name = name
        self.theme = THEMES[name]
        cfg = load_config(); cfg["theme"] = name; save_config(cfg)
        self._apply_theme()

    def _status_colors(self):
        return STATUS_COLORS_LIGHT if self.theme.get("mode") == "light" else STATUS_COLORS_DARK

    def _apply_theme(self):
        t = self.theme
        qss = f"""
        QMainWindow, QWidget {{
            background-color: {t['bg']}; color: {t['fg']}; font-size: 13px;
        }}
        QLabel#appTitle {{
            color: {t['accent']}; font-weight: 700;
            font-size: 14px; letter-spacing: 4px;
        }}
        QLabel#shortcutHint {{
            color: {t['fg_dim']}; font-size: 10px;
            font-family: "Consolas", "monospace";
        }}
        QFrame#sidebar {{
            background-color: {t['bg2']}; border: 1px solid {t['border']};
            border-radius: 10px;
        }}
        QFrame#statCard {{
            background-color: {t['bg2']}; border: 1px solid {t['border']};
            border-radius: 8px;
        }}
        QLabel#statValue {{
            font-size: 22px; font-weight: 700;
            font-family: "Consolas", "monospace";
        }}
        QLabel#statName {{
            color: {t['fg_dim']}; font-size: 10px;
            font-weight: 700; letter-spacing: 1px;
        }}
        QLabel#sectionLabel {{
            color: {t['accent']}; font-weight: 700;
            font-size: 11px; letter-spacing: 1px; padding: 2px 0;
        }}
        QLabel#dimLabel {{ color: {t['fg_dim']}; font-size: 12px; }}
        QLabel#monoDimLabel {{
            color: {t['fg_dim']}; font-family: "Consolas", "monospace"; font-size: 11px;
        }}
        QLabel#summaryLabel {{ color: {t['fg']}; font-size: 13px; }}
        QLabel#statusLabel {{ color: {t['fg']}; font-size: 11px; }}
        QTextEdit#logView, QPlainTextEdit#detailedLogView {{
            background-color: {t['bg3']}; color: {t['fg']};
            border: 1px solid {t['border']}; border-radius: 6px;
            font-family: "Consolas", "monospace"; font-size: 11px; padding: 6px;
        }}
        QFrame#divider {{
            background-color: {t['border']}; border: none; max-height: 1px;
        }}
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
            background-color: {t['bg3']}; color: {t['fg']};
            border: 1px solid {t['border']}; border-radius: 5px;
            padding: 6px 8px; font-size: 12px;
            selection-background-color: {t['accent']};
        }}
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
            border: 1px solid {t['accent']};
        }}
        QComboBox QAbstractItemView {{
            background-color: {t['bg2']}; color: {t['fg']};
            border: 1px solid {t['border']};
            selection-background-color: {t['accent']}; selection-color: {t['bg']};
        }}
        QCheckBox {{ color: {t['fg']}; font-size: 12px; spacing: 8px; padding: 2px 0; }}
        QCheckBox::indicator {{
            width: 16px; height: 16px;
            border: 1px solid {t['border']}; border-radius: 3px;
            background-color: {t['bg3']};
        }}
        QCheckBox::indicator:checked {{
            background-color: {t['accent']}; border: 1px solid {t['accent']};
        }}
        QPushButton#accentButton {{
            background-color: {t['accent']}; color: {t['bg']};
            border: none; border-radius: 6px;
            padding: 8px 14px; font-weight: 700;
            font-size: 12px; letter-spacing: 1px;
        }}
        QPushButton#accentButton:hover {{ background-color: {t['accent_hover']}; }}
        QPushButton#accentButton:disabled {{
            background-color: {t['border']}; color: {t['fg_dim']};
        }}
        QPushButton#ghostButton {{
            background-color: {t['bg3']}; color: {t['fg']};
            border: 1px solid {t['border']}; border-radius: 6px;
            padding: 6px 10px; font-size: 11px;
        }}
        QPushButton#ghostButton:hover {{ background-color: {t['border']}; }}
        QPushButton#ghostButton:disabled {{
            color: {t['fg_dim']}; background-color: {t['bg2']};
        }}
        QPushButton#sectionToggle {{
            background-color: transparent; color: {t['accent']};
            border: none; text-align: left;
            font-weight: 700; font-size: 11px;
            letter-spacing: 1px; padding: 6px 0;
        }}
        QPushButton#sectionToggle:hover {{ color: {t['accent_hover']}; }}
        QTabWidget#mainTabs::pane {{
            background-color: {t['bg2']}; border: 1px solid {t['border']};
            border-radius: 8px; top: -1px;
        }}
        QTabBar::tab {{
            background-color: {t['bg2']}; color: {t['fg_dim']};
            border: 1px solid {t['border']}; border-bottom: none;
            padding: 8px 18px; margin-right: 2px;
            border-top-left-radius: 6px; border-top-right-radius: 6px;
            font-size: 12px; font-weight: 600;
        }}
        QTabBar::tab:selected {{
            background-color: {t['bg3']}; color: {t['accent']};
            border-bottom: 2px solid {t['accent']};
        }}
        QGroupBox {{
            color: {t['accent']}; font-weight: 700;
            border: 1px solid {t['border']}; border-radius: 6px;
            margin-top: 12px; padding-top: 8px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin; left: 10px; padding: 0 5px;
        }}
        QTableWidget {{
            background-color: {t['bg2']}; alternate-background-color: {t['bg']};
            color: {t['fg']}; border: 1px solid {t['border']};
            border-radius: 6px; gridline-color: {t['border']};
            font-family: "Consolas", "monospace"; font-size: 11px;
        }}
        QTableWidget::item {{ padding: 5px; }}
        QTableWidget::item:selected {{
            background-color: {t['accent']}; color: {t['bg']};
        }}
        QHeaderView::section {{
            background-color: {t['bg3']}; color: {t['accent']};
            border: none; border-bottom: 1px solid {t['border']};
            padding: 6px; font-weight: 700; font-size: 11px; letter-spacing: 1px;
        }}
        QMenu {{
            background-color: {t['bg2']}; color: {t['fg']};
            border: 1px solid {t['border']};
        }}
        QMenu::item:selected {{
            background-color: {t['accent']}; color: {t['bg']};
        }}
        QStatusBar {{
            background-color: {t['bg2']}; color: {t['fg_dim']};
            border-top: 1px solid {t['border']};
        }}
        QScrollArea {{ background: transparent; border: none; }}
        QScrollBar:vertical {{
            background-color: {t['bg2']}; width: 8px;
            border-radius: 4px; margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background-color: {t['border']}; border-radius: 4px; min-height: 24px;
        }}
        QScrollBar::handle:vertical:hover {{ background-color: {t['accent']}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QSplitter::handle {{ background-color: {t['border']}; }}
        QSplitter::handle:hover {{ background-color: {t['accent']}; }}
        """
        self.setStyleSheet(qss)
        try:
            self.status_dot.set_theme(t)
            self.banner.set_theme(t)
            self.circ_progress.set_theme(t)
            self.shimmer_bar.set_theme(t)
            for c in (self.stat_available, self.stat_taken, self.stat_reserved,
                      self.stat_rate, self.stat_honeypot):
                c.theme = t
        except Exception:
            pass
        self._refresh_table_colors()

    def _refresh_table_colors(self):
        try:
            colors = self._status_colors()
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 1)
                if item:
                    color = colors.get(item.text())
                    if color: item.setForeground(QColor(color))
        except Exception:
            pass

    def _make_row(self, r):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(r.username))
        status_item = QTableWidgetItem(r.availability.value)
        colors = self._status_colors()
        color = colors.get(r.availability.value, self.theme["fg"])
        status_item.setForeground(QColor(color))
        self.table.setItem(row, 1, status_item)
        self.table.setItem(row, 2, QTableWidgetItem(str(r.status_code or "-")))
        self.table.setItem(row, 3, QTableWidgetItem(f"{r.latency_ms:.0f}" if r.latency_ms else "-"))
        self.table.setItem(row, 4, QTableWidgetItem(r.note or ""))
        self.table.setItem(row, 5, QTableWidgetItem(r.checked_at.strftime("%H:%M:%S")))

    def _render_all_results(self):
        self.table.setRowCount(0)
        for r in self.results:
            self._make_row(r)
        self._update_stats()

    def _update_stats(self):
        counts = Counter(r.availability.value for r in self.results)
        self.summary_label.setText(
            "  ·  ".join(f"{k}: {v}" for k, v in counts.most_common()) or "Ready.")
        self.stats_label.setText(
            "\n".join(f"{k}: {v}" for k, v in counts.most_common()) or "no data")
        try:
            self.stat_available.set_value(counts.get("available", 0))
            self.stat_taken.set_value(counts.get("taken", 0))
            self.stat_reserved.set_value(counts.get("reserved", 0))
            self.stat_rate.set_value(counts.get("rate_limited", 0))
            self.stat_honeypot.set_value(counts.get("honeypot", 0))
        except Exception:
            pass

    def apply_filter(self, text):
        text = text.strip().lower()
        for row in range(self.table.rowCount()):
            if not text:
                self.table.setRowHidden(row, False); continue
            match = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and text in item.text().lower():
                    match = True; break
            self.table.setRowHidden(row, not match)

    def on_header_clicked(self, index):
        reverse = getattr(self, "_sort_reverse", False)
        try:
            self.table.sortItems(index, Qt.DescendingOrder if reverse else Qt.AscendingOrder)
        except Exception:
            pass
        self._sort_reverse = not reverse

    def on_table_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item: return
        row = item.row()
        ui = self.table.item(row, 0)
        if not ui: return
        username = ui.text()
        menu = QMenu(self)
        a1 = QAction("Copy username", self)
        a1.triggered.connect(lambda: QApplication.clipboard().setText(username))
        menu.addAction(a1)
        a2 = QAction("Open in browser", self)
        a2.triggered.connect(lambda: __import__("webbrowser").open(f"https://instagram.com/{username}"))
        menu.addAction(a2)
        a3 = QAction("Filter by this", self)
        a3.triggered.connect(lambda: self.filter_input.setText(username))
        menu.addAction(a3)
        a4 = QAction("Remove row", self)
        def remove():
            self.table.removeRow(row)
            self.results = [r for r in self.results if r.username != username]
            self.checked_set.discard(username)
            self._update_stats()
        a4.triggered.connect(remove)
        menu.addAction(a4)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def on_generate(self):
        if self.checking:
            self._toast("Check running", "warn"); return
        length = self.length_input.value()
        count = self.count_input.value()
        if not (self.cb_letters.isChecked() or self.cb_digits.isChecked()):
            self._toast("Select letters or digits", "error"); return
        seed_raw = self.seed_input.text().strip()
        seed = int(seed_raw) if seed_raw.isdigit() else None
        self.candidates = generate_random(
            length=length, count=count,
            use_letters=self.cb_letters.isChecked(),
            use_digits=self.cb_digits.isChecked(),
            use_dots=self.cb_dots.isChecked(),
            use_underscores=self.cb_under.isChecked(),
            seed=seed)
        self.on_log_event("ok", f"Generated {len(self.candidates)} candidates")
        self._toast(f"Generated {len(self.candidates)}", "ok")

    def on_check(self):
        if self.checking:
            self._toast("Check running", "warn"); return
        if not self.candidates:
            self._toast("Generate or import first", "error"); return
        concurrency = self.conc_input.value()
        session_id = self.session_input.text().strip() or None
        proxy = self.proxy_input.text().strip() or None
        csrf_token = self.csrf_input.text().strip() or None
        if not session_id:
            reply = QMessageBox.question(self, "No sessionid",
                "sessionid is empty. IG returns 401/403.\nContinue?",
                QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes: return
        to_check = [u for u in self.candidates if u not in self.checked_set]
        skipped = len(self.candidates) - len(to_check)
        if skipped:
            self.on_log_event("warn", f"Skipped {skipped} already-checked")
        if not to_check:
            self._toast("All already checked", "warn"); return

        settings = Settings(
            concurrency=concurrency, proxy=proxy,
            session_id=session_id, csrf_token=csrf_token,
            timeout_s=self.user_settings.timeout_s,
            retries=self.user_settings.retries,
            backoff_base_s=self.user_settings.backoff_base_s,
            jitter_lo_ms=self.user_settings.jitter_lo_ms,
            jitter_hi_ms=self.user_settings.jitter_hi_ms,
        )

        self.checking = True
        self.paused = False
        self.stopped = False
        self.total = len(to_check)
        self.done_count = 0
        self.start_time = time.time()
        self.shimmer_bar.set_value(0, self.total)
        self.shimmer_bar.set_active(True)
        self.circ_progress.set_value(0, self.total)
        self.progress_label.setText(f"0 / {self.total}")
        self.btn_pause.setEnabled(True); self.btn_pause.setText("PAUSE")
        self.btn_stop.setEnabled(True)
        self.btn_check.setEnabled(False)
        self.status_dot.set_active(True, self.theme["accent"])
        self.on_log_event("info", f"Checking {self.total} (conc={concurrency})")
        self._toast(f"Checking {self.total}", "info")
        self.runner.submit_check(to_check, settings)

    def on_pause_resume(self):
        if not self.checking: return
        if self.paused:
            self.runner.resume()
            self.paused = False
            self.btn_pause.setText("PAUSE")
            self.status_dot.set_active(True, self.theme["accent"])
            self.on_log_event("ok", "Resumed")
            self._toast("Resumed", "ok")
        else:
            self.runner.pause()
            self.paused = True
            self.btn_pause.setText("RESUME")
            self.status_dot.set_active(False)
            self.on_log_event("warn", "Paused")
            self._toast("Paused", "warn")

    def on_stop(self):
        if not self.checking: return
        self.runner.stop()
        self.stopped = True
        self.checking = False
        self.btn_pause.setEnabled(False); self.btn_stop.setEnabled(False)
        self.btn_check.setEnabled(True)
        self.shimmer_bar.set_active(False)
        self.status_dot.set_active(False)
        self.on_log_event("error", "Stopped by user")
        self._toast("Stopped", "error")

    def on_result(self, r):
        if r.username in self.checked_set: return
        self.checked_set.add(r.username)
        self.results.append(r)
        self.done_count += 1
        self._make_row(r)
        self.table.scrollToBottom()
        self.shimmer_bar.set_value(self.done_count, self.total)
        self.circ_progress.set_value(self.done_count, self.total)
        self.progress_label.setText(f"{self.done_count} / {self.total}")
        self._update_stats()
        # special notify for AVAILABLE
        if (r.availability == Availability.AVAILABLE
                and self.user_settings.notify_on_available):
            if self.user_settings.notify_sound:
                threading.Thread(target=play_sound, args=("ok",), daemon=True).start()
            self._toast(f"AVAILABLE: {r.username}", "ok")
        if self.done_count % self.user_settings.autosave_every == 0:
            save_autosave(self.results)

    def on_finished(self):
        self.checking = False
        self.paused = False
        self.btn_pause.setEnabled(False); self.btn_stop.setEnabled(False)
        self.btn_check.setEnabled(True)
        self.shimmer_bar.set_active(False)
        self.status_dot.set_active(False)
        if not self.stopped:
            self.on_log_event("ok", f"Done. {self.done_count} checked.")
            self._toast(f"Done. {self.done_count} checked.", "ok")
            if self.user_settings.notify_sound:
                threading.Thread(target=play_sound, args=("info",), daemon=True).start()
        clear_autosave()

    def on_retry_failed(self):
        if self.checking:
            self._toast("Check running", "warn"); return
        failed = [r.username for r in self.results
                  if r.availability in (Availability.ERROR, Availability.UNKNOWN)]
        if not failed:
            self._toast("No failed to retry", "warn"); return
        for u in failed: self.checked_set.discard(u)
        self.results = [r for r in self.results if r.username not in set(failed)]
        self._render_all_results()
        self.candidates = failed
        self.on_log_event("warn", f"Retrying {len(failed)}")
        self._toast(f"Retrying {len(failed)}", "warn")
        self.on_check()

    def on_test_proxy(self):
        proxy = self.proxy_input.text().strip()
        if not proxy:
            self._toast("No proxy", "error"); return
        def worker():
            try:
                with httpx.Client(proxy=proxy, timeout=10.0) as c:
                    r = c.get("https://api.ipify.org?format=json")
                    if r.status_code == 200:
                        ip = r.json().get("ip", "?")
                        self.on_log_event("ok", f"Proxy OK — IP {ip}")
                        self._toast(f"Proxy OK — {ip}", "ok")
                    else:
                        self.on_log_event("error", f"Proxy {r.status_code}")
            except Exception as e:
                self.on_log_event("error", f"Proxy failed: {type(e).__name__}")
                self._toast("Proxy failed", "error")
        threading.Thread(target=worker, daemon=True).start()
        self.on_log_event("info", "Testing proxy…")

    def on_test_session(self):
        sid = self.session_input.text().strip()
        if not sid:
            self._toast("No sessionid", "error"); return
        def worker():
            try:
                headers = _build_headers(Settings().user_agent)
                r = httpx.get(_WEB_PROFILE_INFO_URL, params={"username": "instagram"},
                              headers=headers, cookies={"sessionid": sid}, timeout=15.0)
                if r.status_code == 200:
                    self.on_log_event("ok", "Session valid")
                    self._toast("Session valid", "ok")
                elif r.status_code == 401:
                    self.on_log_event("error", "Session invalid (401)")
                    self._toast("Session invalid", "error")
                else:
                    self.on_log_event("warn", f"Session {r.status_code}")
            except Exception as e:
                self.on_log_event("error", f"Session test failed: {type(e).__name__}")
        threading.Thread(target=worker, daemon=True).start()
        self.on_log_event("info", "Testing session…")

    def on_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose usernames file", "",
                                               "Text (*.txt);;All (*)")
        if not path: return
        try:
            lines = Path(path).read_text(encoding="utf-8").splitlines()
        except Exception as e:
            self._toast(f"Read failed: {e}", "error"); return
        self.candidates = [ln.strip() for ln in lines
                           if ln.strip() and not ln.startswith("#")]
        self.on_log_event("ok", f"Imported {len(self.candidates)}")
        self._toast(f"Imported {len(self.candidates)}", "ok")

    def on_export(self):
        if not self.results:
            self._toast("No results", "warn"); return
        out_dir = QFileDialog.getExistingDirectory(self, "Export directory")
        if not out_dir: return
        out_path = Path(out_dir)
        try:
            (out_path / "results.json").write_text(
                json.dumps([r.to_dict() for r in self.results], indent=2),
                encoding="utf-8")
            with (out_path / "results.csv").open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["username", "availability", "status_code", "latency_ms", "note"])
                for r in self.results:
                    w.writerow([r.username, r.availability.value,
                                r.status_code, r.latency_ms, r.note or ""])
            (out_path / "results.txt").write_text(
                "\n".join(f"{r.username}\t{r.availability.value}" for r in self.results),
                encoding="utf-8")
            manifest = {}
            for name in ("results.json", "results.csv", "results.txt"):
                data = (out_path / name).read_bytes()
                manifest[name] = {"size": len(data),
                                  "sha256": hashlib.sha256(data).hexdigest()}
            (out_path / "manifest.json").write_text(
                json.dumps(manifest, indent=2), encoding="utf-8")
        except Exception as e:
            self._toast(f"Export failed: {e}", "error"); return
        self.on_log_event("ok", f"Exported to {out_dir}")
        self._toast("Exported with manifest", "ok")

    def on_clear(self):
        self.results.clear(); self.candidates.clear(); self.checked_set.clear()
        self.table.setRowCount(0)
        self.shimmer_bar.set_value(0, 1, animated=False)
        self.circ_progress.set_value(0, 1, animated=False)
        self.progress_label.setText("0 / 0")
        self.summary_label.setText("Ready.")
        self.stats_label.setText("no data")
        self.log_view.clear()
        try:
            for c in (self.stat_available, self.stat_taken, self.stat_reserved,
                      self.stat_rate, self.stat_honeypot):
                c.set_value(0)
        except Exception:
            pass
        clear_autosave()
        self._toast("Cleared", "info")

    def closeEvent(self, event):
        try:
            if self.checking:
                reply = QMessageBox.question(self, "Check running",
                    "Autosave keeps results.\nQuit?",
                    QMessageBox.Yes | QMessageBox.No)
                if reply != QMessageBox.Yes:
                    event.ignore(); return
                self.runner.stop()
            save_autosave(self.results)
            cfg = load_config()
            cfg["theme"] = self.theme_name
            cfg["window_size"] = [self.width(), self.height()]
            if hasattr(self, "splitter"):
                cfg["splitter"] = self.splitter.sizes()
            save_config(cfg)
            self.runner.stop_loop()
        except Exception:
            pass
        event.accept()


# =========================================================
# MAIN
# =========================================================

def main():
    try:
        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)

        # --- Icon loading ---
        icon_paths = [
            Path(__file__).resolve().parent / "botcher_icon.png",
            Path(__file__).resolve().parent / "botcher_icon.ico",
            Path(__file__).resolve().parent / "icon.png",
            Path(__file__).resolve().parent / "icon.ico",
            Path.cwd() / "botcher_icon.png",
            Path.cwd() / "botcher_icon.ico",
        ]
        icon = None
        for p in icon_paths:
            if p.exists():
                try:
                    icon = QIcon(str(p))
                    app.setWindowIcon(icon)
                    print(f"[icon] loaded {p}")
                    break
                except Exception:
                    continue
        if icon is None:
            print("[icon] not found — using default")

        window = BotcherApp()
        if icon is not None:
            window.setWindowIcon(icon)
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            QMessageBox.critical(None, "BOTCHER crashed",
                f"{type(e).__name__}: {e}")
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
