import json, os, sys
try:
    from PyQt5.QtCore import QLibraryInfo
except Exception as e:
    print(json.dumps({"error": f"PyQt5 not importable: {e}"}))
    sys.exit(0)

base = QLibraryInfo.location(QLibraryInfo.PluginsPath)
platforms = []
imageformats = []

candidates = {
    "platforms": ["qwindows.dll"],
    "imageformats": ["qico.dll", "qjpeg.dll", "qpng.dll"],
}

for sub, names in candidates.items():
    d = os.path.join(base, sub)
    items = []
    for name in names:
        p = os.path.join(d, name)
        if os.path.exists(p):
            items.append(p)
    if sub == "platforms":
        platforms = items
    elif sub == "imageformats":
        imageformats = items

print(json.dumps({"platforms": platforms, "imageformats": imageformats}))
