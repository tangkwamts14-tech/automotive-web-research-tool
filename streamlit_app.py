import io
import re
import json

from urllib.parse import urljoin, urlparse, unquote

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup


# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="Automotive Web Research Tool V3",
    page_icon="🚗",
    layout="wide",
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/124 Safari/537.36"
    )
}


# =========================================================
# BRAND LIST
# =========================================================

BRANDS = [
    "Acura",
    "Alfa Romeo",
    "Aston Martin",
    "Audi",
    "BAIC",
    "Bentley",
    "Bestune",
    "BMW",
    "BYD",
    "Cadillac",
    "Changan",
    "Chery",
    "Chevrolet",
    "Chrysler",
    "Denza",
    "Dodge",
    "Exeed",
    "FAW",
    "Ferrari",
    "Fiat",
    "Ford",
    "Foton",
    "GAC",
    "Geely",
    "Genesis",
    "GMC",
    "Great Wall",
    "GWM",
    "Haval",
    "Honda",
    "Hongqi",
    "Hyundai",
    "iCAUR",
    "Ineos",
    "Infiniti",
    "Isuzu",
    "JAC",
    "Jaecoo",
    "Jaguar",
    "Jeep",
    "Jetour",
    "Kia",
    "Lamborghini",
    "Land Rover",
    "Lexus",
    "Lincoln",
    "Lotus",
    "Maserati",
    "Mazda",
    "McLaren",
    "Mercedes-Benz",
    "MG",
    "MINI",
    "Mitsubishi",
    "Nissan",
    "Omoda",
    "Ora",
    "Peugeot",
    "Porsche",
    "RAM",
    "Renault",
    "Rolls-Royce",
    "Skoda",
    "Soueast",
    "Ssangyong",
    "Subaru",
    "Suzuki",
    "Tata",
    "Tesla",
    "Toyota",
    "Volkswagen",
    "Volvo",
    "Yangwang",
]


# =========================================================
# WORDS USED TO FIND MODEL SECTIONS
# =========================================================

SECTION_WORDS = (
    "vehicle",
    "vehicles",
    "model",
    "models",
    "cars",
    "our cars",
    "our models",
    "lineup",
    "line-up",
    "range",
    "explore vehicles",
    "explore models",
)


NOISE = {
    "home",
    "overview",
    "gallery",
    "brand",
    "explore more",
    "discover more",
    "learn more",
    "view more",
    "details",
    "offers",
    "services",
    "owners",
    "news",
    "events",
    "contact",
    "contact us",
    "request a test drive",
    "test drive",
    "find a dealer",
    "build",
    "configure",
    "configurator",
    "vehicles",
    "models",
    "cars",
    "see all vehicles",
    "all vehicles",
    "order options",
    "request a call",
    "brochure",
    "download brochure",
    "menu",
    "search",
    "privacy",
    "terms",
}


# =========================================================
# SPEC NAMES
# =========================================================

SPEC_ALIASES = {

    "Engine / Motor": [
        "engine",
        "engine type",
        "motor type",
        "electric motor",
    ],

    "Displacement": [
        "displacement",
        "engine displacement",
        "engine capacity",
        "capacity",
    ],

    "Cylinders": [
        "cylinders",
        "cylinder count",
        "number of cylinders",
    ],

    "Fuel / Powertrain": [
        "fuel",
        "fuel type",
        "powertrain",
        "propulsion",
        "engine fuel",
    ],

    "Max Power": [
        "max power",
        "maximum power",
        "power output",
        "engine power",
        "horsepower",
        "hp",
        "ps",
        "kw",
    ],

    "Max Torque": [
        "max torque",
        "maximum torque",
        "torque output",
        "engine torque",
        "torque",
    ],

    "Transmission": [
        "transmission",
        "gearbox",
        "transmission type",
        "gear type",
    ],

    "Drivetrain": [
        "drivetrain",
        "drive type",
        "drive system",
        "driven wheels",
        "wheel drive",
        "fwd",
        "rwd",
        "awd",
        "4wd",
        "4x4",
        "2wd",
    ],

    "Battery Capacity": [
        "battery capacity",
        "battery pack",
        "battery size",
        "battery energy",
        "usable battery",
    ],

    "Electric Range": [
        "electric range",
        "driving range",
        "ev range",
        "wltp range",
        "nedc range",
    ],

    "Charging": [
        "charging time",
        "charging",
        "dc charging",
        "ac charging",
        "charging power",
        "fast charging",
    ],

    "Fuel Economy": [
        "fuel economy",
        "fuel consumption",
        "mileage",
        "km/l",
        "l/100 km",
    ],

    "Fuel Tank": [
        "fuel tank",
        "tank capacity",
        "fuel tank capacity",
    ],

    "Seats": [
        "seating capacity",
        "seat capacity",
        "number of seats",
        "seats",
        "passenger capacity",
        "passengers",
    ],

    "Length": [
        "overall length",
        "length",
    ],

    "Width": [
        "overall width",
        "width",
    ],

    "Height": [
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

    "Wheels / Tires": [
        "wheel size",
        "wheels",
        "tyre size",
        "tire size",
        "tires",
        "tyres",
    ],

    "Drive Modes": [
        "drive modes",
        "driving modes",
        "terrain modes",
    ],

    "Acceleration": [
        "0-100",
        "0–100",
        "acceleration",
    ],

    "Top Speed": [
        "top speed",
        "maximum speed",
        "max speed",
    ],

    "Body Type": [
        "body type",
        "vehicle type",
        "body style",
    ],
}


# =========================================================
# BASIC FUNCTIONS
# =========================================================

def clean(text):

    return re.sub(
        r"\s+",
        " ",
        str(text or "")
    ).strip(" :-|\t\r\n")


def normalize_url(url):

    url = url.strip()

    if url.startswith(
        ("http://", "https://")
    ):
        return url

    return "https://" + url


@st.cache_data(
    ttl=600,
    show_spinner=False
)
def fetch(url):

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
        allow_redirects=True,
    )

    response.raise_for_status()

    return (
        response.url,
        response.text,
    )


# =========================================================
# MAKE DETECTION
# =========================================================

def infer_make(
    soup,
    url,
    manual_make,
):

    # User manually entered Make
    if clean(manual_make):

        return clean(
            manual_make
        )

    title = ""

    if soup.title:

        title = clean(
            soup.title.get_text(
                " ",
                strip=True
            )
        )

    site_name = ""

    meta = soup.find(
        "meta",
        attrs={
            "property":
            "og:site_name"
        }
    )

    if meta:

        site_name = clean(
            meta.get(
                "content",
                ""
            )
        )

    hostname = (
        urlparse(url)
        .netloc
    )

    blob = (
        hostname
        + " "
        + title
        + " "
        + site_name
    ).lower()

    # Longest brand first
    for brand in sorted(
        BRANDS,
        key=len,
        reverse=True
    ):

        brand_lower = (
            brand.lower()
        )

        compact_brand = (
            brand_lower
            .replace(
                " ",
                ""
            )
        )

        compact_blob = re.sub(
            r"[\W_]",
            "",
            blob
        )

        if (
            brand_lower
            in blob
            or
            compact_brand
            in compact_blob
        ):

            return brand

    # fallback from domain
    domain = (
        hostname
        .replace(
            "www.",
            ""
        )
        .split(".")[0]
    )

    return (
        domain
        .replace(
            "-",
            " "
        )
        .title()
    )


# =========================================================
# URL → MODEL
# =========================================================

def pretty_slug(slug):

    slug = re.sub(
        r"[-_]+",
        " ",
        unquote(slug)
    ).strip()

    words = []

    for word in slug.split():

        if (
            re.search(
                r"\d",
                word
            )
            or
            len(word) <= 3
        ):

            words.append(
                word.upper()
            )

        else:

            words.append(
                word.title()
            )

    return " ".join(
        words
    )


def candidate_name_from_url(url):

    path = (
        urlparse(url)
        .path
        .strip("/")
    )

    parts = [
        part
        for part in path.split("/")
        if part
    ]

    bad = {
        "en",
        "ar",
        "sa",
        "qa",
        "ksa",
        "vehicles",
        "vehicle",
        "models",
        "model",
        "cars",
        "car",
        "suv",
        "sedan",
        "mpv",
        "commercial",
    }

    lower_parts = [
        part.lower()
        for part in parts
    ]

    for key in (
        "vehicles",
        "vehicle",
        "models",
        "model",
        "cars",
        "car",
    ):

        if key in lower_parts:

            index = (
                lower_parts
                .index(key)
            )

            if (
                index + 1
                < len(parts)
            ):

                candidate = (
                    parts[
                        index + 1
                    ]
                )

                if (
                    candidate.lower()
                    not in bad
                ):

                    return pretty_slug(
                        candidate
                    )

    if parts:

        candidate = parts[-1]

        if (
            candidate.lower()
            not in bad
            and
            "." not in candidate
        ):

            return pretty_slug(
                candidate
            )

    return ""


# =========================================================
# JSON-LD MODEL SEARCH
# =========================================================

def jsonld_models(
    soup,
    base_url,
    make,
):

    rows = []

    scripts = soup.find_all(
        "script",
        type="application/ld+json"
    )

    for tag in scripts:

        try:

            data = json.loads(
                tag.string or ""
            )

        except Exception:

            continue

        if isinstance(
            data,
            list
        ):

            stack = data

        else:

            stack = [data]

        while stack:

            item = stack.pop()

            if isinstance(
                item,
                dict
            ):

                item_type = str(
                    item.get(
                        "@type",
                        ""
                    )
                ).lower()

                if any(
                    keyword
                    in item_type
                    for keyword in (
                        "product",
                        "vehicle",
                        "car",
                        "itemlist",
                    )
                ):

                    name = clean(
                        item.get(
                            "name",
                            ""
                        )
                    )

                    url = urljoin(
                        base_url,
                        clean(
                            item.get(
                                "url",
                                ""
                            )
                        )
                    )

                    if (
                        name
                        and
                        name.lower()
                        not in NOISE
                        and
                        len(name) < 70
                    ):

                        rows.append(
                            (
                                make,
                                name,
                                url,
                                "JSON-LD",
                            )
                        )

                for value in (
                    item.values()
                ):

                    if isinstance(
                        value,
                        (dict, list)
                    ):

                        stack.append(
                            value
                        )

            elif isinstance(
                item,
                list
            ):

                stack.extend(
                    item
                )

    return rows


# =========================================================
# DISCOVER MODELS
# =========================================================

def discover_models(
    soup,
    base_url,
    make,
):

    host = (
        urlparse(base_url)
        .netloc
        .lower()
        .replace(
            "www.",
            ""
        )
    )

    rows = []

    # -----------------------------------------------------
    # METHOD 1
    # Links + URL + surrounding section
    # -----------------------------------------------------

    for link in soup.find_all(
        "a",
        href=True
    ):

        url = urljoin(
            base_url,
            link["href"]
        )

        link_host = (
            urlparse(url)
            .netloc
            .lower()
            .replace(
                "www.",
                ""
            )
        )

        if link_host != host:
            continue

        text = clean(
            link.get_text(
                " ",
                strip=True
            )
        )

        path = (
            urlparse(url)
            .path
            .lower()
        )

        # URL signal
        url_signal = any(
            "/" + keyword + "/"
            in path
            for keyword in (
                "vehicle",
                "vehicles",
                "model",
                "models",
                "car",
                "cars",
            )
        )

        # Look at surrounding section
        section_signal = False

        parents = list(
            link.parents
        )[:5]

        for parent in parents:

            parent_text = clean(
                parent.get_text(
                    " ",
                    strip=True
                )
            ).lower()[:800]

            if any(
                word
                in parent_text
                for word
                in SECTION_WORDS
            ):

                section_signal = True
                break

        if not (
            url_signal
            or
            section_signal
        ):

            continue

        # Generic button text
        if (
            not text
            or
            text.lower()
            in NOISE
            or
            len(text) > 70
        ):

            name = (
                candidate_name_from_url(
                    url
                )
            )

            source = "URL"

        else:

            name = text
            source = "Link/Card"

        if (
            name
            and
            name.lower()
            not in NOISE
            and
            len(name) < 70
        ):

            rows.append(
                (
                    make,
                    name,
                    url,
                    source,
                )
            )


    # -----------------------------------------------------
    # METHOD 2
    # Heading:
    #
    # The Kia K4
    # The Kia EV5
    # The Kia Sportage L
    # -----------------------------------------------------

    headings = soup.find_all(
        re.compile(
            "^h[1-4]$"
        )
    )

    for heading in headings:

        text = clean(
            heading.get_text(
                " ",
                strip=True
            )
        )

        pattern = (
            r"^(?:the\s+)?"
            + re.escape(make)
            + r"\s+(.+)$"
        )

        match = re.match(
            pattern,
            text,
            re.I
        )

        if match:

            name = clean(
                match.group(1)
            )

            if (
                name
                and
                name.lower()
                not in NOISE
            ):

                near_link = (
                    heading.find_next(
                        "a",
                        href=True
                    )
                )

                if near_link:

                    model_url = urljoin(
                        base_url,
                        near_link[
                            "href"
                        ]
                    )

                else:

                    model_url = (
                        base_url
                    )

                rows.append(
                    (
                        make,
                        name,
                        model_url,
                        "Heading",
                    )
                )


    # -----------------------------------------------------
    # METHOD 3
    # JSON-LD
    # -----------------------------------------------------

    rows += jsonld_models(
        soup,
        base_url,
        make
    )


    # -----------------------------------------------------
    # DATAFRAME
    # -----------------------------------------------------

    df = pd.DataFrame(
        rows,
        columns=[
            "Make",
            "Model",
            "Model URL",
            "Detected From",
        ]
    )

    if df.empty:

        return df


    # Remove year at end
    df["Model"] = (
        df["Model"]
        .str
        .replace(
            r"\s+\d{4}$",
            "",
            regex=True
        )
        .str
        .strip()
    )


    # Remove noise
    df = df[
        ~df[
            "Model"
        ]
        .str
        .lower()
        .isin(NOISE)
    ]


    # Remove duplicates
    df = df.drop_duplicates(
        subset=[
            "Make",
            "Model",
        ],
        keep="first"
    )


    return (
        df
        .sort_values(
            "Model"
        )
        .reset_index(
            drop=True
        )
    )


# =========================================================
# SPEC PAIRS
# =========================================================

def add_pair(
    pairs,
    key,
    value,
):

    key = clean(key)
    value = clean(value)

    if not key:
        return

    if not value:
        return

    if len(key) > 100:
        return

    if len(value) > 300:
        return

    pairs.append(
        (
            key,
            value
        )
    )


def extract_pairs(
    soup
):

    pairs = []


    # -----------------------------------------------------
    # HTML TABLES
    # -----------------------------------------------------

    for row in soup.find_all(
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
            in row.find_all(
                [
                    "th",
                    "td",
                ]
            )
        ]

        if len(cells) >= 2:

            add_pair(
                pairs,
                cells[0],
                " | ".join(
                    cells[1:]
                )
            )


    # -----------------------------------------------------
    # DT / DD
    # -----------------------------------------------------

    for dt in soup.find_all(
        "dt"
    ):

        dd = (
            dt.find_next_sibling(
                "dd"
            )
        )

        if dd:

            add_pair(
                pairs,
                dt.get_text(
                    " ",
                    strip=True
                ),
                dd.get_text(
                    " ",
                    strip=True
                )
            )


    # -----------------------------------------------------
    # Label : Value
    # -----------------------------------------------------

    for element in soup.find_all(
        [
            "li",
            "p",
            "div",
        ]
    ):

        text = clean(
            element.get_text(
                " ",
                strip=True
            )
        )

        if (
            len(text) > 3
            and
            len(text) < 220
        ):

            match = re.match(
                r"^([^:]{2,60})"
                r"\s*:\s*"
                r"(.{1,150})$",
                text
            )

            if match:

                add_pair(
                    pairs,
                    match.group(1),
                    match.group(2)
                )

    return pairs


# =========================================================
# MAP WEBSITE LABEL → STANDARD FIELD
# =========================================================

def canonical_field(
    label
):

    label = (
        clean(label)
        .lower()
    )

    for (
        field,
        aliases
    ) in SPEC_ALIASES.items():

        for alias in aliases:

            if (
                alias == label
                or
                alias in label
            ):

                return field

    return None


# =========================================================
# INSPECT MODEL SPECS
# =========================================================

@st.cache_data(
    ttl=600,
    show_spinner=False
)
def inspect_model(
    url,
    make,
    model,
):

    try:

        final_url, html = fetch(
            url
        )

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        result = {
            "Make":
            make,

            "Model":
            model,

            "Source URL":
            final_url,
        }

        raw_matches = []


        # -------------------------------------------------
        # Structured HTML values
        # -------------------------------------------------

        for (
            key,
            value
        ) in extract_pairs(
            soup
        ):

            field = (
                canonical_field(
                    key
                )
            )

            if (
                field
                and
                not result.get(
                    field
                )
            ):

                result[
                    field
                ] = value

                raw_matches.append(
                    f"{key}: {value}"
                )


        # -------------------------------------------------
        # Full page text
        # -------------------------------------------------

        text = clean(
            soup.get_text(
                "\n",
                strip=True
            )
        )


        # -------------------------------------------------
        # FALLBACK REGEX
        # -------------------------------------------------

        fallback_patterns = {

            "Max Power":
            (
                r"(?i)"
                r"(?:max(?:imum)?\s+power"
                r"|power output"
                r"|horsepower)"
                r"\s*[:\-]?\s*"
                r"([0-9.,]+\s*"
                r"(?:hp|ps|kw|bhp))"
            ),

            "Max Torque":
            (
                r"(?i)"
                r"(?:max(?:imum)?\s+torque"
                r"|torque)"
                r"\s*[:\-]?\s*"
                r"([0-9.,]+\s*"
                r"(?:nm|n\.m))"
            ),

            "Battery Capacity":
            (
                r"(?i)"
                r"(?:battery"
                r"(?:\s+capacity"
                r"|\s+pack"
                r"|\s+size)?)"
                r"\s*[:\-]?\s*"
                r"([0-9.,]+\s*kwh)"
            ),

            "Electric Range":
            (
                r"(?i)"
                r"(?:electric"
                r"|driving"
                r"|ev"
                r"|wltp)?"
                r"\s*range"
                r"\s*[:\-]?\s*"
                r"([0-9.,]+\s*km)"
            ),

            "Drivetrain":
            (
                r"(?i)"
                r"\b("
                r"FWD"
                r"|RWD"
                r"|AWD"
                r"|4WD"
                r"|4X4"
                r"|2WD"
                r")\b"
            ),
        }


        for (
            field,
            pattern
        ) in fallback_patterns.items():

            if not result.get(
                field
            ):

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


        # -------------------------------------------------
        # Keep raw matched specs for checking
        # -------------------------------------------------

        result[
            "Raw matched specs"
        ] = " ; ".join(
            raw_matches[:80]
        )

        return result


    except Exception as error:

        return {

            "Make":
            make,

            "Model":
            model,

            "Source URL":
            url,

            "Error":
            str(error),
        }


# =========================================================
# EXCEL
# =========================================================

def make_excel(
    models,
    specs,
    source_url,
):

    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        models.to_excel(
            writer,
            index=False,
            sheet_name="Models"
        )

        if (
            specs is not None
            and
            not specs.empty
        ):

            specs.to_excel(
                writer,
                index=False,
                sheet_name="Specs"
            )

        methodology = pd.DataFrame(
            [
                {
                    "Source URL":
                    source_url,

                    "Rule":
                    (
                        "Only display fields "
                        "found on source page. "
                        "Blank means not detected. "
                        "Verify against OEM page "
                        "before final use."
                    )
                }
            ]
        )

        methodology.to_excel(
            writer,
            index=False,
            sheet_name="Methodology"
        )

    return output.getvalue()


# =========================================================
# UI
# =========================================================

st.title(
    "🚗 Automotive Web Research Tool V3"
)

st.caption(
    "URL → Make → Model → Flexible Specs → Excel"
)


manual_make = (
    st.sidebar.text_input(
        "Make (optional)",
        placeholder=(
            "Auto-detect if blank"
        )
    )
)


max_pages = (
    st.sidebar.slider(
        "Max model pages for spec scan",
        min_value=1,
        max_value=50,
        value=10,
    )
)


url = st.text_input(
    "Website URL",
    placeholder=(
        "https://www.kia.com/sa/en/main.html"
    )
)


# =========================================================
# CHECK WEBSITE
# =========================================================

if st.button(
    "🔎 Check website",
    type="primary",
    use_container_width=True,
):

    if not url.strip():

        st.error(
            "Enter a website URL."
        )

        st.stop()

    try:

        final_url, html = fetch(
            normalize_url(
                url
            )
        )

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        make = infer_make(
            soup,
            final_url,
            manual_make
        )

        models = discover_models(
            soup,
            final_url,
            make
        )

        st.session_state.models = (
            models
        )

        st.session_state.source = (
            final_url
        )

        st.session_state.specdf = (
            pd.DataFrame()
        )

        st.session_state.make = (
            make
        )

    except Exception as error:

        st.error(
            str(error)
        )


# =========================================================
# MODEL RESULTS
# =========================================================

if "models" in st.session_state:

    models = (
        st.session_state.models
    )

    col1, col2 = st.columns(
        2
    )

    col1.metric(
        "Make",
        st.session_state.make
    )

    col2.metric(
        "Detected models",
        len(models)
    )


    st.subheader(
        "1. Models found"
    )


    if models.empty:

        st.warning(
            "No reliable model candidates "
            "detected from the returned HTML. "
            "This site may require JavaScript "
            "rendering or a dedicated adapter."
        )


    else:

        editable = (
            models.assign(
                Inspect=False
            )
        )


        edited = st.data_editor(
            editable,
            hide_index=True,
            use_container_width=True,

            column_config={

                "Inspect":
                st.column_config.CheckboxColumn(
                    "Inspect specs"
                )

            },

            disabled=[
                "Make",
                "Model",
                "Model URL",
                "Detected From",
            ],
        )


        # -------------------------------------------------
        # INSPECT SPECS
        # -------------------------------------------------

        if st.button(
            "⚙️ Inspect selected models"
        ):

            selected = edited[
                edited[
                    "Inspect"
                ] == True
            ].head(
                max_pages
            )


            if selected.empty:

                st.warning(
                    "Select at least one model."
                )


            else:

                progress = (
                    st.progress(
                        0
                    )
                )

                results = []

                total = len(
                    selected
                )


                for (
                    index,
                    (_, row)
                ) in enumerate(
                    selected.iterrows()
                ):

                    result = (
                        inspect_model(
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

                    results.append(
                        result
                    )

                    progress.progress(
                        (index + 1)
                        / total
                    )


                st.session_state.specdf = (
                    pd.DataFrame(
                        results
                    )
                )


    # =====================================================
    # SPECS TABLE
    # =====================================================

    if (
        "specdf"
        in st.session_state
        and
        not st.session_state.specdf.empty
    ):

        st.subheader(
            "2. Specs found"
        )

        specs_df = (
            st.session_state
            .specdf
            .copy()
        )


        # -----------------------------------------------
        # Important:
        #
        # Column is shown only if
        # at least one selected vehicle
        # actually has data.
        # -----------------------------------------------

        useful_columns = []

        for column in specs_df.columns:

            if column in (
                "Make",
                "Model",
                "Source URL",
                "Error",
            ):

                useful_columns.append(
                    column
                )

                continue


            has_data = (
                specs_df[column]
                .replace(
                    "",
                    pd.NA
                )
                .notna()
                .any()
            )


            if has_data:

                useful_columns.append(
                    column
                )


        st.dataframe(
            specs_df[
                useful_columns
            ],
            use_container_width=True,
            hide_index=True,
        )


    # =====================================================
    # EXCEL
    # =====================================================

    specs_df = (
        st.session_state.get(
            "specdf",
            pd.DataFrame()
        )
    )


    excel_file = (
        make_excel(
            models,
            specs_df,
            st.session_state.source,
        )
    )


    st.download_button(
        "⬇️ Download Excel",

        data=excel_file,

        file_name=(
            "automotive_research_v3.xlsx"
        ),

        mime=(
            "application/"
            "vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),

        use_container_width=True,
    )


# =========================================================
# RULE
# =========================================================

st.info(
    "V3 rule: "
    "if the source publishes a field, show it; "
    "if it does not, leave it blank. "
    "No invented values."
)
