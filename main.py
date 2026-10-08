#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BOTCHER APK — Kivy app for Android."""
import threading
import random
import string
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.properties import StringProperty
from kivy.core.clipboard import Clipboard

try:
    import httpx
except ImportError:
    httpx = None

_VALID_CHARS = set(string.ascii_lowercase + string.digits + "._")
_URL = "https://i.instagram.com/api/v1/users/web_profile_info/"
_HEADERS = {
    "user-agent": (
        "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
    ),
    "x-ig-app-id": "936619743392459",
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "referer": "https://www.instagram.com/",
    "x-requested-with": "XMLHttpRequest",
    "origin": "https://www.instagram.com",
}


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


def generate_random(length, count, seed=None):
    rng = random.Random(seed)
    pool = string.ascii_lowercase + string.digits
    out = set()
    attempts = 0
    max_attempts = max(count * 50, 1000)
    while len(out) < count and attempts < max_attempts:
        attempts += 1
        cand = "".join(rng.choice(pool) for _ in range(length))
        if _is_valid(cand):
            out.add(cand)
    return list(out)


def check_one(username, session_id=None, timeout=20.0):
    if httpx is None:
        return username, "error", None, "httpx missing"
    username = username.strip().lower().lstrip("@")
    cookies = {}
    if session_id:
        cookies["sessionid"] = session_id
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True,
                          headers=_HEADERS, cookies=cookies or None) as client:
            r = client.get(_URL, params={"username": username})
            code = r.status_code
            if code == 200:
                try:
                    data = r.json()
                except Exception:
                    data = {}
                user = (data.get("data") or {}).get("user")
                if user:
                    return username, "taken", code, ""
                return username, "available", code, ""
            if code == 404:
                return username, "available", code, ""
            if code == 429:
                return username, "rate_limited", code, "rate limited"
            if code == 401:
                return username, "error", code, "invalid session"
            if code == 403:
                return username, "reserved", code, "blocked"
            return username, "unknown", code, ""
    except httpx.TimeoutException:
        return username, "error", None, "Timeout"
    except Exception as e:
        return username, "error", None, type(e).__name__


class MainLayout(BoxLayout):
    status_text = StringProperty("Ready.")
    progress_text = StringProperty("0 / 0")

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=10, spacing=8, **kwargs)

        self.add_widget(Label(
            text="BOTCHER", font_size="28sp",
            size_hint_y=None, height=50, color=(0.02, 0.71, 0.83, 1)))

        self.status_label = Label(text=self.status_text, size_hint_y=None,
                                  height=30, font_size="13sp")
        self.add_widget(self.status_label)

        gen = GridLayout(cols=2, size_hint_y=None, height=100, spacing=4)
        gen.add_widget(Label(text="Length:", size_hint_x=0.3))
        self.length_input = TextInput(text="5", multiline=False, input_filter="int")
        gen.add_widget(self.length_input)
        gen.add_widget(Label(text="Count:", size_hint_x=0.3))
        self.count_input = TextInput(text="20", multiline=False, input_filter="int")
        gen.add_widget(self.count_input)
        self.add_widget(gen)

        sess = BoxLayout(size_hint_y=None, height=40, spacing=4)
        sess.add_widget(Label(text="sessionid:", size_hint_x=0.3))
        self.session_input = TextInput(multiline=False, password=True)
        sess.add_widget(self.session_input)
        self.add_widget(sess)

        row = BoxLayout(size_hint_y=None, height=48, spacing=6)
        self.btn_gen = Button(text="GENERATE",
                              background_color=(0.02, 0.71, 0.83, 1))
        self.btn_gen.bind(on_press=self.on_generate)
        row.add_widget(self.btn_gen)
        self.btn_chk = Button(text="CHECK",
                              background_color=(0.02, 0.71, 0.83, 1))
        self.btn_chk.bind(on_press=self.on_check)
        row.add_widget(self.btn_chk)
        self.add_widget(row)

        self.progress_label = Label(text=self.progress_text, size_hint_y=None,
                                    height=30, font_size="12sp")
        self.add_widget(self.progress_label)

        self.results_scroll = ScrollView()
        self.results_grid = GridLayout(cols=1, size_hint_y=None, spacing=2)
        self.results_grid.bind(
            minimum_height=self.results_grid.setter("height"))
        self.results_scroll.add_widget(self.results_grid)
        self.add_widget(self.results_scroll)

        bot = BoxLayout(size_hint_y=None, height=42, spacing=6)
        self.btn_copy = Button(text="COPY ALL")
        self.btn_copy.bind(on_press=self.on_copy_all)
        bot.add_widget(self.btn_copy)
        self.btn_clear = Button(text="CLEAR")
        self.btn_clear.bind(on_press=self.on_clear)
        bot.add_widget(self.btn_clear)
        self.add_widget(bot)

        self.candidates = []
        self.results = []
        self.checking = False

    def log(self, msg):
        self.status_text = msg
        self.status_label.text = msg

    def add_row(self, username, status, code, note):
        colors = {
            "available": (0.13, 0.77, 0.37, 1),
            "taken": (0.94, 0.27, 0.27, 1),
            "reserved": (0.92, 0.70, 0.03, 1),
            "rate_limited": (0.66, 0.33, 0.97, 1),
            "unknown": (0.02, 0.71, 0.83, 1),
            "error": (0.86, 0.15, 0.15, 1),
        }
        color = colors.get(status, (0.8, 0.8, 0.8, 1))
        text = f"{username}  ·  {status}  ·  {code or '-'}"
        if note:
            text += f"  ·  {note}"
        lbl = Label(text=text, size_hint_y=None, height=28,
                    color=color, font_size="12sp", halign="left")
        lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        self.results_grid.add_widget(lbl)

    def on_generate(self, *args):
        try:
            length = int(self.length_input.text or "5")
            count = int(self.count_input.text or "20")
        except ValueError:
            self.log("Length w Count khass ykounou raqam")
            return
        if not (1 <= length <= 30):
            self.log("Length khass ykoun bin 1 w 30")
            return
        if not (1 <= count <= 1000):
            self.log("Count khass ykoun bin 1 w 1000")
            return
        self.candidates = generate_random(length, count)
        self.log(f"Generated {len(self.candidates)} usernames")
        self.progress_text = f"0 / {len(self.candidates)}"
        self.progress_label.text = self.progress_text

    def on_check(self, *args):
        if self.checking:
            self.log("Check déjà kayn")
            return
        if not self.candidates:
            self.log("Generate awalan")
            return
        self.checking = True
        self.results_grid.clear_widgets()
        self.results = []
        self.log(f"Checking {len(self.candidates)}...")
        session_id = self.session_input.text.strip() or None
        threading.Thread(target=self._run_check,
                         args=(self.candidates, session_id),
                         daemon=True).start()

    def _run_check(self, candidates, session_id):
        total = len(candidates)
        for i, u in enumerate(candidates, 1):
            result = check_one(u, session_id)
            self.results.append(result)
            Clock.schedule_once(
                lambda dt, r=result: self.add_row(*r), 0)
            Clock.schedule_once(
                lambda dt, i=i, t=total: self._progress(i, t), 0)
        Clock.schedule_once(lambda dt: self._finish(), 0)

    def _progress(self, i, t):
        self.progress_text = f"{i} / {t}"
        self.progress_label.text = self.progress_text

    def _finish(self):
        self.checking = False
        self.log(f"Done. {len(self.results)} checked.")

    def on_copy_all(self, *args):
        lines = [f"{u}\t{s}" for u, s, _, _ in self.results]
        Clipboard.copy("\n".join(lines))
        self.log("Copied to clipboard")

    def on_clear(self, *args):
        self.results_grid.clear_widgets()
        self.results = []
        self.candidates = []
        self.progress_text = "0 / 0"
        self.progress_label.text = self.progress_text
        self.log("Cleared")


class BotcherApp(App):
    def build(self):
        self.title = "BOTCHER"
        return MainLayout()


if __name__ == "__main__":
    BotcherApp().run()
