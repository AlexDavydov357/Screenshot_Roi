import wx
from PIL import Image, ImageGrab, ImageFilter, ImageDraw, ImageFont
from datetime import datetime
from functools import lru_cache
import copy
import json
import math
from pathlib import Path
import sys
from wx.lib.embeddedimage import PyEmbeddedImage

# Проверка на wxPython Phoenix (для совместимости)
if not hasattr(wx, 'Display'):
    wx.MessageBox("Ваша версия wxPython устарела. Требуется wxPython Phoenix (4.0+).", "Ошибка", wx.OK | wx.ICON_ERROR)
    sys.exit(1)

import ctypes
from ctypes import wintypes
import winsound
import time
import threading as th

# Константы Windows API
MONITOR_DEFAULTTONULL = 0x00000000
MONITOR_DEFAULTTOPRIMARY = 0x00000001
MONITOR_DEFAULTTONEAREST = 0x00000002

# Callback-функция для EnumDisplayMonitors
MONITORENUMPROC = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.HMONITOR,
    wintypes.HDC,
    ctypes.POINTER(wintypes.RECT),
    wintypes.LPARAM
)


def _set_dpi_awareness():
    """Включает DPI-осведомлённость процесса, чтобы координаты мониторов из EnumDisplayMonitors
        были в тех же физических пикселях, что и снимок ImageGrab.grab(all_screens=True).
        Без этого при масштабе Windows 125%/150% координаты «съезжают».
    """
    try:
        # Per-Monitor v2 (Windows 10 1703+)
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        return
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass


_set_dpi_awareness()


def _get_monitors():
    """Возвращает список мониторов: [(x, y, w, h), ...] в физических пикселях
        Использует Windows API (EnumDisplayMonitors + callback) для получения точных координат.
        Работает только на Windows.
    """
    monitors = []

    def callback(hmonitor, hdc, lprcMonitor, lParam):
        rect = lprcMonitor.contents
        x, y = rect.left, rect.top
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        monitors.append((x, y, w, h))
        return True  # продолжаем перечисление

    EnumDisplayMonitors = ctypes.windll.user32.EnumDisplayMonitors
    EnumDisplayMonitors.argtypes = [wintypes.HDC, ctypes.POINTER(wintypes.RECT), MONITORENUMPROC, wintypes.LPARAM]
    EnumDisplayMonitors(None, None, MONITORENUMPROC(callback), 0)

    return monitors


# ----------------------------------------------------------------------
_screen_shot_icon_32 = PyEmbeddedImage(
    b'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAABMWlDQ1BBZG9iZSBSR0IgKDE5'
    b'OTgpAAAoz62OsUrDUBRAz4ui4lArBHFweJMoKLbqYMakLUUQrNUhydakoUppEl5e1X6Eo1sH'
    b'F3e/wMlRcFD8Av9AcergECGDgwie6dzD5XLBqNh1p2GUYRBr1W460vV8OfvEDFMA0Amz1G61'
    b'DgDiJI74wecrAuB50647Df7GfJgqDUyA7W6UhSAqQP9CpxrEGDCDfqpB3AGmOmnXQDwApV7u'
    b'L0ApyP0NKCnX80F8AGbP9Xww5gAzyH0FMHV0qQFqSTpSZ71TLauWZUm7mwSRPB5lOhpkcj8O'
    b'E5UmqqOjLpD/B8BivthuOnKtall76/wzrufL3N6PEIBYeixaQThU598qjJ3f5+LGeBkOb2F6'
    b'UrTdK7jZgIXroq1WobwF9+MvwMZP/U6/OGUAAAAJcEhZcwAACxMAAAsTAQCanBgAAAahaVRY'
    b'dFhNTDpjb20uYWRvYmUueG1wAAAAAAA8P3hwYWNrZXQgYmVnaW49Iu+7vyIgaWQ9Ilc1TTBN'
    b'cENlaGlIenJlU3pOVGN6a2M5ZCI/PiA8eDp4bXBtZXRhIHhtbG5zOng9ImFkb2JlOm5zOm1l'
    b'dGEvIiB4OnhtcHRrPSJBZG9iZSBYTVAgQ29yZSA1LjYtYzE0NSA3OS4xNjM0OTksIDIwMTgv'
    b'MDgvMTMtMTY6NDA6MjIgICAgICAgICI+IDxyZGY6UkRGIHhtbG5zOnJkZj0iaHR0cDovL3d3'
    b'dy53My5vcmcvMTk5OS8wMi8yMi1yZGYtc3ludGF4LW5zIyI+IDxyZGY6RGVzY3JpcHRpb24g'
    b'cmRmOmFib3V0PSIiIHhtbG5zOnhtcD0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wLyIg'
    b'eG1sbnM6ZGM9Imh0dHA6Ly9wdXJsLm9yZy9kYy9lbGVtZW50cy8xLjEvIiB4bWxuczpwaG90'
    b'b3Nob3A9Imh0dHA6Ly9ucy5hZG9iZS5jb20vcGhvdG9zaG9wLzEuMC8iIHhtbG5zOnhtcE1N'
    b'PSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvbW0vIiB4bWxuczpzdEV2dD0iaHR0cDov'
    b'L25zLmFkb2JlLmNvbS94YXAvMS4wL3NUeXBlL1Jlc291cmNlRXZlbnQjIiB4bXA6Q3JlYXRv'
    b'clRvb2w9IkFkb2JlIFBob3Rvc2hvcCBDQyAyMDE5IChXaW5kb3dzKSIgeG1wOkNyZWF0ZURh'
    b'dGU9IjIwMjYtMDYtMzBUMTY6NDg6MzArMDM6MDAiIHhtcDpNb2RpZnlEYXRlPSIyMDI2LTA2'
    b'LTMwVDE2OjQ5OjU1KzAzOjAwIiB4bXA6TWV0YWRhdGFEYXRlPSIyMDI2LTA2LTMwVDE2OjQ5'
    b'OjU1KzAzOjAwIiBkYzpmb3JtYXQ9ImltYWdlL3BuZyIgcGhvdG9zaG9wOkNvbG9yTW9kZT0i'
    b'MyIgeG1wTU06SW5zdGFuY2VJRD0ieG1wLmlpZDpiYmNlY2E0ZC1jMTc3LTQwNDYtOTcyYy0z'
    b'MzYwNDg3YjUyMjEiIHhtcE1NOkRvY3VtZW50SUQ9ImFkb2JlOmRvY2lkOnBob3Rvc2hvcDpj'
    b'ZmZhMzQwNy01MGM3LWM5NDctODg3MS00ZDFhZDA5ZmViNzQiIHhtcE1NOk9yaWdpbmFsRG9j'
    b'dW1lbnRJRD0ieG1wLmRpZDoxM2VmZmM5Ny01ZTAzLWYwNDMtYTk1Yy1jNDFkZTE2MDZhYmUi'
    b'PiA8eG1wTU06SGlzdG9yeT4gPHJkZjpTZXE+IDxyZGY6bGkgc3RFdnQ6YWN0aW9uPSJjcmVh'
    b'dGVkIiBzdEV2dDppbnN0YW5jZUlEPSJ4bXAuaWlkOjEzZWZmYzk3LTVlMDMtZjA0My1hOTVj'
    b'LWM0MWRlMTYwNmFiZSIgc3RFdnQ6d2hlbj0iMjAyNi0wNi0zMFQxNjo0ODozMCswMzowMCIg'
    b'c3RFdnQ6c29mdHdhcmVBZ2VudD0iQWRvYmUgUGhvdG9zaG9wIENDIDIwMTkgKFdpbmRvd3Mp'
    b'Ii8+IDxyZGY6bGkgc3RFdnQ6YWN0aW9uPSJzYXZlZCIgc3RFdnQ6aW5zdGFuY2VJRD0ieG1w'
    b'LmlpZDpmMzAyZjE3OS00YWE3LWNmNDctYjU4ZS1kZDg4ZDdhNThlNjQiIHN0RXZ0OndoZW49'
    b'IjIwMjYtMDYtMzBUMTY6NDk6NTUrMDM6MDAiIHN0RXZ0OnNvZnR3YXJlQWdlbnQ9IkFkb2Jl'
    b'IFBob3Rvc2hvcCBDQyAyMDE5IChXaW5kb3dzKSIgc3RFdnQ6Y2hhbmdlZD0iLyIvPiA8cmRm'
    b'OmxpIHN0RXZ0OmFjdGlvbj0ic2F2ZWQiIHN0RXZ0Omluc3RhbmNlSUQ9InhtcC5paWQ6YmJj'
    b'ZWNhNGQtYzE3Ny00MDQ2LTk3MmMtMzM2MDQ4N2I1MjIxIiBzdEV2dDp3aGVuPSIyMDI2LTA2'
    b'LTMwVDE2OjQ5OjU1KzAzOjAwIiBzdEV2dDpzb2Z0d2FyZUFnZW50PSJBZG9iZSBQaG90b3No'
    b'b3AgQ0MgMjAxOSAoV2luZG93cykiIHN0RXZ0OmNoYW5nZWQ9Ii8iLz4gPC9yZGY6U2VxPiA8'
    b'L3htcE1NOkhpc3Rvcnk+IDwvcmRmOkRlc2NyaXB0aW9uPiA8L3JkZjpSREY+IDwveDp4bXBt'
    b'ZXRhPiA8P3hwYWNrZXQgZW5kPSJyIj8+ddHQjgAACRFJREFUWMOVl3us5VV1xz9r7/07j3vu'
    b'uffO3MfcOwyUGR6WkUHUMQMzo7YSWiEhaCAZ0kariURix9qmbXy2aoPvRKMxVo0hxMRQSlN0'
    b'hFgCFEQKRihxhqGCIJN53Xlc5t5zzz3P3/7ttfrHOd7BcMe0Oznn98taO7+19t7f9V3fLW3b'
    b'jyI889JBXl44OHsy//X1Pdrberp8nkqa7mp7PLgsw6zigmRFEQWgWqoA0I09ACqhjAGFFkbh'
    b'8yTaQ1KsuvqSs+yVETc6X2LswLhteMDH0RNvev3lTI6vJ7SLiNcKzy09+ulfrPzoo9G3q+oi'
    b'4EGhJCVUC0DQnuG9B4TTnRwBMl8CjNiNgODFI84QwJLjdJEjGIpS8hUyrfc22ZVf3e13frIS'
    b'Rgm/OnSUA4s/+fgjS9/9TCeBi5A5GMlq1P0EhSU8BgAOzAwRwfvBDsjQF3wVMwMMGUzEBCqu'
    b'Rie16MQmK70cdc3Koj/+ibn52dp1/gN/HZq9hfrTjR99vpXg2o03cdnYHyPJ88zyAxzo/Cdj'
    b'fmwQHAPncCJYUkSGNmToNpxzIKCFIiKIwHLR5NLRN3P1xB5MlJfbT/Hg8Tt5bP7uj0zo5m+4'
    b'E+nFG5vFaTSHnTO3MO428fTpB1lun8L3HKlXUHQjRTtiSdEiUXQiqVuQumn4HPw0T2hSUjeS'
    b'egOb6zlanUV+ufAQGSV2Tb8Xi9ChxcsrB24JC40jbzBneIEiFw4uPsT9p/6dLaM1qjKGagIT'
    b'zAxLNnwqmFtdPDawi3OYCKqGM8MwqlLlVPcQT72yH8t6vCPsxSOoGdGal/ur3jf33oX+kStq'
    b'2SittMSJ1ksEaVJ2NQzDhsdvChIyQChiREUHyWCoKqaKCwFE0Dg4AgzUDEegngU0CfO9l1gp'
    b'TpNSTs1PNYLzMplSopaN8GzrASR31FlP0jRc3OCcTcGLY6l7iuZKn+D5LTTBICUYd2UmqjNE'
    b'tYHPYPhGydU43f4Nx9JBJvwsMXXoxJWx0O60quIhLyL18jQpRqLG1a+LCGqKx3G4eYQLapv5'
    b'8I7bqYUJVNKwODyduMz3X/w4h1uHmWMGNV3FqCAUKSdIhYofo8gjZiBoLeRFv+IIKIIqqA1q'
    b'udFfoNlLIGAGy324eHI9t1/1EHO1Law1Lpnawd/+dBf7F04yURkuABgtwfrKBgpLmAlmgpDR'
    b'T3kpuEAtdYBMMDVIwmJvmZmRC3j7xrcheAqLtGOHW6+4/ZzBATaObuHrb3uSb+//KJWQUS9P'
    b'4CTwy5MPc2TlBcazCTQZ4BD1RNfPgomzVCjqFO+FohzxVuJTO/exZd3l/H/HTP1C/nH33b9j'
    b'a3aX+NCjV9JmkXo2Qd7vYzhiUaiLUTGBNET6Sq/BVHnm9wc3+NbP/4EP3beT2+7bwZd+divt'
    b'XuM107755N9x24+3M1ZdxwUjW2l2W6SUUIxcC5xkEsSJppSwDDQZsat0NacdV6hl9dd8dKm9'
    b'xC33bCOrFFx/6R5KboTHj+zjmh+s544bnmDrzFWrc//0dX/O1ZuvBYPldoPYhVRVQHAI/Zhb'
    b'0KQiOEwH5CCr1Lr24j98/y7mJie584b9q7YPXPkFvvbzj7D3P67m/j9rUg2DxC9Z/8bBBIVk'
    b'yiosVUgpUXIlcYgjJUPVwAQUTHXN4E8df5BT+Yu/E/y342+u+jobxv6Au1743DmPzYbEpKYI'
    b'gVjk5lJMYghmihmYCWprb8GTJ/Zx2eyOc0Jj++x1PD3/0NrxzVAdJpKgSAlHEOeD01QoaqCm'
    b'Q1pde//HKlO04so5E2j2zlDJRtf0qQ1ArqYohhgUKZrLY3I2JJuUIE+QzpHAOze/nwNHDvA/'
    b'J//rNb7Y77PvV/fw7kv3rr0DCYoCUjKSGVETzgVx4rzGNKgAL0IoB3wWzoLxVWO2dgHv3/b3'
    b'XH/3bh479sNV+/MLz7DzjmmuPn83b91485oJuMwRqh5xjlSAiKNX5BZSSm7QTAzFcMEhXlgj'
    b'PgB/ufPLhFqNTz16CzPZJsw8p3pHuWbrjXzx7Xedmzqc4bxDxKFmFEmpSpCQ+UxjAZSEIiZa'
    b'SzkTo0rmy+f82Aff8Glu2vJBHj78b0Tts2Pjn3DJ1LZzE5cD7UDzlci6UsIJaBIsmIVuJ2/5'
    b'4IbAE4IXVvI2mSv9Xsqdqs+y5/K9/2eK7sQuPgMZVkNhOSWpxtDKW/2SlDAd9PxqGGOh1eAL'
    b'j9zGNVv24IbKR81wfoAMTcZQFJ4tVxPEDdv3EMTCQEn94ujD/Gb516wrj2BqmDoKTTjLemG6'
    b'OteabxyiWq3RyM+g0bGhNs4PnvsOdz37HWzAnKQCavVBtXRa4PwQJjIUJAqVKmQZtJpn/Wag'
    b'HjaOjdPt9+n3zzDupoiFEqqVdrDkF9WEVr/H1sntLLsm882jzIzUUdLqFqZkjIyVMFWqrsD7'
    b's6JcAFWjXPX4IJStwAXhrJoP9POCyeoGZtfN8cLpg5g5JLHoMvXHVJWTK21uuviveOP0H/H8'
    b'mTa92CNYQNQj6hB1uORwmg1sQ59Tj5gfzgs4zUAdkgKigUAgL/q8vNRm8/qt7LnkYzRWWkQz'
    b'SoweDdPZhf/tFGKCclbmD6e289ZNb8G0wfzKMcreDYRooaiCmVJERXADvTjEQkpKKYF5oygG'
    b'KtkJdPsF07UZzj9/lm3TuxjJRskTWN84b+7i/eGydbt/8sQr+/qn/ZnyY4fuY/v0O3nf6/fy'
    b'+Ml7OcVx6uWRoSo2spLDgBACzg3uQKuyHAjB4RxMTPrBBQaj6CsXTl3EtRv/Ai8lHj/8Y/oO'
    b'pkOJyyZ2/Is8c+gJHn7+3tu+99xX/lkzGBEoO0+5XGakXCYlB6IIMugTIjg35O5XDXkV3/tw'
    b'1u3F0Ys5nV6HqIn2sBm9Z9Otn7nhovd8NswfW2R7/V3fXpxs1H/WuOezy9KoLhcJrx3aeQfv'
    b'HDEpwQnihjdBG14+X/MPDtC+kdRwDgoFhUEnTDAjE+1dE+/+8s7Rm/9p/uQC8q/77iHzZdS3'
    b'ePH4s7Mn8xM3+tHuFcv50vmN7pl1/dSdKJdLpZhyn8xMoCxIQswBhslA/mPiBDGTXJyzIMG0'
    b'sLwUykslKo1Rt/7wzOh5B6Yqc/vmKhedSrmjGzv8L6ay8nmyP5lcAAAAAElFTkSuQmCC')


def InfoMessageBox(title: str, text: str, show_time: int, style: int = 0, sound: int = 1) -> None:
    """ Выводит исчезающее сообщение с иконкой и звуком.
    Params: text - сообщение,
            show_time - время показа сообщения
            style - тип звукового оповещения 0/1 SystemExclamation / SystemHand
            sound - False/True - отключить/включить звуковое оповещение. """

    sound_ls = ['SystemExclamation', 'SystemHand']
    title = (f'{title}').encode('cp1251')  # cp1251
    if sound:
        winsound.PlaySound(sound_ls[style], winsound.SND_ASYNC)  # SystemExclamation

    def killer(title, show_time):
        time.sleep(show_time)
        wd = ctypes.windll.user32.FindWindowA(0, title)
        ctypes.windll.user32.SendMessageA(wd, 0x0010, 0, 0)

    th.Thread(target=killer, args=(title, show_time)).start()

    MB_SYSTEMMODAL = 0x00001000
    MB_ICONINFORMATION = 0x00000040
    ctypes.windll.user32.MessageBoxA(0, text.encode('cp1251'), title, MB_SYSTEMMODAL | MB_ICONINFORMATION)


# ---------- Слой объектов (стрелки и надписи) ----------
# Объект — словарь в координатах оригинального изображения:
#   {"type": "arrow", "p1": (x, y), "p2": (x, y), "color": (r, g, b), "width": px}
#   {"type": "text", "pos": (x, y), "text": str, "color": (r, g, b), "size": px}

_MEASURE_DRAW = ImageDraw.Draw(Image.new("RGB", (1, 1)))  # только для измерения размеров текста


@lru_cache(maxsize=64)
def _load_font(size: int):
    """Шрифт для надписей: Arial (есть в Windows, поддерживает кириллицу), иначе встроенный шрифт PIL."""
    size = max(1, int(size))
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        try:
            return ImageFont.load_default(size)  # Pillow 10.1+
        except TypeError:
            return ImageFont.load_default()


def _text_bbox(ann, scale: float = 1.0):
    """Габариты надписи (x1, y1, x2, y2) при заданном масштабе."""
    x, y = ann["pos"]
    font = _load_font(round(ann["size"] * scale))
    return _MEASURE_DRAW.multiline_textbbox((x * scale, y * scale), ann["text"], font=font)


def _draw_arrow(draw, p1, p2, width, color):
    """Рисует стрелку от p1 к p2: линия и залитый треугольный наконечник."""
    x1, y1 = p1
    x2, y2 = p2
    length = math.hypot(x2 - x1, y2 - y1)
    if length < 1:
        return
    head = min(max(width * 4, 6), length)  # длина наконечника
    ux, uy = (x2 - x1) / length, (y2 - y1) / length
    bx, by = x2 - ux * head, y2 - uy * head  # основание наконечника
    half = head * 0.5
    draw.line([(x1, y1), (bx, by)], fill=color, width=width)
    draw.polygon([(x2, y2), (bx - uy * half, by + ux * half), (bx + uy * half, by - ux * half)], fill=color)


def draw_annotations(img: Image.Image, annotations, scale: float = 1.0):
    """Рисует объекты слоя на изображении img (на месте); scale — масштаб img относительно оригинала."""
    draw = ImageDraw.Draw(img)
    for ann in annotations:
        if ann["type"] == "arrow":
            p1 = (ann["p1"][0] * scale, ann["p1"][1] * scale)
            p2 = (ann["p2"][0] * scale, ann["p2"][1] * scale)
            _draw_arrow(draw, p1, p2, max(1, round(ann["width"] * scale)), ann["color"])
        elif ann["type"] == "text":
            x, y = ann["pos"]
            draw.multiline_text((x * scale, y * scale), ann["text"], fill=ann["color"],
                                font=_load_font(round(ann["size"] * scale)))


class ROISelectorPanel(wx.ScrolledWindow):
    def __init__(self, parent, pil_image: Image.Image):
        super().__init__(parent, style=wx.VSCROLL | wx.HSCROLL | wx.WANTS_CHARS)

        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_LEFT_DCLICK, self.on_left_dclick)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        # Оригинальное изображение (PIL)
        self.original_pil = pil_image
        self.display_pil = pil_image.copy()
        self.scale = 1.0

        # Координаты выделения (в координатах оригинала)
        self.start_point = None
        self.current_point = None
        self.final_roi = None  # (x1, y1, x2, y2)

        # Слой объектов поверх скриншота (стрелки и надписи)
        self.annotations = []
        self.selected = None      # индекс выбранного объекта
        self.tool = "select"      # "select" | "arrow" | "text"
        self.drag = None          # текущее перетаскивание: рисование стрелки или перенос объекта
        self.pen_color = (255, 0, 0)
        self.pen_width = 3        # толщина стрелки в экранных пикселях
        self.font_size = 20       # размер шрифта в экранных пикселях

        # История для отмены: [(изображение, объекты), ...] — обрезка, блюр и изменения слоя
        self.history = []
        self.on_history_changed = None  # вызывается при изменении истории (обновить кнопку «Отменить»)

        # Подготовка к отображению
        self._update_display_image()

    def _update_display_image(self):
        """Масштабирует оригинальное изображение под текущий размер окна, сохраняя aspect ratio.

            Вычисляет масштаб как min(ширина_окна / ширина_изображения, высота_окна / высота_изображения),
            затем создаёт уменьшенную копию с помощью LANCZOS-интерполяции.
            """
        client_w, client_h = self.GetClientSize().Get()
        if client_w <= 0 or client_h <= 0:
            return

        orig_w, orig_h = self.original_pil.size
        scale_w = client_w / orig_w
        scale_h = client_h / orig_h
        self.scale = min(scale_w, scale_h)

        new_w = int(orig_w * self.scale)
        new_h = int(orig_h * self.scale)
        self.display_pil = self.original_pil.resize((new_w, new_h), Image.LANCZOS)

    def on_size(self, event):
        """Обработчик изменения размера окна: обновляет отображаемое изображение и перерисовывает панель."""
        self._update_display_image()
        self.Refresh()
        event.Skip()

    def on_left_down(self, event):
        """Нажатие мыши: в зависимости от инструмента начинает выделение ROI, перенос объекта,
            рисование стрелки или ставит надпись. Рисовать можно только в пределах изображения.
            """
        self.SetFocus()  # чтобы стрелки клавиатуры приходили в панель
        pos = event.GetPosition()
        inside = self._inside_image(pos)
        point = self._screen_to_original(pos)

        if self.tool == "arrow":
            if inside:
                self.drag = {"mode": "arrow", "ann": {"type": "arrow", "p1": point, "p2": point,
                                                      "color": self.pen_color,
                                                      "width": max(1, round(self.pen_width / self.scale))}}
        elif self.tool == "text":
            if inside:
                self._add_text(point)
        else:
            idx = self._hit_test(point) if inside else None
            self.selected = idx
            if idx is not None:
                self.drag = {"mode": "move", "last": point, "moved": False,
                             "before": (self.original_pil, copy.deepcopy(self.annotations))}
            else:
                self.start_point = point
                self.current_point = point
        self.Refresh()

    def on_left_up(self, event):
        """Отпускание мыши: завершает рисование стрелки, перенос объекта или выделение ROI."""
        if self.drag:
            drag, self.drag = self.drag, None
            if drag["mode"] == "arrow":
                ann = drag["ann"]
                (x1, y1), (x2, y2) = ann["p1"], ann["p2"]
                if math.hypot(x2 - x1, y2 - y1) * self.scale >= 5:  # случайный клик стрелку не создаёт
                    self._push_history()
                    self.annotations.append(ann)
            elif drag["mode"] == "move" and drag["moved"]:
                self._push_history(drag["before"])
            self.Refresh()
            return
        if self.start_point and self.current_point:
            x1, y1 = self.start_point
            x2, y2 = self.current_point
            x1, x2 = sorted([x1, x2])
            y1, y2 = sorted([y1, y2])
            # Простой клик (без протяжки) снимает выделение: тогда сохраняется весь текущий кадр
            self.final_roi = (x1, y1, x2, y2) if x2 - x1 >= 2 and y2 - y1 >= 2 else None
            self.start_point = None
            self.current_point = None
            self.Refresh()
            # wx.MessageBox(f"ROI сохранено: ({x1}, {y1}) — ({x2}, {y2})", "Готово", wx.OK | wx.ICON_INFORMATION)

    def on_motion(self, event):
        """Движение мыши: тянет стрелку, переносит объект или обновляет выделение ROI."""
        if self.drag:
            point = self._screen_to_original(event.GetPosition())
            if self.drag["mode"] == "arrow":
                self.drag["ann"]["p2"] = point
            elif self.drag["mode"] == "move" and self.selected is not None:
                lx, ly = self.drag["last"]
                if (point[0], point[1]) != (lx, ly):
                    self._shift_annotation(self.annotations[self.selected], point[0] - lx, point[1] - ly)
                    self.drag["last"] = point
                    self.drag["moved"] = True
            self.Refresh()
            return
        if self.start_point:
            pos = event.GetPosition()
            self.current_point = self._screen_to_original(pos)
            self.Refresh()

    _ARROW_KEYS = {wx.WXK_LEFT, wx.WXK_RIGHT, wx.WXK_UP, wx.WXK_DOWN,
                   wx.WXK_NUMPAD_LEFT, wx.WXK_NUMPAD_RIGHT, wx.WXK_NUMPAD_UP, wx.WXK_NUMPAD_DOWN}

    def on_key_down(self, event):
        """Стрелки двигают ROI (с Shift шаг 10 пикселей вместо 1);
            Ctrl + стрелка сужает ROI в сторону стрелки, Ctrl + Shift + стрелка расширяет ROI в сторону стрелки.
            """
        key = event.GetKeyCode()
        if key in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE, wx.WXK_BACK) and self.selected is not None:
            self._push_history()
            del self.annotations[self.selected]
            self.selected = None
            self.Refresh()
            return
        if key == wx.WXK_ESCAPE and (self.selected is not None or self.final_roi):
            # Esc снимает выбор объекта, а если объект не выбран — выделение области
            if self.selected is not None:
                self.selected = None
            else:
                self.final_roi = None
            self.Refresh()
            return
        if key not in self._ARROW_KEYS or not self.final_roi:
            event.Skip()
            return

        dx = {wx.WXK_LEFT: -1, wx.WXK_NUMPAD_LEFT: -1, wx.WXK_RIGHT: 1, wx.WXK_NUMPAD_RIGHT: 1}.get(key, 0)
        dy = {wx.WXK_UP: -1, wx.WXK_NUMPAD_UP: -1, wx.WXK_DOWN: 1, wx.WXK_NUMPAD_DOWN: 1}.get(key, 0)

        if event.ControlDown():
            self.resize_roi(dx, dy, grow=event.ShiftDown())
        else:
            step = 10 if event.ShiftDown() else 1
            self.move_roi(dx * step, dy * step)

    def move_roi(self, dx, dy):
        """Сдвигает ROI на (dx, dy) пикселей оригинала, не выходя за границы изображения."""
        x1, y1, x2, y2 = self.final_roi
        orig_w, orig_h = self.original_pil.size
        dx = max(-x1, min(dx, orig_w - x2))
        dy = max(-y1, min(dy, orig_h - y2))
        self.final_roi = (x1 + dx, y1 + dy, x2 + dx, y2 + dy)
        self.Refresh()

    def resize_roi(self, dx, dy, grow: bool):
        """Меняет размер ROI в направлении стрелки (dx, dy).

            grow=True  — граница со стороны стрелки уходит наружу (← двигает левую границу влево и т.д.);
            grow=False — противоположная граница идёт внутрь по стрелке (← двигает правую границу влево и т.д.).
            Минимальный размер ROI — 1 пиксель, ROI не выходит за границы изображения.
            """
        x1, y1, x2, y2 = self.final_roi
        orig_w, orig_h = self.original_pil.size
        if grow:
            if dx < 0:
                x1 = max(0, x1 + dx)
            elif dx > 0:
                x2 = min(orig_w, x2 + dx)
            if dy < 0:
                y1 = max(0, y1 + dy)
            elif dy > 0:
                y2 = min(orig_h, y2 + dy)
        else:
            if dx < 0:
                x2 = max(x1 + 1, x2 + dx)
            elif dx > 0:
                x1 = min(x2 - 1, x1 + dx)
            if dy < 0:
                y2 = max(y1 + 1, y2 + dy)
            elif dy > 0:
                y1 = min(y2 - 1, y1 + dy)
        self.final_roi = (x1, y1, x2, y2)
        self.Refresh()

    def on_left_dclick(self, event):
        """Двойной клик по надписи в режиме «Выделение» — изменить её текст."""
        if self.tool != "select":
            event.Skip()
            return
        pos = event.GetPosition()
        idx = self._hit_test(self._screen_to_original(pos)) if self._inside_image(pos) else None
        if idx is None or self.annotations[idx]["type"] != "text":
            return
        ann = self.annotations[idx]
        text = self._ask_text(ann["text"])
        if text is not None and text != ann["text"]:
            self._push_history()
            ann["text"] = text
            self._shift_annotation(ann, 0, 0)  # удержать в пределах изображения
            self.selected = idx
            self.Refresh()

    def set_tool(self, tool: str):
        """Переключает инструмент: "select" — выделение и перенос объектов, "arrow" — стрелка, "text" — надпись."""
        self.tool = tool
        self.drag = None
        self.start_point = None
        self.current_point = None
        if tool != "select":
            self.selected = None
        cursor = {"arrow": wx.CURSOR_CROSS, "text": wx.CURSOR_IBEAM}.get(tool, wx.CURSOR_ARROW)
        self.SetCursor(wx.Cursor(cursor))
        self.Refresh()

    def set_style(self, color=None, width=None, font_size=None):
        """Задаёт цвет, толщину стрелки и размер шрифта (в экранных пикселях) для новых объектов
            и применяет их к выбранному объекту.
            """
        if color is not None:
            self.pen_color = color
        if width is not None:
            self.pen_width = width
        if font_size is not None:
            self.font_size = font_size
        if self.selected is None:
            return
        ann = copy.deepcopy(self.annotations[self.selected])
        if color is not None:
            ann["color"] = color
        if width is not None and ann["type"] == "arrow":
            ann["width"] = max(1, round(width / self.scale))
        if font_size is not None and ann["type"] == "text":
            ann["size"] = max(1, round(font_size / self.scale))
        if ann != self.annotations[self.selected]:
            self._push_history()
            self.annotations[self.selected] = ann
            self._shift_annotation(ann, 0, 0)
            self.Refresh()

    def _ask_text(self, value: str = ""):
        """Диалог ввода текста надписи. Возвращает текст или None, если отменено или пусто."""
        with wx.TextEntryDialog(self, "Текст надписи:", "Надпись", value=value,
                                style=wx.TextEntryDialogStyle | wx.TE_MULTILINE) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return None
            text = dlg.GetValue()
        return text if text.strip() else None

    def _add_text(self, point):
        """Ставит надпись в точку point (координаты оригинала) после ввода текста в диалоге."""
        text = self._ask_text()
        if text is None:
            return
        ann = {"type": "text", "pos": point, "text": text, "color": self.pen_color,
               "size": max(1, round(self.font_size / self.scale))}
        self._shift_annotation(ann, 0, 0)  # надпись у края сдвигается внутрь изображения
        self._push_history()
        self.annotations.append(ann)

    def _ann_bounds(self, ann):
        """Габариты объекта (x1, y1, x2, y2) в координатах оригинала: концы стрелки или прямоугольник текста."""
        if ann["type"] == "arrow":
            (x1, y1), (x2, y2) = ann["p1"], ann["p2"]
            return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)
        return _text_bbox(ann)

    def _shift_annotation(self, ann, dx, dy):
        """Сдвигает объект на (dx, dy), не выпуская его за границы изображения."""
        orig_w, orig_h = self.original_pil.size
        x1, y1, x2, y2 = self._ann_bounds(ann)
        dx = int(max(-x1, min(dx, orig_w - 1 - x2)))
        dy = int(max(-y1, min(dy, orig_h - 1 - y2)))
        if ann["type"] == "arrow":
            ann["p1"] = (ann["p1"][0] + dx, ann["p1"][1] + dy)
            ann["p2"] = (ann["p2"][0] + dx, ann["p2"][1] + dy)
        else:
            ann["pos"] = (ann["pos"][0] + dx, ann["pos"][1] + dy)

    def _hit_test(self, point):
        """Индекс верхнего объекта под точкой (координаты оригинала) или None."""
        px, py = point
        tol = 6 / self.scale  # допуск попадания — 6 экранных пикселей
        for idx in range(len(self.annotations) - 1, -1, -1):
            ann = self.annotations[idx]
            if ann["type"] == "arrow":
                (x1, y1), (x2, y2) = ann["p1"], ann["p2"]
                seg = (x2 - x1) ** 2 + (y2 - y1) ** 2
                t = 0 if seg == 0 else max(0, min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / seg))
                dist = math.hypot(px - (x1 + t * (x2 - x1)), py - (y1 + t * (y2 - y1)))
                if dist <= ann["width"] * 2 + tol:
                    return idx
            else:
                x1, y1, x2, y2 = _text_bbox(ann)
                if x1 - tol <= px <= x2 + tol and y1 - tol <= py <= y2 + tol:
                    return idx
        return None

    def _push_history(self, state=None):
        """Кладёт состояние (изображение, объекты) в историю отмены; по умолчанию — текущее."""
        self.history.append(state or (self.original_pil, copy.deepcopy(self.annotations)))
        self._notify_history()

    def _notify_history(self):
        if self.on_history_changed:
            self.on_history_changed()

    def _image_offset(self):
        """Смещение левого верхнего угла изображения в окне (изображение центрируется)."""
        disp_w, disp_h = self.display_pil.size
        client_w, client_h = self.GetClientSize().Get()
        return (client_w - disp_w) // 2, (client_h - disp_h) // 2

    def _inside_image(self, screen_pos) -> bool:
        """Попадает ли экранная точка на изображение."""
        x_off, y_off = self._image_offset()
        disp_w, disp_h = self.display_pil.size
        return 0 <= screen_pos[0] - x_off < disp_w and 0 <= screen_pos[1] - y_off < disp_h

    def _screen_to_original(self, screen_pos):
        """Преобразует экранные координаты (пиксели окна) в координаты оригинального изображения.

            Учитывает:
            - центрирование изображения в окне,
            - масштаб (отношение размеров),
            - границы изображения (ограничивает координаты).
            """
        disp_w, disp_h = self.display_pil.size
        orig_w, orig_h = self.original_pil.size
        x_screen, y_screen = screen_pos

        # Учитываем центрирование
        client_w, client_h = self.GetClientSize().Get()
        x_offset = (client_w - disp_w) // 2
        y_offset = (client_h - disp_h) // 2
        x_disp = x_screen - x_offset
        y_disp = y_screen - y_offset

        if disp_w == 0 or disp_h == 0:
            return 0, 0

        x_orig = int(x_disp * orig_w / disp_w)
        y_orig = int(y_disp * orig_h / disp_h)

        x_orig = max(0, min(x_orig, orig_w - 1))
        y_orig = max(0, min(y_orig, orig_h - 1))
        return x_orig, y_orig

    def on_paint(self, event):
        """Отрисовка: фон, изображение, выделяемый прямоугольник (красный), и финальный ROI (зелёный)."""
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(wx.WHITE))
        dc.Clear()

        # Рисуем изображение вместе со слоем объектов (и стрелкой, которую сейчас тянут)
        frame = self.display_pil.convert("RGB")
        annotations = self.annotations
        if self.drag and self.drag["mode"] == "arrow":
            annotations = annotations + [self.drag["ann"]]
        if annotations:
            frame = frame.copy() if frame is self.display_pil else frame
            draw_annotations(frame, annotations, frame.width / self.original_pil.width)
        w, h = frame.size
        bitmap = wx.Bitmap.FromBuffer(w, h, frame.tobytes())

        client_w, client_h = self.GetClientSize().Get()
        x = (client_w - w) // 2
        y = (client_h - h) // 2
        dc.DrawBitmap(bitmap, x, y, True)

        # Рисуем прямоугольник (в координатах экрана)
        if self.start_point and self.current_point:
            x1_s, y1_s = self._original_to_screen(self.start_point)
            x2_s, y2_s = self._original_to_screen(self.current_point)
            x1_s += x;
            y1_s += y;
            x2_s += x;
            y2_s += y

            dc.SetPen(wx.Pen(wx.Colour(255, 0, 0, 64), 2))
            dc.SetBrush(wx.Brush(wx.Colour(255, 0, 0, 32)))
            dc.DrawRectangle(int(x1_s), int(y1_s), int(x2_s - x1_s), int(y2_s - y1_s))

        # Если ROI выбран — рисуем его границу
        if self.final_roi:
            x1, y1, x2, y2 = self.final_roi
            x1_s, y1_s = self._original_to_screen((x1, y1))
            x2_s, y2_s = self._original_to_screen((x2, y2))
            x1_s += x;
            y1_s += y;
            x2_s += x;
            y2_s += y
            dc.SetPen(wx.Pen(wx.Colour(0, 255, 0, 200), 3))
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            dc.DrawRectangle(int(x1_s), int(y1_s), int(x2_s - x1_s), int(y2_s - y1_s))

        # Рамка вокруг выбранного объекта
        if self.selected is not None and self.selected < len(self.annotations):
            k = w / self.original_pil.width
            ann = self.annotations[self.selected]
            bx1, by1, bx2, by2 = self._ann_bounds(ann)
            pad = 4 + (ann["width"] * 2 * k if ann["type"] == "arrow" else 0)
            dc.SetPen(wx.Pen(wx.Colour(0, 120, 255), 1, wx.PENSTYLE_SHORT_DASH))
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            dc.DrawRectangle(int(x + bx1 * k - pad), int(y + by1 * k - pad),
                             int((bx2 - bx1) * k + 2 * pad), int((by2 - by1) * k + 2 * pad))

    def _original_to_screen(self, orig_point):
        """Преобразует координаты оригинального изображения в экранные (пиксели окна).
            Обратная операция к _screen_to_original: учитывает масштаб и центрирование.
            """
        orig_w, orig_h = self.original_pil.size
        disp_w, disp_h = self.display_pil.size
        x_orig, y_orig = orig_point
        x_disp = int(x_orig * disp_w / orig_w)
        y_disp = int(y_orig * disp_h / orig_h)
        return x_disp, y_disp

    def get_roi_image(self) -> Image.Image:
        """Возвращает выделенную область (ROI) как PIL.Image, обрезанную по координатам final_roi.

            Объекты слоя (стрелки, надписи) впечатываются в результат. Если ROI не выбран — всё изображение.
            """
        image = self.original_pil
        if self.annotations:
            image = image.copy()
            draw_annotations(image, self.annotations)
        if not self.final_roi:
            return image
        x1, y1, x2, y2 = self.final_roi
        return image.crop((x1, y1, x2, y2))

    def set_image(self, pil_image: Image.Image):
        """Загружает новый скриншот: сбрасывает выделение, объекты слоя и историю отмены."""
        self.history = []
        self.annotations = []
        self._show_image(pil_image.convert("RGB"))
        self._notify_history()

    def _show_image(self, pil_image: Image.Image):
        """Показывает изображение в панели и сбрасывает выделение."""
        self.original_pil = pil_image
        self.display_pil = pil_image.copy()
        self.final_roi = None
        self.start_point = None
        self.current_point = None
        self.selected = None
        self.drag = None
        self._update_display_image()
        self.Refresh()

    def crop_to_roi(self) -> bool:
        """Обрезает изображение и слой объектов по выделенной области (ROI); прежнее состояние кладётся в историю.

            Возвращает False, если область не выбрана или имеет нулевой размер.
            """
        if not self.final_roi:
            return False
        x1, y1, x2, y2 = self.final_roi
        if x2 - x1 < 1 or y2 - y1 < 1:
            return False
        self._push_history()
        # Объекты слоя переносятся в координаты обрезанного изображения; полностью вне области — удаляются
        kept = []
        for ann in self.annotations:
            bx1, by1, bx2, by2 = self._ann_bounds(ann)
            if bx2 < x1 or bx1 > x2 or by2 < y1 or by1 > y2:
                continue
            ann = copy.deepcopy(ann)
            if ann["type"] == "arrow":
                ann["p1"] = (ann["p1"][0] - x1, ann["p1"][1] - y1)
                ann["p2"] = (ann["p2"][0] - x1, ann["p2"][1] - y1)
            else:
                ann["pos"] = (ann["pos"][0] - x1, ann["pos"][1] - y1)
            kept.append(ann)
        self.annotations = kept
        self._show_image(self.original_pil.crop((x1, y1, x2, y2)))
        return True

    def blur_roi(self) -> bool:
        """Пикселизирует выделенную область (ROI) так, чтобы текст в ней нельзя было прочитать.

            Область сначала размывается, затем уменьшается до крупных блоков и растягивается обратно
            без сглаживания. Прежнее изображение кладётся в историю (отменяется как обрезка),
            выделение остаётся на месте. Возвращает False, если область не выбрана или пустая.
            """
        if not self.final_roi:
            return False
        x1, y1, x2, y2 = self.final_roi
        w, h = x2 - x1, y2 - y1
        if w < 1 or h < 1:
            return False
        block = max(2, min(w, h) // 20)  # размер «пикселя»: не меньше 12 px, крупнее для больших областей
        region = self.original_pil.crop((x1, y1, x2, y2)).filter(ImageFilter.GaussianBlur(block))
        small = region.resize((max(1, w // block), max(1, h // block)), Image.BILINEAR)
        pixelated = small.resize((w, h), Image.NEAREST)

        self._push_history()
        self.original_pil = self.original_pil.copy()  # блюр меняет только скриншот, стрелки и надписи не трогает
        self.original_pil.paste(pixelated, (x1, y1))
        self._update_display_image()
        self.Refresh()
        return True

    def undo(self) -> bool:
        """Отменяет последнее действие: обрезку, блюр или изменение слоя объектов. False — если отменять нечего."""
        if not self.history:
            return False
        image, self.annotations = self.history.pop()
        if image.size == self.original_pil.size:
            # Размер не менялся (блюр или рисование) — выделение оставляем на месте
            self.original_pil = image
            self.selected = None
            self.drag = None
            self._update_display_image()
            self.Refresh()
        else:
            self._show_image(image)
        self._notify_history()
        return True

    def copy_to_clipboard(self):
        """Копирует выделенную область (ROI) в буфер обмена как wx.Bitmap.
            Возвращает True при успехе, False — при ошибке (например, буфер недоступен).
            """
        roi = self.get_roi_image()
        # # Конвертируем PIL → wx.Bitmap
        # if roi.mode != "RGB":
        #     roi = roi.convert("RGB")
        data = roi.tobytes()
        w, h = roi.size
        # Создаём wx.Image (он сам разбирает RGB)
        img = wx.Image(w, h, data)
        bitmap = img.ConvertToBitmap()
        bitmap_data_object = wx.BitmapDataObject(bitmap)
        try:
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(bitmap_data_object)
                wx.TheClipboard.Flush()  # Обязательно очистите буфер
                wx.TheClipboard.Close()
                return True
            else:
                print("Не удалось открыть буфер обмена")
                return False
        except Exception:
            return False


class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Screenshot ROI Tool — Multi-Monitor", size=(1200, 800))

        self.SetIcon(wx.Icon(_screen_shot_icon_32.GetBitmap()))
        # Инициализация кэша скриншота
        self._cached_full_screenshot = None

        # Загрузка настроек (папка сохранения)
        self.config_file = Path.home() / ".screenshot_roi_config.json"
        self.save_dir = self._load_save_dir()

        # Получаем список экранов
        raw_monitors = _get_monitors()
        self.displays = []
        for i, (x, y, w, h) in enumerate(raw_monitors, start=1):
            self.displays.append({
                "index": i,
                "name": f"Экран {i}",
                "rect": (x, y, w, h),
                "name_full": f"Экран {i} — {w}x{h} @ ({x}, {y})"
            })
        print(f"[DEBUG] Обнаружено мониторов: {len(self.displays)}")
        for m in self.displays:
            print(f"  {m['name_full']}")

        # Панель выбора экрана
        choice_panel = wx.Panel(self)
        choice_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.choice_screen = wx.ComboBox(choice_panel, choices=[
            "🖥️ Все экраны (объединённый)",
            *[d["name_full"] for d in self.displays]
        ], style=wx.CB_READONLY)
        self.choice_screen.SetSelection(0)
        self.choice_screen.Bind(wx.EVT_COMBOBOX, self.on_screen_change)
        choice_sizer.Add(wx.StaticText(choice_panel, label="Выберите экран: "), 0, wx.ALL | wx.CENTER, 5)
        choice_sizer.Add(self.choice_screen, 1, wx.ALL | wx.EXPAND, 5)
        choice_panel.SetSizer(choice_sizer)

        # Панель выбора папки
        folder_panel = wx.Panel(self)
        folder_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_folder = wx.TextCtrl(folder_panel, value=str(self.save_dir), style=wx.TE_READONLY)
        self.btn_browse = wx.Button(folder_panel, label="📂 Выбрать папку")
        self.btn_browse.Bind(wx.EVT_BUTTON, self.on_browse_folder)
        folder_sizer.Add(wx.StaticText(folder_panel, label="Папка сохранения: "), 0, wx.ALL | wx.CENTER, 5)
        folder_sizer.Add(self.txt_folder, 1, wx.ALL | wx.EXPAND, 5)
        folder_sizer.Add(self.btn_browse, 0, wx.ALL, 5)
        folder_panel.SetSizer(folder_sizer)

        # Скриншот по умолчанию — все экраны
        screenshot_pil = self._capture_screen(0)

        # Панель с прокруткой
        self.panel = ROISelectorPanel(self, screenshot_pil)
        self.panel.on_history_changed = lambda: self.btn_undo_crop.Enable(bool(self.panel.history))

        # Панель инструментов: выделение / стрелка / текст, цвет, толщина, размер шрифта
        tool_panel = wx.Panel(self)
        tool_sizer = wx.BoxSizer(wx.HORIZONTAL)
        tool_sizer.Add(wx.StaticText(tool_panel, label="Инструмент: "), 0, wx.ALL | wx.CENTER, 5)
        self.tool_buttons = {}
        self.tool_ids = {}
        for tool, label in (("select", "⬚ Выделение (V)"), ("arrow", "➜ Стрелка (A)"), ("text", "🔤 Текст (T)")):
            btn = wx.ToggleButton(tool_panel, label=label)
            btn.Bind(wx.EVT_TOGGLEBUTTON, lambda e, t=tool: self.set_tool(t))
            tool_sizer.Add(btn, 0, wx.ALL, 5)
            self.tool_buttons[tool] = btn
            self.tool_ids[tool] = wx.NewIdRef()
            self.Bind(wx.EVT_MENU, lambda e, t=tool: self.set_tool(t), id=self.tool_ids[tool])
        self.tool_buttons["select"].SetValue(True)

        self.color_picker = wx.ColourPickerCtrl(tool_panel, colour=wx.Colour(*self.panel.pen_color))
        self.color_picker.Bind(wx.EVT_COLOURPICKER_CHANGED, self.on_style_change)
        self.spin_width = wx.SpinCtrl(tool_panel, min=1, max=30, initial=self.panel.pen_width, size=(60, -1))
        self.spin_width.Bind(wx.EVT_SPINCTRL, self.on_style_change)
        self.spin_font = wx.SpinCtrl(tool_panel, min=6, max=120, initial=self.panel.font_size, size=(60, -1))
        self.spin_font.Bind(wx.EVT_SPINCTRL, self.on_style_change)
        for label, ctrl in (("Цвет:", self.color_picker), ("Толщина:", self.spin_width), ("Шрифт:", self.spin_font)):
            tool_sizer.Add(wx.StaticText(tool_panel, label=label), 0, wx.LEFT | wx.CENTER, 15)
            tool_sizer.Add(ctrl, 0, wx.ALL | wx.CENTER, 5)
        tool_panel.SetSizer(tool_sizer)

        # Кнопки
        btn_panel = wx.Panel(self)
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_save = wx.Button(btn_panel, label="💾 Сохранить в PNG")
        self.btn_save.Bind(wx.EVT_BUTTON, self.on_save)
        # self.btn_save.Enable(False)
        self.btn_save_as = wx.Button(btn_panel, label="💾 Сохранить как...")
        self.btn_save_as.Bind(wx.EVT_BUTTON, self.on_save_as)
        self.btn_copy =wx.Button(btn_panel, label="📋 Копировать в буфер обмена")
        self.btn_copy.Bind(wx.EVT_BUTTON, self.on_copy)
        # self.btn_copy.Enable(False)

        self.btn_refresh = wx.Button(btn_panel, label="🔄 Обновить скриншот")
        self.btn_refresh.Bind(wx.EVT_BUTTON, self.on_refresh)

        self.btn_crop = wx.Button(btn_panel, label="✂️ Обрезать по выделению")
        self.btn_crop.Bind(wx.EVT_BUTTON, self.on_crop)
        self.btn_blur = wx.Button(btn_panel, label="🔲 Заблюрить")
        self.btn_blur.Bind(wx.EVT_BUTTON, self.on_blur)
        self.btn_undo_crop = wx.Button(btn_panel, label="↩️ Отменить")
        self.btn_undo_crop.Bind(wx.EVT_BUTTON, self.on_undo_crop)
        self.btn_undo_crop.Enable(False)

        self.btn_info = wx.Button(btn_panel, label="ℹ️ Управление")
        self.btn_info.Bind(wx.EVT_BUTTON, self.on_info)

        btn_sizer.Add(self.btn_save, 0, wx.ALL, 5)
        btn_sizer.Add(self.btn_save_as, 0, wx.ALL, 5)
        btn_sizer.Add(self.btn_refresh, 0, wx.ALL, 5)
        btn_sizer.Add(self.btn_copy, 0, wx.ALL, 5)
        btn_sizer.Add(self.btn_crop, 0, wx.ALL, 5)
        btn_sizer.Add(self.btn_blur, 0, wx.ALL, 5)
        btn_sizer.Add(self.btn_undo_crop, 0, wx.ALL, 5)
        btn_sizer.AddStretchSpacer()
        btn_sizer.Add(self.btn_info, 0, wx.ALL, 5)
        btn_panel.SetSizer(btn_sizer)

        # Создаём таблицу горячих клавиш
        self.accel_tbl = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('S'), self.btn_save.GetId()),
            (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('S'), self.btn_save_as.GetId()),
            (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('C'), self.btn_copy.GetId()),
            (wx.ACCEL_CTRL, ord('R'), self.btn_refresh.GetId()),
            (wx.ACCEL_CTRL, ord('X'), self.btn_crop.GetId()),
            (wx.ACCEL_CTRL, ord('B'), self.btn_blur.GetId()),
            (wx.ACCEL_CTRL, ord('Z'), self.btn_undo_crop.GetId()),
            (wx.ACCEL_NORMAL, wx.WXK_F1, self.btn_info.GetId()),
            (wx.ACCEL_NORMAL, ord('V'), self.tool_ids["select"]),
            (wx.ACCEL_NORMAL, ord('A'), self.tool_ids["arrow"]),
            (wx.ACCEL_NORMAL, ord('T'), self.tool_ids["text"]),
        ])
        self.SetAcceleratorTable(self.accel_tbl)

        # Лэйаут
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(choice_panel, 0, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(folder_panel, 0, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(tool_panel, 0, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(self.panel, 1, wx.EXPAND)
        main_sizer.Add(btn_panel, 0, wx.EXPAND)
        self.SetSizer(main_sizer)

        # Слушаем изменения ROI
        self.panel.Bind(wx.EVT_LEFT_UP, self.on_roi_change)
        self.panel.Bind(wx.EVT_MOTION, self.on_roi_change)
        self.Maximize(True)
        self.Centre()
        self.Show()

        # Глобальная горячая клавиша PrtScr: работает, даже когда окно свёрнуто или неактивно
        self.Bind(wx.EVT_HOTKEY, self.on_prtscr, id=self.HOTKEY_PRTSCR_ID)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        if not self.RegisterHotKey(self.HOTKEY_PRTSCR_ID, 0, wx.WXK_SNAPSHOT):
            print("[DEBUG] Не удалось зарегистрировать PrtScr: клавиша занята другой программой "
                  "(или включена настройка Windows «Использовать PrtScn для открытия Ножниц»)")

    def _load_save_dir(self):
        """Загружает путь к папке сохранения из JSON-конфига (по умолчанию: ~/Screenshots).
           Если конфиг отсутствует или повреждён — возвращает путь по умолчанию.
        """
        default_dir = Path.home() / "Screenshots"
        try:
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    saved = data.get("save_dir")
                    if saved:
                        return Path(saved)
        except Exception as e:
            print(f"[WARN] Ошибка загрузки конфига: {e}")
        return default_dir

    def _save_save_dir(self):
        """Загружает путь к папке сохранения из JSON-конфига (по умолчанию: ~/Screenshots/ROI).
           Если конфиг отсутствует или повреждён — возвращает путь по умолчанию.
        """
        print(f"[DEBUG] папки сохранения: {self.config_file}")
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump({"save_dir": str(self.save_dir)}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] Ошибка сохранения конфига: {e}")

    def on_save(self, event):
        """Сохраняет выделенную область (ROI) в PNG-файл в указанной папке с временной меткой."""
        roi = self.panel.get_roi_image()
        if not roi:
            wx.MessageBox("Сначала выделите область!", "Ошибка", wx.OK | wx.ICON_ERROR)
            return
        # Убедимся, что папка существует
        self.save_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.save_dir / f"roi_{timestamp}.png"
        self._save_image(roi, filename)

    def on_save_as(self, event):
        """Сохраняет выделенную область (ROI) в файл, имя и папку которого задаёт пользователь."""
        roi = self.panel.get_roi_image()
        self.save_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with wx.FileDialog(self, "Сохранить как", defaultDir=str(self.save_dir),
                           defaultFile=f"roi_{timestamp}.png",
                           wildcard="PNG (*.png)|*.png|JPEG (*.jpg)|*.jpg|BMP (*.bmp)|*.bmp",
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            filename = Path(dlg.GetPath())
            ext = [".png", ".jpg", ".bmp"][dlg.GetFilterIndex()]
        if filename.suffix.lower() not in (".png", ".jpg", ".jpeg", ".bmp"):
            filename = filename.with_name(filename.name + ext)
        # Запоминаем выбранную папку до закрытия программы (в конфиг не пишем — путь по умолчанию не меняется)
        self.save_dir = filename.parent
        self.txt_folder.SetValue(str(self.save_dir))
        self._save_image(roi, filename)

    def _save_image(self, roi: Image.Image, filename: Path):
        """Сохраняет изображение в файл; формат определяется по расширению."""
        formats = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".bmp": "BMP"}
        fmt = formats.get(filename.suffix.lower(), "PNG")
        try:
            if fmt == "PNG":
                roi.save(filename, fmt, optimize=True)
            else:
                roi.convert("RGB").save(filename, fmt)
            # wx.MessageBox(f"Сохранено: {filename}", "Успех", wx.OK | wx.ICON_INFORMATION)
            InfoMessageBox(title="Успех", text=f"Сохранено: {filename}", show_time=5, style=0, sound=1)
        except Exception as e:
            #wx.MessageBox(f"Ошибка сохранения: {e}", "Ошибка", wx.OK | wx.ICON_ERROR)
            InfoMessageBox(title="Ошибка", text=f"Ошибка сохранения: {e}", show_time=3, style=1, sound=1)

    def on_copy(self, event):
        """Копирует выделенную область (ROI) в буфер обмена и уведомляет пользователя."""
        if self.panel.copy_to_clipboard():
            #wx.MessageBox("ROI скопирован в буфер обмена!", "Успех", wx.OK | wx.ICON_INFORMATION)
            InfoMessageBox(title="Успех",text="ROI скопирован в буфер обмена!", show_time=3, style=0, sound=1)
        else:
            #wx.MessageBox("Не удалось скопировать ROI.", "Ошибка", wx.OK | wx.ICON_ERROR)
            InfoMessageBox(title="Ошибка", text="ROI скопирован в буфер обмена!", show_time=3, style=1, sound=1)

    HOTKEY_PRTSCR_ID = 0xB001  # id глобальной горячей клавиши PrtScr (0x0000–0xBFFF для приложений)

    # Список клавиш управления для окна «Управление»: (клавиши, действие); None — заголовок раздела
    HELP_KEYS = [
        (None, "Кнопки"),
        ("PrtScr", "Новый снимок экрана (работает и из свёрнутого окна)"),
        ("Ctrl + S", "Сохранить в PNG"),
        ("Ctrl + Shift + S", "Сохранить как..."),
        ("Ctrl + Shift + C", "Копировать в буфер обмена"),
        ("Ctrl + R", "Обновить скриншот"),
        ("Ctrl + X", "Обрезать по выделению"),
        ("Ctrl + B", "Заблюрить выделенную область"),
        ("Ctrl + Z", "Отменить последнее действие (обрезка, блюр, рисование)"),
        ("F1", "Это окно"),
        (None, "Выделение (ROI)"),
        ("Левая кнопка мыши", "Выделить область, простой клик — снять выделение"),
        ("← → ↑ ↓", "Сдвинуть область на 1 px"),
        ("Shift + стрелка", "Сдвинуть область на 10 px"),
        ("Ctrl + стрелка", "Сузить область в сторону стрелки"),
        ("Ctrl + Shift + стрелка", "Расширить область в сторону стрелки"),
        (None, "Рисование"),
        ("V / A / T", "Инструмент: выделение / стрелка / текст"),
        ("Стрелка: протянуть мышью", "Нарисовать стрелку (наконечник — где отпустили)"),
        ("Текст: клик", "Поставить надпись в точку клика"),
        ("Выделение: клик по объекту", "Выбрать объект, протянуть — переместить"),
        ("Двойной клик по надписи", "Изменить текст"),
        ("Цвет / толщина / шрифт", "Применяются к новым и к выбранному объекту"),
        ("Delete", "Удалить выбранный объект"),
        ("Esc", "Снять выбор объекта, повторно — выделение области"),
    ]

    def on_info(self, event):
        """Показывает всплывающее окно со списком клавиш управления программой."""
        with wx.Dialog(self, title="Управление программой") as dlg:
            grid = wx.FlexGridSizer(cols=2, vgap=4, hgap=20)
            bold = dlg.GetFont().Bold()
            for keys, action in self.HELP_KEYS:
                if keys is None:
                    title = wx.StaticText(dlg, label=action)
                    title.SetFont(bold)
                    grid.Add(title, 0, wx.TOP, 8)
                    grid.AddSpacer(0)
                    continue
                key_text = wx.StaticText(dlg, label=keys)
                key_text.SetFont(bold)
                grid.Add(key_text)
                grid.Add(wx.StaticText(dlg, label=action))

            sizer = wx.BoxSizer(wx.VERTICAL)
            sizer.Add(grid, 1, wx.ALL | wx.EXPAND, 15)
            sizer.Add(dlg.CreateButtonSizer(wx.OK), 0, wx.ALL | wx.ALIGN_RIGHT, 10)
            dlg.SetSizerAndFit(sizer)
            dlg.CentreOnParent()
            dlg.ShowModal()

    def on_browse_folder(self, event):
        """Открывает диалог выбора папки и обновляет путь сохранения (с сохранением в конфиг)."""
        with wx.DirDialog(self, "Выберите папку для сохранения скриншотов", str(self.save_dir),
                          style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.save_dir = Path(dlg.GetPath())
                self.txt_folder.SetValue(str(self.save_dir))
                self._save_save_dir()

    def _capture_screen(self, screen_index: int) -> Image.Image:
        """Возвращает скриншот выбранного экрана (0 = все экраны, 1..N = конкретный экран).

        Особенности:
        - Делает один полный скриншот всего виртуального рабочего стола и кэширует его.
        - Координаты мониторов (EnumDisplayMonitors) заданы относительно основного экрана
          и могут быть отрицательными, а левый верхний угол снимка ImageGrab.grab(all_screens=True)
          соответствует точке (min(left), min(top)) по всем мониторам. Поэтому для обрезки
          координаты монитора сдвигаются на начало виртуального рабочего стола.
        """

        # Делаем полный скриншот один раз
        if self._cached_full_screenshot is None:
            self._cached_full_screenshot = ImageGrab.grab(all_screens=True)

        full_img = self._cached_full_screenshot

        if screen_index == 0 or not (1 <= screen_index <= len(self.displays)):
            return full_img.copy()

        # Начало виртуального рабочего стола (левый верхний угол полного снимка)
        origin_x = min(d["rect"][0] for d in self.displays)
        origin_y = min(d["rect"][1] for d in self.displays)

        x, y, w, h = self.displays[screen_index - 1]["rect"]
        left, top = x - origin_x, y - origin_y
        bbox = (left, top, left + w, top + h)

        print(f"[DEBUG] Screen {screen_index}: sys=(x:{x},y:{y},w:{w},h:{h}), "
              f"origin=({origin_x},{origin_y}), full={full_img.size}, bbox={bbox}")
        return full_img.crop(bbox)

    def on_screen_change(self, event):
        """Обработчик смены экрана: сбрасывает кэш скриншота, делает новый и обновляет панель.
        Сброс кэша — чтобы при следующем _capture_screen сделать новый полный скриншот"""

        self._cached_full_screenshot = None
        new_screenshot = self._capture_screen(self.choice_screen.GetSelection())
        self.panel.set_image(new_screenshot)
        self.btn_undo_crop.Enable(False)
        # self.btn_save.Enable(False)

    def on_crop(self, event):
        """Обрезает скриншот по выделенной области, чтобы затем сохранить или скопировать результат."""
        if not self.panel.crop_to_roi():
            wx.MessageBox("Сначала выделите область для обрезки!", "Обрезка", wx.OK | wx.ICON_INFORMATION)
            return
        self.btn_undo_crop.Enable(True)

    def on_blur(self, event):
        """Пикселизирует выделенную область, чтобы скрыть текст и другие данные."""
        if not self.panel.blur_roi():
            wx.MessageBox("Сначала выделите область для блюра!", "Заблюрить", wx.OK | wx.ICON_INFORMATION)
            return
        self.btn_undo_crop.Enable(True)

    def on_undo_crop(self, event):
        """Отменяет последнее действие: обрезку, блюр или рисование."""
        self.panel.undo()

    def set_tool(self, tool: str):
        """Переключает инструмент рисования и состояние кнопок-переключателей."""
        for name, btn in self.tool_buttons.items():
            btn.SetValue(name == tool)
        self.panel.set_tool(tool)
        self.panel.SetFocus()

    def on_style_change(self, event):
        """Цвет, толщина или размер шрифта изменены: применяем к новым объектам и к выбранному объекту."""
        colour = self.color_picker.GetColour()
        self.panel.set_style(color=(colour.Red(), colour.Green(), colour.Blue()),
                             width=self.spin_width.GetValue(), font_size=self.spin_font.GetValue())

    def on_roi_change(self, event):
        """Обновляет состояние кнопок: включает «Сохранить» и «Копировать», если ROI выбран."""
        print(f"[DEBUG] ROI изменён: on_roi_change")
        has_roi = bool(self.panel.final_roi)
        # self.btn_save.Enable(has_roi)
        # self.btn_copy.Enable(has_roi)
        event.Skip()

    def on_prtscr(self, event):
        """PrtScr: прячет окно программы, делает новый снимок и показывает окно с ним."""
        if self.IsShown() and not self.IsIconized():
            self.Hide()
            wx.CallLater(300, self._capture_and_show)  # даём Windows убрать окно с экрана
        else:
            self._capture_and_show()

    def _capture_and_show(self):
        """Делает новый скриншот выбранного экрана и выводит окно программы на передний план."""
        self.on_refresh(None)
        self.Show()
        self.Iconize(False)
        self.Raise()
        self.panel.SetFocus()

    def on_close(self, event):
        """Освобождает глобальную клавишу PrtScr при закрытии программы."""
        self.UnregisterHotKey(self.HOTKEY_PRTSCR_ID)
        event.Skip()

    def on_refresh(self, event):
        """Обновляет скриншот: сбрасывает кэш, делает новый и сбрасывает выделение."""
        self._cached_full_screenshot = None  # сброс кэша
        screen_idx = self.choice_screen.GetSelection()
        new_screenshot = self._capture_screen(screen_idx)
        self.panel.set_image(new_screenshot)
        self.btn_undo_crop.Enable(False)
        # self.btn_save.Enable(False)


class App(wx.App):
    def OnInit(self):
        frame = MainFrame()
        self.SetTopWindow(frame)
        return True


if __name__ == "__main__":
    app = App(False)
    app.MainLoop()
