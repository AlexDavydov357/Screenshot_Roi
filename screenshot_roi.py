import wx
from PIL import Image, ImageGrab
from datetime import datetime
import json
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


class ROISelectorPanel(wx.ScrolledWindow):
    def __init__(self, parent, pil_image: Image.Image):
        super().__init__(parent, style=wx.VSCROLL | wx.HSCROLL)

        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_SIZE, self.on_size)

        # Оригинальное изображение (PIL)
        self.original_pil = pil_image
        self.display_pil = pil_image.copy()
        self.scale = 1.0

        # Координаты выделения (в координатах оригинала)
        self.start_point = None
        self.current_point = None
        self.final_roi = None  # (x1, y1, x2, y2)

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
        """Начало выделения ROI: сохраняет начальную точку в координатах оригинального изображения."""
        pos = event.GetPosition()
        x, y = self._screen_to_original(pos)
        self.start_point = (x, y)
        self.current_point = (x, y)
        self.Refresh()

    def on_left_up(self, event):
        """Завершение выделения ROI: нормализует координаты и сохраняет как final_roi."""
        if self.start_point and self.current_point:
            x1, y1 = self.start_point
            x2, y2 = self.current_point
            x1, x2 = sorted([x1, x2])
            y1, y2 = sorted([y1, y2])
            self.final_roi = (x1, y1, x2, y2)
            self.start_point = None
            self.current_point = None
            self.Refresh()
            # wx.MessageBox(f"ROI сохранено: ({x1}, {y1}) — ({x2}, {y2})", "Готово", wx.OK | wx.ICON_INFORMATION)

    def on_motion(self, event):
        """Отслеживает движение мыши при выделении: обновляет текущую точку и перерисовывает."""
        if self.start_point:
            pos = event.GetPosition()
            self.current_point = self._screen_to_original(pos)
            self.Refresh()

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

        # Рисуем изображение
        if self.display_pil.mode == "RGB":
            data = self.display_pil.tobytes()
            w, h = self.display_pil.size
            bitmap = wx.Bitmap.FromBuffer(w, h, data)
        else:
            rgb = self.display_pil.convert("RGB")
            data = rgb.tobytes()
            w, h = rgb.size
            bitmap = wx.Bitmap.FromBuffer(w, h, data)

        client_w, client_h = self.GetClientSize().Get()
        x = (client_w - w) // 2
        y = (client_h - h) // 2
        dc.DrawBitmap(bitmap, x, y, True)

        # Рисуем выделение (в координатах экрана)
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

            Если ROI не выбран — возвращает original_pil.
            """
        if not self.final_roi:
            return self.original_pil
        x1, y1, x2, y2 = self.final_roi
        return self.original_pil.crop((x1, y1, x2, y2))

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

        # Кнопки
        btn_panel = wx.Panel(self)
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_save = wx.Button(btn_panel, label="💾 Сохранить в PNG")
        self.btn_save.Bind(wx.EVT_BUTTON, self.on_save)
        # self.btn_save.Enable(False)
        self.btn_copy = wx.Button(btn_panel, label="📋 Копировать в буфер обмена")
        self.btn_copy.Bind(wx.EVT_BUTTON, self.on_copy)
        # self.btn_copy.Enable(False)

        self.btn_refresh = wx.Button(btn_panel, label="🔄 Обновить скриншот")
        self.btn_refresh.Bind(wx.EVT_BUTTON, self.on_refresh)
        btn_sizer.Add(self.btn_save, 0, wx.ALL, 5)
        btn_sizer.Add(self.btn_refresh, 0, wx.ALL, 5)
        btn_sizer.Add(self.btn_copy, 0, wx.ALL, 5)
        btn_panel.SetSizer(btn_sizer)

        # Создаём таблицу горячих клавиш
        self.accel_tbl = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('S'), self.btn_save.GetId()),
            (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('C'), self.btn_copy.GetId()),
            (wx.ACCEL_CTRL, ord('R'), self.btn_refresh.GetId()),
        ])
        self.SetAcceleratorTable(self.accel_tbl)

        # Лэйаут
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(choice_panel, 0, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(folder_panel, 0, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(self.panel, 1, wx.EXPAND)
        main_sizer.Add(btn_panel, 0, wx.EXPAND)
        self.SetSizer(main_sizer)

        # Слушаем изменения ROI
        self.panel.Bind(wx.EVT_LEFT_UP, self.on_roi_change)
        self.panel.Bind(wx.EVT_MOTION, self.on_roi_change)
        self.Maximize(True)
        self.Centre()
        self.Show()

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

        try:
            roi.save(filename, "PNG", optimize=True)
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
        - Делает один полный скриншот и кэширует его.
        - Учитывает, что wx.Display.GetGeometry() использует Y=0 внизу (как в OpenGL),
          а ImageGrab.grab() — Y=0 вверху (как в Windows GDI).
        - Использует смещение Y-оси, вычисленное по первому экрану (как эталон).
        """

        # Делаем полный скриншот один раз
        if not hasattr(self, '_cached_full_screenshot') or self._cached_full_screenshot is None:
            self._cached_full_screenshot = ImageGrab.grab(all_screens=True)
            # print(f"[DEBUG] Полный скриншот: {self._cached_full_screenshot.size}")

        full_img = self._cached_full_screenshot
        full_w, full_h = full_img.size

        if screen_index == 0:
            return full_img.copy()

        # Получаем координаты первого экрана — как эталон для Y-смещения
        if not self.displays:
            return full_img.copy()

        x0, y0, w0, h0 = self.displays[0]["rect"]

        # Вычисляем Y-смещение:
        # Если y0 > 0, значит Y=0 находится ниже нижней границы первого экрана → сдвигаем вверх
        # Если y0 < 0, значит Y=0 находится выше верхней границы → сдвигаем вниз
        # ofset_y = -y0 — это "коррекция", чтобы Y=0 совпал с нижней границей в системе ImageGrab
        ofset_y = -y0

        # Конкретный экран
        if 1 <= screen_index <= len(self.displays):
            x, y, w, h = self.displays[screen_index - 1]["rect"]

            # Для экранов, кроме первого — инвертируем смещение (т.к. они по-разному расположены относительно Y=0)
            if screen_index > 1:
                ofset_y = -ofset_y

            # Вычисляем y_top и y_bottom в системе ImageGrab (Y=0 сверху)
            if y >= 0:
                # y >= 0: экран выше Y=0 → y_top = full_h - (y + ofset_y + h)
                y_top = full_h - (y + ofset_y + h)
            else:
                # y < 0: экран ниже Y=0 → y_top = 0 (начало изображения)
                y_top = 0

            y_bottom = y_top + h
            bbox = (x, y_top, x + w, y_bottom)

            print(f"[DEBUG] Screen {screen_index}: sys=(x:{x},y:{y},w:{w},h:{h}), "
                  f"ofset_y:{ofset_y}, bbox=(x1:{x},y1:{y_top},x2:{x + w},y2:{y_bottom})")
            return full_img.crop(bbox)
        else:
            return full_img.copy()

    def on_screen_change(self, event):
        """Обработчик смены экрана: сбрасывает кэш скриншота, делает новый и обновляет панель.
        Сброс кэша — чтобы при следующем _capture_screen сделать новый полный скриншот"""

        self._cached_full_screenshot = None
        new_screenshot = self._capture_screen(self.choice_screen.GetSelection())
        self.panel.original_pil = new_screenshot.convert("RGB")
        self.panel.display_pil = self.panel.original_pil.copy()
        self.panel.final_roi = None
        self.panel.start_point = None
        self.panel.current_point = None
        self.panel._update_display_image()
        self.panel.Refresh()
        # self.btn_save.Enable(False)

    def on_roi_change(self, event):
        """Обновляет состояние кнопок: включает «Сохранить» и «Копировать», если ROI выбран."""
        print(f"[DEBUG] ROI изменён: on_roi_change")
        has_roi = bool(self.panel.final_roi)
        # self.btn_save.Enable(has_roi)
        # self.btn_copy.Enable(has_roi)
        event.Skip()

    def on_refresh(self, event):
        """Обновляет скриншот: сбрасывает кэш, делает новый и сбрасывает выделение."""
        self._cached_full_screenshot = None  # сброс кэша
        screen_idx = self.choice_screen.GetSelection()
        new_screenshot = self._capture_screen(screen_idx)
        self.panel.original_pil = new_screenshot.convert("RGB")
        self.panel.display_pil = new_screenshot.convert("RGB").copy()
        self.panel.final_roi = None
        self.panel.start_point = None
        self.panel.current_point = None
        self.panel._update_display_image()
        self.panel.Refresh()
        # self.btn_save.Enable(False)


class App(wx.App):
    def OnInit(self):
        frame = MainFrame()
        self.SetTopWindow(frame)
        return True


if __name__ == "__main__":
    app = App(False)
    app.MainLoop()
