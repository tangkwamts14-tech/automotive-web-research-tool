        if "/showroom/" in low:
            s += 20

        if "gallery.html" in low:
            s += 10

        if "overview.html" in low:
            s += 8

        if "features.html" in low:
            s += 6

        if "specification.html" in low:
            s += 5

        return s

    df["_score"] = df["Model URL"].map(score)

    df = (
        df.sort_values(
            ["Model", "_score"],
            ascending=[True, False]
        )
        .drop_duplicates(
            ["Make", "Model"],
            keep="first"
        )
        .drop(columns="_score")
        .reset_index(drop=True)
    )

    return df


# ============================================================
# MODEL PAGE FAMILY
# ============================================================

def model_base_url(model_url):

    url = model_url.split("#")[0].split("?")[0]

    filename = url.rstrip("/").split("/")[-1].lower()

    known = {
        "gallery.html",
        "features.html",
        "feature.html",
        "overview.html",
        "specification.html",
        "specifications.html",
    }

    if filename in known:
        return url.rsplit("/", 1)[0] + "/"

    if url.endswith("/"):
        return url

    return url.rsplit("/", 1)[0] + "/"


def _page_kind(text, href):
    blob = clean(f"{text} {href}").lower()
    rules = [
        ("Specification", ["specification", "specifications", "technical data", "technical-data", "technical specification", "specs"]),
        ("Features", ["features", "feature", "performance", "powertrain", "engine", "technology"]),
        ("Dimensions", ["dimensions", "dimension", "measurements"]),
        ("Battery", ["battery", "charging", "electric range", "range"]),
        ("Overview", ["overview", "highlights", "summary"]),
    ]
    for kind, words in rules:
        if any(word in blob for word in words):
            return kind
    return ""


def discover_model_pages(model_url):
    discovered, seen = {}, set()
    try:
        final_url, soup = get_page(model_url)
    except Exception:
        return discovered

    discovered["Model"] = (final_url, soup)
    seen.add(final_url.split("#")[0])
    candidates = []

    for a in soup.find_all("a", href=True):
        href = urljoin(final_url, a.get("href"))
        if not same_site(final_url, href):
            continue
        label = clean(a.get_text(" ", strip=True))
        kind = _page_kind(label, href)
        if not kind:
            continue
        clean_href = href.split("#")[0]
        if clean_href in seen:
            continue
        candidates.append((kind, clean_href))
        seen.add(clean_href)

    priority = {"Specification": 0, "Features": 1, "Battery": 2, "Dimensions": 3, "Overview": 4}
    candidates.sort(key=lambda item: priority.get(item[0], 99))

    for kind, href in candidates[:10]:
        try:
            page_url, page_soup = get_page(href)
            if len(clean(page_soup.get_text(" ", strip=True))) < 100:
                continue
            key, n = kind, 2
            while key in discovered:
                key = f"{kind} {n}"
                n += 1
            discovered[key] = (page_url, page_soup)
        except Exception:
            continue
    return discovered


def get_model_pages(model_url):
    pages = discover_model_pages(model_url)
    if [key for key in pages if key != "Model"]:
        return pages

    base = model_base_url(model_url)
    guesses = [
        ("Specification", "specification.html"),
        ("Specification", "specifications.html"),
        ("Features", "features.html"),
        ("Overview", "overview.html"),
    ]
    for kind, filename in guesses:
        guessed = urljoin(base, filename)
        try:
            page_url, page_soup = get_page(guessed)
            title_text = clean(page_soup.title.get_text(" ", strip=True) if page_soup.title else "").lower()
            body_text = clean(page_soup.get_text(" ", strip=True))
            if len(body_text) < 100 or "page not found" in title_text or title_text == "404":
                continue
            key, n = kind, 2
            while key in pages:
                key = f"{kind} {n}"
                n += 1
            pages[key] = (page_url, page_soup)
        except Exception:
            continue
    return pages


# ============================================================
# LABEL NORMALIZATION
# ============================================================

def canonical_label(label):

    label = clean(label)

    low = label.lower()

    aliases = [
        ("Overall Length",
         ["overall length", "length"]),

        ("Overall Width",
         ["overall width", "width"]),

        ("Overall Height",
         ["overall height", "overall hight", "height"]),

        ("Wheelbase",
         ["wheelbase", "wheel base"]),

        ("Ground Clearance",
         ["minimum ground clearance", "ground clearance"]),

        ("Curb Weight",
         ["curb weight", "kerb weight"]),

        ("Engine Displacement",
         ["engine displacement", "displacement",
          "engine capacity"]),

        ("Engine Type",
         ["engine type"]),

        ("Cylinder Count",
         ["number of cylinders", "cylinder count",
          "cylinders"]),

        ("Fuel Type",
