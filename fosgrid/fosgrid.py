#!/usr/bin/env python3
import json
import threading
import time
import os
import signal
from urllib.parse import quote

import cv2
from tkinter import Tk, Frame, Label, BOTH
from PIL import Image, ImageTk, ImageOps

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

FILL_MODE = {"value": False}


class CamWidget:
    def __init__(self, parent, cfg):
        self.cfg = cfg
        self.ip = cfg.get("ip", "")
        self.full_url = cfg.get("full_url")
        self.disabled = not (self.ip and cfg.get("port"))
        self.label = Label(parent, bg="black", fg="white")
        self.label.pack(fill=BOTH, expand=True)

        self.state = "disabled" if self.disabled else "loading"
        self.frame = None
        self.loading_phase = 0
        self.stop = False
        self.photo = None
        self.thread = None

        if not self.disabled:
            self.thread = threading.Thread(target=self.worker, daemon=True)
            self.thread.start()

        self.update_gui()

    def build_url(self):
        if self.full_url:
            return self.full_url

        ip = self.cfg.get("ip", "")
        port = self.cfg.get("port", 0)
        user = self.cfg.get("username", "")
        pw = self.cfg.get("password", "")
        path = self.cfg.get("path", "")

        if path and not path.startswith("/"):
            path = "/" + path

        user_enc = quote(user, safe="")
        pw_enc = quote(pw, safe="")

        return f"rtsp://{user_enc}:{pw_enc}@{ip}:{port}{path}"

    def worker(self):
        while not self.stop:
            self.state = "loading"
            url = self.build_url()

            cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)

            if not cap.isOpened():
                self.state = "error"
                for _ in range(30):
                    if self.stop:
                        cap.release()
                        return
                    time.sleep(0.1)
                continue

            self.state = "ok"
            empty_count = 0

            while not self.stop:
                ok, frame = cap.read()
                if not ok or frame is None:
                    empty_count += 1
                    if empty_count > 50:
                        self.state = "error"
                        break
                    time.sleep(0.1)
                    continue

                empty_count = 0
                self.frame = frame

            cap.release()
            for _ in range(30):
                if self.stop:
                    return
                time.sleep(0.1)

    def update_gui(self):
        if self.stop:
            return

        if self.disabled:
            self.label.config(bg="black", text="", image="")
        elif self.state == "ok" and self.frame is not None:
            try:
                rgb = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb)
                w = self.label.winfo_width() or 320
                h = self.label.winfo_height() or 240

                if FILL_MODE["value"]:
                    img = img.resize((w, h), Image.BILINEAR)
                else:
                    img = ImageOps.contain(img, (w, h))

                self.photo = ImageTk.PhotoImage(img)
                self.label.config(image=self.photo, text="")
            except Exception:
                self.state = "error"
        elif self.state == "loading":
            phases = ["●      ", " ●     ", "  ●    ", "   ●   ",
                      "    ●  ", "     ● ", "      ●", "     ● ",
                      "    ●  ", "   ●   ", "  ●    ", " ●     "]
            txt = phases[self.loading_phase % len(phases)]
            self.loading_phase += 1
            self.label.config(
                bg="black",
                text=f"{self.ip}\n{txt}",
                image="",
                font=("Helvetica", 18)
            )
        elif self.state == "error":
            self.label.config(
                bg="black",
                text="X",
                image="",
                fg="red",
                font=("Helvetica", 72)
            )

        self.label.after(100, self.update_gui)


def main():
    with open("config.json", "r") as f:
        cams = json.load(f)

    if not isinstance(cams, list) or not cams:
        raise ValueError("config.json must be a non-empty JSON array")

    while len(cams) < 4:
        cams.append({"ip": "", "port": 0, "username": "", "password": "", "path": ""})
    cams = cams[:4]

    root = Tk()
    root.title("fosgrid")
    root.configure(bg="black")

    try:
        root.state("zoomed")
    except Exception:
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{sw}x{sh}+0+0")

    for r in range(2):
        root.grid_rowconfigure(r, weight=1, uniform="row")
    for c in range(2):
        root.grid_columnconfigure(c, weight=1, uniform="col")

    frames = []
    for r in range(2):
        for c in range(2):
            f = Frame(root, bg="black", highlightthickness=0)
            f.grid(row=r, column=c, sticky="nsew")
            frames.append(f)

    widgets = [CamWidget(frames[i], cams[i]) for i in range(4)]
    fullscreen = {"index": None}
    closing = {"value": False}

    def restoreGrid():
        fullscreen["index"] = None
        idx = 0
        for rr in range(2):
            for cc in range(2):
                frames[idx].grid_forget()
                frames[idx].grid(row=rr, column=cc, sticky="nsew")
                idx += 1
        root.update_idletasks()

    def showFullscreen(i):
        fullscreen["index"] = i
        for f in frames:
            f.grid_forget()
        frames[i].grid(row=0, column=0, rowspan=2, columnspan=2, sticky="nsew")
        root.update_idletasks()

    def onCamClick(i, _event=None):
        if fullscreen["index"] == i:
            restoreGrid()
        elif fullscreen["index"] is None:
            showFullscreen(i)
        else:
            showFullscreen(i)

    def onEscape(_event=None):
        if fullscreen["index"] is not None:
            restoreGrid()

    def onFKey(_event=None):
        FILL_MODE["value"] = not FILL_MODE["value"]

    def shutdown():
        if closing["value"]:
            return
        closing["value"] = True

        for w in widgets:
            w.stop = True
        for w in widgets:
            if w.thread is not None:
                try:
                    w.thread.join(timeout=2)
                except RuntimeError:
                    pass

        if root.winfo_exists():
            root.destroy()

    def onClose():
        shutdown()

    for i, w in enumerate(widgets):
        if not w.disabled:
            w.label.bind("<Button-1>", lambda e, idx=i: onCamClick(idx))

    root.bind("<Escape>", onEscape)
    root.bind("<Key-f>", onFKey)
    root.bind("<Key-F>", onFKey)
    root.protocol("WM_DELETE_WINDOW", onClose)

    def signalHandler(signum, frame):
        shutdown()

    signal.signal(signal.SIGINT, signalHandler)
    signal.signal(signal.SIGTERM, signalHandler)
    signal.signal(signal.SIGTSTP, signalHandler)

    try:
        root.mainloop()
    finally:
        shutdown()


if __name__ == "__main__":
    main()
