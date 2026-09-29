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
    "Paste automotive website URL → Find Models → Get Specs → Download Excel"
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


# =========================================================
# BASIC FUNCTIONS
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


def same_site(url1, url2):
    return domain(url1) == domain(url2)


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

    # Domain first
    for brand in sorted(
        BRANDS,
        key=len,
        reverse=True
    ):

        compact_brand = re.sub(
            r"[^a-z0-9]",
            "",
            brand.lower()
        )

        if compact_brand in compact_host:
            return brand

    # Page title
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

    return host.split(".")[0].title()


# =========================================================
# MODEL CLEANING
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

    name = re.split(
        r"\bfrom\s+(?:sar|qar|aed|usd)\b",
        name,
        flags=re.I,
    )[0]

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

    if len(name) < 2:
        return False

    if len(name) > 45:
        return False

    if re.fullmatch(
        r"[\d\s.,]+",
        name
    ):
        return False

    if any(
        bad in lower
        for bad in BAD_MODEL_WORDS
    ):
        return False

    if lower.endswith(
        (".html", ".htm", ".php")
    ):
        return False

    return True


# =========================================================
# MODEL NAME FROM URL
# =========================================================

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
            or
            re.search(r"\d", word)
        ):
            words.append(
                word.upper()
            )
        else:
            words.append(
                word.title()
            )

    result = " ".join(words)

    return clean_model_name(
        result,
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

    # -----------------------------------------------------
    # METHOD 1:
    # URLs containing showroom/model/vehicle
    # -----------------------------------------------------

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
            pattern in path
            for pattern in [
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
            "Detected From": "Vehicle URL",
        })

    # -----------------------------------------------------
    # METHOD 2:
    # Headings with nearby links
    # -----------------------------------------------------

    for heading in soup.find_all(
        [
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
        ]
    ):

        heading_text = clean(
            heading.get_text(
                " ",
                strip=True
            )
        )

        model = clean_model_name(
            heading_text,
            make
        )

        if not valid_model(
            model,
            make
        ):
            continue

        container = heading

        found_url = ""

        for _ in range(4):

            if container is None:
                break

            links = container.find_all(
                "a",
                href=True
            )

            for link in links:

                href = urljoin(
                    base_url,
                    link.get("href")
                )

                path = (
                    urlparse(href)
                    .path
                    .lower()
                )

                if (
                    same_site(
                        base_url,
                        href
                    )
                    and
                    any(
                        x in path
                        for x in [
                            "/showroom/",
                            "/model/",
                            "/models/",
                            "/vehicle/",
                            "/vehicles/",
                        ]
                    )
                ):
                    found_url = href
                    break

            if found_url:
                break

            container = container.parent

        if found_url:

            url_model = model_from_url(
                found_url,
                make
            )

            if valid_model(
                url_model,
                make
            ):
                model = url_model

            rows.append({
                "Make": make,
                "Model": model,
                "Model URL": found_url,
                "Detected From": "Heading + Vehicle URL",
            })

    if not rows:

        return pd.DataFrame(
            columns=[
                "Make",
                "Model",
                "Model URL",
                "Detected From",
            ]
        )

    df = pd.DataFrame(rows)

    # Prefer gallery / overview pages
    def score_url(url):

        lower = url.lower()

        score = 0

        if "/showroom/" in lower:
            score += 10

        if "gallery.html" in lower:
            score += 5

        if "overview.html" in lower:
            score += 4

        if "features.html" in lower:
            score += 2

        if "specification" in lower:
            score += 3

        return score

    df["Score"] = (
        df["Model URL"]
        .map(score_url)
    )

    df = (
        df.sort_values(
            ["Model", "Score"],
            ascending=[
                True,
                False,
            ]
        )
        .drop_duplicates(
            subset=[
                "Make",
                "Model",
            ],
            keep="first",
        )
        .drop(
            columns=["Score"]
        )
        .reset_index(
            drop=True
        )
    )

    return df


# =========================================================
# FIND SPECIFICATION PAGE
# =========================================================

def find_spec_page(model_url):

    try:
        final_url, soup = get_page(
            model_url
        )

    except Exception:
        return model_url

    # Look for explicit Specification link
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

        href_lower = href.lower()

        if (
            "specification" in label
            or
            "specifications" in label
            or
            "technical specification" in label
            or
            "specification" in href_lower
        ):
            return href

    # Kia style
    if "gallery.html" in final_url.lower():

        return re.sub(
            r"gallery\.html",
            "specification.html",
            final_url,
            flags=re.I,
        )

    if "features.html" in final_url.lower():

        return re.sub(
            r"features\.html",
            "specification.html",
            final_url,
            flags=re.I,
        )

    if "overview.html" in final_url.lower():

        return re.sub(
            r"overview\.html",
            "specification.html",
            final_url,
            flags=re.I,
        )

    return final_url


# =========================================================
# EXTRACT SPECS
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

        return {
            "Make": make,
            "Model": model,
            "Source URL": spec_url,
            "Error": str(error),
        }

    result = {
        "Make": make,
        "Model": model,
        "Source URL": final_url,
    }

    # =====================================================
    # HTML TABLE
    # =====================================================

    for table in soup.find_all(
        "table"
    ):

        for tr in table.find_all(
            "tr"
        ):

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
                x for x in cells
                if x
            ]

            if len(cells) >= 2:

                label = cells[0]

                value = " | ".join(
                    cells[1:]
                )

                if (
                    1 < len(label) <= 80
                    and
                    len(value) <= 300
                ):

                    result[label] = value

    # =====================================================
    # DT DD
    # =====================================================

    for dt in soup.find_all(
        "dt"
    ):

        dd = dt.find_next_sibling(
            "dd"
        )

        if not dd:
            continue

        label = clean(
            dt.get_text(
                " ",
                strip=True
            )
        )

        value = clean(
            dd.get_text(
                " ",
                strip=True
            )
        )

        if (
            label
            and value
            and len(label) <= 80
            and len(value) <= 300
        ):
            result[label] = value

    # =====================================================
    # CLEAN PAGE LINES
    # =====================================================

    text = soup.get_text(
        "\n",
        strip=True
    )

    lines = [
        clean(x)
        for x in text.splitlines()
        if clean(x)
    ]

    # =====================================================
    # DIMENSIONS
    # =====================================================

    dimension_labels = [
        "Overall length",
        "Overall width",
        "Overall height",
        "Wheelbase",
    ]

    # Kia often places labels together
    # and numeric values together.

    positions = {}

    for label in dimension_labels:

        for i, line in enumerate(
            lines
        ):

            if (
                line.lower()
                == label.lower()
            ):
                positions[label] = i
                break

    if positions:

        last_position = max(
            positions.values()
        )

        numbers = []

        for line in lines[
            last_position + 1:
            last_position + 40
        ]:

            if re.fullmatch(
                r"[0-9,]{3,}(?:\.[0-9]+)?",
                line
            ):
                numbers.append(
                    line
                )

        numbers = list(
            dict.fromkeys(numbers)
        )

        labels_found = [
            label
            for label
            in dimension_labels
            if label in positions
        ]

        if (
            len(numbers)
            >= len(labels_found)
        ):

            for label, value in zip(
                labels_found,
                numbers
            ):

                result[label] = (
                    value + " mm"
                )

    # =====================================================
    # WHEELS
    # =====================================================

    wheels = []

    for line in lines:

        if re.search(
            r"\b\d{2}[- ]inch\b",
            line,
            re.I,
        ):

            if (
                len(line) <= 150
                and
                line not in wheels
            ):
                wheels.append(line)

    if wheels:

        result["Wheels"] = (
            " | ".join(wheels[:6])
        )

    # =====================================================
    # FULL TEXT FALLBACK
    # =====================================================

    full_text = clean(
        soup.get_text(
            " ",
            strip=True
        )
    )

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
                r"[^0-9]{0,30}"
                r"([0-9.,]+\s*"
                r"(?:hp|ps|kw|bhp))"
            ),
        ],

        "Max Torque": [
            (
                r"(?i)"
                r"(?:maximum|max\.?)?\s*"
                r"torque"
                r"[^0-9]{0,30}"
                r"([0-9.,]+\s*"
                r"(?:nm|n\.m))"
            ),
        ],

        "Battery Capacity": [
            (
                r"(?i)"
                r"battery"
                r"(?:\s+capacity|\s+pack|\s+size)?"
                r"[^0-9]{0,30}"
                r"([0-9.,]+\s*kwh)"
            ),
        ],

        "Electric Range": [
            (
                r"(?i)"
                r"(?:electric\s+|driving\s+|ev\s+)?"
                r"range"
                r"[^0-9]{0,30}"
                r"([0-9.,]+\s*km)"
            ),
        ],

        "Fuel Tank Capacity": [
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
    }

    for field, regexes in (
        patterns.items()
    ):

        if result.get(field):
            continue

        for pattern in regexes:

            match = re.search(
                pattern,
                full_text
            )

            if match:

                result[field] = clean(
                    match.group(1)
                )

                break

    # =====================================================
    # TRANSMISSION
    # =====================================================

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
            full_text,
            re.I,
        )

        if match:

            result["Transmission"] = (
                clean(
                    match.group(1)
                )
            )

            break

    # =====================================================
    # DRIVETRAIN
    # =====================================================

    drive = re.search(
        r"\b(AWD|4WD|4X4|FWD|RWD)\b",
        full_text,
        re.I,
    )

    if drive:

        result["Drivetrain"] = (
            drive.group(1).upper()
        )

    # =====================================================
    # FUEL / POWERTRAIN
    # =====================================================

    powertrain = []

    checks = [
        ("PHEV", r"\bPHEV\b|plug-in hybrid"),
        ("HEV", r"\bHEV\b|\bhybrid\b"),
        ("BEV", r"\bBEV\b|battery electric"),
        ("EV", r"\belectric vehicle\b"),
        ("Diesel", r"\bdiesel\b"),
        ("Gasoline", r"\bgasoline\b|\bpetrol\b"),
    ]

    for value, pattern in checks:

        if re.search(
            pattern,
            full_text,
            re.I,
        ):
            powertrain.append(value)

    if powertrain:

        result[
            "Fuel / Powertrain"
        ] = ", ".join(
            dict.fromkeys(
                powertrain
            )
        )

    return result


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
# INPUT
# =========================================================

url = st.text_input(
    "Website URL",
    placeholder=(
        "https://www.kia.com/sa/en/main.html"
    ),
)


# =========================================================
# RESEARCH
# =========================================================

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
# MODELS
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
                "Detected From",
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
                        "กำลังอ่าน "
                        f"{row['Make']} "
                        f"{row['Model']} "
                        f"({number}/{total})"
                    )

                    result = extract_specs(
                        row["Model URL"],
                        row["Make"],
                        row["Model"],
                    )

                    results.append(
                        result
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
# RESULTS
# =========================================================

specs_df = (
    st.session_state.get(
        "specs",
        pd.DataFrame()
    )
)

if not specs_df.empty:

    # Remove columns that contain
    # no useful values at all
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
    "แสดงเฉพาะข้อมูลที่ตรวจพบจากเว็บไซต์ต้นทาง "
    "ข้อมูลที่หาไม่พบจะไม่ถูกสร้างขึ้นเอง"
)
