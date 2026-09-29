import io
import re
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup


# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="Automotive Website Research",
    page_icon="🚗",
    layout="wide",
)

st.title("🚗 Automotive Website Research")
st.caption(
    "Website URL → Models → Variants → Specifications → Excel"
)


# =========================================================
# SETTINGS
# =========================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124 Safari/537.36"
    )
}

BRANDS = [
    "Acura", "Alfa Romeo", "Aston Martin", "Audi",
    "BAIC", "Bentley", "Bestune", "BMW", "BYD",
    "Cadillac", "Changan", "Chery", "Chevrolet",
    "Chrysler", "Denza", "Dodge", "Exeed", "FAW",
    "Ferrari", "Fiat", "Ford", "Foton", "GAC",
    "Geely", "Genesis", "GMC", "Great Wall",
    "GWM", "Haval", "Honda", "Hongqi", "Hyundai",
    "iCAUR", "Ineos", "Infiniti", "Isuzu", "JAC",
    "Jaecoo", "Jaguar", "Jeep", "Jetour", "Kia",
    "Lamborghini", "Land Rover", "Lexus", "Lincoln",
    "Lotus", "Maserati", "Mazda", "McLaren",
    "Mercedes-Benz", "MG", "MINI", "Mitsubishi",
    "Nissan", "Omoda", "Ora", "Peugeot", "Porsche",
    "RAM", "Renault", "Rolls-Royce", "Skoda",
    "Soueast", "Ssangyong", "Subaru", "Suzuki",
    "Tata", "Tesla", "Toyota", "Volkswagen",
    "Volvo", "Yangwang",
]

NOISE = {
    "",
    "home",
    "brand",
    "gallery",
    "features",
    "features.html",
    "specification",
    "specifications",
    "overview",
    "vehicles",
    "vehicle",
    "models",
    "model",
    "all models",
    "all vehicles",
    "cars",
    "car",
    "offers",
    "owners",
    "services",
    "shopping tools",
    "about",
    "contact",
    "contact us",
    "connect",
    "find a dealer",
    "request a quote",
    "test drive",
    "learn more",
    "explore more",
    "discover",
    "discover more",
    "view details",
    "build your kia tasman",
    "saudi arabia aljabr",
    "aljabr",
}

BAD_MODEL_WORDS = [
    "build your",
    "discover kia",
    "shopping",
    "request",
    "dealer",
    "service",
    "owner",
    "accessories",
    "warranty",
    "cookie",
    "privacy",
    "terms",
    "saudi arabia",
]

UI_NOISE = {
    "next",
    "prev",
    "previous",
    "close",
    "skip",
    "skip_entry",
    "play",
    "pause",
    "share",
    "download",
    "print",
    "gallery",
    "features",
    "specifications",
    "specification",
}


# =========================================================
# BASIC
# =========================================================

def clean(value):
    return re.sub(
        r"\s+",
        " ",
        str(value or "")
    ).strip()


def normalize_url(url):

    url = clean(url)

    if not url.startswith(
        ("http://", "https://")
    ):
        url = "https://" + url

    return url


def domain(url):

    return (
        urlparse(url)
        .netloc
        .lower()
        .replace("www.", "")
    )


def same_site(a, b):

    return domain(a) == domain(b)


def get_page(url):

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=40,
        allow_redirects=True,
    )

    response.raise_for_status()

    return (
        response.url,
        BeautifulSoup(
            response.text,
            "html.parser"
        ),
    )


# =========================================================
# MAKE
# =========================================================

def detect_make(soup, url):

    host = domain(url)

    compact_host = re.sub(
        r"[^a-z0-9]",
        "",
        host
    )

    for brand in sorted(
        BRANDS,
        key=len,
        reverse=True,
    ):

        compact_brand = re.sub(
            r"[^a-z0-9]",
            "",
            brand.lower()
        )

        if compact_brand in compact_host:
            return brand

    title = clean(
        soup.title.get_text(
            " ",
            strip=True
        )
        if soup.title
        else ""
    )

    for brand in sorted(
        BRANDS,
        key=len,
        reverse=True,
    ):

        if re.search(
            r"(?<![A-Za-z0-9])"
            + re.escape(brand)
            + r"(?![A-Za-z0-9])",
            title,
            re.I,
        ):
            return brand

    return host.split(".")[0].title()


# =========================================================
# MODEL
# =========================================================

def clean_model_name(name, make):

    name = clean(name)

    name = re.sub(
        r"^the\s+",
        "",
        name,
        flags=re.I,
    )

    name = re.sub(
        r"^"
        + re.escape(make)
        + r"\s+",
        "",
        name,
        flags=re.I,
    )

    return clean(name)


def valid_model(name, make):

    name = clean_model_name(
        name,
        make
    )

    if not name:
        return False

    lower = name.lower()

    if lower in NOISE:
        return False

    if lower == make.lower():
        return False

    if len(name) < 2 or len(name) > 45:
        return False

    if re.fullmatch(
        r"[\d\s.,]+",
        name
    ):
        return False

    if any(
        x in lower
        for x in BAD_MODEL_WORDS
    ):
        return False

    if lower.endswith(
        (".html", ".htm", ".php")
    ):
        return False

    return True


def model_from_url(url, make):

    parts = [
        p
        for p in
        urlparse(url)
        .path
        .strip("/")
        .split("/")
        if p
    ]

    ignore = {
        "en",
        "ar",
        "showroom",
        "models",
        "model",
        "vehicles",
        "vehicle",
        "cars",
        "car",
        "gallery.html",
        "overview.html",
        "features.html",
        "feature.html",
        "specification.html",
        "specifications.html",
    }

    usable = [
        p
        for p in parts
        if p.lower() not in ignore
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
            words.append(
                word.upper()
            )
        else:
            words.append(
                word.title()
            )

    return clean_model_name(
        " ".join(words),
        make
    )


# =========================================================
# FIND MODELS
# =========================================================

def find_models(
    soup,
    base_url,
    make
):

    rows = []

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

        path = (
            urlparse(href)
            .path
            .lower()
        )

        looks_vehicle = any(
            x in path
            for x in [
                "/showroom/",
                "/models/",
                "/model/",
                "/vehicles/",
                "/vehicle/",
            ]
        )

        if not looks_vehicle:
            continue

        model = model_from_url(
            href,
            make
        )

        if not valid_model(
            model,
            make
        ):
            continue

        rows.append({
            "Make": make,
            "Model": model,
            "Model URL": href,
        })

    if not rows:

        return pd.DataFrame(
            columns=[
                "Make",
                "Model",
                "Model URL",
            ]
        )

    df = pd.DataFrame(rows)

    def score_url(url):

        url = url.lower()

        score = 0

        if "/showroom/" in url:
            score += 10

        if "gallery.html" in url:
            score += 6

        if "overview.html" in url:
            score += 5

        if "features.html" in url:
            score += 4

        if "specification" in url:
            score += 3

        return score

    df["score"] = (
        df["Model URL"]
        .map(score_url)
    )

    df = (
        df.sort_values(
            ["Model", "score"],
            ascending=[
                True,
                False,
            ]
        )
        .drop_duplicates(
            ["Make", "Model"],
            keep="first"
        )
        .drop(
            columns=["score"]
        )
        .reset_index(
            drop=True
        )
    )

    return df


# =========================================================
# SPEC URL
# =========================================================

def find_spec_page(model_url):

    try:

        final_url, soup = get_page(
            model_url
        )

    except Exception:

        return model_url

    for a in soup.find_all(
        "a",
        href=True
    ):

        label = clean(
            a.get_text(
                " ",
                strip=True
            )
        ).lower()

        href = urljoin(
            final_url,
            a.get("href")
        )

        if (
            "specification" in label
            or
            "specifications" in label
            or
            "technical specification" in label
            or
            "specification" in href.lower()
        ):

            return href

    replacements = [
        "gallery.html",
        "features.html",
        "overview.html",
    ]

    for old in replacements:

        if old in final_url.lower():

            return re.sub(
                re.escape(old),
                "specification.html",
                final_url,
                flags=re.I,
            )

    return final_url


# =========================================================
# CLEAN SPEC LABEL
# =========================================================

def clean_label(label):

    label = clean(label)

    label = re.sub(
        r"[:：]+$",
        "",
        label
    )

    return clean(label)


def valid_spec_label(label):

    label = clean_label(label)

    if not label:
        return False

    if len(label) > 100:
        return False

    if label.lower() in UI_NOISE:
        return False

    if re.fullmatch(
        r"[0-9,.]+",
        label
    ):
        return False

    return True


# =========================================================
# CANONICAL SPEC NAME
# =========================================================

def canonical_label(label):

    original = clean_label(label)

    x = original.lower()

    aliases = {

        "Engine Displacement": [
            "engine displacement",
            "displacement",
            "engine capacity",
        ],

        "Engine Type": [
            "engine type",
        ],

        "Cylinder Count": [
            "number of cylinders",
            "cylinders",
            "cylinder",
        ],

        "Fuel Type": [
            "fuel type",
            "fuel",
        ],

        "Max Power": [
            "maximum power",
            "max power",
            "engine power",
            "power output",
            "horsepower",
        ],

        "Max Torque": [
            "maximum torque",
            "max torque",
            "torque",
        ],

        "Transmission": [
            "transmission",
            "transmission type",
            "gearbox",
        ],

        "Drivetrain": [
            "drivetrain",
            "drive type",
            "drive system",
        ],

        "Battery Capacity": [
            "battery capacity",
            "battery pack capacity",
            "battery size",
        ],

        "Electric Range": [
            "electric range",
            "driving range",
            "ev range",
            "range",
        ],

        "Charging Time": [
            "charging time",
            "charge time",
        ],

        "AC Charging": [
            "ac charging",
            "ac charger",
        ],

        "DC Charging": [
            "dc charging",
            "fast charging",
            "dc fast charging",
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

        "Seats": [
            "seating capacity",
            "seat capacity",
            "number of seats",
            "seats",
        ],

        "Fuel Tank": [
            "fuel tank capacity",
            "fuel tank",
            "tank capacity",
        ],

        "Cargo Capacity": [
            "cargo capacity",
            "cargo volume",
            "boot capacity",
        ],

        "Top Speed": [
            "top speed",
            "maximum speed",
        ],

        "Acceleration": [
            "acceleration",
            "0-100",
            "0–100",
        ],
    }

    for standard, names in (
        aliases.items()
    ):

        for name in names:

            if (
                x == name
                or x.startswith(
                    name + " "
                )
            ):
                return standard

    return original


# =========================================================
# TABLE → VARIANT ROWS
# =========================================================

def extract_table_rows(
    soup,
    make,
    model,
    source_url
):

    all_rows = []

    for table in soup.find_all(
        "table"
    ):

        trs = table.find_all(
            "tr"
        )

        matrix = []

        for tr in trs:

            cells = [
                clean(
                    cell.get_text(
                        " ",
                        strip=True
                    )
                )
                for cell
                in tr.find_all(
                    ["th", "td"]
                )
            ]

            cells = [
                x
                for x in cells
                if x
            ]

            if cells:
                matrix.append(cells)

        if len(matrix) < 2:
            continue

        max_cols = max(
            len(row)
            for row in matrix
        )

        # -------------------------------------------------
        # FORMAT:
        #
        # Specification | GT-Line | Base model
        # Length        | 4710    | 4710
        # Width         | 1850    | 1850
        #
        # -------------------------------------------------

        if max_cols >= 3:

            first = matrix[0]

            possible_variants = (
                first[1:]
                if len(first) >= 3
                else []
            )

            variant_like = (
                len(possible_variants) >= 2
                and
                all(
                    len(x) <= 50
                    for x
                    in possible_variants
                )
            )

            if variant_like:

                rows = []

                for variant in (
                    possible_variants
                ):

                    rows.append({
                        "Make": make,
                        "Model": model,
                        "Variant": variant,
                        "Source URL": source_url,
                    })

                for data_row in matrix[1:]:

                    if len(data_row) < 2:
                        continue

                    label = (
                        canonical_label(
                            data_row[0]
                        )
                    )

                    if not valid_spec_label(
                        label
                    ):
                        continue

                    values = (
                        data_row[1:]
                    )

                    for index, value in enumerate(
                        values
                    ):

                        if index >= len(rows):
                            break

                        rows[index][
                            label
                        ] = value

                if rows:
                    all_rows.extend(
                        rows
                    )

    return all_rows


# =========================================================
# KIA DIMENSIONS + VARIANTS
# =========================================================

def extract_kia_dimensions(
    soup,
    make,
    model,
    source_url
):

    lines = [
        clean(x)
        for x in
        soup.get_text(
            "\n",
            strip=True
        ).splitlines()
        if clean(x)
    ]

    dimensions = [
        "Overall length",
        "Overall width",
        "Overall height",
        "Wheelbase",
    ]

    positions = {}

    for label in dimensions:

        for i, line in enumerate(
            lines
        ):

            if (
                line.lower()
                == label.lower()
            ):

                positions[
                    label
                ] = i

                break

    if not positions:
        return []

    first_position = min(
        positions.values()
    )

    last_position = max(
        positions.values()
    )

    # Look before dimension labels for variants
    before = lines[
        max(
            0,
            first_position - 25
        ):
        first_position
    ]

    variants = []

    known_variant_words = [
        "base model",
        "gt-line",
        "gt line",
        "standard",
        "premium",
        "luxury",
        "executive",
        "sport",
        "ex",
        "lx",
        "sx",
        "gx",
    ]

    for line in before:

        low = line.lower()

        if (
            low in known_variant_words
            and
            line not in variants
        ):
            variants.append(
                line
            )

    # Kia fallback from observed pages
    if not variants:

        full = " ".join(lines)

        if re.search(
            r"\bGT[- ]Line\b",
            full,
            re.I,
        ):
            variants.append(
                "GT-Line"
            )

        if re.search(
            r"\bBase model\b",
            full,
            re.I,
        ):
            variants.append(
                "Base model"
            )

    # Dimension values
    numbers = []

    for line in lines[
        last_position + 1:
        last_position + 60
    ]:

        if re.fullmatch(
            r"[0-9,]{3,}(?:\.[0-9]+)?",
            line
        ):

            numbers.append(
                line
            )

    # Do not deduplicate:
    # same value can belong to multiple variants.
    label_order = [
        x
        for x in dimensions
        if x in positions
    ]

    if not variants:

        variants = [""]

    rows = []

    number_index = 0

    for variant in variants:

        row = {
            "Make": make,
            "Model": model,
            "Variant": variant,
            "Source URL": source_url,
        }

        for label in label_order:

            if number_index < len(numbers):

                row[
                    canonical_label(label)
                ] = (
                    numbers[number_index]
                    + " mm"
                )

                number_index += 1

        rows.append(row)

    # Sometimes dimensions are displayed once but apply
    # to every variant.
    if (
        len(variants) > 1
        and
        len(numbers)
        == len(label_order)
    ):

        for row in rows:

            for i, label in enumerate(
                label_order
            ):

                row[
                    canonical_label(label)
                ] = (
                    numbers[i]
                    + " mm"
                )

    return rows


# =========================================================
# GENERIC KEY VALUE SPECS
# =========================================================

def extract_key_values(soup):

    specs = {}

    # TABLES
    for tr in soup.find_all(
        "tr"
    ):

        cells = [
            clean(
                x.get_text(
                    " ",
                    strip=True
                )
            )
            for x
            in tr.find_all(
                ["th", "td"]
            )
        ]

        cells = [
            x
            for x in cells
            if x
        ]

        if len(cells) == 2:

            label = (
                canonical_label(
                    cells[0]
                )
            )

            value = cells[1]

            if valid_spec_label(
                label
            ):

                specs[
                    label
                ] = value

    # DT DD
    for dt in soup.find_all(
        "dt"
    ):

        dd = dt.find_next_sibling(
            "dd"
        )

        if not dd:
            continue

        label = (
            canonical_label(
                dt.get_text(
                    " ",
                    strip=True
                )
            )
        )

        value = clean(
            dd.get_text(
                " ",
                strip=True
            )
        )

        if (
            valid_spec_label(label)
            and value
        ):

            specs[
                label
            ] = value

    return specs


# =========================================================
# TEXT FALLBACK
# =========================================================

def text_fallback_specs(soup):

    text = clean(
        soup.get_text(
            " ",
            strip=True
        )
    )

    result = {}

    patterns = {

        "Engine Displacement": [
            r"(?i)\b([0-9,]{3,4})\s*cc\b",

            (
                r"(?i)\b"
                r"([0-9.]+\s*[Ll])"
                r"\s+(?:engine|turbo)"
            ),
        ],

        "Max Power": [
            (
                r"(?i)"
                r"(?:maximum|max\.?)?\s*"
                r"(?:power|horsepower)"
                r"[^0-9]{0,35}"
                r"([0-9.,]+\s*"
                r"(?:hp|ps|kw|bhp))"
            ),
        ],

        "Max Torque": [
            (
                r"(?i)"
                r"(?:maximum|max\.?)?\s*"
                r"torque"
                r"[^0-9]{0,35}"
                r"([0-9.,]+\s*"
                r"(?:nm|n\.m))"
            ),
        ],

        "Battery Capacity": [
            (
                r"(?i)"
                r"battery"
                r"(?:\s+capacity|\s+pack|\s+size)?"
                r"[^0-9]{0,40}"
                r"([0-9.,]+\s*kwh)"
            ),
        ],

        "Electric Range": [
            (
                r"(?i)"
                r"(?:electric\s+|driving\s+|ev\s+|wltp\s+)?"
                r"range"
                r"[^0-9]{0,40}"
                r"([0-9.,]+\s*km)"
            ),
        ],

        "Charging Time": [
            (
                r"(?i)"
                r"(?:charging|charge)\s+time"
                r"[^0-9]{0,30}"
                r"([0-9.,]+\s*"
                r"(?:min|minutes|hours|hrs))"
            ),
        ],

        "Fuel Tank": [
            (
                r"(?i)"
                r"(?:fuel\s+)?tank"
                r"(?:\s+capacity)?"
                r"[^0-9]{0,30}"
                r"([0-9.,]+\s*"
                r"(?:l|liters|litres))"
            ),
        ],

        "Top Speed": [
            (
                r"(?i)"
                r"(?:top|max(?:imum)?)"
                r"\s+speed"
                r"[^0-9]{0,30}"
                r"([0-9.,]+\s*km/?h)"
            ),
        ],

        "Seats": [
            (
                r"(?i)"
                r"(?:seating capacity|seat capacity|seats)"
                r"[^0-9]{0,20}"
                r"([2-9])"
            ),
        ],
    }

    for field, regexes in (
        patterns.items()
    ):

        for pattern in regexes:

            match = re.search(
                pattern,
                text
            )

            if match:

                result[
                    field
                ] = clean(
                    match.group(1)
                )

                break

    # Transmission
    transmission_patterns = [
        r"\b(\d+[- ]speed automatic)\b",
        r"\b(\d+[- ]speed manual)\b",
        r"\b(\d+[- ]speed DCT)\b",
        r"\b(e-CVT)\b",
        r"\b(CVT)\b",
        r"\b(DCT)\b",
    ]

    for pattern in (
        transmission_patterns
    ):

        match = re.search(
            pattern,
            text,
            re.I,
        )

        if match:

            result[
                "Transmission"
            ] = clean(
                match.group(1)
            )

            break

    # Drivetrain
    drive = re.search(
        r"\b(AWD|4WD|4X4|FWD|RWD)\b",
        text,
        re.I,
    )

    if drive:

        result[
            "Drivetrain"
        ] = (
            drive.group(1)
            .upper()
        )

    # Powertrain
    powertrains = []

    checks = [
        (
            "PHEV",
            r"\bPHEV\b|plug-in hybrid"
        ),
        (
            "HEV",
            r"\bHEV\b|\bhybrid\b"
        ),
        (
            "BEV",
            r"\bBEV\b|battery electric"
        ),
        (
            "EV",
            r"\belectric vehicle\b"
        ),
        (
            "Diesel",
            r"\bdiesel\b"
        ),
        (
            "Gasoline",
            r"\bgasoline\b|\bpetrol\b"
        ),
    ]

    for name, pattern in checks:

        if re.search(
            pattern,
            text,
            re.I,
        ):

            powertrains.append(
                name
            )

    if powertrains:

        result[
            "Fuel / Powertrain"
        ] = ", ".join(
            dict.fromkeys(
                powertrains
            )
        )

    return result


# =========================================================
# WHEELS
# =========================================================

def extract_wheels(soup):

    lines = [
        clean(x)
        for x in
        soup.get_text(
            "\n",
            strip=True
        ).splitlines()
        if clean(x)
    ]

    values = []

    for line in lines:

        if re.search(
            r"\b\d{2}[- ]inch\b",
            line,
            re.I,
        ):

            if (
                len(line) <= 160
                and
                line not in values
            ):

                values.append(
                    line
                )

    if values:

        return " | ".join(
            values[:8]
        )

    return ""


# =========================================================
# COMPLETE SPEC EXTRACTION
# =========================================================

def extract_specs(
    model_url,
    make,
    model
):

    spec_url = find_spec_page(
        model_url
    )

    try:

        final_url, soup = get_page(
            spec_url
        )

    except Exception as error:

        return [{
            "Make": make,
            "Model": model,
            "Variant": "",
            "Source URL": spec_url,
            "Error": str(error),
        }]

    # -----------------------------------------------------
    # First try real HTML table variants
    # -----------------------------------------------------

    rows = extract_table_rows(
        soup,
        make,
        model,
        final_url,
    )

    # -----------------------------------------------------
    # Kia-style variant/dimension layout
    # -----------------------------------------------------

    if not rows:

        rows = extract_kia_dimensions(
            soup,
            make,
            model,
            final_url,
        )

    # -----------------------------------------------------
    # At least one row
    # -----------------------------------------------------

    if not rows:

        rows = [{
            "Make": make,
            "Model": model,
            "Variant": "",
            "Source URL": final_url,
        }]

    # -----------------------------------------------------
    # Generic specs
    # -----------------------------------------------------

    generic = extract_key_values(
        soup
    )

    fallback = text_fallback_specs(
        soup
    )

    wheels = extract_wheels(
        soup
    )

    # -----------------------------------------------------
    # Apply common specs to each variant.
    #
    # Variant-specific table values already present
    # will NOT be overwritten.
    # -----------------------------------------------------

    for row in rows:

        for key, value in (
            generic.items()
        ):

            if not row.get(key):

                row[key] = value

        for key, value in (
            fallback.items()
        ):

            if not row.get(key):

                row[key] = value

        if (
            wheels
            and
            not row.get("Wheels")
        ):

            row[
                "Wheels"
            ] = wheels

    return rows


# =========================================================
# EXCEL
# =========================================================

def create_excel(
    models_df,
    specs_df
):

    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        models_df.to_excel(
            writer,
            index=False,
            sheet_name="Models",
        )

        if not specs_df.empty:

            specs_df.to_excel(
                writer,
                index=False,
                sheet_name="Specs",
            )

    return output.getvalue()


# =========================================================
# UI
# =========================================================

url = st.text_input(
    "Website URL",
    placeholder=(
        "https://www.kia.com/sa/en/main.html"
    ),
)


if st.button(
    "🔎 Research Website",
    type="primary",
    use_container_width=True,
):

    if not clean(url):

        st.warning(
            "ใส่ URL ก่อนค่ะ"
        )

        st.stop()

    try:

        with st.spinner(
            "กำลังอ่านเว็บไซต์..."
        ):

            final_url, soup = get_page(
                normalize_url(url)
            )

            make = detect_make(
                soup,
                final_url
            )

            models_df = find_models(
                soup,
                final_url,
                make,
            )

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
            f"อ่านเว็บไซต์ไม่ได้: {error}"
        )


# =========================================================
# MODEL RESULTS
# =========================================================

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
        ),
    )

    c2.metric(
        "Models found",
        len(models_df),
    )

    st.subheader(
        "Models"
    )

    if models_df.empty:

        st.warning(
            "ยังไม่พบ Model จากเว็บไซต์นี้"
        )

    else:

        selection = (
            models_df.copy()
        )

        selection.insert(
            0,
            "Research Specs",
            False,
        )

        edited = st.data_editor(
            selection,
            hide_index=True,
            use_container_width=True,

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

        if st.button(
            "⚙️ Get Specs",
            use_container_width=True,
        ):

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

                results = []

                progress = st.progress(0)

                status = st.empty()

                total = len(selected)

                for number, (
                    _,
                    row
                ) in enumerate(
                    selected.iterrows(),
                    start=1,
                ):

                    status.write(
                        f"กำลังอ่าน "
                        f"{row['Make']} "
                        f"{row['Model']} "
                        f"({number}/{total})"
                    )

                    model_rows = (
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

                    results.extend(
                        model_rows
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
                    results
                )


# =========================================================
# DISPLAY RESULTS
# =========================================================

specs_df = (
    st.session_state.get(
        "specs",
        pd.DataFrame()
    )
)

if not specs_df.empty:

    specs_df = (
        specs_df
        .replace(
            "",
            pd.NA
        )
        .dropna(
            axis=1,
            how="all"
        )
        .fillna("")
    )

    # Important columns first
    first_columns = [
        "Make",
        "Model",
        "Variant",
        "Fuel / Powertrain",
        "Engine Type",
        "Engine Displacement",
        "Cylinder Count",
        "Max Power",
        "Max Torque",
        "Transmission",
        "Drivetrain",
        "Battery Capacity",
        "Electric Range",
        "Charging Time",
        "AC Charging",
        "DC Charging",
        "Seats",
        "Overall Length",
        "Overall Width",
        "Overall Height",
        "Wheelbase",
        "Ground Clearance",
        "Fuel Tank",
        "Cargo Capacity",
        "Wheels",
        "Top Speed",
        "Acceleration",
        "Source URL",
    ]

    ordered = [
        c
        for c in first_columns
        if c in specs_df.columns
    ]

    extras = [
        c
        for c in specs_df.columns
        if c not in ordered
    ]

    specs_df = specs_df[
        ordered + extras
    ]

    st.subheader(
        "Research Results"
    )

    st.dataframe(
        specs_df,
        hide_index=True,
        use_container_width=True,

        column_config={
            "Source URL":
                st.column_config.LinkColumn(
                    "Source URL"
                )
        },
    )

    excel = create_excel(
        st.session_state[
            "models"
        ],
        specs_df,
    )

    st.download_button(
        "⬇️ Download Excel",
        data=excel,
        file_name=(
            "automotive_research.xlsx"
        ),
        mime=(
            "application/"
            "vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        use_container_width=True,
    )


st.caption(
    "Source-only extraction: "
    "ถ้าเว็บไซต์ไม่มีข้อมูล ช่องนั้นจะว่าง "
    "ระบบไม่สร้างค่าขึ้นเอง"
)
