#!/usr/bin/env python3
"""Offline test of flights.py: no Google, no server. Run: python3 -I app/tests/test_flights.py"""
import builtins, importlib.util, io, json, os, sys, tempfile, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("flights", HERE.parent / "flights.py")
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)
F._GEO = False                                   # deterministic: no city database unless a test sets one
F.LOCAL_TZ_FILE = Path(tempfile.mkdtemp()) / "city_timezones_local.json"

fails = 0
def check(cond, msg):
    global fails
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        fails += 1

CANON = {
    "segments": [{"Travel Date": "2026-01-09", "Time Depart": "13:55", "From": "Stavropol", "To": "Moscow (Sheremetyevo)",
                  "Arrival Date": "2026-01-09", "Time Arrival": "17:15", "Flight Number": "SU1367"}],
    "passengers": [{"Passenger Name": "Rodionov Aleksei", "Ticket Number": "5552376681192"}],
    "Carrier": "Aeroflot", "Original Amount": "323.50", "Currency": "USD", "Issue Date": "2025-12-30",
    "PNR": "89GG62", "OTA Order ID": "", "Category": "Flight", "Vendor/App": "Aeroflot (direct airline sale)", "Comment": ""}

# ---------------- validation
check(F.validate(CANON) == [], "V1 canonical JSON is valid")
def bad(mod, needle, label):
    d = json.loads(json.dumps(CANON)); mod(d)
    e = F.validate(d)
    check(any(needle in x for x in e), "%s -> %s" % (label, [x for x in e if needle in x][:1] or e))
bad(lambda d: d.__setitem__("Carrier", "Аэрофлот"), "кириллица", "V2 Cyrillic rejected")
bad(lambda d: d.__setitem__("USD Value", "1"), "лишние ключи", "V3 USD Value rejected")
bad(lambda d: d.__setitem__("passengers", ["Rodionov Aleksei"]), "должен быть объектом", "V4 passenger as string rejected")
bad(lambda d: d["segments"][0].__setitem__("Travel Date", ""), "Travel Date", "V5 empty Travel Date rejected")
bad(lambda d: d["passengers"][0].__setitem__("Passenger Name", "ALEXEY RODIONOV"), "не из списка", "V6 wrong name format rejected")
bad(lambda d: d["passengers"][0].__setitem__("Passenger Name", "Xu Wei"), "не из списка", "V7 untracked passenger rejected")
bad(lambda d: d.__setitem__("booking", {}), "лишние ключи", "V8 nested wrapper rejected")
bad(lambda d: d.pop("Vendor/App"), "нет ключей", "V9 missing Vendor/App rejected")
bad(lambda d: d["segments"][0].__setitem__("Time Depart", "1355"), "Time Depart", "V10 bad time rejected")
bad(lambda d: d.__setitem__("Comment", "confirmed directly from document"), "Comment", "V11 explanatory Comment rejected")
bad(lambda d: d.__setitem__("Category", "Bus"), "Category", "V12 unknown Category rejected")

# ---------------- plan
plan, warn = F.plan_booking(CANON)
check(len(plan) == 1 and plan[0]["year"] == 2026, "P1 one year part")
check(plan[0]["file_name"] == "2026_09-01_Stavropol-Moscow_RodionovAleksei-89GG62.pdf", "P2 file name scheme: " + plan[0]["file_name"])
r = plan[0]["rows"][0]
check(r["To"] == "Moscow" and r["Duration"] == "3:20" and r["Comment"] == "" and r["OTA Order ID"] == F.STATUS_OK,
      "P3 city normalized, Duration 3:20, Comment empty, W = status (%s, %s)" % (r["To"], r["Duration"]))
fam = json.loads(json.dumps(CANON))
fam["passengers"].append({"Passenger Name": "Rodionova Anna", "Ticket Number": "1"})
fam["segments"][0]["Time Depart"] = "06:00"   # not the same as the row already in the sheet
fam["segments"].append({"Travel Date": "2026-12-31", "Time Depart": "23:00", "From": "Moscow", "To": "Tel Aviv (Ben Gurion)",
                        "Arrival Date": "2027-01-01", "Time Arrival": "03:10", "Flight Number": "SU508"})
fam["segments"].append({"Travel Date": "2027-01-05", "Time Depart": "10:00", "From": "Tel Aviv", "To": "Atlantis",
                        "Arrival Date": "", "Time Arrival": "", "Flight Number": "XX1"})
plan2, warn2 = F.plan_booking(fam)
check([p["year"] for p in plan2] == [2026, 2027], "P4 booking split by year: %s" % [p["year"] for p in plan2])
check(plan2[0]["file_name"] == "2026_09-01_Stavropol-Moscow_31-12_Moscow-TelAviv_RodionovAleksei-RodionovaAnna-89GG62.pdf"
      and plan2[1]["file_name"] == "2027_05-01_TelAviv-Atlantis_RodionovAleksei-RodionovaAnna-89GG62.pdf",
      "P5 per-year file names: %s | %s" % (plan2[0]["file_name"], plan2[1]["file_name"]))
check([x["Comment"] for x in plan2[0]["rows"]] == ["", "Family flight", "", "Family flight"], "P6 Family flight only for Anna rows, order seg->pax")
mt = [x for x in plan2[0]["rows"] if x["Flight Number"] == "SU508"][0]
check(mt["Duration"] == "5:10", "P7 Duration across time zones and midnight (MSK UTC+3 23:00 -> IL UTC+2 03:10 = 5:10): %s" % mt["Duration"])
check(any("Atlantis" in w for w in warn2) and plan2[1]["rows"][0]["Duration"] == "", "P8 unknown city -> warning, Duration empty")

# ---------------- cells, duplicates, position
cells = F.row_cells(r, "https://drive.google.com/file/d/ABCDEFGHIJKLMNOPQRSTUV/view", plan[0]["file_name"])
check(cells[F.COL["Travel Date"]]["userEnteredValue"]["numberValue"] == 46031 and
      cells[F.COL["Duration"]]["userEnteredValue"]["stringValue"] == "3:20" and
      cells[F.COL["Ticket Number"]]["userEnteredValue"]["stringValue"] == "5552376681192" and
      cells[F.COL["Receipt Link"]]["textFormatRuns"][0]["format"]["link"]["uri"].endswith("/view") and
      "Comment" not in json.dumps(cells[F.COL["Comment"]]), "C1 cells: date serial, Duration text, ticket text, link, empty Comment")
values = [F.HEADER,
          ["Flight", "05.01.2026", "10:00", "A", "B", "", "", "XX1"] + [""] * 11 + ["Rodionov Aleksei"],
          ["Flight", "09.01.2026", "13:55", "Stavropol", "Moscow", "", "", "SU 1367"] + [""] * 11 + ["Rodionov Aleksei"],
          ["Flight", "20.02.2026", "08:00", "A", "B", "", "", "XX2"] + [""] * 11 + ["Rodionova Anna"]]
check(F.is_duplicate(values, r), "D1 same passenger+flight+date+time = duplicate (flight number with space)")
r2 = dict(r, **{"Time Depart": "14:00"})
check(not F.is_duplicate(values, r2), "D2 other time = not duplicate")
check(F.insert_position(values, r2) == 4, "D3 insert before first later row (row 4)")
check(F.insert_position(values, dict(r, **{"Travel Date": "2026-12-01"})) == 5, "D4 latest -> append at end")

# ---------------- fake Google + full add / publish / check
TMP = Path(tempfile.mkdtemp())
F.STATE_FILE = TMP / "state.json"
F.LOCAL_HC = TMP / "HC"
F.SITE_AUTH_FILE = TMP / "site_auth.json"
F.SITE_AUTH_FILE.write_text('{"user":"u","password":"p"}')

class FakeGoogle:
    def __init__(self):
        self.sheets_data = {2026: [list(x) for x in values]}
        self.links = {2026: []}
        self.folders = {2026: "fold2026"}
        self.files = {}   # (folder, name) -> id
        self.uploaded, self.created_sheets, self.inserted = [], [], []
        self.meta, self.content = {}, {}
        self.drive = None
    def year_sheets(self): return {y: "ss%d" % y for y in sorted(self.sheets_data)}
    def sheet_id(self, y): return "ss%d" % y if y in self.sheets_data else None
    def values(self, ssid): return self.sheets_data[int(ssid[2:])]
    def create_year_sheet(self, y):
        self.created_sheets.append(y); self.sheets_data[y] = [list(F.HEADER)]; self.links[y] = []; return "ss%d" % y
    def year_folder(self, y, create):
        if y not in self.folders and create: self.folders[y] = "fold%d" % y
        return self.folders.get(y)
    def find_file(self, name, folder):
        i = self.files.get((folder, name)); return {"id": i, "webViewLink": "https://drive.google.com/file/d/%s/view" % i} if i else None
    def upload(self, path, name, folder):
        i = "F%021d" % (len(self.files) + 1); self.files[(folder, name)] = i; self.uploaded.append((folder, name, Path(path).read_bytes()[:5]))
        self.meta[i] = {"id": i, "name": name, "mimeType": "application/pdf", "parents": [folder], "trashed": False}
        self.content[i] = Path(path).read_bytes()
        return i, "https://drive.google.com/file/d/%s/view?usp=drivesdk" % i
    def insert_rows(self, ssid, at, cell_rows):
        y = int(ssid[2:]); self.inserted.append((y, at, len(cell_rows)))
        for k, c in enumerate(cell_rows):
            row = [""] * F.TOTAL_COLS
            from datetime import date, timedelta
            def sv(col): return (c[F.COL[col]].get("userEnteredValue") or {})
            row[F.COL["Travel Date"]] = (date(1899, 12, 30) + timedelta(days=int(sv("Travel Date")["numberValue"]))).strftime("%d.%m.%Y")
            if "numberValue" in sv("Time Depart"):
                m = round(sv("Time Depart")["numberValue"] * 1440); row[F.COL["Time Depart"]] = "%02d:%02d" % divmod(m, 60)
            row[F.COL["Flight Number"]] = sv("Flight Number").get("stringValue", "")
            row[F.COL["Passenger Name"]] = sv("Passenger Name").get("stringValue", "")
            self.sheets_data[y].insert(at - 1 + k, row)
            href = c[F.COL["Receipt Link"]]["textFormatRuns"][0]["format"]["link"]["uri"]
            name = c[F.COL["Receipt Link"]]["userEnteredValue"]["stringValue"]
            rec = {h: "" for h in F.HEADER}
            rec.update({"Category": c[0]["userEnteredValue"]["stringValue"], "Travel Date": "d", "From": "A", "To": "B",
                        "Passenger Name": c[F.COL["Passenger Name"]]["userEnteredValue"]["stringValue"],
                        "Comment": (c[F.COL["Comment"]].get("userEnteredValue") or {}).get("stringValue", ""),
                        "_href": href, "_name": name})
            self.links[y].append(rec)
    def link_rows(self, ssid): return self.links[int(ssid[2:])]
    def download(self, fid): return self.content.get(fid, b"%PDF-" + fid.encode())
    def file_meta(self, fid):
        return self.meta.get(fid) or {"id": fid, "name": None, "mimeType": "application/pdf", "parents": ["fold2026"], "trashed": False}
    def export_xlsx(self, ssid):
        import openpyxl
        wb = openpyxl.Workbook(); ws = wb.active; ws.append(F.HEADER)
        for r in self.links[int(ssid[2:])]: ws.append([r.get(h, "") for h in F.HEADER])
        b = io.BytesIO(); wb.save(b); return b.getvalue()

pdf = TMP / "ticket.pdf"; pdf.write_bytes(b"%PDF-1.4 test ticket")
g = FakeGoogle()
calls = []
class R:
    def __init__(self, rc=0, out="", err=""): self.returncode, self.stdout, self.stderr = rc, out, err
SERVER_LS = "2026 2\n"
def fake_run(cmd):
    calls.append(cmd)
    if cmd[0] == "ssh" and "systemctl cat" in cmd[-1] and "journalctl" in cmd[-1]:
        return R(0, "FLIGHTS_OK site copy confirmed\nSERVICE_EXIT=0\n")
    if cmd[0] == "ssh" and "hostname -I" in cmd[-1]:
        return R(0, "88.216.61.42\nHC_FOLDER_OK\n")
    if cmd[0] == "ssh" and "ls $d" in cmd[-1]:
        return R(0, SERVER_LS)
    return R(0)
F.run = fake_run
F.socket.gethostbyname = lambda h: "88.216.61.42"   # v1.5 server_check
F.http_code = lambda url: "200"
SITE_OVERRIDE = {}
def fake_http_get(url):
    y = int(url.rstrip("/").split("/")[-1])
    n = SITE_OVERRIDE.get(y, len(g.links.get(y, [])))
    if n == "404":
        return ("404", "")
    return ("200", '<p class="count">%s records</p>' % n)
F.http_get = fake_http_get
F.pick_files = lambda: [str(pdf)]
answers = []
builtins.input = lambda prompt="": answers.pop(0)

# add canonical (2026, not duplicate because time differs)
c1 = json.loads(json.dumps(CANON)); c1["segments"][0]["Time Depart"] = "14:05"; c1["segments"][0]["Time Arrival"] = "17:25"
answers[:] = json.dumps(c1, indent=1).splitlines() + ["", "да"]
F.add_flight(g)
check(g.inserted == [(2026, 4, 1)] and g.uploaded[0][0] == "fold2026", "A1 added 1 row at position 4, file into year folder")
check(json.loads(F.STATE_FILE.read_text())["dirty_years"] == [2026], "A2 year 2026 marked as changed")
part = {"year": 2026, "ssid": "ss2026", "file_name": g.uploaded[0][1], "rows": [1]}
fid1 = g.files[("fold2026", g.uploaded[0][1])]
check(F.verify_part(g, part, fid1, "fold2026") == [], "A10 post-write check passes: link text = file name, file on Drive, PDF, year folder, opens")
g.meta[fid1]["name"] = "renamed.pdf"
e = F.verify_part(g, part, fid1, "fold2026")
check(any("имя файла на Диске" in x for x in e), "A11 name on Drive differs -> check fails: %s" % e[:1])
g.meta[fid1]["name"] = g.uploaded[0][1]
g.content[fid1] = b"JFIF...."
e = F.verify_part(g, part, fid1, "fold2026")
check(any("не PDF" in x for x in e), "A12 content not PDF -> check fails: %s" % e[:1])
g.content[fid1] = b"%PDF-1.4"
jpg = TMP / "fake.pdf"; jpg.write_bytes(b"\xff\xd8\xff JPEG renamed")
F.pick_files = lambda: [str(jpg)]
c3 = json.loads(json.dumps(CANON)); c3["segments"][0]["Time Depart"] = "18:00"
answers[:] = json.dumps(c3).splitlines() + ["", "да"]
n0 = len(g.uploaded); F.add_flight(g)
check(len(g.uploaded) == n0, "A13 file without %PDF header refused before upload")
F.pick_files = lambda: [str(pdf)]
# duplicate is refused
answers[:] = json.dumps(c1).splitlines() + [""]
n_before = len(g.inserted)
F.add_flight(g)
check(len(g.inserted) == n_before, "A3 duplicate refused, nothing inserted")
# invalid JSON -> refused (answer 'нет' to edit)
answers[:] = ['{"segments": []}', "", "нет"]
F.add_flight(g)
check(len(g.inserted) == n_before, "A4 invalid JSON refused, nothing inserted")
# booking 2026 -> 2027: new year sheet + folder auto
answers[:] = json.dumps(fam).splitlines() + ["", "", "да"]   # 2nd "": time zone of Atlantis -> leave empty
F.add_flight(g)
check(g.created_sheets == [2027] and "fold2027" in g.folders.values(), "A5 new year 2027: sheet and folder created")
check([(y, n) for y, at, n in g.inserted[-2:]] == [(2026, 4), (2027, 2)], "A6 rows into both years (4 + 2)")
check(sorted(json.loads(F.STATE_FILE.read_text())["dirty_years"]) == [2026, 2027], "A7 dirty years 2026, 2027")
# images -> one PDF
from PIL import Image
imgs = []
for i in range(2):
    p = TMP / ("s%d.png" % i); Image.new("RGB", (60, 80), (200, i * 90, 30)).save(p); imgs.append(str(p))
out, tmpf = F.to_single_pdf(imgs)
check(Path(out).read_bytes()[:5] == b"%PDF-" and tmpf is not None, "A8 two screenshots -> one PDF")
try:
    F.to_single_pdf([str(pdf), imgs[0]]); check(False, "A9 mix PDF+image refused")
except ValueError:
    check(True, "A9 mix PDF+image refused")

# publish both years
(F.LOCAL_HC / "2026" / "2026_files").mkdir(parents=True, exist_ok=True)
(F.LOCAL_HC / "2026" / "2026_files" / "old_orphan.pdf").write_bytes(b"old")
calls.clear()
ok = F.publish(g, [2026, 2027])
z = zipfile.ZipFile(F.LOCAL_HC / "2026" / "2026_archive.zip")
names = z.namelist()
check(ok and "2026.xlsx" in names and not any("old_orphan" in n for n in names) and len(names) == 1 + len({r["_href"] for r in g.links[2026]}),
      "B1 publish ok; zip = xlsx + only referenced files (%d entries, orphan excluded)" % len(names))
html = (F.LOCAL_HC / "2027" / "index.html").read_text()
check('href="/2027/"' in html and "Flights 2027" in html and "2027_files/" in html, "B2 2027 page built with year switcher and file links")
check('href="/2027/"' in (F.LOCAL_HC / "index.html").read_text(), "B3 main page lists 2027")
check(any(c[0] == "scp" and c[-1].endswith("/root/HC/2027/") for c in calls), "B4 files sent to server /root/HC/2027/")
check(any(c[0] == "ssh" and "virlab-flights-backup.service" in c[-1] for c in calls), "B5 server site copy started after successful publish")
# publish refuses backup when site check fails
F.http_code = lambda url: "502"
calls.clear()
ok2 = F.publish(g, [2026])
check(not ok2 and not any("virlab-flights-backup" in c[-1] for c in calls if c[0] == "ssh"), "B6 site not 200 -> publish not OK, no site copy")
F.http_code = lambda url: "200"
# v1.5: server_check stops publication when ssh fails or /root/HC is missing
_old_run = F.run
n0 = len(calls)
F.run = lambda cmd: (calls.append(cmd) or R(255, "", "Permission denied")) if cmd[0] == "ssh" else _old_run(cmd)
ok3 = F.publish(g, [2026])
check(not ok3 and not any(c[0] == "scp" for c in calls[n0:]), "S1 no ssh login -> publish stopped before any upload")
F.run = lambda cmd: (calls.append(cmd) or R(0, "88.216.61.42\n")) if (cmd[0] == "ssh" and "hostname -I" in cmd[-1]) else _old_run(cmd)
n1 = len(calls)
ok4 = F.publish(g, [2026])
check(not ok4 and not any(c[0] == "scp" for c in calls[n1:]), "S2 no /root/HC on server -> publish stopped before any upload")
F.run = _old_run
check(F.SERVER_HOST == "archive.billup.cloud", "S3 server is addressed by name, not by IP")
# read-only check: no writes to Google, no scp
before = (len(g.inserted), len(g.uploaded), len(g.created_sheets))
calls.clear()
buf = io.StringIO(); old = sys.stdout; sys.stdout = buf
try:
    F.check(g)
finally:
    sys.stdout = old
outp = buf.getvalue()
check((len(g.inserted), len(g.uploaded), len(g.created_sheets)) == before and not any(c[0] == "scp" for c in calls),
      "K1 check is read-only (no inserts/uploads/scp)")
check("2026:" in outp and "Сайт / -> 200" in outp, "K2 check report printed")
check("имя в таблице != имя на Диске 0" in outp and "ИТОГ: ✅" in outp, "K3 check compares table names with Drive names and PDF type")
print("\n".join("    " + l for l in outp.splitlines()[:8]))
# ---------------- v1.6: site vs table comparison
check(F.parse_site_records('<p class="count">743 records</p>') == 743 and F.parse_site_records("<html></html>") is None,
      "C1 'N records' parsed from the year page")
cl = F.classify_year
check(cl(10, 10, 5, 5)[0] == "ok", "C2 equal rows and files -> ok")
check(cl(10, 7, 5, 5)[0] == "plus", "C3 site has fewer rows than table -> plus (publish)")
check(cl(10, 10, 5, 3)[0] == "plus", "C4 server has fewer files than table links -> plus")
check(cl(10, 12, 5, 5)[0] == "minus", "C5 site has MORE rows than table -> minus (do not publish)")
st_, why_ = cl(10, 10, 5, 9)
check(st_ == "ok" and any("старые имена" in w for w in why_), "C6 extra files on server -> info only, not an error")
check(cl(10, "missing", 5, 5)[0] == "plus" and cl(0, "missing", 0, 0)[0] == "ok", "C7 year page absent -> plus only if the table has rows")
check(cl(10, None, 5, 5)[0] == "unknown", "C8 page unreadable -> unknown, never auto-publish")
check(cl(10, 10, 5, None)[0] == "ok", "C9 server files unknown (no ssh answer) -> rows alone decide")
check(cl(10, 12, 5, 3)[0] == "minus", "C10 rows minus and files plus together -> minus wins (stop and investigate)")
# update_dirty end to end (fake site / fake server)
n26 = len(g.links[2026]); f26 = len(F.files_map_for(g.links[2026]))
n27 = len(g.links.get(2027, [])); f27 = len(F.files_map_for(g.links.get(2027, [])))
SERVER_LS = "2026 %d\n2027 %d\n" % (f26, f27)
SITE_OVERRIDE.clear(); SITE_OVERRIDE[2026] = n26 - 1
F.save_state({"dirty_years": [], "history": []})
calls.clear()
answers[:] = ["да"]
buf = io.StringIO(); old = sys.stdout; sys.stdout = buf
try:
    F.update_dirty(g)
finally:
    sys.stdout = old
o6 = buf.getvalue()
check("ПЛЮС" in o6 and "добавлены в очередь" in o6 and any(c[0] == "scp" and c[-1].endswith("/root/HC/2026/") for c in calls),
      "C11 empty queue but site has fewer rows than table -> year queued by itself and published")
check(F.load_state()["dirty_years"] == [], "C12 queue cleared after successful publish")
SITE_OVERRIDE[2026] = n26 + 1
calls.clear(); answers[:] = []
buf = io.StringIO(); sys.stdout = buf
try:
    F.update_dirty(g)
finally:
    sys.stdout = old
o7 = buf.getvalue()
check("МИНУС" in o7 and not any(c[0] == "scp" for c in calls), "C13 site has more rows than table -> warning, no publish, no question asked")
SITE_OVERRIDE.clear()
calls.clear(); answers[:] = []
buf = io.StringIO(); sys.stdout = buf
try:
    F.update_dirty(g)
finally:
    sys.stdout = old
check("Изменённых годов нет, сайт совпадает с таблицами" in buf.getvalue() and not any(c[0] == "scp" for c in calls),
      "C14 everything matches -> nothing to publish")
_old_run = F.run
F.run = lambda cmd: (calls.append(cmd) or R(255, "", "Permission denied")) if cmd[0] == "ssh" else _old_run(cmd)
calls.clear(); answers[:] = []
buf = io.StringIO(); sys.stdout = buf
try:
    F.update_dirty(g)
finally:
    sys.stdout = old
F.run = _old_run
check(not any(c[0] == "scp" for c in calls), "C15 no ssh -> stopped before comparing and publishing")
SERVER_LS = "2026 2\n"
# ---------------- time zones (v1.4)
RZD = {"segments": [{"Travel Date": "2026-10-06", "Time Depart": "14:40", "From": "Moscow", "To": "Ryazan",
                     "Arrival Date": "2026-10-06", "Time Arrival": "17:05", "Flight Number": "070"}],
       "passengers": [{"Passenger Name": "Rodionov Aleksei", "Ticket Number": "76965070033124"}],
       "Carrier": "RZD (FPK Moskovsky)", "Original Amount": "778.00", "Currency": "RUB", "Issue Date": "2026-10-06",
       "PNR": "", "OTA Order ID": "76965070033124", "Category": "Train", "Vendor/App": "RZD (direct sale)", "Comment": ""}
check(F.validate(RZD) == [], "Z0 Alex's RZD JSON 16.10 is valid")
_, wz = F.plan_booking(RZD)
check(any("geonamescache" in w for w in wz), "Z1 no city database installed -> warning says how to install: %s" % wz)
F._GEO = ({F.city_key("Ryazan’"): [("Ryazan’", "RU", 538962, "Europe/Moscow")],
           "tolyatti": [("Tolyatti", "RU", 702879, "Europe/Samara")],
           "springfield": [("Springfield", "US", 167000, "America/Chicago"), ("Springfield", "US", 155000, "America/New_York")]},
          {"stavropol": [("Tolyatti", "RU", 702879, "Europe/Samara")], "krakow": [("Kraków", "PL", 816614, "Europe/Warsaw")]})
pz, wz = F.plan_booking(RZD)
rz = pz[0]["rows"][0]
check(rz["Duration"] == "2:25" and not wz, "Z2 Ryazan found in city database (Ryazan’), Duration 14:40->17:05 = 2:25: %r %s" % (rz["Duration"], wz))
check(pz[0]["file_name"] == "2026_06-10_Moscow-Ryazan_RodionovAleksei.pdf", "Z3 file name: " + pz[0]["file_name"])
check(F.resolve_tz("Krakow")[0] == "Europe/Warsaw", "Z4 other spelling found (Krakow = Kraków)")
check(F.resolve_tz("Stavropol") == ("Europe/Moscow", "таблица программы"), "Z5 program table wins over database (Stavropol is not Tolyatti)")
check(F.resolve_tz("Ulyanovsk")[0] == "Europe/Ulyanovsk" and F.resolve_tz("Los Cabos")[0] == "America/Mazatlan",
      "Z6 corrected zones: Ulyanovsk UTC+4, Los Cabos America/Mazatlan")
tz, why = F.resolve_tz("Springfield")
check(tz is None and "разных поясах" in why, "Z7 same name in different zones -> not guessed: " + why[:60])
answers = iter(["Mars/Base", "2"])
buf = io.StringIO(); old = sys.stdout; sys.stdout = buf
try:
    F.confirm_timezones({"segments": [{"From": "Springfield", "To": "Moscow"}]}, ask=lambda _: next(answers))
finally:
    sys.stdout = old
check("Такого пояса нет" in buf.getvalue() and F.resolve_tz("Springfield") == ("America/New_York", "подтверждён Alex"),
      "Z8 wrong zone refused, choice 2 remembered in city_timezones_local.json")
buf = io.StringIO(); sys.stdout = buf
try:
    F.confirm_timezones({"segments": [{"From": "Atlantis", "To": "Ryazan"}]}, ask=lambda _: "")
finally:
    sys.stdout = old
check(F.resolve_tz("Atlantis")[0] is None and "Atlantis" not in F.load_local_tz(), "Z9 Enter -> nothing remembered, Duration stays empty")
print("RESULT " + ("ALL PASS" if not fails else "FAIL %d" % fails))
sys.exit(1 if fails else 0)
