#!/usr/bin/env python3
"""
flights.py v1.6 — единая программа архива перелётов (заменяет add_flight_v2.py + generate_site.py).

Меню:  python flights.py     Из BAT: python flights.py add (добавить перелёт) | python flights.py upload (обновить сайт)
  1) Добавить перелёт: вставить JSON (стандартная схема) -> проверка по правилам -> выбрать PDF
     (или фото/скриншоты одной брони -> один PDF) -> превью -> "да" -> файл в папку года на Диске,
     строки в таблицу года по хронологии со ссылкой на файл.
  2) Обновить сайт: годы, в которых были добавления после прошлой публикации.
  3) Обновить сайт: выбрать год вручную.
  4) Проверка (ТОЛЬКО ЧТЕНИЕ): таблицы, ссылки на файлы, папки годов, локальная папка HC, сервер, сайт.
  5) Тест загрузки: создать в папке года крошечный тестовый файл и сразу удалить (проверка прав).

Правила (из рабочих скриптов и договорённостей):
  - JSON плоский: segments (список), passengers (список ОБЪЕКТОВ), Carrier, Original Amount, Currency,
    Issue Date, PNR, OTA Order ID, Category, Vendor/App, Comment. Никаких USD/CAD Value и прочих ключей.
  - Сегмент: Travel Date (YYYY-MM-DD, обязательно), Time Depart, From, To, Arrival Date, Time Arrival,
    Flight Number. Пассажир: Passenger Name ("Фамилия Имя") + Ticket Number.
  - Пассажиры только: Rodionov Aleksei/Alexey/Aleksey, Rodionova Anna, Rodionova Alisa.
  - Кириллица запрещена во всех значениях.
  - Comment пишется программой: "Family flight" для Anna/Alisa, иначе пусто (для отменённых — как раньше).
  - Колонка W (OTA Order ID) = "✅ PDF Verified" — как в add_flight_v2.py.
  - Города: снимается уточнение аэропорта в скобках и применяются CITY_ALIASES (как format_normalizer.py);
    Duration считается по часовым поясам (порядок поиска — v1.4 ниже).
  - Год берётся из дат сегментов. Бронь на два года: строки в таблицу каждого года, файл — в папку
    каждого года (имя по сегментам этого года).
  - Таблица и папка нового года (2027+) создаются автоматически при первом перелёте этого года.
  - Дубль = пассажир + рейс + дата + время.
  - Все данные только на английском (кириллица отклоняется до записи). Файл — только PDF: фото/скриншоты
    переводятся в PDF; файл, не начинающийся с %PDF, не загружается.
  - После записи — обязательная проверка (v1.1): строки перечитываются из таблицы; текст ячейки Receipt Link
    = имени файла; ссылка ведёт на этот файл; на Диске файл с тем же именем, PDF, в папке своего года,
    не в корзине; файл реально открывается (скачивается и начинается с %PDF).
  - v1.2: параллельные запросы к Диску (проверка, скачивание файлов сайта) идут через ОТДЕЛЬНОЕ соединение
    в каждом потоке — общий объект googleapiclient/httplib2 не потокобезопасен (16.10 на ПК Alex: падение
    Windows 0xc0000374 при 8 потоках на одном соединении).
  - v1.3: разрешение Google для загрузки проверяется при первом обращении за запуск; если оно истекло или
    отозвано (invalid_grant — при статусе приложения "Testing" Google выдаёт его на 7 дней), старый токен
    удаляется и сразу открывается браузер для нового входа. В «Проверке» показан возраст токена.
  - v1.4: часовой пояс города для Duration ищется по порядку: (1) city_timezones_local.json — пояса, которые
    Alex уже подтвердил в программе; (2) CITY_TIMEZONES; (3) база городов GeoNames (пакет geonamescache,
    офлайн, все города мира от 15 000 жителей, вместе с пригородами): сначала по основному имени, затем по
    другим написаниям (Ryazan = Ryazan’, Krakow = Kraków). Если у одноимённых городов разные пояса или город
    не найден — программа спрашивает один раз и запоминает ответ в city_timezones_local.json. В превью
    показано, откуда взят каждый пояс. Исправлено в CITY_TIMEZONES (только для новых строк): Ulyanovsk —
    Europe/Ulyanovsk (UTC+4 с 27.03.2016), San Jose del Cabo / Los Cabos — America/Mazatlan (Южная Нижняя
    Калифорния, UTC-7).
  - v1.5: сервер — по имени archive.billup.cloud (раньше был зашит IP Финляндии). Перед публикацией
    server_check() показывает «Публикация на имя -> IP», входит по ssh (только чтение), проверяет папку
    /root/HC; нет входа или папки — публикация не начинается, годы остаются в очереди.
    ssh/scp с StrictHostKeyChecking=accept-new (новый сервер принимается при первом входе, подмена ключа — нет).
    Запуск из BAT: «flights.py add» и «flights.py upload» (один пункт и выход); меню без аргументов — как раньше.
  - v1.6: «Обновить сайт» (BAT 2, пункт 2) и «Проверка» (пункт 4) сверяют сайт с таблицами, а не только
    список изменённых годов на ПК: по каждому году — строки в таблице и «N records» на странице сайта,
    файлы по ссылкам и файлы на сервере. На сайте меньше, чем в таблице (ПЛЮС в таблице: добавили, на сайт не
    попало, или сервер откатили) — год сам попадает в очередь на публикацию. На сайте БОЛЬШЕ, чем в таблице
    (МИНУС: строки пропали из таблицы) — публикация этого года не предлагается, показано предупреждение:
    сначала найти и восстановить, иначе сайт повторил бы потерю. Лишние файлы на сервере (старые имена) —
    только справка, на сервере ничего не удаляется.
  - Сайт: на сервере ничего не удаляется; в zip года — только файлы, на которые есть ссылки в таблице.
  - После успешной публикации — копия сайта на сервере (служба virlab-flights-backup.service),
    если она уже установлена.

Файлы рядом с программой:
  secrets/credentials.json      сервисный аккаунт (чтение/запись таблиц, чтение Диска)
  secrets/client_secret.json    OAuth-клиент для загрузки файлов (drive.file)
  secrets/upload_token.json     создаётся сам при первой загрузке (вход через браузер)
  secrets/site_auth.json        {"user": "...", "password": "..."} — пароль сайта (Basic Auth)
  flights_state.json            какие годы изменены после последней публикации (создаётся сам)
  city_timezones_local.json     часовые пояса городов, подтверждённые Alex в программе (создаётся сам)
  HC/                           локальная рабочая копия сайта (как у generate_site.py)

Требуется: pip install google-api-python-client google-auth google-auth-oauthlib openpyxl pillow tzdata geonamescache
"""
import concurrent.futures
import io
import json
import os
import re
import socket
import base64
import subprocess
import sys
import tempfile
import unicodedata
import threading
import urllib.request
import zipfile
from datetime import date, datetime, time as dtime
from pathlib import Path
from zoneinfo import ZoneInfo

VERSION = "1.6"
HERE = Path(__file__).resolve().parent
SECRETS = HERE / "secrets"
SA_FILE = SECRETS / "credentials.json"
CLIENT_SECRET_FILE = SECRETS / "client_secret.json"
UPLOAD_TOKEN_FILE = SECRETS / "upload_token.json"
SITE_AUTH_FILE = SECRETS / "site_auth.json"
STATE_FILE = HERE / "flights_state.json"
LOCAL_TZ_FILE = HERE / "city_timezones_local.json"
LOCAL_HC = HERE / "HC"

SA_SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
UPLOAD_SCOPES = ["https://www.googleapis.com/auth/drive.file"]

BASE_FOLDER_ID = "1wCHiGXiGKKg3aMTlApuXc1n5Q6tNib4V"    # "Flight Extraction 2016": таблицы и папки годов
SERVER_HOST = "archive.billup.cloud"   # имя, не IP: DNS указывает на тот сервер, где сейчас сайт (v1.5)
SERVER_USER = "root"
REMOTE_HC_ROOT = "/root/HC"
SITE_BASE = "https://archive.billup.cloud:8443"
BACKUP_SERVICE = "virlab-flights-backup.service"
FIRST_YEAR = 2016
SHEET_NAME_RE = re.compile(r"^flights_(\d{4})_from_archive$")
KNOWN_SPREADSHEET_IDS = {
    2016: "1KO-UAWTO_mohidjpApqS353ViA87O31Iv7iOTlaOGJc",
    2017: "1KFVnqt0tL8h-TqrB9Z2g4Or1HfM1t4twmEGWmfyS3PE",
    2018: "1EdjdpcV_m1xx0q16-8P8dPq9kYDTMlNv606NML3eT5U",
    2019: "18zdcAslE_tE7vKc4uJWU5w6l1eFGRXrHJYrEoST4-Tw",
    2020: "13_GXdvqfbm-Dz5j-P_DiKM8c1915Fejd5C7HxOSlYcU",
    2021: "1l_1D0mlQwKyeqlLXdI95qrdZ0MQ7R0GL32FnwU4oZNw",
    2022: "1278ulc6ydCxZUwUualW2v1FjfVzrB_W04leJ_bASXU4",
    2023: "1Xtx_Lxj7Qc0QLUVCXQzdLfZNSzfUkWDGlrPgh2uuolY",
    2024: "1fC9hedh-kKIedcZqL-a3WuRD18SZxEh-JrmUmifU1Es",
    2025: "1aP6SVEFksr5y1OUgRA_2Lb8vuyn_zEV16rOZo-ITQJk",
    2026: "1Fm8vq5A5gsQ3RUeL9j0k43CUURwjyAPmNEsy6ryVHSI",
}

HEADER = ["Category", "Travel Date", "Time Depart", "From", "To", "Arrival Date", "Time Arrival",
          "Flight Number", "Carrier", "Duration", "Original Amount", "Currency", "USD Value",
          "CAD Value", "Vendor/App", "Issue Date", "Itinerary Link", "Comment", "UniqueID",
          "Passenger Name", "Ticket Number", "PNR", "OTA Order ID", "Receipt Link", "Boarding Pass Link"]
COL = {name: i for i, name in enumerate(HEADER)}
TOTAL_COLS = len(HEADER)
COLUMN_WIDTHS = [71, 85, 91, 170, 170, 100, 95, 106, 154, 67, 62, 71, 80, 81, 105, 80, 99, 78, 81,
                 125, 111, 83, 172, 1006, 1006]
STATUS_OK = "✅ PDF Verified"

TOP_KEYS = ["segments", "passengers", "Carrier", "Original Amount", "Currency", "Issue Date", "PNR",
            "OTA Order ID", "Category", "Vendor/App", "Comment"]
SEGMENT_KEYS = ["Travel Date", "Time Depart", "From", "To", "Arrival Date", "Time Arrival", "Flight Number"]
PASSENGER_KEYS = ["Passenger Name", "Ticket Number"]
ALLOWED_PASSENGERS = {"Rodionov Aleksei", "Rodionov Alexey", "Rodionov Aleksey",
                      "Rodionova Anna", "Rodionova Alisa"}
FAMILY_PASSENGERS = {"Rodionova Anna", "Rodionova Alisa"}
ALLOWED_CATEGORIES = {"Flight", "Flight - CANCELLED", "Train", "Taxi", "Car"}
CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")

# ---- copied verbatim from format_normalizer.py (16.10) ----
CITY_ALIASES = {
    "adler": "Sochi",
    "sochi (adler)": "Sochi",
    "kiev": "Kyiv",
    "lvov": "Lviv",
    "rostov glavny": "Rostov-Glavny",
    "tel aviv yafo": "Tel Aviv",
    "tel-aviv": "Tel Aviv",
    "st. petersburg": "Saint Petersburg",
    "sankt-peterburg glavny": "Saint Petersburg",
    "jiaozhou": "Qingdao",
    "qingdao north": "Qingdao",
    "wuxi north": "Wuxi",
    "beijing south": "Beijing",
    "milan malpensa airport t1": "Milan",
    "warsaw airport": "Warsaw",
    "amsterdam centraal": "Amsterdam",
    "tashkent janubiy": "Tashkent",
    "rostovondon": "Rostov-on-Don",
    "huangshi north": "Huangshi",
    "moscow sheremetyevo": "Moscow",
    "moscow domodedovo": "Moscow",
    "moscow kievskaya": "Moscow",
    "istambul": "Istanbul",
    "volgograd 1": "Volgograd",
    "pridacha": "Voronezh",
    "krakow airport": "Krakow",
    "paris nord": "Paris",
    "samarqand": "Samarkand",
    "nevinnomysskaia": "Nevinnomysskaya",
    "shanghai hongqiao": "Shanghai",
    "guangzhoudong": "Guangzhou",
}

CITY_TIMEZONES = {
    "moscow": "Europe/Moscow",
    "moscow kazanskaya": "Europe/Moscow",
    "rostov-glavny": "Europe/Moscow",
    "rostov-on-don": "Europe/Moscow",
    "volgograd": "Europe/Volgograd",
    "stavropol": "Europe/Moscow",
    "mineralnye vody": "Europe/Moscow",
    "nevinnomysskaya": "Europe/Moscow",
    "sochi": "Europe/Moscow",
    "saint petersburg": "Europe/Moscow",
    "nizhny novgorod": "Europe/Moscow",
    "kazan": "Europe/Moscow",
    "samarkand": "Asia/Samarkand",
    "tashkent": "Asia/Tashkent",
    "bukhara": "Asia/Samarkand",
    "andizhan": "Asia/Tashkent",
    "kurgan": "Asia/Yekaterinburg",
    "tyumen": "Asia/Yekaterinburg",
    "novosibirsk": "Asia/Novosibirsk",
    "irkutsk": "Asia/Irkutsk",
    "vladivostok": "Asia/Vladivostok",
    "khabarovsk": "Asia/Vladivostok",
    "bryansk orlovsky": "Europe/Moscow",
    "orel": "Europe/Moscow",
    "belgorod": "Europe/Moscow",
    "pridacha (voronezh-yuzhny)": "Europe/Moscow",
    "voronezh yuzhnyj": "Europe/Moscow",
    "nizhnekamsk": "Europe/Moscow",
    "ulyanovsk": "Europe/Ulyanovsk",
    "astana": "Asia/Almaty",
    "almaty": "Asia/Almaty",
    "karaganda": "Asia/Almaty",
    "baku": "Asia/Baku",
    "ashgabat": "Asia/Ashgabat",
    "ashgabad": "Asia/Ashgabat",
    "bishkek": "Asia/Bishkek",
    "tbilisi": "Asia/Tbilisi",
    "kyiv": "Europe/Kyiv",
    "lviv": "Europe/Kyiv",
    "minsk": "Europe/Minsk",
    "tel aviv": "Asia/Jerusalem",
    "istanbul": "Europe/Istanbul",
    "dubai": "Asia/Dubai",
    "abu dhabi": "Asia/Dubai",
    "delhi": "Asia/Kolkata",
    "new delhi": "Asia/Kolkata",
    "kochi": "Asia/Kolkata",
    "coimbatore": "Asia/Kolkata",
    "mumbai": "Asia/Kolkata",
    "kaunas": "Europe/Vilnius",
    "stockholm": "Europe/Stockholm",
    "arn": "Europe/Stockholm",
    "warsaw": "Europe/Warsaw",
    "poznan": "Europe/Warsaw",
    "paris": "Europe/Paris",
    "london": "Europe/London",
    "edinburgh": "Europe/London",
    "dusseldorf": "Europe/Berlin",
    "frankfurt": "Europe/Berlin",
    "cologne bonn": "Europe/Berlin",
    "amsterdam": "Europe/Amsterdam",
    "rome": "Europe/Rome",
    "milan": "Europe/Rome",
    "athens": "Europe/Athens",
    "belgrad": "Europe/Belgrade",
    "helsinki": "Europe/Helsinki",
    "calgary": "America/Edmonton",
    "vancouver": "America/Vancouver",
    "toronto": "America/Toronto",
    "halifax": "America/Halifax",
    "chicago": "America/Chicago",
    "dallas": "America/Chicago",
    "san francisco": "America/Los_Angeles",
    "mexico city": "America/Mexico_City",
    "san jose del cabo": "America/Mazatlan",
    "los cabos": "America/Mazatlan",
    "qingdao": "Asia/Shanghai",
    "shanghai": "Asia/Shanghai",
    "beijing": "Asia/Shanghai",
    "guangzhou": "Asia/Shanghai",
    "quanzhou": "Asia/Shanghai",
    "shenzhen": "Asia/Shanghai",
    "xi'an": "Asia/Shanghai",
    "wuxi": "Asia/Shanghai",
    "seoul": "Asia/Seoul",
    "hong kong": "Asia/Hong_Kong",
    "tver": "Europe/Moscow",
    "kaliningrad": "Europe/Kaliningrad",
    "krasnodar": "Europe/Moscow",
    "antalya": "Europe/Istanbul",
    "yekaterinburg": "Asia/Yekaterinburg",
    "chelyabinsk": "Asia/Yekaterinburg",
    "chisinau": "Europe/Chisinau",
    "jinan": "Asia/Shanghai",
    "sanya": "Asia/Shanghai",
    "munich": "Europe/Berlin",
    "cluj-napoca": "Europe/Bucharest",
    "krakow": "Europe/Warsaw",
    "tallinn": "Europe/Tallinn",
    "cairo": "Africa/Cairo",
    "dalaman": "Europe/Istanbul",
    "krasnoyarsk": "Asia/Krasnoyarsk",
    "sofia": "Europe/Sofia",
    "ufa": "Asia/Yekaterinburg",
    "ivanovo": "Europe/Moscow",
    "wuhan": "Asia/Shanghai",
    "singapore": "Asia/Singapore",
    "huangshi": "Asia/Shanghai",
    "dalian": "Asia/Shanghai",
    "new york": "America/New_York",
    "ahmedabad": "Asia/Kolkata",
    "houston": "America/Chicago",
    "guadalajara": "America/Mexico_City",
    "puerto vallarta": "America/Mexico_City",
    "voronezh": "Europe/Moscow",
    "yerevan": "Asia/Yerevan",
    "muscat": "Asia/Muscat",
    "abbotsford": "America/Vancouver",
    "bryansk": "Europe/Moscow",
    "belorechenskaya": "Europe/Moscow",
    "tirana": "Europe/Tirane",
    "xiamen": "Asia/Shanghai",
}
# ------------------------------------------------------------


# =============================================================== helpers (pure)

def parse_date(s):
    return datetime.strptime(str(s).strip(), "%Y-%m-%d").date()


def parse_time(s):
    s = str(s or "").strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            pass
    return None


def parse_sheet_date(s):
    s = str(s or "").strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def parse_sheet_time(s):
    return parse_time(s) or dtime(0, 0)


def date_to_serial(d):
    return (d - date(1899, 12, 30)).days


def time_to_serial(t):
    return (t.hour * 3600 + t.minute * 60 + t.second) / 86400.0


def normalize_city(city):
    """Как format_normalizer.apply_city_alias: снять '(...)', применить CITY_ALIASES."""
    stripped = re.sub(r"\(.*?\)", "", str(city)).strip()
    return CITY_ALIASES.get(stripped.lower(), stripped)


def city_key(name):
    """Ключ сравнения названий: без регистра, диакритики, апострофов, пробелов и дефисов (Ryazan’ = Ryazan)."""
    s = unicodedata.normalize("NFKD", str(name))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", s.lower())


_GEO = None          # {key: [(name, country, population, tz)]} по основному имени и {key: [...]} по другим


def geo_index():
    """Офлайн-база GeoNames (geonamescache). None, если пакет не установлен."""
    global _GEO
    if _GEO is None:
        try:
            import geonamescache
        except ImportError:
            _GEO = False
            return None
        main, alt = {}, {}
        for c in geonamescache.GeonamesCache().get_cities().values():
            rec = (c["name"], c["countrycode"], int(c["population"]), c["timezone"])
            main.setdefault(city_key(c["name"]), []).append(rec)
            for a in set(c.get("alternatenames") or []):
                k = city_key(a)
                if k:
                    alt.setdefault(k, []).append(rec)
        _GEO = (main, alt)
    return _GEO or None


def load_local_tz():
    try:
        return {k.lower(): v for k, v in json.loads(LOCAL_TZ_FILE.read_text(encoding="utf-8")).items()}
    except FileNotFoundError:
        return {}


def save_local_tz(city, tz):
    d = {}
    if LOCAL_TZ_FILE.exists():
        d = json.loads(LOCAL_TZ_FILE.read_text(encoding="utf-8"))
    d[city] = tz
    tmp = LOCAL_TZ_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, LOCAL_TZ_FILE)


def geo_candidates(city):
    """Города GeoNames с этим названием: сначала по основному имени, иначе по другим написаниям.
    Список (name, country, population, tz), крупнейший первым; одинаковые города не повторяются."""
    idx = geo_index()
    if not idx:
        return None
    k = city_key(city)
    found = idx[0].get(k) or idx[1].get(k) or []
    return sorted(set(found), key=lambda r: -r[2])


def resolve_tz(city):
    """(пояс, откуда) или (None, причина). Без вопросов: неоднозначное и ненайденное -> None."""
    low = city.lower()
    local = load_local_tz()
    if low in local:
        return local[low], "подтверждён Alex"
    if low in CITY_TIMEZONES:
        return CITY_TIMEZONES[low], "таблица программы"
    cand = geo_candidates(city)
    if cand is None:
        return None, "нет в таблице программы, база городов не установлена (pip install geonamescache)"
    if not cand:
        return None, "не найден ни в таблице программы, ни в базе городов"
    zones = sorted({r[3] for r in cand})
    if len(zones) > 1:
        return None, "одноимённые города в разных поясах: " + "; ".join(
            "%s, %s, %d жит. -> %s" % r for r in cand[:5])
    r = cand[0]
    return r[3], "база городов: %s, %s, %d жит." % (r[0], r[1], r[2])


def confirm_timezones(data, ask=None):
    """До превью: для городов без однозначного пояса спрашивает Alex один раз и запоминает ответ."""
    ask = ask or input
    cities = []
    for seg in data["segments"]:
        for c in (normalize_city(seg["From"]), normalize_city(seg["To"])):
            if c and c not in cities:
                cities.append(c)
    for c in cities:
        tz, why = resolve_tz(c)
        if tz:
            continue
        cand = geo_candidates(c) or []
        print("\n🕓 Часовой пояс для города %r: %s" % (c, why))
        opts = []
        for r in cand[:5]:
            if r[3] not in [o[3] for o in opts]:
                opts.append(r)
        for i, r in enumerate(opts, 1):
            print("   %d) %s — %s, %s, %d жит." % (i, r[3], r[0], r[1], r[2]))
        opts = [r[3] for r in opts]
        while True:
            a = ask("   Номер из списка или пояс вида Europe/Moscow; Enter — оставить Duration пустым: ").strip()
            if not a:
                break
            if a.isdigit() and 1 <= int(a) <= len(opts):
                a = opts[int(a) - 1]
            try:
                ZoneInfo(a)
            except Exception:  # noqa
                print("   ❌ Такого пояса нет: %r" % a)
                continue
            save_local_tz(c, a)
            print("   ✅ %s -> %s (запомнено в %s)" % (c, a, LOCAL_TZ_FILE.name))
            break


def compute_duration(seg, from_city, to_city):
    """'Ч:ММ' или (None, причина)."""
    d1 = parse_date(seg["Travel Date"])
    t1 = parse_time(seg.get("Time Depart"))
    d2 = parse_date(seg["Arrival Date"]) if str(seg.get("Arrival Date") or "").strip() else d1
    t2 = parse_time(seg.get("Time Arrival"))
    if not (t1 and t2):
        return None, "нет времени вылета/прилёта"
    tz1, w1 = resolve_tz(from_city)
    tz2, w2 = resolve_tz(to_city)
    if not tz1 or not tz2:
        miss = ["%s (%s)" % (c, w) for c, tz, w in ((from_city, tz1, w1), (to_city, tz2, w2)) if not tz]
        return None, "нет часового пояса для: " + "; ".join(miss)
    minutes = int((datetime.combine(d2, t2, tzinfo=ZoneInfo(tz2)) -
                   datetime.combine(d1, t1, tzinfo=ZoneInfo(tz1))).total_seconds() // 60)
    if minutes < 0:
        return None, "отрицательная длительность — проверьте даты и время"
    return "%d:%02d" % divmod(minutes, 60), None


def clean_place(s):
    s = re.sub(r"\(.*?\)", "", str(s))
    return s.replace(" ", "").replace(",", "").replace("-", "")


def build_filename(year, segments, passengers, pnr):
    """Схема add_flight_v2/rename_files: {ГОД}_{ДД-ММ}_{Откуда}-{Куда}_..._{Пассажиры}[-{PNR}].pdf"""
    parts = [str(year)]
    for seg in segments:
        parts.append(parse_date(seg["Travel Date"]).strftime("%d-%m"))
        parts.append("%s-%s" % (clean_place(seg["From"]), clean_place(seg["To"])))
    names, seen = [], set()
    for p in passengers:
        n = clean_place(p["Passenger Name"])
        if n.lower() not in seen:
            seen.add(n.lower())
            names.append(n)
    tail = list(names)
    pnr = str(pnr or "").strip()
    if pnr:
        tail.append(pnr.replace(" ", ""))
    return "_".join(parts) + "_" + "-".join(tail) + ".pdf"


def sanitize_filename(name):
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip()


def validate(data):
    """Проверка JSON по правилам. Возвращает список ошибок (пустой = всё верно)."""
    errs = []
    if not isinstance(data, dict):
        return ["JSON должен быть объектом { ... }"]
    extra = [k for k in data if k not in TOP_KEYS]
    missing = [k for k in TOP_KEYS if k not in data]
    if extra:
        errs.append("лишние ключи верхнего уровня: " + ", ".join(extra))
    if missing:
        errs.append("нет ключей: " + ", ".join(missing))

    def walk(v, where):
        if isinstance(v, str):
            if CYRILLIC_RE.search(v):
                errs.append("кириллица в %s: %r" % (where, v))
        elif isinstance(v, dict):
            for k, x in v.items():
                walk(x, "%s.%s" % (where, k))
        elif isinstance(v, list):
            for i, x in enumerate(v):
                walk(x, "%s[%d]" % (where, i))
        elif v is not None and not isinstance(v, (int, float)):
            errs.append("недопустимое значение в %s" % where)
    walk(data, "JSON")

    segs = data.get("segments")
    if not isinstance(segs, list) or not segs:
        errs.append("segments должен быть непустым списком")
        segs = []
    for i, s in enumerate(segs):
        w = "segments[%d]" % i
        if not isinstance(s, dict):
            errs.append(w + " должен быть объектом")
            continue
        ex = [k for k in s if k not in SEGMENT_KEYS]
        mi = [k for k in SEGMENT_KEYS if k not in s]
        if ex:
            errs.append("%s: лишние ключи %s" % (w, ", ".join(ex)))
        if mi:
            errs.append("%s: нет ключей %s" % (w, ", ".join(mi)))
        try:
            parse_date(s.get("Travel Date", ""))
        except ValueError:
            errs.append("%s: Travel Date должна быть YYYY-MM-DD и не пустая (сейчас %r)" % (w, s.get("Travel Date")))
        ad = str(s.get("Arrival Date") or "").strip()
        if ad:
            try:
                parse_date(ad)
            except ValueError:
                errs.append("%s: Arrival Date должна быть YYYY-MM-DD или пусто (сейчас %r)" % (w, ad))
        for k in ("Time Depart", "Time Arrival"):
            v = str(s.get(k) or "").strip()
            if v and not parse_time(v):
                errs.append("%s: %s должно быть HH:MM или пусто (сейчас %r)" % (w, k, v))
        for k in ("From", "To"):
            if not str(s.get(k) or "").strip():
                errs.append("%s: %s пустой" % (w, k))

    pax = data.get("passengers")
    if not isinstance(pax, list) or not pax:
        errs.append("passengers должен быть непустым списком объектов")
        pax = []
    for i, p in enumerate(pax):
        w = "passengers[%d]" % i
        if not isinstance(p, dict):
            errs.append(w + " должен быть объектом {\"Passenger Name\": ..., \"Ticket Number\": ...}")
            continue
        ex = [k for k in p if k not in PASSENGER_KEYS]
        mi = [k for k in PASSENGER_KEYS if k not in p]
        if ex:
            errs.append("%s: лишние ключи %s" % (w, ", ".join(ex)))
        if mi:
            errs.append("%s: нет ключей %s" % (w, ", ".join(mi)))
        if p.get("Passenger Name") not in ALLOWED_PASSENGERS:
            errs.append("%s: пассажир %r не из списка (%s)" % (w, p.get("Passenger Name"),
                                                             ", ".join(sorted(ALLOWED_PASSENGERS))))
    if data.get("Category", "Flight") not in ALLOWED_CATEGORIES:
        errs.append("Category %r не из списка %s" % (data.get("Category"), sorted(ALLOWED_CATEGORIES)))
    amt = str(data.get("Original Amount") or "").strip()
    if amt:
        try:
            float(amt)
        except ValueError:
            errs.append("Original Amount должен быть числом или пусто (сейчас %r)" % amt)
    if str(data.get("Comment") or "") not in ("", "Family flight"):
        errs.append('Comment должен быть "" или "Family flight" (программа всё равно ставит его сама)')
    return errs


def plan_booking(data):
    """Готовит запись: группы по годам -> (имя файла, строки). Ничего не пишет."""
    common = {k: data.get(k) for k in ("Carrier", "Original Amount", "Currency", "Issue Date", "PNR",
                                        "Vendor/App")}
    category = data.get("Category") or "Flight"
    by_year = {}
    for seg in data["segments"]:
        by_year.setdefault(parse_date(seg["Travel Date"]).year, []).append(seg)
    plan, warnings = [], []
    for year in sorted(by_year):
        segs = by_year[year]
        fname = build_filename(year, segs, data["passengers"], data.get("PNR"))
        rows = []
        for seg in segs:
            frm, to = normalize_city(seg["From"]), normalize_city(seg["To"])
            dur, why = compute_duration(seg, frm, to)
            if why:
                warnings.append("%s %s->%s: Duration не проставлен — %s" % (seg["Travel Date"], frm, to, why))
            for p in data["passengers"]:
                name = p["Passenger Name"]
                if name in FAMILY_PASSENGERS:
                    comment = "Family flight"
                elif "CANCEL" in category.upper():
                    comment = data.get("Comment") or "CANCELLED"
                else:
                    comment = ""
                rows.append(dict(common, **{
                    "Category": category, "Travel Date": seg["Travel Date"],
                    "Time Depart": seg.get("Time Depart") or "", "From": frm, "To": to,
                    "Arrival Date": seg.get("Arrival Date") or "", "Time Arrival": seg.get("Time Arrival") or "",
                    "Flight Number": seg.get("Flight Number") or "", "Duration": dur or "",
                    "Comment": comment, "Passenger Name": name, "Ticket Number": p.get("Ticket Number") or "",
                    "OTA Order ID": STATUS_OK}))
        plan.append({"year": year, "file_name": fname, "segments": segs, "rows": rows})
    return plan, warnings


def row_cells(row, file_url, file_name):
    """Ячейки строки для Sheets API (как add_flight_v2.build_row_cell_data + Duration)."""
    cells = [{} for _ in range(TOTAL_COLS)]

    def text(col, v):
        if v not in (None, ""):
            cells[COL[col]] = {"userEnteredValue": {"stringValue": str(v)}}

    def num(col, v):
        if v not in (None, ""):
            cells[COL[col]] = {"userEnteredValue": {"numberValue": float(v)}}

    def dt(col, v):
        if v:
            cells[COL[col]] = {"userEnteredValue": {"numberValue": date_to_serial(parse_date(v))},
                               "userEnteredFormat": {"numberFormat": {"type": "DATE", "pattern": "dd.mm.yyyy"}}}

    def tm(col, v):
        t = parse_time(v)
        if t:
            cells[COL[col]] = {"userEnteredValue": {"numberValue": time_to_serial(t)},
                               "userEnteredFormat": {"numberFormat": {"type": "TIME", "pattern": "hh:mm"}}}

    text("Category", row["Category"]); dt("Travel Date", row["Travel Date"]); tm("Time Depart", row["Time Depart"])
    text("From", row["From"]); text("To", row["To"]); dt("Arrival Date", row["Arrival Date"])
    tm("Time Arrival", row["Time Arrival"]); text("Flight Number", row["Flight Number"])
    text("Carrier", row["Carrier"]); text("Duration", row["Duration"]); num("Original Amount", row["Original Amount"])
    text("Currency", row["Currency"]); text("Vendor/App", row["Vendor/App"]); text("Issue Date", row["Issue Date"])
    text("Comment", row["Comment"]); text("Passenger Name", row["Passenger Name"])
    text("Ticket Number", row["Ticket Number"]); text("PNR", row["PNR"])
    cells[COL["OTA Order ID"]] = {"userEnteredValue": {"stringValue": row["OTA Order ID"]}}
    cells[COL["Receipt Link"]] = {"userEnteredValue": {"stringValue": file_name},
                                  "textFormatRuns": [{"startIndex": 0, "format": {"link": {"uri": file_url}}}]}
    return cells


def is_duplicate(values, row):
    """values: строки таблицы (FORMATTED_VALUE). Дубль = пассажир + рейс + дата + время."""
    d, t = parse_date(row["Travel Date"]), parse_sheet_time(row["Time Depart"])
    fl = str(row["Flight Number"]).replace(" ", "").lower()
    pax = row["Passenger Name"].strip().lower()
    for r in values[1:]:
        if len(r) <= COL["Passenger Name"]:
            continue
        if (parse_sheet_date(r[COL["Travel Date"]]) == d and parse_sheet_time(r[COL["Time Depart"]]) == t
                and str(r[COL["Flight Number"]]).replace(" ", "").lower() == fl
                and pax in str(r[COL["Passenger Name"]]).strip().lower()):
            return True
    return False


def insert_position(values, first_row):
    """1-based номер строки, перед которой вставлять (как add_flight_v2.find_target_row_index)."""
    new_dt = datetime.combine(parse_date(first_row["Travel Date"]), parse_sheet_time(first_row["Time Depart"]))
    for idx in range(1, len(values)):
        r = values[idx]
        if len(r) <= COL["Travel Date"] or not str(r[COL["Travel Date"]]).strip():
            continue
        rd = parse_sheet_date(r[COL["Travel Date"]])
        if rd is None:
            continue
        rt = parse_sheet_time(r[COL["Time Depart"]]) if len(r) > COL["Time Depart"] else dtime(0, 0)
        if datetime.combine(rd, rt) > new_dt:
            return idx + 1
    return len(values) + 1


def extract_file_id(url):
    m = re.search(r"/d/([a-zA-Z0-9_-]{20,})|[?&]id=([a-zA-Z0-9_-]{20,})", url or "")
    return (m.group(1) or m.group(2)) if m else None


def load_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"dirty_years": [], "history": []}


def save_state(st):
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, STATE_FILE)


# =============================================================== Google access

class Google:
    def __init__(self):
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        if not SA_FILE.exists():
            raise SystemExit("❌ Нет %s — положите ключ сервисного аккаунта в папку secrets." % SA_FILE)
        creds = service_account.Credentials.from_service_account_file(str(SA_FILE), scopes=SA_SCOPES)
        self.sa_email = json.loads(SA_FILE.read_text(encoding="utf-8")).get("client_email", "")
        self.sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
        self.drive = build("drive", "v3", credentials=creds, cache_discovery=False)
        self._creds = creds
        self._tl = threading.local()
        self._user = None
        self._ids = dict(KNOWN_SPREADSHEET_IDS)

    def user(self):
        """OAuth пользователя (drive.file) — только для загрузки файлов и создания таблиц/папок."""
        if self._user:
            return self._user
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from google.auth.exceptions import RefreshError
        creds = None
        if UPLOAD_TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(UPLOAD_TOKEN_FILE), UPLOAD_SCOPES)
            if creds.refresh_token:
                try:
                    creds.refresh(Request())          # проверка разрешения сразу, а не посреди записи
                except RefreshError as e:
                    print("ℹ️ Разрешение Google для загрузки истекло или отозвано (%s) — нужен новый вход."
                          % (e.args[0] if e.args else e))
                    UPLOAD_TOKEN_FILE.unlink()
                    creds = None
        if not creds or not creds.valid:
            if not CLIENT_SECRET_FILE.exists():
                raise SystemExit("❌ Нет %s (нужен для загрузки файлов)." % CLIENT_SECRET_FILE)
            print("🌐 Открывается браузер: войдите под polymercalgary и разрешите доступ "
                  "(только к файлам, которые создаёт эта программа)...")
            creds = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_FILE), UPLOAD_SCOPES).run_local_server(port=0)
            print("✅ Вход выполнен, разрешение сохранено.")
        UPLOAD_TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        self._user = {"drive": build("drive", "v3", credentials=creds, cache_discovery=False),
                      "sheets": build("sheets", "v4", credentials=creds, cache_discovery=False)}
        return self._user

    # ---- sheets
    def year_sheets(self):
        """{год: id} всех таблиц flights_<год>_from_archive, видимых сервисному аккаунту."""
        found, token = {}, None
        while True:
            r = self.drive.files().list(
                q="mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false and "
                  "name contains '_from_archive'",
                fields="nextPageToken, files(id, name)", pageSize=200, pageToken=token).execute()
            for f in r.get("files", []):
                m = SHEET_NAME_RE.match(f["name"])
                if m:
                    found.setdefault(int(m.group(1)), f["id"])
            token = r.get("nextPageToken")
            if not token:
                break
        self._ids.update(found)
        return dict(sorted(found.items()))

    def sheet_id(self, year):
        if year in self._ids:
            return self._ids[year]
        return self.year_sheets().get(year)

    def values(self, ssid):
        r = self.sheets.spreadsheets().values().get(spreadsheetId=ssid, range="A1:Y",
                                                    valueRenderOption="FORMATTED_VALUE").execute()
        return r.get("values", [])

    def tab_id(self, ssid):
        r = self.sheets.spreadsheets().get(spreadsheetId=ssid, fields="sheets.properties").execute()
        return r["sheets"][0]["properties"]["sheetId"]

    def link_rows(self, ssid):
        """Строки с текстом и гиперссылкой Receipt Link (как generate_site.read_rows)."""
        r = self.sheets.spreadsheets().get(spreadsheetId=ssid, ranges=["A2:Y10000"],
                                           fields="sheets.data.rowData.values(hyperlink,formattedValue)").execute()
        rows = []
        try:
            data = r["sheets"][0]["data"][0].get("rowData", [])
        except (KeyError, IndexError):
            return rows
        for row in data:
            vals = row.get("values", [])
            if not vals:
                continue
            rec = {name: (vals[i].get("formattedValue", "") if i < len(vals) else "") for i, name in enumerate(HEADER)}
            link = vals[COL["Receipt Link"]] if len(vals) > COL["Receipt Link"] else {}
            rec["_href"] = link.get("hyperlink", "")
            rec["_name"] = link.get("formattedValue", "")
            if rec.get("Category") or rec.get("Travel Date"):
                rows.append(rec)
        return rows

    def insert_rows(self, ssid, at_row_1based, cell_rows):
        tab = self.tab_id(ssid)
        start = at_row_1based - 1
        n = len(cell_rows)
        self.sheets.spreadsheets().batchUpdate(spreadsheetId=ssid, body={"requests": [
            {"insertDimension": {"range": {"sheetId": tab, "dimension": "ROWS", "startIndex": start,
                                           "endIndex": start + n}, "inheritFromBefore": False}},
            {"updateCells": {"range": {"sheetId": tab, "startRowIndex": start, "endRowIndex": start + n,
                                       "startColumnIndex": 0, "endColumnIndex": TOTAL_COLS},
                             "rows": [{"values": c} for c in cell_rows],
                             "fields": "userEnteredValue,userEnteredFormat.numberFormat,textFormatRuns"}}]}).execute()

    def create_year_sheet(self, year):
        """Новая таблица года в папке BASE_FOLDER_ID с тем же заголовком и оформлением."""
        u = self.user()
        f = u["drive"].files().create(body={"name": "flights_%d_from_archive" % year, "parents": [BASE_FOLDER_ID],
                                            "mimeType": "application/vnd.google-apps.spreadsheet"},
                                      fields="id").execute()
        ssid = f["id"]
        tab = u["sheets"].spreadsheets().get(spreadsheetId=ssid, fields="sheets.properties").execute()["sheets"][0]["properties"]["sheetId"]
        reqs = [{"updateCells": {"range": {"sheetId": tab, "startRowIndex": 0, "endRowIndex": 1,
                                           "startColumnIndex": 0, "endColumnIndex": TOTAL_COLS},
                                 "rows": [{"values": [{"userEnteredValue": {"stringValue": h},
                                                       "userEnteredFormat": {"textFormat": {"bold": True}}} for h in HEADER]}],
                                 "fields": "userEnteredValue,userEnteredFormat.textFormat.bold"}},
                {"updateSheetProperties": {"properties": {"sheetId": tab, "gridProperties": {"frozenRowCount": 1}},
                                           "fields": "gridProperties.frozenRowCount"}}]
        for i, w in enumerate(COLUMN_WIDTHS):
            reqs.append({"updateDimensionProperties": {"range": {"sheetId": tab, "dimension": "COLUMNS",
                                                                 "startIndex": i, "endIndex": i + 1},
                                                       "properties": {"pixelSize": w}, "fields": "pixelSize"}})
        u["sheets"].spreadsheets().batchUpdate(spreadsheetId=ssid, body={"requests": reqs}).execute()
        self._ensure_sa_access(ssid)
        self._ids[year] = ssid
        return ssid

    def _ensure_sa_access(self, file_id):
        try:
            self.drive.files().get(fileId=file_id, fields="id").execute()
        except Exception:  # noqa
            self.user()["drive"].permissions().create(fileId=file_id, sendNotificationEmail=False,
                                                      body={"type": "user", "role": "writer",
                                                            "emailAddress": self.sa_email}).execute()

    # ---- drive
    def year_folder(self, year, create):
        q = ("name = '%d' and '%s' in parents and mimeType = 'application/vnd.google-apps.folder' "
             "and trashed = false" % (year, BASE_FOLDER_ID))
        files = self.drive.files().list(q=q, fields="files(id, name)").execute().get("files", [])
        if files:
            return files[0]["id"]
        if not create:
            return None
        f = self.user()["drive"].files().create(body={"name": str(year), "parents": [BASE_FOLDER_ID],
                                                      "mimeType": "application/vnd.google-apps.folder"},
                                                fields="id").execute()
        self._ensure_sa_access(f["id"])
        return f["id"]

    def find_file(self, name, folder_id):
        q = "name = '%s' and '%s' in parents and trashed = false" % (name.replace("'", "\\'"), folder_id)
        files = self.drive.files().list(q=q, fields="files(id, webViewLink)").execute().get("files", [])
        return files[0] if files else None

    def upload(self, path, name, folder_id):
        from googleapiclient.http import MediaFileUpload
        media = MediaFileUpload(str(path), mimetype="application/pdf", resumable=True)
        f = self.user()["drive"].files().create(body={"name": name, "parents": [folder_id]}, media_body=media,
                                                fields="id, webViewLink").execute()
        return f["id"], f.get("webViewLink")

    def _drive_t(self):
        """Свой объект Drive (своё HTTP-соединение) для каждого потока: httplib2 не потокобезопасен."""
        d = getattr(self._tl, "drive", None)
        if d is None:
            from googleapiclient.discovery import build
            d = build("drive", "v3", credentials=self._creds, cache_discovery=False)
            self._tl.drive = d
        return d

    def file_meta(self, file_id):
        return self._drive_t().files().get(fileId=file_id, fields="id,name,mimeType,parents,trashed,size").execute()

    def download(self, file_id):
        from googleapiclient.http import MediaIoBaseDownload
        fh = io.BytesIO()
        dl = MediaIoBaseDownload(fh, self._drive_t().files().get_media(fileId=file_id))
        done = False
        while not done:
            _, done = dl.next_chunk()
        return fh.getvalue()

    def export_xlsx(self, ssid):
        from googleapiclient.http import MediaIoBaseDownload
        fh = io.BytesIO()
        dl = MediaIoBaseDownload(fh, self.drive.files().export_media(
            fileId=ssid, mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))
        done = False
        while not done:
            _, done = dl.next_chunk()
        return fh.getvalue()


# =============================================================== server / site

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def ssh(cmd):
    return run(["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new",
                "%s@%s" % (SERVER_USER, SERVER_HOST), cmd])


def scp(local, remote):
    return run(["scp", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new", "-r", str(local), "%s@%s:%s" % (SERVER_USER, SERVER_HOST, remote)])


def site_auth():
    try:
        a = json.loads(SITE_AUTH_FILE.read_text(encoding="utf-8"))
        return a["user"], a["password"]
    except (OSError, ValueError, KeyError):
        raise SystemExit("❌ Нет %s с {\"user\": ..., \"password\": ...} (пароль сайта)." % SITE_AUTH_FILE)


def http_code(url):
    user, pw = site_auth()
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", "Basic " + base64.b64encode(("%s:%s" % (user, pw)).encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            r.read(1)
            return str(r.status)
    except urllib.error.HTTPError as e:
        return str(e.code)
    except Exception as e:  # noqa
        return "ERR " + type(e).__name__


def http_get(url):
    """v1.6: (код, текст страницы). Ошибка сети -> ("ERR ...", "")."""
    user, pw = site_auth()
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", "Basic " + base64.b64encode(("%s:%s" % (user, pw)).encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return str(r.status), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return str(e.code), ""
    except Exception as e:  # noqa
        return "ERR " + type(e).__name__, ""


# ---- HTML (шаблон generate_site.py 21.09 без изменений вида)
DOWNLOAD_SVG = '''<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>'''
PAGE_CSS = """
  body { font-family: -apple-system, "Segoe UI", Arial, sans-serif; background:#f0f0f0; margin:0; padding:0; min-height:100vh; }
  .card { max-width:1600px; width:95%; margin:24px auto; padding:32px; background:#fff; border-radius:8px; border:1px solid #e0e0e0; color:#1a1a1a; box-sizing:border-box; }
  .header { display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:16px; flex-wrap:wrap; gap:12px; }
  h2 { margin:0 0 4px; font-size:20px; font-weight:600; color:#111; }
  .count { margin:0; color:#666; font-size:13px; }
  .dl-btn { text-decoration:none; display:inline-flex; align-items:center; gap:8px; background:#1a56db; color:#fff; padding:10px 18px; border-radius:6px; font-size:14px; font-weight:500; }
  .dl-hint { margin:8px 0 0; font-size:15px; color:#1a56db; max-width:260px; border:1px solid #1a56db; border-radius:6px; padding:8px 12px; background:#f0f5ff; }
  .years { display:flex; gap:6px; margin-bottom:12px; flex-wrap:wrap; }
  .years a { text-decoration:none; font-size:12px; padding:5px 10px; border:1px solid #ddd; border-radius:6px; color:#333; }
  .years a.active { border:1.5px solid #1a56db; color:#1a56db; font-weight:600; }
  .filters { display:flex; gap:6px; margin-bottom:16px; flex-wrap:wrap; }
  .filters button { font-size:12px; padding:5px 10px; border:1px solid #ddd; border-radius:6px; background:#fff; cursor:pointer; }
  .filters button.active { border:1.5px solid #1a56db; color:#1a56db; font-weight:600; }
  .table-wrap { overflow-x:auto; }
  table { width:100%; border-collapse:collapse; font-size:13px; border:1px solid #e0e0e0; border-radius:6px; }
  th { text-align:left; padding:8px 10px; font-weight:600; color:#555; background:#f5f5f5; border-bottom:1px solid #e0e0e0; white-space:nowrap; }
  td { padding:8px 10px; border-bottom:1px solid #eee; white-space:nowrap; }
  tr.family { background:#fdeef3; }
  .badge-flight { background:#e3edfc; color:#1a56db; font-size:11px; padding:2px 8px; border-radius:4px; }
  .badge-train { background:#e6f4ea; color:#1e7e34; font-size:11px; padding:2px 8px; border-radius:4px; }
  .badge-taxi { background:#fdf1dc; color:#b06a00; font-size:11px; padding:2px 8px; border-radius:4px; }
  .badge-car { background:#fdf1dc; color:#b06a00; font-size:11px; padding:2px 8px; border-radius:4px; }
  .file-link { color:#1a56db; text-decoration:none; }
  .center { text-align:center; }
  .muted { color:#bbb; }
  .num { color:#999; text-align:center; }
  .view-num { color:#999; text-align:center; width:68px; min-width:68px; }
  th.view-num { text-align:center; }
  .legend { margin-top:10px; font-size:12px; color:#888; }
  .legend .sw { display:inline-block; width:10px; height:10px; background:#fdeef3; border-radius:2px; margin-right:6px; vertical-align:middle; }
  @media (max-width:600px) {
    .card { padding:16px; margin:12px auto; }
    .header { flex-direction:column; }
    .years, .filters { flex-wrap:wrap; }
  }
"""
BADGE_CLASS = {"Flight": "badge-flight", "Train": "badge-train", "Taxi": "badge-taxi", "Car": "badge-car"}


def html_escape(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def year_links(all_years, current):
    return "\n    ".join('<a class="%s" href="/%d/">%d</a>' % ("active" if y == current else "", y, y) for y in all_years)


def year_html(year, rows, files_map, all_years):
    trs = []
    for idx, r in enumerate(rows, start=1):
        cat = r.get("Category", "")
        fam = r.get("Comment", "").strip() == "Family flight"
        fid = extract_file_id(r.get("_href"))
        if fid and fid in files_map:
            cell = ('<a class="file-link" title="Download this document" href="%d_files/%s">%s</a>'
                    % (year, html_escape(files_map[fid]), DOWNLOAD_SVG))
        else:
            cell = '<span class="muted">✕</span>'
        trs.append("""
      <tr class="%s">
        <td class="num">%d</td>
        <td class="view-num"></td>
        <td>%s</td>
        <td><span class="%s">%s</span></td>
        <td>%s</td>
        <td>%s</td>
        <td>%s</td>
        <td>%s</td>
        <td class="center muted">%s</td>
        <td class="center">%s</td>
      </tr>""" % ("family" if fam else "", idx, html_escape(r.get("Travel Date", "")),
                  BADGE_CLASS.get(cat, "badge-flight"), html_escape(cat), html_escape(r.get("From", "")),
                  html_escape(r.get("To", "")), html_escape(r.get("Flight Number", "")),
                  html_escape(r.get("Passenger Name", "")), "👪" if fam else "—", cell))
    return YEAR_TEMPLATE.format(year=year, css=PAGE_CSS, total=len(rows), svg=DOWNLOAD_SVG,
                                years=year_links(all_years, year), rows="".join(trs))


YEAR_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>Flights {year}</title>
<style>{css}</style>
</head>
<body>
<div class="card">
  <div class="header">
    <div>
      <h2>Flights {year}</h2>
      <p class="count">{total} records</p>
    </div>
    <div style="text-align:right">
      <a class="dl-btn" href="{year}_archive.zip">{svg} Download {year} archive (.zip)</a>
      <p class="dl-hint">Includes full flight details and every linked document. Please fully extract (unzip) the file before opening the spreadsheet.</p>
    </div>
  </div>

  <div class="years">
    <a href="/">← All years</a>
    {years}
  </div>

  <div class="filters">
    <button class="active" onclick="filterRows('all')">All flights</button>
    <button onclick="filterRows('mine')">My flights</button>
    <button onclick="filterRows('family')">Family flights</button>
  </div>

  <div class="table-wrap">
  <table id="flightsTable">
    <thead>
      <tr>
        <th>#</th><th class="view-num">View #</th><th>Date</th><th>Category</th><th>From</th><th>To</th>
        <th>Number</th><th>Passenger</th><th class="center">Family</th><th class="center">File</th>
      </tr>
    </thead>
    <tbody>{rows}
    </tbody>
  </table>
  </div>

  <p class="legend"><span class="sw"></span>Row tint = family flight (Comment says "Family flight")</p>
</div>
<script>
function renumberVisible() {{
  let n = 1;
  document.querySelectorAll('#flightsTable tbody tr').forEach(row => {{
    if (row.style.display === 'none') return;
    const cell = row.querySelector('.view-num');
    if (cell) cell.textContent = String(n++);
  }});
}}
function filterRows(mode) {{
  document.querySelectorAll('.filters button').forEach(b => b.classList.remove('active'));
  if (typeof event !== 'undefined' && event && event.target) {{
    event.target.classList.add('active');
  }}
  document.querySelectorAll('#flightsTable tbody tr').forEach(row => {{
    const isFamily = row.classList.contains('family');
    if (mode === 'all') row.style.display = '';
    else if (mode === 'family') row.style.display = isFamily ? '' : 'none';
    else if (mode === 'mine') row.style.display = isFamily ? 'none' : '';
  }});
  renumberVisible();
}}
renumberVisible();
</script>
</body>
</html>"""


def index_html(all_years):
    links = "\n    ".join('<a class="year" href="/%d/">%d</a>' % (y, y) for y in sorted(all_years))
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>Family Flight Archive</title>
<style>
  body { font-family: -apple-system, "Segoe UI", Arial, sans-serif; background:#f0f0f0; margin:0; padding:0; min-height:100vh; }
  .card { max-width:400px; margin:60px auto; background:#fff; padding:24px; border-radius:8px; border:1px solid #e0e0e0; color:#1a1a1a; }
  h2 { margin:0 0 16px; font-size:20px; }
  a.year { display:block; text-decoration:none; padding:10px 14px; border:1px solid #ddd; border-radius:6px; color:#1a56db; margin-bottom:8px; font-size:14px; }
</style>
</head>
<body>
<div class="card">
  <h2>Family Flight Archive</h2>
  """ + links + """
</div>
</body>
</html>"""


def files_map_for(rows):
    """{file_id: локальное имя} — как generate_site.download_missing_files (совпадающие имена -> _2, _3)."""
    m, used = {}, set()
    for r in rows:
        fid = extract_file_id(r.get("_href"))
        if not fid or fid in m:
            continue
        base = sanitize_filename(r.get("_name") or fid + ".pdf")
        name, n = base, 2
        while name in used:
            stem, ext = os.path.splitext(base)
            name = "%s_%d%s" % (stem, n, ext)
            n += 1
        used.add(name)
        m[fid] = name
    return m


def build_year(g, year, all_years):
    """Собирает HC/<год> локально. Возвращает (ok, сообщения)."""
    msgs = []
    ssid = g.sheet_id(year)
    if not ssid:
        return False, ["таблица flights_%d_from_archive не найдена" % year]
    rows = g.link_rows(ssid)
    fmap = files_map_for(rows)
    ydir = LOCAL_HC / str(year)
    fdir = ydir / ("%d_files" % year)
    fdir.mkdir(parents=True, exist_ok=True)

    def one(item):
        fid, name = item
        p = fdir / name
        if p.exists():
            return "skip", name
        try:
            data = g.download(fid)
            tmp = p.with_suffix(p.suffix + ".part")
            tmp.write_bytes(data)
            os.replace(tmp, p)
            return "new", name
        except Exception as e:  # noqa
            return "error", "%s: %s" % (name, e)
    stats = {"new": 0, "skip": 0, "error": 0}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for st, info in pool.map(one, list(fmap.items())):
            stats[st] += 1
            if st == "error":
                msgs.append("  ! " + info)
    msgs.append("  строк %d, файлов по ссылкам %d: скачано %d, уже было %d, ошибок %d"
                % (len(rows), len(fmap), stats["new"], stats["skip"], stats["error"]))
    if stats["error"]:
        return False, msgs
    # xlsx с относительными ссылками
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(g.export_xlsx(ssid)))
    ws = wb.active
    header = [c.value for c in ws[1]]
    col = header.index("Receipt Link") + 1 if "Receipt Link" in header else COL["Receipt Link"] + 1
    for i, r in enumerate(rows, start=2):
        if i > ws.max_row:
            break
        fid = extract_file_id(r.get("_href"))
        if fid and fid in fmap:
            ws.cell(row=i, column=col).hyperlink = "./%d_files/%s" % (year, fmap[fid])
    xlsx = ydir / ("%d.xlsx" % year)
    wb.save(xlsx)
    # zip: только xlsx + файлы, на которые есть ссылки
    zpath = ydir / ("%d_archive.zip" % year)
    tmpz = zpath.with_suffix(".zip.part")
    with zipfile.ZipFile(tmpz, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(xlsx, arcname=xlsx.name)
        for name in sorted(set(fmap.values())):
            zf.write(fdir / name, arcname="%d_files/%s" % (year, name))
    os.replace(tmpz, zpath)
    extra = sorted(p.name for p in fdir.iterdir() if p.is_file() and p.name not in set(fmap.values()))
    if extra:
        msgs.append("  в локальной папке %d файл(ов) без ссылки в таблице — в zip и на страницу НЕ попали" % len(extra))
    (ydir / "index.html").write_text(year_html(year, rows, fmap, all_years), encoding="utf-8")
    msgs.append("  zip %d байт, файлов в zip %d" % (zpath.stat().st_size, len(set(fmap.values()))))
    return True, msgs


def server_check():
    """v1.5: перед публикацией показать, на какой сервер идёт загрузка, и убедиться, что это тот сервер,
    куда указывает DNS, и что на нём есть папка сайта. Только чтение. Нет — публикация не начинается."""
    try:
        ip = socket.gethostbyname(SERVER_HOST)
    except OSError as e:
        print("❌ Имя %s не определяется (%s). Публикация не начата, годы остаются в очереди." % (SERVER_HOST, e))
        return False
    print("Публикация на %s -> %s" % (SERVER_HOST, ip))
    r = ssh("hostname -I; test -d %s && echo HC_FOLDER_OK" % REMOTE_HC_ROOT)
    out = (r.stdout or "")
    if r.returncode != 0:
        print("❌ Нет входа на сервер по ssh: %s" % (r.stderr.strip() or "код %s" % r.returncode))
        print("   Публикация не начата, на сайте ничего не изменено, годы остаются в очереди.")
        return False
    addrs = [w for w in out.split() if w != "HC_FOLDER_OK"]
    print("   сервер сообщает свои адреса: %s" % " ".join(addrs[:4]))
    if ip not in addrs:
        print("   ℹ️ Адрес из DNS не найден среди адресов сервера (так бывает, если публичный адрес за NAT) — сверьте с ожидаемым сервером.")
    if "HC_FOLDER_OK" not in out:
        print("❌ На сервере %s нет папки %s. Остановлено, ничего не залито." % (ip, REMOTE_HC_ROOT))
        return False
    if ip in addrs:
        print("✅ Сервер подтверждён: адрес совпадает с DNS, папка %s есть." % REMOTE_HC_ROOT)
    else:
        print("✅ Сервер доступен, папка %s есть (адрес сверьте, см. выше)." % REMOTE_HC_ROOT)
    return True


def publish(g, years):
    """Собрать и залить указанные годы, проверить сайт, сделать копию сайта на сервере."""
    if not server_check():
        return False
    all_years = sorted(set(g.year_sheets()) | set(years))
    LOCAL_HC.mkdir(parents=True, exist_ok=True)
    (LOCAL_HC / "index.html").write_text(index_html(all_years), encoding="utf-8")
    ok_all = True
    for y in years:
        print("\n=== %d ===" % y)
        ok, msgs = build_year(g, y, all_years)
        print("\n".join(msgs))
        if not ok:
            print("  ❌ %d не собран — на сервер не заливается." % y)
            ok_all = False
            continue
        ydir = LOCAL_HC / str(y)
        r = ssh("mkdir -p %s/%d" % (REMOTE_HC_ROOT, y))
        errs = [] if r.returncode == 0 else ["mkdir: " + r.stderr.strip()]
        for local, remote in ((ydir / "index.html", "%s/%d/" % (REMOTE_HC_ROOT, y)),
                              (ydir / ("%d.xlsx" % y), "%s/%d/" % (REMOTE_HC_ROOT, y)),
                              (ydir / ("%d_archive.zip" % y), "%s/%d/" % (REMOTE_HC_ROOT, y)),
                              (ydir / ("%d_files" % y), "%s/%d/" % (REMOTE_HC_ROOT, y))):
            r = scp(local, remote)
            if r.returncode != 0:
                errs.append("%s: %s" % (local.name, r.stderr.strip()))
        codes = {u: http_code(SITE_BASE + u) for u in ("/%d/" % y, "/%d/%d_archive.zip" % (y, y))}
        for u, c in codes.items():
            print("  %s -> %s" % (u, c))
        if errs or any(c != "200" for c in codes.values()):
            print("  ❌ ошибки: " + "; ".join(errs) if errs else "  ❌ сайт ответил не 200")
            ok_all = False
        else:
            print("  ✅ %d на сайте." % y)
    # главная и переключатель годов на страницах остальных лет
    r = scp(LOCAL_HC / "index.html", REMOTE_HC_ROOT + "/")
    if r.returncode != 0:
        print("  ❌ главная страница: " + r.stderr.strip())
        ok_all = False
    for y in all_years:
        if y in years:
            continue
        p = LOCAL_HC / str(y) / "index.html"
        if p.exists():
            content = p.read_text(encoding="utf-8")
            new = re.sub(r'<a href="/">← All years</a>.*?(?=\n  </div>\n\n  <div class="filters">)',
                         '<a href="/">← All years</a>\n    ' + year_links(all_years, y), content, flags=re.DOTALL)
            if new != content:
                p.write_text(new, encoding="utf-8")
                r = scp(p, "%s/%d/" % (REMOTE_HC_ROOT, y))
                if r.returncode != 0:
                    print("  ❌ переключатель %d: %s" % (y, r.stderr.strip()))
                    ok_all = False
    code = http_code(SITE_BASE + "/")
    print("  / -> %s" % code)
    ok_all = ok_all and code == "200"
    if not ok_all:
        print("\n⚠️ Публикация с ошибками — копия сайта НЕ запускается. Годы остаются в списке изменённых.")
        return False
    print("\n💾 Копия сайта на сервере...")
    r = ssh("systemctl cat %s >/dev/null 2>&1 || { echo NOT_INSTALLED; exit 0; }; "
            "T=$(date +%%s); systemctl start %s; RC=$?; "
            "journalctl -u %s --since @$T -o cat --no-pager | grep -E '^(FLIGHTS_|UPLOAD (confirm|RESULT))' | tail -5; "
            "echo SERVICE_EXIT=$RC" % (BACKUP_SERVICE, BACKUP_SERVICE, BACKUP_SERVICE))
    out = (r.stdout or "").strip()
    print("  " + out.replace("\n", "\n  "))
    if "NOT_INSTALLED" in out:
        print("  ℹ️ Копия сайта на сервере ещё не настроена (этап 5, шаг 3). Сайт обновлён.")
    elif "FLIGHTS_OK" not in out:
        print("  ⚠️ Копия сайта не подтверждена — сообщите Claude.")
    return True


# =============================================================== actions

def read_json_block():
    print("\nВставьте JSON и нажмите Enter на пустой строке:")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line == "" and lines:
            break
        lines.append(line)
    return "\n".join(lines)


def pick_files():
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.attributes("-topmost", True)
    root.withdraw()
    paths = filedialog.askopenfilenames(title="PDF билета или фото/скриншоты ОДНОЙ брони",
                                        filetypes=[("PDF и изображения", "*.pdf *.jpg *.jpeg *.png"), ("Все", "*.*")])
    root.destroy()
    return list(paths)


def to_single_pdf(paths):
    """Один PDF → как есть. Изображения одной брони → один PDF (правило: фото всегда в PDF)."""
    pdfs = [p for p in paths if p.lower().endswith(".pdf")]
    imgs = [p for p in paths if p.lower().endswith((".jpg", ".jpeg", ".png"))]
    if pdfs and (len(pdfs) > 1 or imgs):
        raise ValueError("нужен ОДИН PDF или только изображения одной брони")
    if pdfs:
        return pdfs[0], None
    if not imgs:
        raise ValueError("файл не выбран")
    from PIL import Image
    pages = [Image.open(p).convert("RGB") for p in imgs]
    out = Path(tempfile.mkstemp(suffix=".pdf")[1])
    pages[0].save(out, "PDF", save_all=True, append_images=pages[1:])
    return str(out), out


def edit_in_notepad(text):
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    if os.name == "nt":
        subprocess.run(["notepad", path])
    else:
        input("Отредактируйте файл %s и нажмите Enter..." % path)
    text = Path(path).read_text(encoding="utf-8")
    os.unlink(path)
    return text


def verify_part(g, part, file_id, folder_id):
    """Проверка после записи: таблица <-> файл на Диске. Возвращает список ошибок."""
    errs = []
    rows = [r for r in g.link_rows(part["ssid"]) if extract_file_id(r.get("_href")) == file_id]
    if len(rows) < len(part["rows"]):
        errs.append("в таблице найдено строк со ссылкой на файл %d, ожидалось %d" % (len(rows), len(part["rows"])))
    bad_text = [r.get("_name") for r in rows if r.get("_name") != part["file_name"]]
    if bad_text:
        errs.append("текст ссылки в таблице не равен имени файла: %s" % bad_text[:2])
    try:
        m = g.file_meta(file_id)
    except Exception as e:  # noqa
        return errs + ["файл по ссылке не найден на Диске: %s" % e]
    if m.get("name") != part["file_name"]:
        errs.append("имя файла на Диске %r не равно имени в таблице %r" % (m.get("name"), part["file_name"]))
    if m.get("mimeType") != "application/pdf":
        errs.append("файл не PDF (%s)" % m.get("mimeType"))
    if m.get("trashed"):
        errs.append("файл в корзине")
    if folder_id not in (m.get("parents") or []):
        errs.append("файл не в папке года %d" % part["year"])
    try:
        head = g.download(file_id)[:5]
        if head != b"%PDF-":
            errs.append("файл открывается, но это не PDF (начало %r)" % head)
    except Exception as e:  # noqa
        errs.append("файл не открывается (скачивание не удалось: %s)" % e)
    return errs


def add_flight(g):
    raw = read_json_block()
    while True:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            print("❌ Это не JSON: %s" % e)
            if input("Исправить в Блокноте? (да/нет): ").strip().lower() in ("да", "y", "yes"):
                raw = edit_in_notepad(raw)
                continue
            return
        errs = validate(data)
        if errs:
            print("❌ JSON не прошёл проверку, ничего не записано:")
            for e in errs:
                print("   - " + e)
            if input("Исправить в Блокноте? (да/нет): ").strip().lower() in ("да", "y", "yes"):
                raw = edit_in_notepad(json.dumps(data, ensure_ascii=False, indent=2))
                continue
            return
        confirm_timezones(data)
        plan, warnings = plan_booking(data)
        # дубли и места вставки
        dups, sheets_needed = [], []
        for part in plan:
            ssid = g.sheet_id(part["year"])
            part["ssid"] = ssid
            if not ssid:
                sheets_needed.append(part["year"])
                part["values"] = [HEADER]
                continue
            part["values"] = g.values(ssid)
            for row in part["rows"]:
                if is_duplicate(part["values"], row):
                    dups.append("%s %s %s %s" % (row["Travel Date"], row["Time Depart"], row["Flight Number"], row["Passenger Name"]))
        if dups:
            print("❌ Уже есть в таблице (дубль), ничего не записано:")
            for d in dups:
                print("   - " + d)
            return
        print("\n" + "=" * 70 + "\nПРЕВЬЮ — будет добавлено:")
        for part in plan:
            print("\n  Таблица flights_%d_from_archive%s, папка %d, файл:\n    %s"
                  % (part["year"], " (БУДЕТ СОЗДАНА)" if not part["ssid"] else "", part["year"], part["file_name"]))
            for r in part["rows"]:
                print("    %s %-5s %s -> %s  %-8s %-6s %s%s" % (r["Travel Date"], r["Time Depart"], r["From"], r["To"],
                      r["Flight Number"], r["Duration"] or "—", r["Passenger Name"],
                      "  [Family flight]" if r["Comment"] == "Family flight" else ""))
        print("\n  Часовые пояса:")
        shown = set()
        for seg in data["segments"]:
            for c in (normalize_city(seg["From"]), normalize_city(seg["To"])):
                if c not in shown:
                    shown.add(c)
                    tz, src = resolve_tz(c)
                    print("    %s -> %s (%s)" % (c, tz or "—", src))
        for w in warnings:
            print("  ⚠️ " + w)
        ans = input("\nЗаписать? (да / нет / править): ").strip().lower()
        if ans in ("править", "edit", "e"):
            raw = edit_in_notepad(json.dumps(data, ensure_ascii=False, indent=2))
            continue
        if ans not in ("да", "y", "yes"):
            print("Отмена, ничего не записано.")
            return
        break
    paths = pick_files()
    try:
        pdf, temp_pdf = to_single_pdf(paths)
    except ValueError as e:
        print("❌ " + str(e) + " — ничего не записано.")
        return
    except ImportError:
        print("❌ Для фото нужен Pillow: pip install pillow — ничего не записано.")
        return
    with open(pdf, "rb") as fh:
        if fh.read(5) != b"%PDF-":
            print("❌ Выбранный файл не PDF (нет заголовка %PDF) — ничего не записано.")
            return
    st = load_state()
    problems = []
    try:
        for part in plan:
            y = part["year"]
            if not part["ssid"]:
                print("🆕 Создаю таблицу flights_%d_from_archive..." % y)
                part["ssid"] = g.create_year_sheet(y)
                part["values"] = g.values(part["ssid"])
            folder = g.year_folder(y, create=True)
            existing = g.find_file(part["file_name"], folder)
            if existing:
                print("ℹ️ Файл уже есть в папке %d — повторно не загружается: %s" % (y, part["file_name"]))
                fid, url = existing["id"], existing.get("webViewLink")
            else:
                print("🚀 Загрузка в папку %d: %s" % (y, part["file_name"]))
                fid, url = g.upload(pdf, part["file_name"], folder)
            url = url or "https://drive.google.com/file/d/%s/view?usp=drivesdk" % fid
            at = insert_position(part["values"], part["rows"][0])
            g.insert_rows(part["ssid"], at, [row_cells(r, url, part["file_name"]) for r in part["rows"]])
            print("✅ %d: добавлено строк %d (с позиции %d)." % (y, len(part["rows"]), at))
            errs = verify_part(g, part, fid, folder)
            if errs:
                problems.append((y, errs))
                print("❌ %d: ПРОВЕРКА ПОСЛЕ ЗАПИСИ НЕ ПРОЙДЕНА:" % y)
                for e in errs:
                    print("     - " + e)
            else:
                print("✅ %d: проверено — в таблице %d строк(и) со ссылкой, текст ссылки = имя файла, файл на Диске "
                      "с тем же именем, PDF, в папке %d, открывается." % (y, len(part["rows"]), y))
            if y not in st["dirty_years"]:
                st["dirty_years"].append(y)
            st.setdefault("history", []).append({"t": datetime.now().isoformat(timespec="seconds"), "year": y,
                                                 "file": part["file_name"], "rows": len(part["rows"])})
            save_state(st)
    finally:
        if temp_pdf:
            try:
                os.unlink(temp_pdf)
            except OSError:
                pass
    if problems:
        print("⚠️ Есть ошибки проверки (выше) — сообщите Claude, сайт пока не обновляйте.")
    print("Годы с изменениями для сайта: %s (пункт 2 меню)." % sorted(st["dirty_years"]))


def check(g):
    """ТОЛЬКО ЧТЕНИЕ."""
    print("\n=== ПРОВЕРКА (только чтение) ===")
    sheets = g.year_sheets()
    print("Таблицы flights_<год>_from_archive: %s" % (", ".join(str(y) for y in sheets) or "нет"))
    for y, sid in sheets.items():
        if y in KNOWN_SPREADSHEET_IDS and KNOWN_SPREADSHEET_IDS[y] != sid:
            print("  ⚠️ %d: найдена таблица %s, а в программе записана %s" % (y, sid, KNOWN_SPREADSHEET_IDS[y]))
    server_counts = server_file_counts()
    if server_counts is None:
        print("  ⚠️ сервер: файлы на сервере не прочитаны")
        server_counts = {}
    total_bad = 0
    for y, sid in sheets.items():
        rows = g.link_rows(sid)
        fmap = files_map_for(rows)
        nolink = sum(1 for r in rows if not extract_file_id(r.get("_href")))
        folder = g.year_folder(y, create=False)

        def meta(fid):
            try:
                return g.file_meta(fid)
            except Exception:  # noqa
                return None
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            metas = list(pool.map(meta, list(fmap)))
        missing = sum(1 for m in metas if not m or m.get("trashed"))
        names = {fid: r.get("_name") for r in rows for fid in [extract_file_id(r.get("_href"))] if fid}
        name_bad = [fid for fid, m in zip(list(fmap), metas) if m and m.get("name") != names.get(fid)]
        not_pdf = sum(1 for m in metas if m and m.get("mimeType") != "application/pdf")
        in_year = sum(1 for m in metas if m and folder and folder in (m.get("parents") or []))
        in_root = sum(1 for m in metas if m and BASE_FOLDER_ID in (m.get("parents") or []))
        ldir = LOCAL_HC / str(y) / ("%d_files" % y)
        local = {p.name for p in ldir.iterdir() if p.is_file()} if ldir.exists() else set()
        need = set(fmap.values())
        total_bad += missing + len(name_bad) + not_pdf
        print("  %d: строк %d (без ссылки %d), файлов %d: недоступно %d, имя в таблице != имя на Диске %d, не PDF %d | "
              "в папке %s %d, в корне %d | локально: нет %d, лишних %d | на сервере файлов %s"
              % (y, len(rows), nolink, len(fmap), missing, len(name_bad), not_pdf, y if folder else "(нет папки)",
                 in_year, in_root, len(need - local), len(local - need), server_counts.get(str(y), "?")))
        for fid in name_bad[:5]:
            m = metas[list(fmap).index(fid)]
            print("      ! таблица: %s | Диск: %s" % (names.get(fid), m.get("name")))
    print("Сайт / -> %s" % http_code(SITE_BASE + "/"))
    print_site_vs_table(site_vs_table(g))
    if UPLOAD_TOKEN_FILE.exists():
        age = (datetime.now() - datetime.fromtimestamp(UPLOAD_TOKEN_FILE.stat().st_mtime)).days
        print("Вход для загрузки: токен есть, обновлён %d дн. назад (при истечении программа сама откроет вход)" % age)
    else:
        print("Вход для загрузки: токена нет (при первой загрузке откроется вход через браузер)")
    print("Копия сайта на сервере: %s" % ("настроена" if ssh("systemctl cat %s >/dev/null 2>&1" % BACKUP_SERVICE).returncode == 0
                                         else "ещё не настроена"))
    print("Изменённые годы (ждут публикации): %s" % (sorted(load_state()["dirty_years"]) or "нет"))
    print("ИТОГ: %s" % ("✅ все файлы доступны, имена совпадают, все PDF" if not total_bad
                        else "⚠️ проблем с файлами: %d (подробности выше)" % total_bad))


def upload_test(g):
    y = date.today().year
    folder = g.year_folder(y, create=False)
    if not folder:
        print("Папки %d нет — тест на корневой папке не делаю (создавать папку ради теста не буду)." % y)
        return
    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.write(fd, b"%PDF-1.4\n% flights.py upload test\n")
    os.close(fd)
    name = "_flights_upload_test_%s.pdf" % datetime.now().strftime("%Y%m%d%H%M%S")
    try:
        fid, _ = g.upload(path, name, folder)
        print("✅ Загрузка в папку %d работает (файл %s создан)." % (y, name))
        g.user()["drive"].files().update(fileId=fid, body={"trashed": True}).execute()
        print("✅ Тестовый файл удалён в корзину.")
    except Exception as e:  # noqa
        print("❌ Загрузка в папку %d НЕ работает: %s" % (y, e))
    finally:
        os.unlink(path)


RECORDS_RE = re.compile(r'class="count">\s*(\d+)\s+records')


def parse_site_records(html):
    """Число «N records» со страницы года на сайте или None."""
    m = RECORDS_RE.search(html or "")
    return int(m.group(1)) if m else None


def classify_year(table_rows, site_rows, table_files, server_files):
    """v1.6. site_rows: число | "missing" (страницы нет) | None (не удалось прочитать).
    server_files: число | None (сервер не ответил). Возвращает (статус, причины):
    ok | plus (в таблице больше, чем на сайте — публиковать) | minus (на сайте больше — искать потерю) | unknown."""
    plus, minus, info = [], [], []
    if site_rows is None:
        return "unknown", ["страницу года на сайте прочитать не удалось"]
    if site_rows == "missing":
        if table_rows > 0:
            plus.append("страницы года нет на сайте, а в таблице %d строк" % table_rows)
    else:
        if site_rows < table_rows:
            plus.append("строк: в таблице %d, на сайте %d" % (table_rows, site_rows))
        elif site_rows > table_rows:
            minus.append("строк: в таблице %d, на сайте %d" % (table_rows, site_rows))
    if server_files is not None:
        if server_files < table_files:
            plus.append("файлов: по ссылкам таблицы %d, на сервере %d" % (table_files, server_files))
        elif server_files > table_files:
            info.append("на сервере файлов больше (%d, по ссылкам %d) — старые имена, не удаляются" % (server_files, table_files))
    if minus:
        return "minus", minus + plus + info
    if plus:
        return "plus", plus + info
    return "ok", info


SERVER_COUNT_CMD = "cd %s && for d in 20[0-9][0-9]; do printf '%%s %%s\\n' $d $(ls $d/${d}_files 2>/dev/null | wc -l); done" % REMOTE_HC_ROOT


def server_file_counts():
    """{год(str): число файлов} или None, если сервер не ответил."""
    r = ssh(SERVER_COUNT_CMD)
    if r.returncode != 0:
        return None
    return dict(l.split() for l in (r.stdout or "").splitlines() if len(l.split()) == 2)


def site_vs_table(g):
    """v1.6, ТОЛЬКО ЧТЕНИЕ: сверка каждого года таблицы с сайтом."""
    counts = server_file_counts()
    res = []
    for y, sid in sorted(g.year_sheets().items()):
        rows = g.link_rows(sid)
        fmap = files_map_for(rows)
        code, text = http_get("%s/%d/" % (SITE_BASE, y))
        if code == "200":
            site_rows = parse_site_records(text)
        elif code == "404":
            site_rows = "missing"
        else:
            site_rows = None
        sf = None if counts is None else int(counts.get(str(y), 0))
        st, why = classify_year(len(rows), site_rows, len(fmap), sf)
        res.append({"year": y, "table_rows": len(rows), "site_rows": site_rows, "table_files": len(fmap),
                    "server_files": sf, "status": st, "why": why})
    return res


def print_site_vs_table(res):
    print("\nСверка таблиц с сайтом (строки: таблица / сайт, файлы: по ссылкам / на сервере):")
    for r in res:
        sr = "нет страницы" if r["site_rows"] == "missing" else ("?" if r["site_rows"] is None else r["site_rows"])
        sf = "?" if r["server_files"] is None else r["server_files"]
        mark = {"ok": "✅", "plus": "⬆️ ПЛЮС в таблице — на сайт добавить", "minus": "❌ МИНУС в таблице — искать потерю",
                "unknown": "⚠️ не проверено"}[r["status"]]
        print("  %d: строк %s / %s, файлов %s / %s  %s" % (r["year"], r["table_rows"], sr, r["table_files"], sf, mark))
        if r["status"] != "ok":
            for w in r["why"]:
                print("       - " + w)


def update_dirty(g):
    """Меню 2 / BAT 2. v1.6: сначала сверка таблиц с сайтом; годы с ПЛЮСОМ добавляются в очередь сами;
    годы с МИНУСОМ не публикуются (нужно найти потерю)."""
    if not server_check():
        return
    res = site_vs_table(g)
    print_site_vs_table(res)
    st = load_state()
    dirty = set(st.get("dirty_years", []))
    minus = sorted(r["year"] for r in res if r["status"] == "minus")
    added = sorted(r["year"] for r in res if r["status"] == "plus" and r["year"] not in dirty)
    if added:
        print("\nГоды добавлены в очередь по результату сверки: %s" % added)
        dirty |= set(added)
        st["dirty_years"] = sorted(dirty)
        save_state(st)
    if minus:
        print("\n❌ На сайте больше, чем в таблице: %s. Публикация этих лет НЕ предлагается — сайт повторил бы потерю." % minus)
        print("   Пришлите этот вывод Claude: нужно найти, какие строки пропали из таблицы, и восстановить их.")
    todo = sorted(dirty - set(minus))
    if not todo:
        print("\nИзменённых годов нет, сайт совпадает с таблицами." if not minus else "\nПубликовать нечего.")
        return
    if input("\nОбновить сайт для %s и залить на сервер? (да/нет): " % todo).strip().lower() in ("да", "y", "yes"):
        if publish(g, todo):
            st = load_state()
            st["dirty_years"] = [y for y in st.get("dirty_years", []) if y not in todo]
            st.setdefault("history", []).append({"t": datetime.now().isoformat(timespec="seconds"), "published": todo})
            save_state(st)


def main():
    if sys.version_info < (3, 9):
        raise SystemExit("Нужен Python 3.9+")
    g = Google()
    # v1.5: запуск из BAT-файлов — один пункт меню и выход (flights.py add | flights.py upload)
    if len(sys.argv) > 1:
        if sys.argv[1] == "add":
            add_flight(g)
        elif sys.argv[1] == "upload":
            update_dirty(g)
        else:
            raise SystemExit("Неизвестный аргумент: %s (допустимо: add, upload)" % sys.argv[1])
        return
    while True:
        st = load_state()
        dirty = sorted(st.get("dirty_years", []))
        print("\n" + "=" * 60)
        print("  flights.py v%s — архив перелётов" % VERSION)
        print("=" * 60)
        print("  1) Добавить перелёт (JSON + файл)")
        print("  2) Обновить сайт: изменённые годы %s" % (dirty or "(нет)"))
        print("  3) Обновить сайт: выбрать год")
        print("  4) Проверка (только чтение)")
        print("  5) Тест загрузки в папку года")
        print("  0) Выход")
        c = input("Выбор: ").strip()
        if c == "0":
            break
        elif c == "1":
            add_flight(g)
        elif c == "2":
            update_dirty(g)
        elif c == "3":
            raw = input("Год: ").strip()
            if raw.isdigit() and int(raw) >= FIRST_YEAR:
                y = int(raw)
                if input("Обновить %d и залить на сервер? (да/нет): " % y).strip().lower() in ("да", "y", "yes"):
                    if publish(g, [y]):
                        st = load_state()
                        st["dirty_years"] = [d for d in st["dirty_years"] if d != y]
                        save_state(st)
        elif c == "4":
            check(g)
        elif c == "5":
            upload_test(g)


if __name__ == "__main__":
    main()
