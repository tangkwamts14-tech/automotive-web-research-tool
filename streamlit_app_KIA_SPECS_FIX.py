import io
import re
import shutil
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="Automotive Website Research",
    page_icon="🚗",
    layout="wide",
)

st.title("🚗 Automotive Website Research")
st.caption(
    "Website URL → Models → Variants → Specifications → Excel"
)
st.caption("App version: 2026-09-30 KIA-SPECS-FIX")


# INPUTS RENDER FIRST
url = st.text_input(
    "Website URL",
    value=st.session_state.get("current_url", ""),
    placeholder="https://www.kia.com/aljabr/en/main.html",
)
research = st.button(
    "🔎 Research Website",
    type="primary",
    use_container_width=True,
)


# ============================================================
# SETTINGS
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

BRANDS = [
    "Acura", "Alfa Romeo", "Aston Martin", "Audi", "BAIC",
    "Bentley", "Bestune", "BMW", "BYD", "Cadillac", "Changan",
    "Chery", "Chevrolet", "Chrysler", "Denza", "Dodge", "Exeed",
    "FAW", "Ferrari", "Fiat", "Ford", "Foton", "GAC", "Geely",
    "Genesis", "GMC", "Great Wall", "GWM", "Haval", "Honda",
    "Hongqi", "Hyundai", "iCAUR", "Ineos", "Infiniti", "Isuzu",
    "JAC", "Jaecoo", "Jaguar", "Jeep", "Jetour", "Kia",
    "Lamborghini", "Land Rover", "Lexus", "Lincoln", "Lotus",
    "Maserati", "Mazda", "McLaren", "Mercedes-Benz", "MG",
    "MINI", "Mitsubishi", "Nissan", "Omoda", "Ora", "Peugeot",
    "Porsche", "RAM", "Renault", "Rolls-Royce", "Skoda",
    "Soueast", "Ssangyong", "Subaru", "Suzuki", "Tata",
    "Tesla", "Toyota", "Volkswagen", "Volvo", "Yangwang",
]

BAD_MODEL_NAMES = {
    "", "home", "brand", "gallery", "features",
    "specification", "specifications", "overview",
    "vehicle", "vehicles", "model", "models", "cars",
    "all models", "all vehicles", "offers", "owners",
    "services", "shopping tools", "contact", "connect",
    "find a dealer", "request a quote", "test drive",
    "learn more", "explore more", "discover",
    "build your kia tasman", "saudi arabia aljabr",
}

BAD_MODEL_PHRASES = [
    "build your",
    "shopping",
    "dealer",
    "service",
    "warranty",
    "accessories",
    "privacy",
    "cookie",
    "contact us",
    "request",
]


# ============================================================
# BASIC
# ============================================================

def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_url(url):
    url = clean(url)

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    return url


def host(url):
    return urlparse(url).netloc.lower().replace("www.", "")


def same_site(a, b):
    return host(a) == host(b)


def browser_page(url):
    from playwright.sync_api import sync_playwright

    chromium_path = (
        shutil.which("chromium")
        or shutil.which("chromium-browser")
        or shutil.which("google-chrome")
    )

    with sync_playwright() as p:
        launch_options = {
            "headless": True,
            "args": [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        }

        if chromium_path:
            launch_options["executable_path"] = chromium_path

        browser = p.chromium.launch(**launch_options)

        page = browser.new_page(
            user_agent=HEADERS["User-Agent"],
            viewport={"width": 1440, "height": 1200},
        )

        try:
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            try:
                page.wait_for_load_state(
                    "networkidle",
                    timeout=15000,
                )
            except Exception:
                pass

            page.wait_for_timeout(1500)

            final_url = page.url
            html = page.content()

        finally:
            browser.close()

    return (
        final_url,
        BeautifulSoup(html, "html.parser"),
    )


def get_page(url):
    url = normalize_url(url)

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=35,
            allow_redirects=True,
        )

        if response.status_code in (401, 403, 429):
            raise RuntimeError(
                f"HTTP {response.status_code}"
            )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        visible_text = clean(
            soup.get_text(" ", strip=True)
        )

        if len(visible_text) < 250:
            raise RuntimeError(
                "Page requires browser rendering"
            )

        return response.url, soup

    except Exception:
        return browser_page(url)


# ============================================================
# MAKE
# ============================================================

def detect_make(soup, url):
    domain_text = re.sub(
        r"[^a-z0-9]",
        "",
        host(url)
    )

    for brand in sorted(
        BRANDS,
        key=len,
        reverse=True
    ):
        b = re.sub(
            r"[^a-z0-9]",
            "",
            brand.lower()
        )

        if b in domain_text:
            return brand

    title = clean(
        soup.title.get_text(
            " ",
            strip=True
        )
        if soup.title else ""
    )

    for brand in sorted(
        BRANDS,
        key=len,
        reverse=True
    ):
        if re.search(
            r"(?<![A-Za-z0-9])"
            + re.escape(brand)
            + r"(?![A-Za-z0-9])",
            title,
            re.I,
        ):
            return brand

    return host(url).split(".")[0].title()


# ============================================================
# MODEL DISCOVERY
# ============================================================

def model_from_url(url):
    path = urlparse(url).path

    parts = [
        x for x in path.split("/")
        if x
    ]

    ignored = {
        "en", "ar",
        "showroom",
        "model", "models",
        "vehicle", "vehicles",
        "cars", "car",
        "gallery.html",
        "features.html",
        "overview.html",
        "specification.html",
        "specifications.html",
    }

    usable = [
        x for x in parts
        if x.lower() not in ignored
    ]

    if not usable:
        return ""

    value = usable[-1]

    value = re.sub(
        r"\.(html?|php)$",
        "",
        value,
        flags=re.I,
    )

    value = (
        value
        .replace("-", " ")
        .replace("_", " ")
    )

    words = []

    for word in value.split():
        if (
            len(word) <= 3
            or re.search(r"\d", word)
        ):
            words.append(word.upper())
        else:
            words.append(word.title())

    return clean(" ".join(words))


def valid_model(model, make):
    model = clean(model)

    if not model:
        return False

    low = model.lower()

    if low in BAD_MODEL_NAMES:
        return False

    if low == make.lower():
        return False

    if len(model) > 45:
        return False

    if any(
        phrase in low
        for phrase in BAD_MODEL_PHRASES
    ):
        return False

    if re.fullmatch(
        r"[\d\s.,]+",
        model
    ):
        return False

    return True


def find_models(soup, base_url, make):
    results = []

    model_path_words = [
        "/showroom/",
        "/models/",
        "/model/",
        "/vehicles/",
        "/vehicle/",
    ]

    for a in soup.find_all(
        "a",
        href=True
    ):
        href = urljoin(
            base_url,
            a.get("href")
        )

        if not same_site(
            base_url,
            href
        ):
            continue

        path = urlparse(
            href
        ).path.lower()

        if not any(
            word in path
            for word in model_path_words
        ):
            continue

        anchor_text = clean(
            a.get_text(
                " ",
                strip=True
            )
        )

        model = model_from_url(href)

        if not valid_model(
            model,
            make
        ):
            if valid_model(
                anchor_text,
                make
            ):
                model = anchor_text
            else:
                continue

        results.append({
            "Make": make,
            "Model": model,
            "Model URL": href,
        })

    if not results:
        return pd.DataFrame(
            columns=[
                "Make",
                "Model",
                "Model URL",
            ]
        )

    df = pd.DataFrame(results)

    def score(url):
        low = url.lower()
        points = 0

        if "/showroom/" in low:
            points += 20

        if "/models/" in low:
            points += 15

        if "/vehicles/" in low:
            points += 15

        if "gallery" in low:
            points += 10

        if "overview" in low:
            points += 8

        if "features" in low:
            points += 6

        if "specification" in low:
            points += 5

        return points

    df["_score"] = (
        df["Model URL"].map(score)
    )

    df = (
        df.sort_values(
            ["Model", "_score"],
            ascending=[True, False]
        )
        .drop_duplicates(
            ["Make", "Model"],
            keep="first"
        )
        .drop(
            columns="_score"
        )
        .reset_index(
            drop=True
        )
    )

    return df
    # ============================================================
# SPEC RESEARCH
# ============================================================

SPEC_WORDS = [
    "specification", "specifications", "specs",
    "technical", "technical data",
    "features", "performance",
    "engine", "powertrain",
    "dimensions", "battery",
]


def discover_model_pages(model_url):
    pages = {}

    try:
        final_url, soup = get_page(model_url)
        pages["Model"] = (final_url, soup)
    except Exception:
        return pages

    for a in soup.find_all("a", href=True):
        text = clean(a.get_text(" ", strip=True)).lower()
        href = urljoin(final_url, a.get("href"))

        if not same_site(final_url, href):
            continue

        combined = text + " " + href.lower()

        if not any(word in combined for word in SPEC_WORDS):
            continue

        if href in [x[0] for x in pages.values()]:
            continue

        try:
            page_url, page_soup = get_page(href)

            if clean(page_soup.get_text(" ", strip=True)):
                pages[f"Page {len(pages)+1}"] = (
                    page_url,
                    page_soup
                )

        except Exception:
            pass

        if len(pages) >= 8:
            break

    return pages


def extract_pairs(soup):
    data = {}

    # TABLES
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            cells = [
                clean(x.get_text(" ", strip=True))
                for x in tr.find_all(["th", "td"])
            ]

            if len(cells) == 2:
                key, value = cells

                if key and value:
                    data[key] = value

    # DL / DT / DD
    for dt in soup.find_all("dt"):
        dd = dt.find_next_sibling("dd")

        if dd:
            key = clean(dt.get_text(" ", strip=True))
            value = clean(dd.get_text(" ", strip=True))

            if key and value:
                data[key] = value

    return data


def find_value(text, patterns):
    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.I
        )

        if match:
            return clean(match.group(1))

    return ""


def generic_specs(soup):
    text = clean(
        soup.get_text(
            " ",
            strip=True
        )
    )

    specs = {}

    pairs = extract_pairs(soup)

    aliases = {
        "Engine Displacement": [
            "engine displacement",
            "displacement",
            "engine capacity",
            "capacity",
        ],

        "Engine Type": [
            "engine type",
        ],

        "Cylinder Count": [
            "cylinders",
            "number of cylinders",
            "cylinder count",
        ],

        "Fuel Type": [
            "fuel type",
            "fuel",
        ],

        "Max Power": [
            "maximum power",
            "max power",
            "power output",
            "engine power",
        ],

        "Max Torque": [
            "maximum torque",
            "max torque",
            "torque",
        ],

        "Transmission": [
            "transmission",
            "gearbox",
            "transmission type",
        ],

        "Drivetrain": [
            "drivetrain",
            "drive type",
            "drive system",
        ],

        "Battery Capacity": [
            "battery capacity",
            "battery pack size",
        ],

        "EV Range": [
            "electric range",
            "driving range",
            "ev range",
            "range wltp",
        ],

        "Seats": [
            "seats",
            "seating capacity",
        ],

        "Overall Length": [
            "overall length",
            "length",
        ],

        "Overall Width": [
            "overall width",
            "width",
        ],

        "Overall Height": [
            "overall height",
            "height",
        ],

        "Wheelbase": [
            "wheelbase",
            "wheel base",
        ],

        "Ground Clearance": [
            "ground clearance",
        ],

        "Fuel Tank": [
            "fuel tank",
            "fuel tank capacity",
        ],

        "Top Speed": [
            "top speed",
            "maximum speed",
        ],

        "Acceleration 0-100": [
            "0-100",
            "0 - 100",
            "acceleration",
        ],

        "Tyre Size": [
            "tyre size",
            "tire size",
        ],

        "Wheels": [
            "wheel size",
            "wheels",
        ],
    }

    for original_key, value in pairs.items():
        low = original_key.lower()

        for output_key, names in aliases.items():
            if any(name in low for name in names):
                if value:
                    specs.setdefault(
                        output_key,
                        value
                    )

    regex_specs = {
        "Max Power": [
            r"(?:maximum|max)\s+power[^0-9]{0,20}([0-9.,]+\s*(?:hp|ps|kw))",
            r"([0-9.,]+\s*(?:hp|ps|kw))\s+(?:maximum\s+)?power",
        ],

        "Max Torque": [
            r"(?:maximum|max)\s+torque[^0-9]{0,20}([0-9.,]+\s*nm)",
            r"([0-9.,]+\s*nm)\s+(?:maximum\s+)?torque",
        ],

        "Battery Capacity": [
            r"battery\s+capacity[^0-9]{0,20}([0-9.,]+\s*kwh)",
            r"([0-9.,]+\s*kwh)\s+battery",
        ],

        "EV Range": [
            r"(?:electric|driving|ev)\s+range[^0-9]{0,30}([0-9.,]+\s*km)",
        ],

        "Overall Length": [
            r"(?:overall\s+)?length[^0-9]{0,15}([0-9.,]+\s*mm)",
        ],

        "Overall Width": [
            r"(?:overall\s+)?width[^0-9]{0,15}([0-9.,]+\s*mm)",
        ],

        "Overall Height": [
            r"(?:overall\s+)?height[^0-9]{0,15}([0-9.,]+\s*mm)",
        ],

        "Wheelbase": [
            r"wheel\s*base[^0-9]{0,15}([0-9.,]+\s*mm)",
        ],
    }

    for key, patterns in regex_specs.items():
        if not specs.get(key):
            value = find_value(
                text,
                patterns
            )

            if value:
                specs[key] = value

    # drivetrain
    if not specs.get("Drivetrain"):
        match = re.search(
            r"\b(AWD|4WD|FWD|RWD)\b",
            text,
            re.I,
        )

        if match:
            specs["Drivetrain"] = (
                match.group(1).upper()
            )

    # Flexible fallback for OEM pages (especially Kia) whose labels/values are
    # rendered as separate blocks rather than ordinary two-cell HTML tables.
    flexible = {
        "Overall Length": [r"overall\s+length[^0-9]{0,80}([0-9][0-9,\.]{2,})"],
        "Overall Width": [r"overall\s+width[^0-9]{0,80}([0-9][0-9,\.]{2,})"],
        "Overall Height": [r"overall\s+(?:height|hight)[^0-9]{0,80}([0-9][0-9,\.]{2,})"],
        "Wheelbase": [r"wheel\s*base[^0-9]{0,80}([0-9][0-9,\.]{2,})"],
        "Fuel Tank": [r"fuel\s+tank\s+capacity[^0-9]{0,30}([0-9.,]+\s*L)"],
    }
    for key, pats in flexible.items():
        if not specs.get(key):
            v = find_value(text, pats)
            if v:
                specs[key] = v + (" mm" if key in {"Overall Length", "Overall Width", "Overall Height", "Wheelbase"} and "mm" not in v.lower() else "")

    engines = re.findall(r"(\d+(?:\.\d+)?\s*L(?:\s*\(Turbo\))?[^.;]{0,80}?\d+\s*ps[^.;]{0,40}?\d+\s*Nm)", text, re.I)
    if engines and not specs.get("Engine Type"):
        specs["Engine Type"] = " | ".join(dict.fromkeys(clean(x) for x in engines))
    if not specs.get("Transmission"):
        m = re.search(r"\b(IVT\s+or\s+\d+-Speed\s+DCT|\d+-Speed\s+(?:DCT|AT|MT|Automatic|Manual)|IVT|CVT)\b", text, re.I)
        if m:
            specs["Transmission"] = clean(m.group(1))

    return specs


def detect_variants(soup):
    variants = []

    candidates = [
        "GT-Line", "GT Line",
        "Base model",
        "Standard",
        "Premium",
        "Luxury",
        "Executive",
        "EX", "LX", "SX", "GX",
    ]

    text = clean(
        soup.get_text(
            " ",
            strip=True
        )
    )

    for variant in candidates:
        if re.search(
            r"(?<![A-Za-z0-9])"
            + re.escape(variant)
            + r"(?![A-Za-z0-9])",
            text,
            re.I,
        ):
            variants.append(variant)

    return list(dict.fromkeys(variants))

# ============================================================
# VARIANT / GRADE EXTRACTION
# ============================================================

def parse_engine_string(value):
    result = {}

    value = clean(value)

    if not value:
        return result

    result["Engine Type"] = value

    m = re.search(r"(\d+(?:\.\d+)?)\s*L\b", value, re.I)
    if m:
        result["Engine Displacement"] = m.group(1) + " L"

    m = re.search(r"(\d+)\s*[- ]?CYLINDER", value, re.I)
    if m:
        result["Cylinder Count"] = m.group(1)

    if re.search(r"\bPETROL\b|\bGASOLINE\b", value, re.I):
        result["Fuel Type"] = "Petrol"
    elif re.search(r"\bDIESEL\b", value, re.I):
        result["Fuel Type"] = "Diesel"
    elif re.search(r"\bHYBRID\b|\bHEV\b", value, re.I):
        result["Fuel Type"] = "Hybrid"
    elif re.search(r"\bELECTRIC\b|\bBEV\b", value, re.I):
        result["Fuel Type"] = "Electric"

    m = re.search(
        r"(\d+(?:\.\d+)?)\s*(HP|PS|kW)\b",
        value,
        re.I,
    )
    if m:
        result["Max Power"] = (
            m.group(1) + " " + m.group(2).upper()
        )

    m = re.search(
        r"(\d+(?:\.\d+)?)\s*N[- ]?m\b",
        value,
        re.I,
    )
    if m:
        result["Max Torque"] = m.group(1) + " Nm"

    return result


def extract_grade_sections(soup, make, model, source_url):
    """
    Reads pages where each grade/variant is a heading followed by
    Technical Features / Engine / Transmission / Wheels etc.
    """

    rows = []

    headings = soup.find_all(
        ["h1", "h2", "h3", "h4", "h5"]
    )

    bad_headings = {
        "technical features",
        "interior features",
        "exterior features",
        "safety & convenience features",
        "audio & entertainment system",
        "grades",
        "explore by grades",
        "full specs",
        "specifications",
        "specification",
    }

    for heading in headings:

        variant = clean(
            heading.get_text(
                " ",
                strip=True
            )
        )

        low = variant.lower()

        if not variant:
            continue

        if low in bad_headings:
            continue

        # Grade names normally contain letters/numbers such as
        # 1.5L XLI Executive / Premium / GT-Line etc.
        looks_like_grade = bool(
            re.search(
                r"\d+(?:\.\d+)?\s*L|"
                r"\b(XLI|GLI|LX|EX|SX|GX|"
                r"EXECUTIVE|PREMIUM|STANDARD|"
                r"LUXURY|GT[- ]?LINE|HEV|HYBRID)\b",
                variant,
                re.I,
            )
        )

        if not looks_like_grade:
            continue

        content = []

        node = heading.find_next_sibling()

        while node is not None:

            if (
                getattr(node, "name", None)
                in ["h1", "h2", "h3", "h4", "h5"]
            ):
                next_heading = clean(
                    node.get_text(
                        " ",
                        strip=True
                    )
                )

                if re.search(
                    r"\d+(?:\.\d+)?\s*L|"
                    r"\b(XLI|GLI|LX|EX|SX|GX|"
                    r"EXECUTIVE|PREMIUM|STANDARD|"
                    r"LUXURY|GT[- ]?LINE|HEV|HYBRID)\b",
                    next_heading,
                    re.I,
                ):
                    break

            text = clean(
                node.get_text(
                    " ",
                    strip=True
                )
                if hasattr(node, "get_text")
                else ""
            )

            if text:
                content.append(text)

            node = node.find_next_sibling()

        block = clean(
            " ".join(content)
        )

        if not block:
            continue

        row = {
            "Make": make,
            "Model": model,
            "Variant": variant,
            "Source URL": source_url,
        }

        # ENGINE
        m = re.search(
            r"Engine\s*:\s*(.+?)"
            r"(?=\s+(?:Max Output|Max Power|Max Torque|"
            r"Transmission|Wheels|Tire Size|Tyre Size|"
            r"Dimensions|Fuel Efficiency|Fuel Tank|$))",
            block,
            re.I,
        )

        if m:
            engine = clean(m.group(1))

            row.update(
                parse_engine_string(engine)
            )

        # MAX OUTPUT
        m = re.search(
            r"(?:Max Output|Maximum Output|Max Power)"
            r"\s*:\s*"
            r"(\d+(?:\.\d+)?)\s*(HP|PS|kW)",
            block,
            re.I,
        )

        if m:
            row["Max Power"] = (
                m.group(1)
                + " "
                + m.group(2).upper()
            )

        # TORQUE
        m = re.search(
            r"(?:Max Torque|Maximum Torque)"
            r"\s*:?\s*"
            r"(\d+(?:\.\d+)?)\s*N[- ]?m",
            block,
            re.I,
        )

        if m:
            row["Max Torque"] = (
                m.group(1) + " Nm"
            )

        # TRANSMISSION
        m = re.search(
            r"Transmission\s*:\s*(.+?)"
            r"(?=\s+(?:Wheels|Tire Size|Tyre Size|"
            r"Dimensions|Fuel Efficiency|Fuel Tank|"
            r"Exterior Features|Interior Features|$))",
            block,
            re.I,
        )

        if m:
            row["Transmission"] = clean(
                m.group(1)
            )

        # WHEELS
        m = re.search(
            r"Wheels?\s*:\s*(.+?)"
            r"(?=\s+(?:Tire Size|Tyre Size|"
            r"Transmission|Dimensions|$))",
            block,
            re.I,
        )

        if m:
            row["Wheels"] = clean(
                m.group(1)
            )

        # TYRE
        m = re.search(
            r"(?:Tire|Tyre)\s*Size\s*:\s*"
            r"([0-9A-Za-z/\- ]+)",
            block,
            re.I,
        )

        if m:
            row["Tyre Size"] = clean(
                m.group(1)
            )

        # DIMENSIONS L-W-H
        m = re.search(
            r"Dimensions\s+L\s*-\s*W\s*-\s*H"
            r"\s*\(mm\)\s*:\s*"
            r"([\d,.]+)\s*-\s*"
            r"([\d,.]+)\s*-\s*"
            r"([\d,.]+)",
            block,
            re.I,
        )

        if m:
            row["Overall Length"] = m.group(1) + " mm"
            row["Overall Width"] = m.group(2) + " mm"
            row["Overall Height"] = m.group(3) + " mm"

        # FUEL EFFICIENCY
        m = re.search(
            r"Fuel Efficiency\s*:\s*"
            r"([\d.]+\s*KM/L)",
            block,
            re.I,
        )

        if m:
            row["Fuel Efficiency"] = clean(
                m.group(1)
            )

        # FUEL TANK
        m = re.search(
            r"Fuel Tank Capacity\s*:\s*"
            r"([\d.]+\s*L)",
            block,
            re.I,
        )

        if m:
            row["Fuel Tank"] = clean(
                m.group(1)
            )

        # DRIVETRAIN
        m = re.search(
            r"\b(AWD|4WD|FWD|RWD)\b",
            block,
            re.I,
        )

        if m:
            row["Drivetrain"] = (
                m.group(1).upper()
            )

        rows.append(row)

    # Remove duplicates
    unique = []
    seen = set()

    for row in rows:

        key = (
            row["Make"],
            row["Model"],
            row["Variant"],
        )

        if key not in seen:
            seen.add(key)
            unique.append(row)

    return unique



def kia_text_specs(soup, make, model, source_url):
    """Parse Kia Aljabr specification pages whose spec grid is rendered as text, not HTML <table>."""
    text = clean(soup.get_text(" ", strip=True))
    if make.lower() != "kia":
        return []

    # Only treat pages that actually expose Kia's dimension/spec layout.
    if not re.search(r"Dimensions\s*\(mm\)", text, re.I):
        return []

    labels = ["Overall Length", "Overall Width", "Overall Height", "Wheelbase"]
    # Kia occasionally publishes the typo "Overall Hight".
    normalized = re.sub(r"Overall\s+Hight", "Overall Height", text, flags=re.I)

    # Locate variant header after the dimension labels.
    m = re.search(
        r"Overall\s+Length.*?Overall\s+Width.*?Overall\s+Height.*?Wheelbase\s+(.+?)",
        normalized,
        re.I,
    )
    if not m:
        return []
    tail = m.group(1)

    # Known Kia page structure: variant names first, then 4 rows of values per variant.
    vm = re.search(
        r"(GT[- ]?Line|Base model)(?:\s*\|?\s*)(GT[- ]?Line|Base model)\s+"
        r"([0-9.,]+)\s*\|?\s*([0-9.,]+)\s+"
        r"([0-9.,]+)\s*\|?\s*([0-9.,]+)\s+"
        r"([0-9.,]+)\s*\|?\s*([0-9.,]+)\s+"
        r"([0-9.,]+)\s*\|?\s*([0-9.,]+)",
        tail,
        re.I,
    )
    if not vm:
        return []

    variants = [clean(vm.group(1)), clean(vm.group(2))]
    nums = [clean(vm.group(i)) for i in range(3, 11)]
    rows=[]
    for col, variant in enumerate(variants):
        vals=[nums[col], nums[2+col], nums[4+col], nums[6+col]]
        row={"Make":make,"Model":model,"Variant":variant,"Source URL":source_url}
        for label,val in zip(labels, vals):
            # Kia uses 4.615 for 4,615 mm on some pages.
            if re.fullmatch(r"\d\.\d{3}", val):
                val=val.replace('.', ',')
            row[label]=val + " mm"
        rows.append(row)

    wheels=[]
    for w in re.findall(r"(\d{2})[”\"]\s*Alloy wheel", normalized, re.I):
        item=w+' inch Alloy wheel'
        if item not in wheels:
            wheels.append(item)
    if wheels:
        wheel_text=" / ".join(wheels)
        for row in rows:
            row["Wheels"]=wheel_text
    return rows

def extract_specs(model_url, make, model):

    pages = discover_model_pages(
        model_url
    )

    if not pages:
        return [{
            "Make": make,
            "Model": model,
            "Variant": "",
            "Source URL": model_url,
            "Status": "Page could not be read",
        }]

    all_rows = []

    research_urls = []

    for _, (
        page_url,
        soup
    ) in pages.items():

        research_urls.append(
            page_url
        )

        grade_rows = (
            extract_grade_sections(
                soup,
                make,
                model,
                page_url,
            )
        )

        kia_rows = kia_text_specs(soup, make, model, page_url)
        if kia_rows:
            all_rows.extend(kia_rows)
        # ====================================================
        # KIA / HORIZONTAL SPEC TABLE
        # ====================================================

        for table in soup.find_all("table"):

            matrix = []

            for tr in table.find_all("tr"):
                cells = [
                    clean(x.get_text(" ", strip=True))
                    for x in tr.find_all(["th", "td"])
                ]

                if cells:
                    matrix.append(cells)

            if len(matrix) < 2:
                continue

            max_cols = max(len(r) for r in matrix)

            if max_cols < 3:
                continue

            # Normalize rows
            matrix = [
                r + [""] * (max_cols - len(r))
                for r in matrix
            ]

            # ------------------------------------------------
            # Find variant names from first useful row
            # Example:
            # ["", "GT-Line", "Base model"]
            # ------------------------------------------------

            variant_row_index = None
            variant_names = []

            for i, r in enumerate(matrix[:8]):

                values = [
                    clean(x)
                    for x in r[1:]
                ]

                nonempty = [
                    x for x in values
                    if x
                ]

                if len(nonempty) >= 2:

                    joined = " ".join(nonempty)

                    if not re.search(
                        r"\b(mm|kg|kw|nm|hp|ps|kwh|km)\b",
                        joined,
                        re.I,
                    ):
                        variant_row_index = i
                        variant_names = values
                        break

            if variant_row_index is None:
                continue

            for col_index, variant in enumerate(
                variant_names,
                start=1,
            ):

                variant = clean(variant)

                if not variant:
                    continue

                row = {
                    "Make": make,
                    "Model": model,
                    "Variant": variant,
                    "Source URL": page_url,
                }

                for r in matrix[
                    variant_row_index + 1:
                ]:

                    if len(r) <= col_index:
                        continue

                    label = clean(r[0])
                    value = clean(r[col_index])

                    if not label or not value:
                        continue

                    low = label.lower()

                    # ENGINE
                    if (
                        "engine type" in low
                        or low == "engine"
                    ):
                        row["Engine Type"] = value
                        row.update(
                            parse_engine_string(value)
                        )

                    elif (
                        "displacement" in low
                        or "engine capacity" in low
                    ):
                        row["Engine Displacement"] = value

                    elif (
                        "cylinder" in low
                    ):
                        row["Cylinder Count"] = value

                    elif (
                        "fuel type" in low
                    ):
                        row["Fuel Type"] = value

                    # POWER
                    elif (
                        "max power" in low
                        or "maximum power" in low
                        or "max output" in low
                        or "maximum output" in low
                    ):
                        row["Max Power"] = value

                    # TORQUE
                    elif (
                        "torque" in low
                    ):
                        row["Max Torque"] = value

                    # TRANSMISSION
                    elif (
                        "transmission" in low
                        or "gearbox" in low
                    ):
                        row["Transmission"] = value

                    # DRIVE
                    elif (
                        "drive type" in low
                        or "drivetrain" in low
                        or "drive system" in low
                    ):
                        row["Drivetrain"] = value

                    # BATTERY
                    elif (
                        "battery capacity" in low
                        or "battery pack" in low
                    ):
                        row["Battery Capacity"] = value

                    # EV RANGE
                    elif (
                        "range" in low
                        and (
                            "driving" in low
                            or "electric" in low
                            or "wltp" in low
                        )
                    ):
                        row["EV Range"] = value

                    # CHARGING
                    elif (
                        "charging" in low
                        or "charge time" in low
                    ):
                        row["Charging"] = value

                    # LENGTH
                    elif (
                        "overall length" in low
                        or low == "length"
                    ):
                        row["Overall Length"] = value

                    # WIDTH
                    elif (
                        "overall width" in low
                        or low == "width"
                    ):
                        row["Overall Width"] = value

                    # HEIGHT
                    elif (
                        "overall height" in low
                        or low == "height"
                    ):
                        row["Overall Height"] = value

                    # WHEELBASE
                    elif (
                        "wheelbase" in low
                        or "wheel base" in low
                    ):
                        row["Wheelbase"] = value

                    # CLEARANCE
                    elif (
                        "ground clearance" in low
                    ):
                        row["Ground Clearance"] = value

                    # WHEEL
                    elif (
                        "wheel" in low
                        and "base" not in low
                    ):
                        row["Wheels"] = value

                    # TYRE
                    elif (
                        "tire" in low
                        or "tyre" in low
                    ):
                        row["Tyre Size"] = value

                    # SEATS
                    elif (
                        "seat" in low
                        and "heated" not in low
                    ):
                        row["Seats"] = value

                    # TOP SPEED
                    elif (
                        "top speed" in low
                        or "maximum speed" in low
                    ):
                        row["Top Speed"] = value

                    # ACCELERATION
                    elif (
                        "0-100" in low
                        or "acceleration" in low
                    ):
                        row["Acceleration 0-100"] = value

                # Only keep if the row has actual specs
                if len(row) > 4:
                    all_rows.append(row)
        if grade_rows:
            all_rows.extend(
                grade_rows
            )

    # --------------------------------------------------------
    # If grade parser found nothing, use generic parser
    # --------------------------------------------------------

    if not all_rows:

        combined = {}

        for _, (
            page_url,
            soup
        ) in pages.items():

            specs = generic_specs(
                soup
            )

            for key, value in specs.items():

                if (
                    value
                    and not combined.get(key)
                ):
                    combined[key] = value

        row = {
            "Make": make,
            "Model": model,
            "Variant": "",
            "Source URL": model_url,
        }

        row.update(
            combined
        )

        named_variants = []
        for _, (_, variant_soup) in pages.items():
            named_variants.extend(detect_variants(variant_soup))
        named_variants = list(dict.fromkeys(named_variants))
        if named_variants:
            all_rows = []
            for variant in named_variants:
                vr = row.copy()
                vr["Variant"] = variant
                all_rows.append(vr)
        else:
            all_rows = [row]

    # --------------------------------------------------------
    # Merge duplicate variants
    # --------------------------------------------------------

    merged = {}

    for row in all_rows:

        key = clean(
            row.get(
                "Variant",
                ""
            )
        ).lower()

        if key not in merged:
            merged[key] = row.copy()

        else:
            for field, value in row.items():

                if (
                    value
                    and not merged[key].get(field)
                ):
                    merged[key][field] = value

    final_rows = list(
        merged.values()
    )

    source_text = " | ".join(
        list(
            dict.fromkeys(
                research_urls
            )
        )
    )

    for row in final_rows:
        row[
            "Research Source URLs"
        ] = source_text

    return final_rows
    
# ============================================================

def create_excel(models_df, specs_df):
    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        models_df.to_excel(
            writer,
            index=False,
            sheet_name="Models"
        )

        specs_df.to_excel(
            writer,
            index=False,
            sheet_name="Specs"
        )

        for sheet_name in [
            "Models",
            "Specs"
        ]:
            ws = writer.book[
                sheet_name
            ]

            ws.freeze_panes = "A2"

            for column_cells in ws.columns:
                max_length = 0

                column_letter = (
                    column_cells[0]
                    .column_letter
                )

                for cell in column_cells:
                    value = str(
                        cell.value or ""
                    )

                    max_length = max(
                        max_length,
                        len(value)
                    )

                ws.column_dimensions[
                    column_letter
                ].width = min(
                    max(
                        max_length + 2,
                        12
                    ),
                    45
                )

    return output.getvalue()


# ============================================================
# UI ACTIONS
# ============================================================


if research:

    # Clear OLD website results first.
    for key in [
        "make",
        "models",
        "specs",
    ]:
        st.session_state.pop(
            key,
            None
        )

    if not clean(url):
        st.warning(
            "ใส่ URL ก่อนค่ะ"
        )

    else:
        try:
            with st.spinner(
                "กำลังค้นหารุ่นรถ..."
            ):
                normalized = (
                    normalize_url(url)
                )

                final_url, soup = (
                    get_page(
                        normalized
                    )
                )

                make = detect_make(
                    soup,
                    final_url
                )

                models_df = (
                    find_models(
                        soup,
                        final_url,
                        make
                    )
                )

                st.session_state[
                    "current_url"
                ] = normalized

                st.session_state[
                    "make"
                ] = make

                st.session_state[
                    "models"
                ] = models_df

                st.session_state[
                    "specs"
                ] = pd.DataFrame()

        except Exception as error:
            st.error(
                "อ่านเว็บไซต์ไม่ได้: "
                + str(error)
            )


# ============================================================
# MODELS
# ============================================================

if "models" in st.session_state:

    models_df = (
        st.session_state[
            "models"
        ]
    )

    c1, c2 = st.columns(2)

    c1.metric(
        "Make",
        st.session_state.get(
            "make",
            "-"
        )
    )

    c2.metric(
        "Models found",
        len(models_df)
    )

    st.subheader(
        "Models"
    )

    if models_df.empty:
        st.warning(
            "ยังไม่พบ Model จากเว็บไซต์นี้"
        )

    else:
        select_df = (
            models_df.copy()
        )

        select_df.insert(
            0,
            "Research Specs",
            False
        )

        edited = st.data_editor(
            select_df,
            hide_index=True,
            width="stretch",
            column_config={
                "Research Specs":
                    st.column_config.CheckboxColumn(
                        "Research Specs"
                    ),

                "Model URL":
                    st.column_config.LinkColumn(
                        "Model URL"
                    ),
            },
            disabled=[
                "Make",
                "Model",
                "Model URL",
            ],
        )

        col1, col2 = (
            st.columns(2)
        )

        get_selected = (
            col1.button(
                "⚙️ Get Selected Specs",
                use_container_width=True,
            )
        )

        get_all = (
            col2.button(
                "🚗 Get ALL Specs",
                use_container_width=True,
            )
        )

        if (
            get_selected
            or get_all
        ):

            if get_all:
                selected = (
                    models_df
                )

            else:
                selected = edited[
                    edited[
                        "Research Specs"
                    ] == True
                ]

            if selected.empty:
                st.warning(
                    "ติ๊กรุ่นที่ต้องการก่อนค่ะ"
                )

            else:
                all_results = []

                progress = (
                    st.progress(0)
                )

                status = st.empty()

                total = len(
                    selected
                )

                for number, (
                    _,
                    row
                ) in enumerate(
                    selected.iterrows(),
                    start=1,
                ):

                    status.write(
                        "กำลังอ่าน "
                        + str(
                            row["Make"]
                        )
                        + " "
                        + str(
                            row["Model"]
                        )
                        + f" ({number}/{total})"
                    )

                    try:
                        model_results = (
                            extract_specs(
                                row[
                                    "Model URL"
                                ],
                                row[
                                    "Make"
                                ],
                                row[
                                    "Model"
                                ],
                            )
                        )

                    except Exception as error:
                        model_results = [{
                            "Make":
                                row["Make"],

                            "Model":
                                row["Model"],

                            "Variant": "",

                            "Source URL":
                                row[
                                    "Model URL"
                                ],

                            "Status":
                                str(error),
                        }]

                    all_results.extend(
                        model_results
                    )

                    progress.progress(
                        number / total
                    )

                status.success(
                    "เสร็จแล้ว"
                )

                st.session_state[
                    "specs"
                ] = pd.DataFrame(
                    all_results
                )


# ============================================================
# RESULTS
# ============================================================

specs_df = (
    st.session_state.get(
        "specs",
        pd.DataFrame()
    )
)

if not specs_df.empty:

    specs_df = (
        specs_df
        .replace("", pd.NA)
        .dropna(
            axis=1,
            how="all"
        )
        .fillna("")
    )

    preferred = [
        "Make",
        "Model",
        "Variant",
        "Fuel Type",
        "Engine Type",
        "Engine Displacement",
        "Cylinder Count",
        "Max Power",
        "Max Torque",
        "Transmission",
        "Drivetrain",
        "Battery Capacity",
        "EV Range", "Charging",
        "Top Speed",
        "Acceleration 0-100",
        "Seats",
        "Overall Length",
        "Overall Width",
        "Overall Height",
        "Wheelbase",
        "Ground Clearance",
        "Fuel Tank", "Fuel Efficiency",
        "Wheels",
        "Tyre Size",
        "Source URL",
        "Research Source URLs",
        "Status",
    ]

    ordered = [
        column
        for column in preferred
        if column
        in specs_df.columns
    ]

    extras = [
        column
        for column
        in specs_df.columns
        if column
        not in ordered
    ]

    specs_df = specs_df[
        ordered + extras
    ]

    st.subheader(
        "Specifications"
    )

    st.dataframe(
        specs_df,
        hide_index=True,
        width="stretch",
    )

    excel_data = (
        create_excel(
            st.session_state[
                "models"
            ],
            specs_df
        )
    )

    st.download_button(
        "⬇️ Download Excel",
        data=excel_data,
        file_name=(
            "automotive_research.xlsx"
        ),
        mime=(
            "application/vnd."
            "openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        use_container_width=True,
    )
