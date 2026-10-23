#!/usr/bin/env python3
"""
Downloads free-licensed dish photos from Wikimedia Commons into img/dishes/,
writes img/dishes/photos.js (the site picks it up automatically) and
img/dishes/CREDITS.txt (author + licence for every photo).

Run from the project folder (the one with index.html):
    python download_dish_photos.py        (or: py download_dish_photos.py)

Needs internet and Python 3.8+. No extra packages.

TO CHANGE A PHOTO: edit the MAP below. Left side = dish slug (the dish name in
lowercase, symbols/spaces turned into hyphens). Right side = exact Commons file
title. Dishes you leave out simply stay text-only. To use your own photo for a
dish, drop it into img/dishes/ as <slug>.jpg and add the slug to photos.js
(or just delete that dish from MAP and add it by hand).
"""
import json, os, re, sys, time, urllib.parse, urllib.request

WIDTH = 1600
OUT = os.path.join("img", "dishes")
API = "https://commons.wikimedia.org/w/api.php"
UA = "TriStar1947-site/1.0 (menu photos; contact: kashyapshashwat77@gmail.com)"

MAP = {
    # thalis
    "mutton-thali":             "Mutton Thali.jpg",
    "desi-chicken-thali":       "Malwani Chicken Thali.jpg",
    "chicken-thali-normal":     "Non veg thali.jpg",
    "machha-thali-fish-thali":  "Bengali Fish Thali.jpg",
    "egg-thali":                "Egg Curry Thali.jpg",
    "veg-thali":                "Chennai Veg Thali.JPG",
    "vegan-thali":              "'1' Thali Indian Food.jpg",
    # pulao
    "mutton-pulao":             "Kashmiri pulao (cropped).JPG",
    "desi-chicken-pulao":       "Punjabi pullao.JPG",
    "chicken-pulao-normal":     "Chicken Yakhni Pulao.jpg",
    "vegan-pulao":              "Matar Pulao, boondi raita, dry roasted-papad.JPG",
    "paneer-pulao":             "Veg Pulao (Indian fried rice).jpg",
    # biryani
    "mutton-biryani":           "Hyderabadi mutton biryani.jpg",
    "desi-chicken-biryani":     "Hyderabad Chicken Dum Biryani.jpg",
    "chicken-biryani-normal":   "Special chicken biryani.JPG",
    "prawn-biryani":            "Shrimp Biriyani.JPG",
    "mushroom-biryani":         "Veg Kaju Biryani.jpg",
    "vegan-biryani":            "MORADABADI BIRYANI.jpg",
    "paneer-biryani":           "Vegetable Biryani.JPG",
    # handi
    "handi-chicken":            "Handi-chicken-Indian-dum-chicken-curry-recipe.jpg",
    "handi-desi-chicken":       "Indian chicken curry (16261312392).jpg",
    "handi-mutton":             "Odia Mutton Curry (Mansha Tarkari).jpg",
    # podas
    "chicken-baus-poda":        "Bamboo Chicken of Rangamati.JPG",
    "desi-chicken-baus-poda":   "Tribal bamboo chicken dish from Bandarban Bangladesh.jpg",
    "mutton-baus-poda":         "Mutton Coconut Fry.JPG",
    "desi-chicken-patra-poda":  "Bhetki paturi.JPG",
    "mutton-patra-poda":        "Ilish Macher Paturi.jpg",
    "mushroom-patra-poda-paneer-patra-poda": "Grilled Paneer Tikka.jpg",
    "tofu-patra-poda":          "Tandoori Paneer Tikka.jpg",
    # singada
    "aaloo-singada-classic":    "Samosa (Home Made) or Singara.jpg",
    "chicken-singada":          "Chota Samosa.jpg",
    "mutton-keema-singada":     "Samosa (partially open).jpg",
    "paneer-singada":           "Samosas 2 pieces and pakora 1 piece.jpg",
    "mushroom-singada":         "Salem Samosa.jpg",
    "tofu-singada-vegan":       "Samosa - Homemade, Jabalpur - Madhya Pradesh - IMG 20210406 201834.jpg",
    # sweets & drinks
    "chhena-poda":              "Chhena Poda-Puri-Odisha-IMG 1323.jpg",
    "pahala-rasgulla":          "Rasgullas from Odisha and Bengal.jpg",
}
assert len(set(MAP.values())) == len(MAP), "a photo is used twice"
# fresh-coconut-water, hot-water and packaged-drinking-water use the client's own photos already in img/dishes/.
# Every dish has its own photo (checked by the assert above). Some are stand-ins because
# no free photo of the exact dish exists: mutton/desi-chicken pulao, the baus/patra podas,
# tofu & mushroom dishes and the singadas are look-alikes. Replace any with your own photo.

# photos that were tried and removed: deleted from img/dishes/ if an earlier run left them behind
REMOVE = ["chilled-water", "promise-chhena-poda", "promise-coconut-water", "promise-water"]

def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                d = r.read()
                return d if binary else d.decode("utf-8")
        except Exception as e:
            if i == 2: raise
            time.sleep(2 * (i + 1))

def strip(h):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", h or "")).strip()

def free(lic):
    l = (lic or "").lower()
    return l.startswith("cc") or "public domain" in l or l.startswith("pd") or "cc0" in l

def main():
    os.makedirs(OUT, exist_ok=True)
    for r in REMOVE:
        p = os.path.join(OUT, r + ".jpg")
        if os.path.exists(p): os.remove(p)
    titles = sorted(set(MAP.values()))
    info = {}
    for i in range(0, len(titles), 20):                       # API takes batches
        chunk = titles[i:i + 20]
        q = urllib.parse.urlencode({
            "action": "query", "format": "json", "prop": "imageinfo",
            "iiprop": "url|size|extmetadata", "iiurlwidth": WIDTH,
            "titles": "|".join("File:" + t for t in chunk), "redirects": 1,
        })
        data = json.loads(get(API + "?" + q))
        q_ = data["query"]
        redir = {r["to"]: r["from"] for r in q_.get("redirects", [])}
        norm = {n["to"]: n["from"] for n in q_.get("normalized", [])}
        for p in q_["pages"].values():
            t = p["title"]
            orig = redir.get(t, t); orig = norm.get(orig, orig)
            info[orig[5:] if orig.startswith("File:") else orig] = p
            info[t[5:]] = p
    have, credits, bad = {}, {}, []
    for slug, title in MAP.items():
        p = info.get(title)
        if not p or "imageinfo" not in p:
            bad.append((slug, title, "file not found")); continue
        ii = p["imageinfo"][0]; md = ii.get("extmetadata", {})
        lic = strip(md.get("LicenseShortName", {}).get("value"))
        if not free(lic):
            bad.append((slug, title, "licence not free: " + lic)); continue
        dest = os.path.join(OUT, slug + ".jpg")
        if not os.path.exists(dest):
            url = ii.get("thumburl") or ii["url"]
            with open(dest, "wb") as f: f.write(get(url, True))
            print("saved", dest, "from", title)
        have[slug] = slug + ".jpg"
        credits[title] = (strip(md.get("Artist", {}).get("value")), lic, ii.get("descriptionurl", ""))
    for fn in os.listdir(OUT):                       # photos you added by hand stay listed
        if fn.lower().endswith(".jpg"): have.setdefault(fn[:-4], fn)
    with open(os.path.join(OUT, "photos.js"), "w") as f:
        f.write("window.DISH_PHOTOS=" + json.dumps(have, indent=1) + ";\n")
    with open(os.path.join(OUT, "CREDITS.txt"), "w", encoding="utf-8") as f:
        f.write("Dish photos are illustrative and come from Wikimedia Commons.\n\n")
        for t, (a, l, u) in sorted(credits.items()):
            f.write(f"{t}\n  Author: {a or 'unknown'}\n  Licence: {l}\n  Source: {u}\n\n")
    print(f"\n{len(have)} dishes now have photos.")
    for s, t, why in bad: print("SKIPPED", s, "-", t, "-", why)
    if bad: print("Fix the names in MAP above, or choose a different file, then run again.")

if __name__ == "__main__":
    sys.exit(main())
