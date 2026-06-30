import wx
from PIL import Image, ImageDraw, ImageFont
import pyautogui
import numpy as np
import os
from datetime import datetime

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
        self.display_pil = pil_image.copy()  # для отображения (масштабируется)
        self.scale = 1.0

        # Координаты выделения (в координатах оригинала)
        self.start_point = None
        self.current_point = None
        self.final_roi = None  # (x1, y1, x2, y2) в координатах оригинала

        # Подготовка к отображению
        self._update_display_image()

    def _update_display_image(self):
        """Масштабирует изображение под размер окна, сохраняя aspect ratio"""
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
        self._update_display_image()
        self.Refresh()
        event.Skip()

    def on_left_down(self, event):
        pos = event.GetPosition()
        # Перевод в координаты оригинала
        x, y = self._screen_to_original(pos)
        self.start_point = (x, y)
        self.current_point = (x, y)
        self.Refresh()

    def on_left_up(self, event):
        if self.start_point and self.current_point:
            x1, y1 = self.start_point
            x2, y2 = self.current_point
            # Нормализуем (x1 < x2, y1 < y2)
            x1, x2 = sorted([x1, x2])
            y1, y2 = sorted([y1, y2])
            self.final_roi = (x1, y1, x2, y2)
            self.start_point = None
            self.current_point = None
            self.Refresh()
            wx.MessageBox(f"ROI сохранено: ({x1}, {y1}) — ({x2}, {y2})", "Готово", wx.OK | wx.ICON_INFORMATION)

    def on_motion(self, event):
        if self.start_point:
            pos = event.GetPosition()
            self.current_point = self._screen_to_original(pos)
            self.Refresh()

    def _screen_to_original(self, screen_pos):
        """Перевод координат экрана в координаты оригинального изображения"""
        disp_w, disp_h = self.display_pil.size
        orig_w, orig_h = self.original_pil.size
        x_screen, y_screen = screen_pos
        # Учитываем центрирование (если масштаб < 1)
        x_offset = (self.GetClientSize().x - disp_w) // 2
        y_offset = (self.GetClientSize().y - disp_h) // 2
        x_disp = x_screen - x_offset
        y_disp = y_screen - y_offset
        if disp_w == 0 or disp_h == 0:
            return 0, 0
        x_orig = int(x_disp * orig_w / disp_w)
        y_orig = int(y_disp * orig_h / disp_h)
        # Ограничение границами изображения
        x_orig = max(0, min(x_orig, orig_w - 1))
        y_orig = max(0, min(y_orig, orig_h - 1))
        return x_orig, y_orig

    def on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(wx.WHITE))
        dc.Clear()

        # Рисуем изображение
        if self.display_pil.mode == "RGB":
            data = self.display_pil.tobytes()
            w, h = self.display_pil.size
            bitmap = wx.Bitmap.FromBuffer(w, h, data)
        else:
            # Конвертируем RGBA → RGB + альфа-канал игнорируем (или можно использовать AlphaBlend)
            rgb = self.display_pil.convert("RGB")
            data = rgb.tobytes()
            w, h = rgb.size
            bitmap = wx.Bitmap.FromBuffer(w, h, data)

        # Центрируем
        client_w, client_h = self.GetClientSize().Get()
        x = (client_w - w) // 2
        y = (client_h - h) // 2
        dc.DrawBitmap(bitmap, x, y, True)

        # Рисуем выделение (в координатах экрана)
        if self.start_point and self.current_point:
            # Переводим обратно в экранные координаты
            x1_s, y1_s = self._original_to_screen(self.start_point)
            x2_s, y2_s = self._original_to_screen(self.current_point)
            x1_s += x; y1_s += y; x2_s += x; y2_s += y

            # Рисуем прямоугольник
            dc.SetPen(wx.Pen(wx.Colour(255, 0, 0, 128), 2))
            dc.SetBrush(wx.Brush(wx.Colour(255, 0, 0, 64)))
            dc.DrawRectangle(int(x1_s), int(y1_s), int(x2_s - x1_s), int(y2_s - y1_s))

        # Если ROI выбран — рисуем его границу
        if self.final_roi:
            x1, y1, x2, y2 = self.final_roi
            x1_s, y1_s = self._original_to_screen((x1, y1))
            x2_s, y2_s = self._original_to_screen((x2, y2))
            x1_s += x; y1_s += y; x2_s += x; y2_s += y
            dc.SetPen(wx.Pen(wx.Colour(0, 255, 0, 200), 3))
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            dc.DrawRectangle(int(x1_s), int(y1_s), int(x2_s - x1_s), int(y2_s - y1_s))

    def _original_to_screen(self, orig_point):
        """Перевод координат оригинала в экранные"""
        orig_w, orig_h = self.original_pil.size
        disp_w, disp_h = self.display_pil.size
        x_orig, y_orig = orig_point
        x_disp = int(x_orig * disp_w / orig_w)
        y_disp = int(y_orig * disp_h / orig_h)
        return x_disp, y_disp

    def get_roi_image(self) -> Image.Image:
        if not self.final_roi:
            return None
        x1, y1, x2, y2 = self.final_roi
        return self.original_pil.crop((x1, y1, x2, y2))


class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Screenshot ROI Tool", size=(1200, 800))

        # Скриншот
        screenshot_pil = pyautogui.screenshot()
        # Убедимся, что RGB
        if screenshot_pil.mode != "RGB":
            screenshot_pil = screenshot_pil.convert("RGB")

        # Панель с прокруткой
        self.panel = ROISelectorPanel(self, screenshot_pil)

        # Кнопки
        btn_panel = wx.Panel(self)
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_save = wx.Button(btn_panel, label="💾 Сохранить ROI в PNG")
        self.btn_save.Bind(wx.EVT_BUTTON, self.on_save)
        self.btn_save.Enable(False)  # пока нет ROI

        self.btn_refresh = wx.Button(btn_panel, label="🔄 Сделать новый скриншот")
        self.btn_refresh.Bind(wx.EVT_BUTTON, self.on_refresh)

        btn_sizer.Add(self.btn_save, 0, wx.ALL, 5)
        btn_sizer.Add(self.btn_refresh, 0, wx.ALL, 5)
        btn_panel.SetSizer(btn_sizer)

        # Лэйаут
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self.panel, 1, wx.EXPAND)
        main_sizer.Add(btn_panel, 0, wx.EXPAND)
        self.SetSizer(main_sizer)

        # Слушаем изменения ROI
        self.panel.Bind(wx.EVT_LEFT_UP, self.on_roi_change)
        self.panel.Bind(wx.EVT_MOTION, self.on_roi_change)

        # Показываем
        self.Centre()
        self.Show()

    def on_roi_change(self, event):
        if self.panel.final_roi:
            self.btn_save.Enable(True)
        else:
            self.btn_save.Enable(False)
        event.Skip()

    def on_save(self, event):
        roi = self.panel.get_roi_image()
        if not roi:
            wx.MessageBox("Сначала выделите область!", "Ошибка", wx.OK | wx.ICON_ERROR)
            return

        # Генерируем имя файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"roi_{timestamp}.png"

        # Сохраняем с альфа-каналом, если был RGBA (но у нас RGB)
        # Добавим метаданные (опционально)
        try:
            roi.save(filename, "PNG", optimize=True)
            wx.MessageBox(f"Сохранено: {os.path.abspath(filename)}", "Успех", wx.OK | wx.ICON_INFORMATION)
        except Exception as e:
            wx.MessageBox(f"Ошибка сохранения: {e}", "Ошибка", wx.OK | wx.ICON_ERROR)

    def on_refresh(self, event):
        new_screenshot = pyautogui.screenshot().convert("RGB")
        self.panel.original_pil = new_screenshot
        self.panel.display_pil = new_screenshot.copy()
        self.panel.final_roi = None
        self.panel.start_point = None
        self.panel.current_point = None
        self.panel._update_display_image()
        self.panel.Refresh()
        self.btn_save.Enable(False)


class App(wx.App):
    def OnInit(self):
        frame = MainFrame()
        self.SetTopWindow(frame)
        return True


if __name__ == "__main__":
    app = App(False)
    app.MainLoop()
