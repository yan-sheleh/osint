import requests
from datetime import datetime
from PIL import Image, ImageStat
from PIL.ExifTags import TAGS, GPSTAGS
import exifread

# Функция для извлечения EXIF-метаданных с помощью Pillow
def get_exif_data(image_path):
    image = Image.open(image_path)
    info = image.getexif()
    if not info:
        return {}
    exif_data = {}
    for tag, value in info.items():
        decoded = TAGS.get(tag, tag)
        if decoded == "GPSInfo":
            gps_data = {}
            for t in value:
                sub_decoded = GPSTAGS.get(t, t)
                gps_data[sub_decoded] = value[t]
            exif_data["GPSInfo"] = gps_data
        else:
            exif_data[decoded] = value
    return exif_data

# Преобразование координат из EXIF в десятичный формат
def convert_gps(exif_gps):
    def _convert(coord, ref):
        degrees = coord[0][0] / coord[0][1]
        minutes = coord[1][0] / coord[1][1]
        seconds = coord[2][0] / coord[2][1]
        decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
        if ref in ['S', 'W']:
            decimal = -decimal
        return decimal
    lat = _convert(exif_gps['GPSLatitude'], exif_gps['GPSLatitudeRef'])
    lon = _convert(exif_gps['GPSLongitude'], exif_gps['GPSLongitudeRef'])
    return lat, lon

# Анализ яркости изображения (день/ночь)
def is_day_by_image(image_path, threshold=90):
    try:
        image = Image.open(image_path).convert('L')
        stat = ImageStat.Stat(image)
        avg_brightness = stat.mean[0]
        return avg_brightness > threshold
    except Exception:
        return None

# Получение даты съёмки через exifread (ищет по разным тегам)
def get_photo_datetime_exifread(image_path):
    with open(image_path, 'rb') as f:
        tags = exifread.process_file(f)
        for tag in [
            'EXIF DateTimeOriginal',
            'Image DateTime',
            'EXIF DateTimeDigitized',
            'EXIF DateTime',
        ]:
            dt = tags.get(tag)
            if dt:
                try:
                    return datetime.strptime(str(dt), '%Y:%m:%d %H:%M:%S')
                except Exception:
                    continue
    return None

# Получение погодных данных с Open-Meteo
def get_weather(lat, lon, dt):
    date_str = dt.strftime('%Y-%m-%d')
    hour = dt.hour
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": date_str,
        "end_date": date_str,
        "hourly": "temperature_2m,cloudcover,weathercode",
        "timezone": "auto"
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    try:
        idx = data["hourly"]["time"].index(dt.strftime('%Y-%m-%dT%H:00'))
        weather = {
            "timezone": data['timezone'],
            "timezone_abr": data['timezone_abbreviation'],
            "temperature": data["hourly"]["temperature_2m"][idx],
            "clouds": data["hourly"]["cloudcover"][idx],
            "weathercode": data["hourly"]["weathercode"][idx],
        }
    except Exception:
        weather = {"error": "Немає даних про погоду на цей час"}
    return weather

# Основная функция анализа
def analyze_photo(image_path, photo_time, lat, lon):
    try:
        weather_data = get_weather(lat, lon, photo_time)
    except requests.exceptions.RequestException as e:
        return {"error": f"Помилка при запиті до погодного сервісу: {e}"}
    is_day_visual = is_day_by_image(image_path)
    if is_day_visual is None:
        return {"error": "Не вдалося проаналізувати зображення."}
    # Получаем timezone из погодных данных, если есть
    result = {
        "photo_time": photo_time.strftime('%Y-%m-%d %H:%M:%S'),
        "location": {"lat": lat, "lon": lon},
        "weather_at_time": weather_data,
        "visual_day": is_day_visual,
    }
    return result