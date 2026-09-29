import io
import re
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
        BeautifulSoup(response.text, "html.parser"),
    )


# ============================================================
# MAKE
# ============================================================

def detect_make(soup, url):

    domain_text = re.sub(
        r"[^a-z0-9]",
        "",
        host(url)
    )

    for brand in sorted(BRANDS, key=len, reverse=True):

        b = re.sub(
            r"[^a-z0-9]",
            "",
            brand.lower()
        )

        if b in domain_text:
            return brand

    title = clean(
        soup.title.get_text(" ", strip=True)
        if soup.title else ""
    )

    for brand in sorted(BRANDS, key=len, reverse=True):

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
# MODEL
# ============================================================

def model_from_url(url):

    path = urlparse(url).path

    parts = [
        x for x in path.split("/")
        if x
    ]

    ignored = {
        "en", "ar", "showroom", "model", "models",
        "vehicle", "vehicles", "cars", "car",
        "gallery.html", "features.html",
        "overview.html", "specification.html",
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

    value = value.replace("-", " ").replace("_", " ")

    words = []

    for word in value.split():

        if len(word) <= 3 or re.search(r"\d", word):
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

    if any(x in low for x in BAD_MODEL_PHRASES):
        return False

    if re.fullmatch(r"[\d\s.,]+", model):
        return False

    return True


def find_models(soup, base_url, make):

    results = []

    for a in soup.find_all("a", href=True):

        href = urljoin(
            base_url,
            a.get("href")
        )

        if not same_site(base_url, href):
            continue

        path = urlparse(href).path.lower()

        if not any(
            x in path
            for x in [
                "/showroom/",
                "/models/",
                "/model/",
                "/vehicles/",
                "/vehicle/",
            ]
        ):
            continue

        model = model_from_url(href)

        if not valid_model(model, make):
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

        s = 0

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


def get_model_pages(model_url):

    base = model_base_url(model_url)

    candidates = {
        "Specification": urljoin(
            base,
            "specification.html"
        ),
        "Features": urljoin(
            base,
            "features.html"
        ),
        "Overview": urljoin(
            base,
            "overview.html"
        ),
        "Gallery": urljoin(
            base,
            "gallery.html"
        ),
    }

    pages = {}

    for name, url in candidates.items():

        try:
            final_url, soup = get_page(url)

            if soup.get_text(" ", strip=True):
                pages[name] = (
                    final_url,
                    soup
                )

        except Exception:
            pass

    if not pages:

        try:
            final_url, soup = get_page(model_url)

            pages["Model"] = (
                final_url,
                soup
            )

        except Exception:
            pass

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
         ["fuel type"]),

        ("Max Power",
         ["maximum power", "max power",
          "engine power", "power output"]),

        ("Max Torque",
         ["maximum torque", "max torque",
          "torque"]),

        ("Transmission",
         ["transmission type", "transmission",
          "gearbox"]),

        ("Drivetrain",
         ["drive system", "drive type",
          "drivetrain"]),

        ("Motor Type",
         ["motor type"]),

        ("Front Motor Max Power",
         ["electric motor (front) max power"]),

        ("Front Motor Max Torque",
         ["electric motor (front) max torque"]),

        ("Rear Motor Max Power",
         ["electric motor (rear) max power"]),

        ("Rear Motor Max Torque",
         ["electric motor (rear) max torque"]),

        ("Total Motor Max Power",
         ["electric motor (total) max power"]),

        ("Total Motor Max Torque",
         ["electric motor (total) max torque"]),

        ("Battery Type",
         ["battery system type",
          "hybrid battery system type",
          "battery type"]),

        ("Battery Capacity",
         ["hybrid battery capacity",
          "battery capacity"]),

        ("AC Charge Port",
         ["ac / dc charge port type",
          "charge port type"]),

        ("AC Charging Power",
         ["on board charger (ac) maximum capacity",
          "ac charging power"]),

        ("DC Charging Power",
         ["on board charger (dc) maximum capacity",
          "dc charging power"]),

        ("AC Charging Time",
         ["charging duration from 10% to 100% with ac",
          "ac charging time"]),

        ("DC Charging Time",
         ["charging duration from 10% to 80% with dc",
          "dc charging time"]),

        ("Range NEDC",
         ["electric driving range nedc",
          "nedc range"]),

        ("Range WLTP",
         ["electric driving range wltp",
          "wltp range", "drive range (wltp)"]),

        ("Top Speed",
         ["max speed", "maximum speed",
          "top speed"]),

        ("Acceleration 0-100",
         ["accerelation 0-100",
          "acceleration 0-100",
          "0 - 100km/h",
          "0-100"]),

        ("Seats",
         ["seating capacity", "seat capacity",
          "number of seats"]),

        ("Fuel Tank",
         ["fuel tank capacity", "fuel tank"]),

        ("Wheel Type",
         ["wheel type", "alloy rims"]),

        ("Tyre Size",
         ["tyre size", "tire size"]),
    ]

    for standard, names in aliases:

        for name in names:

            if (
                low == name
                or low.startswith(name + " ")
                or name in low
            ):
                return standard

    return label


# ============================================================
# PARSE HTML TABLES PROPERLY
# ============================================================

def html_table_matrix(table):

    matrix = []

    for tr in table.find_all("tr"):

        cells = []

        for cell in tr.find_all(
            ["th", "td"],
            recursive=False
        ):

            value = clean(
                cell.get_text(
                    " ",
                    strip=True
                )
            )

            cells.append(value)

        if cells:
            matrix.append(cells)

    return matrix


def parse_standard_table(
    matrix,
    make,
    model,
    source_url
):

    if len(matrix) < 2:
        return []

    # Most normal spec tables:
    #
    # Feature | Variant A | Variant B
    # Length  | 4710      | 4710

    header = matrix[0]

    if len(header) < 2:
        return []

    variants = [
        clean(x)
        for x in header[1:]
        if clean(x)
    ]

    if not variants:
        return []

    rows = []

    for variant in variants:

        rows.append({
            "Make": make,
            "Model": model,
            "Variant": variant,
            "Source URL": source_url,
        })

    for line in matrix[1:]:

        if len(line) < 2:
            continue

        label = canonical_label(
            line[0]
        )

        values = line[1:]

        for i, value in enumerate(values):

            if i >= len(rows):
                break

            if value:
                rows[i][label] = value

    return rows


# ============================================================
# KIA "TABLE FIX AREA" PARSER
# ============================================================

def kia_fixed_table_parser(
    soup,
    make,
    model,
    source_url
):

    """
    Kia Saudi uses a visually rendered table where the DOM can
    contain labels and values as separate groups rather than a
    conventional <table>. This parser reads the exact sequence.
    """

    lines = [
        clean(x)
        for x in
        soup.get_text(
            "\n",
            strip=True
        ).splitlines()
        if clean(x)
    ]

    # --------------------------------------------------------
    # Dimension labels
    # --------------------------------------------------------

    dimension_aliases = {
        "overall length": "Overall Length",
        "overall width": "Overall Width",
        "overall height": "Overall Height",
        "overall hight": "Overall Height",
        "wheelbase": "Wheelbase",
    }

    label_positions = []

    for i, line in enumerate(lines):

        low = line.lower().strip()

        if low in dimension_aliases:

            label_positions.append(
                (
                    i,
                    dimension_aliases[low]
                )
            )

    if len(label_positions) < 3:
        return []

    # use first dimension block only
    start = label_positions[0][0]

    selected_labels = []

    last_label_position = start

    for pos, label in label_positions:

        if pos - start > 20:
            break

        selected_labels.append(label)
        last_label_position = pos

    if len(selected_labels) < 3:
        return []

    # --------------------------------------------------------
    # Find variants AFTER labels
    # --------------------------------------------------------

    after_labels = lines[
        last_label_position + 1:
        last_label_position + 25
    ]

    variants = []

    variant_patterns = [
        r"^GT[- ]?Line$",
        r"^Base model$",
        r"^Standard$",
        r"^Premium$",
        r"^Luxury$",
        r"^Executive$",
        r"^EX$",
        r"^LX$",
        r"^SX$",
        r"^GX$",
    ]

    first_numeric_index = None

    for i, value in enumerate(after_labels):

        # dimension number
        if re.fullmatch(
            r"\d[\d,.]*",
            value
        ):
            first_numeric_index = i
            break

        if any(
            re.match(
                pattern,
                value,
                re.I
            )
            for pattern in variant_patterns
        ):
            variants.append(value)

    variants = list(
        dict.fromkeys(variants)
    )

    if not variants:
        variants = [""]

    # --------------------------------------------------------
    # Extract numbers
    # --------------------------------------------------------

    if first_numeric_index is None:

        for i, value in enumerate(after_labels):

            if re.fullmatch(
                r"\d[\d,.]*",
                value
            ):
                first_numeric_index = i
                break

    if first_numeric_index is None:
        return []

    numeric_lines = []

    for value in after_labels[
        first_numeric_index:
    ]:

        if re.fullmatch(
            r"\d[\d,.]*",
            value
        ):
            numeric_lines.append(value)

        elif numeric_lines:
            break

    variant_count = len(variants)
    label_count = len(selected_labels)

    needed = (
        variant_count
        * label_count
    )

    # --------------------------------------------------------
    # Kia layout is:
    #
    # GT-Line | Base model
    # 4710    | 4710
    # 1850    | 1850
    # 1435    | 1435
    # 2720    | 2720
    #
    # Thus numeric order is SPEC-FIRST, not variant-first.
    # --------------------------------------------------------

    rows = []

    for variant in variants:

        rows.append({
            "Make": make,
            "Model": model,
            "Variant": variant,
            "Source URL": source_url,
        })

    if len(numeric_lines) >= needed:

        pointer = 0

        for label in selected_labels:

            for variant_index in range(
                variant_count
            ):

                value = numeric_lines[
                    pointer
                ]

                pointer += 1

                # Kia Saudi sometimes writes EV5 length 4.615
                # although dimensions are mm. Convert only
                # dimension values that clearly represent metres.
                normalized = value

                try:
                    number = float(
                        value.replace(",", "")
                    )

                    if (
                        "." in value
                        and
                        number < 10
                    ):
                        number *= 1000

                        normalized = (
                            f"{int(round(number)):,}"
                        )

                except Exception:
                    pass

                rows[
                    variant_index
                ][label] = (
                    normalized + " mm"
                )

    elif len(numeric_lines) >= label_count:

        # dimensions shown once and apply to all variants
        for label, value in zip(
            selected_labels,
            numeric_lines
        ):

            for row in rows:

                row[label] = (
                    value + " mm"
                )

    else:
        return []

    return rows


# ============================================================
# GENERIC TABLE COLLECTION
# ============================================================

def extract_generic_tables(
    soup,
    make,
    model,
    source_url
):

    output = []

    for table in soup.find_all("table"):

        matrix = html_table_matrix(table)

        parsed = parse_standard_table(
            matrix,
            make,
            model,
            source_url
        )

        if parsed:
            output.extend(parsed)

    return output


# ============================================================
# ENGINE OPTIONS FROM FEATURES
# ============================================================

def extract_engine_options(soup):

    text = clean(
        soup.get_text(
            " ",
            strip=True
        )
    )

    results = []

    # Example:
    # 1.6T engine with 190 PS and 265 Nm of torque, (8 A/T)

    pattern = re.compile(
        r"\b"
        r"(\d+(?:\.\d+)?T?)"
        r"\s*(?:L\s*)?"
        r"engine"
        r".{0,30}?"
        r"(\d+(?:\.\d+)?)\s*(PS|HP|kW)"
        r".{0,30}?"
        r"(\d+(?:\.\d+)?)\s*Nm"
        r".{0,40}?"
        r"\(?(\d+)\s*A/T\)?",
        re.I,
    )

    for match in pattern.finditer(text):

        displacement = match.group(1)
        power = (
            match.group(2)
            + " "
            + match.group(3).upper()
        )
        torque = (
            match.group(4)
            + " Nm"
        )
        transmission = (
            match.group(5)
            + "-speed Automatic"
        )

        result = {
            "Engine": displacement + "L",
            "Max Power": power,
            "Max Torque": torque,
            "Transmission": transmission,
        }

        if result not in results:
            results.append(result)

    return results


# ============================================================
# FALLBACK REGEX
# ============================================================

def extract_fallback_specs(soup):

    text = clean(
        soup.get_text(
            " ",
            strip=True
        )
    )

    result = {}

    patterns = {
        "Engine Displacement": [
            r"\b([0-9,]{3,4})\s*cc\b",
        ],

        "Battery Capacity": [
            r"(?i)battery.{0,40}?([0-9.]+\s*kWh)",
        ],

        "Range WLTP": [
            r"(?i)WLTP.{0,40}?([0-9,.]+\s*km)",
        ],

        "Range NEDC": [
            r"(?i)NEDC.{0,40}?([0-9,.]+\s*km)",
        ],

        "Top Speed": [
            r"(?i)(?:top|max(?:imum)?)\s+speed"
            r".{0,30}?([0-9,.]+\s*km/?h)",
        ],

        "Seats": [
            r"(?i)(?:seating capacity|seat capacity)"
            r".{0,20}?([2-9])",
        ],
    }

    for field, expressions in patterns.items():

        for expression in expressions:

            match = re.search(
                expression,
                text
            )

            if match:

                result[field] = clean(
                    match.group(1)
                )

                break

    transmission = re.search(
        r"\b(\d+)\s*(?:speed|A/T)",
        text,
        re.I,
    )

    if transmission:

        result.setdefault(
            "Transmission",
            transmission.group(1)
            + "-speed"
        )

    drivetrain = re.search(
        r"\b(FWD|RWD|AWD|4WD|4X4)\b",
        text,
        re.I,
    )

    if drivetrain:

        result["Drivetrain"] = (
            drivetrain
            .group(1)
            .upper()
        )

    return result


# ============================================================
# WHEELS
# ============================================================

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

    results = []

    for line in lines:

        if re.search(
            r"\b\d{2}[\"”']?\s*(?:inch|alloy|steel|wheel)",
            line,
            re.I,
        ):

            if (
                len(line) <= 130
                and
                line not in results
            ):
                results.append(line)

    return " | ".join(
        results[:10]
    )


# ============================================================
# MERGE VARIANT TABLES
# ============================================================

def merge_rows(base_rows, extra_rows):

    if not extra_rows:
        return base_rows

    if not base_rows:
        return extra_rows

    for extra in extra_rows:

        variant = clean(
            extra.get(
                "Variant",
                ""
            )
        ).lower()

        target = None

        if variant:

            for row in base_rows:

                if clean(
                    row.get(
                        "Variant",
                        ""
                    )
                ).lower() == variant:

                    target = row
                    break

        if target is None:
            continue

        for key, value in extra.items():

            if (
                key not in {
                    "Make",
                    "Model",
                    "Variant",
                    "Source URL",
                }
                and value
                and not target.get(key)
            ):
                target[key] = value

    return base_rows


# ============================================================
# COMPLETE MODEL EXTRACTION
# ============================================================

def extract_specs(
    model_url,
    make,
    model
):

    pages = get_model_pages(
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

    rows = []

    # --------------------------------------------------------
    # SPECIFICATION PAGE
    # --------------------------------------------------------

    if "Specification" in pages:

        spec_url, spec_soup = (
            pages["Specification"]
        )

        # First try real HTML tables
        generic_rows = (
            extract_generic_tables(
                spec_soup,
                make,
                model,
                spec_url,
            )
        )

        # Kia custom layout
        kia_rows = (
            kia_fixed_table_parser(
                spec_soup,
                make,
                model,
                spec_url,
            )
        )

        # Prefer Kia parser when it successfully
        # identifies variants + dimensions.
        if kia_rows:
            rows = kia_rows
            rows = merge_rows(
                rows,
                generic_rows
            )

        elif generic_rows:
            rows = generic_rows

        if not rows:

            rows = [{
                "Make": make,
                "Model": model,
                "Variant": "",
                "Source URL": spec_url,
            }]

        wheels = extract_wheels(
            spec_soup
        )

        fallback = (
            extract_fallback_specs(
                spec_soup
            )
        )

        for row in rows:

            if wheels:
                row.setdefault(
                    "Wheels",
                    wheels
                )

            for key, value in (
                fallback.items()
            ):

                row.setdefault(
                    key,
                    value
                )

    # --------------------------------------------------------
    # NO SPEC PAGE
    # --------------------------------------------------------

    if not rows:

        first_name = next(
            iter(pages)
        )

        first_url, first_soup = (
            pages[first_name]
        )

        rows = [{
            "Make": make,
            "Model": model,
            "Variant": "",
            "Source URL": first_url,
        }]

    # --------------------------------------------------------
    # FEATURES PAGE
    # --------------------------------------------------------

    if "Features" in pages:

        feature_url, feature_soup = (
            pages["Features"]
        )

        engines = extract_engine_options(
            feature_soup
        )

        feature_fallback = (
            extract_fallback_specs(
                feature_soup
            )
        )

        for row in rows:

            for key, value in (
                feature_fallback.items()
            ):
                row.setdefault(
                    key,
                    value
                )

        # Do NOT pretend engine options correspond
        # to a trim unless the source explicitly maps them.
        if engines:

            engine_text = []

            for engine in engines:

                engine_text.append(
                    " / ".join([
                        engine.get(
                            "Engine",
                            ""
                        ),
                        engine.get(
                            "Max Power",
                            ""
                        ),
                        engine.get(
                            "Max Torque",
                            ""
                        ),
                        engine.get(
                            "Transmission",
                            ""
                        ),
                    ])
                )

            combined = " | ".join(
                engine_text
            )

            for row in rows:

                row[
                    "Published Engine Options"
                ] = combined

                row[
                    "Engine Source URL"
                ] = feature_url

    return rows


# ============================================================
# EXCEL
# ============================================================

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
            sheet_name="Models"
        )

        specs_df.to_excel(
            writer,
            index=False,
            sheet_name="Specs"
        )

        ws = writer.book["Specs"]

        ws.freeze_panes = "A2"

        for column_cells in ws.columns:

            length = 0

            column_letter = (
                column_cells[0]
                .column_letter
            )

            for cell in column_cells:

                value = str(
                    cell.value or ""
                )

                length = max(
                    length,
                    len(value)
                )

            ws.column_dimensions[
                column_letter
            ].width = min(
                max(length + 2, 12),
                45
            )

    return output.getvalue()


# ============================================================
# UI
# ============================================================

url = st.text_input(
    "Website URL",
    placeholder=(
        "https://www.kia.com/aljabr/en/main.html"
    ),
)


if st.button(
    "🔎 Research Website",
    type="primary",
    use_container_width=True,
):

    if not clean(url):

        st.warning("ใส่ URL ก่อนค่ะ")
        st.stop()

    try:

        with st.spinner(
            "กำลังค้นหารุ่นรถ..."
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
                make
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

    st.subheader("Models")

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

        col1, col2 = st.columns(2)

        get_selected = col1.button(
            "⚙️ Get Selected Specs",
            use_container_width=True,
        )

        get_all = col2.button(
            "🚗 Get ALL Specs",
            use_container_width=True,
        )

        if get_selected or get_all:

            if get_all:

                selected = models_df

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

                    model_results = (
                        extract_specs(
                            row["Model URL"],
                            row["Make"],
                            row["Model"],
                        )
                    )

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
        "Published Engine Options",
        "Max Power",
        "Max Torque",
        "Transmission",
        "Drivetrain",
        "Motor Type",
        "Front Motor Max Power",
        "Front Motor Max Torque",
        "Rear Motor Max Power",
        "Rear Motor Max Torque",
        "Total Motor Max Power",
        "Total Motor Max Torque",
        "Battery Type",
        "Battery Capacity",
        "Range WLTP",
        "Range NEDC",
        "AC Charge Port",
        "AC Charging Power",
        "DC Charging Power",
        "AC Charging Time",
        "DC Charging Time",
        "Top Speed",
        "Acceleration 0-100",
        "Seats",
        "Overall Length",
        "Overall Width",
        "Overall Height",
        "Wheelbase",
        "Ground Clearance",
        "Curb Weight",
        "Fuel Tank",
        "Wheel Type",
        "Tyre Size",
        "Wheels",
        "Source URL",
        "Engine Source URL",
    ]

    ordered = [
        x
        for x in preferred
        if x in specs_df.columns
    ]

    extras = [
        x
        for x in specs_df.columns
        if x not in ordered
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
                ),
            "Engine Source URL":
                st.column_config.LinkColumn(
                    "Engine Source URL"
                ),
        },
    )

    excel = create_excel(
        st.session_state["models"],
        specs_df
    )

    st.download_button(
        "⬇️ Download Excel",
        data=excel,
        file_name=(
            "automotive_research.xlsx"
        ),
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        use_container_width=True,
    )


st.caption(
    "Source-only extraction • "
    "ไม่เดาค่าที่เว็บไซต์ไม่ได้เผยแพร่ • "
    "ถ้า Engine/Powertrain ไม่ได้ผูกกับ Variant โดยตรง "
    "ระบบจะแสดงเป็น Published Engine Options แทน"
)
