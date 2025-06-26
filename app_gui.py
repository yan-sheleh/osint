import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from main import analyze_photo, get_exif_data, convert_gps, get_photo_datetime_exifread

class PhotoAnalyzerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Фото-Аналізатор")
        self.geometry("600x400")
        self.file_path = None

        self.create_widgets()

    def create_widgets(self):
        self.label = tk.Label(self, text="Оберіть зображення для аналізу:")
        self.label.pack(pady=10)

        self.choose_btn = tk.Button(
            self, text="Обрати файл", command=self.choose_file)
        self.choose_btn.pack(pady=5)

        self.file_label = tk.Label(self, text="Файл не обрано")
        self.file_label.pack(pady=5)

        self.analyze_btn = tk.Button(
            self, text="Аналізувати", command=self.analyze)
        self.analyze_btn.pack(pady=10)

        self.result_text = tk.Text(self, height=15, width=70) 
        self.result_text.pack(pady=10)

    def choose_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("JPEG files", "*.jpg;*.jpeg"), ("All files", "*.*")])
        if file_path:
            self.file_path = file_path
            self.file_label.config(text=f"Обрано файл: {file_path}")
        else:
            self.file_label.config(text="Файл не обрано")

    def analyze(self):
        if not self.file_path:
            messagebox.showwarning("Увага", "Спочатку оберіть файл!")
            return
        
        exif = get_exif_data(self.file_path)
        if not exif:
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(
                tk.END, "Фото створене ШІ (EXIF-метадані відсутні)")
            return

        photo_time = get_photo_datetime_exifread(self.file_path)
        if not photo_time:
            prompt = "В EXIF немає часу зйомки. Введіть дату і час у форматі РРРР:ММ:ДД ГГ:ХХ:СС (наприклад: 2024:06:26 15:45:00)"
            time_str = simpledialog.askstring("Введення часу", prompt)
            if not time_str:
                messagebox.showerror(
                    "Помилка", "Ввід скасовано або порожнє значення!")
                return
            try:
                from datetime import datetime
                photo_time = datetime.strptime(time_str, "%Y:%m:%d %H:%M:%S")
            except Exception:
                messagebox.showerror("Помилка", "Некоректний формат часу!")
                return
        
        if "GPSInfo" in exif:
            try:
                lat, lon = convert_gps(exif["GPSInfo"])
            except Exception:
                lat, lon = None, None
        else:
            lat, lon = None, None
        if lat is None or lon is None:
            prompt = "В EXIF немає координат. Введіть місце (наприклад, Київ) або координати (наприклад: 50.4501, 30.5234)"
            loc_str = simpledialog.askstring("Введення координат", prompt)
            if not loc_str:
                messagebox.showerror(
                    "Помилка", "Ввід скасовано або порожнє значення!")
                return
            try:
                if "," in loc_str:
                    lat, lon = map(float, loc_str.split(","))
                else:
                    from geopy.geocoders import Nominatim
                    import asyncio
                    import types
                    geolocator = Nominatim(user_agent="osint-photo-analyzer")
                    location = geolocator.geocode(loc_str)
                    if location is not None and hasattr(location, '__await__'):
                        location = asyncio.get_event_loop().run_until_complete(location)
                    if (
                        location is not None
                        and not isinstance(location, types.CoroutineType)
                        and hasattr(location, 'latitude')
                        and hasattr(location, 'longitude')
                    ):
                        lat, lon = location.latitude, location.longitude
                    else:
                        raise Exception
            except Exception:
                messagebox.showerror(
                    "Помилка", "Не вдалося визначити координати!")
                return

        try:
            result = analyze_photo(self.file_path, photo_time, lat, lon)
            self.result_text.delete(1.0, tk.END)
            if not isinstance(result, dict):
                self.result_text.insert(tk.END, str(result))
                return

            location = result.get('location', {})
            if not isinstance(location, dict):
                location = {}

            weather = result.get('weather_at_time', {})
            if not isinstance(weather, dict):
                weather = {}

            tz = weather.get('timezone', '-')
            tz_abr = weather.get('timezone_abr', '-')

            filename = self.file_path.split("/")[-1]
            out = f"Назва фото: {filename}\n"
            out += f"Час: {result.get('photo_time', '-') }\n"
            out += f"Координати: {location.get('lat', '-')}, {location.get('lon', '-')}\n"
            out += f"Часовий пояс: {tz} ({tz_abr})\n"
            out += f"Місце: широта {location.get('lat', '-')}, довгота {location.get('lon', '-')}\n"
            out += f"День/ніч (візуально): {'День' if result.get('visual_day') else 'Ніч'}\n"
            out += f"День/ніч (EXIF): {result.get('exif_day', '-')}\n"
            out += f"Температура: {weather.get('temperature', '-')}°C\n"
            out += f"Хмарність: {weather.get('clouds', '-')}%\n"
            if result.get('edited'):
                out += f"⚠️ Фото було оброблене у редакторі: {result.get('editor_name')}\n"
            self.result_text.insert(tk.END, out)
        except Exception as e:
            messagebox.showerror("Помилка", str(e))


if __name__ == "__main__":
    app = PhotoAnalyzerApp()
    app.mainloop()
