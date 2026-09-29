import io
import re
from urllib.parse import urljoin, urlparse, unquote

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup


# =========================================================
# PAGE SETUP
# =========================================================

st.set_page_config(
    page_title="Automotive Web Research Tool V2",
    page_icon="🚗",
    layout="wide"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/124 Safari/537.36"
    )
}


# =========================================================
# FILTER WORDS
# =========================================================

NOISE = {
    "home",
    "about",
    "contact",
    "contact us",
    "offers",
    "services",
    "owners",
    "news",
    "events",
    "overview",
    "test drive",
    "book a test drive",
    "request a quote",
    "quote",
    "brochure",
    "download brochure",
    "discover",
    "explore",
    "learn more",
    "view more",
    "view details",
    "details",
    "dealer",
    "dealers",
    "search",
    "menu",
    "privacy",
    "terms",
    "vehicles",
    "models",
    "new cars",
    "see all vehicles",
    "all vehicles",
    "build",
    "configure",
    "configurator",
}

GENERIC_PATH = {
    "vehicles",
    "vehicle",
    "models",
    "model",
    "cars",
    "car",
    "en",
    "ar",
    "qa",
    "sa",
    "ksa",
    "qatar",
    "home",
    "index",
}


# =========================================================
# AUTOMOTIVE BRANDS
# =========================================================

BRANDS = [
    "Toyota",
    "Genesis",
    "Nissan",
    "Lexus",
    "Kia",
    "Hyundai",
    "Honda",
    "BMW",
    "Audi",
    "Mercedes-Benz",
    "Volkswagen",
    "Porsche",
    "Ford",
    "Chevrolet",
    "Cadillac",
    "GMC",
    "Jeep",
    "Dodge",
    "Land Rover",
    "Jaguar",
    "Mazda",
    "Mitsubishi",
    "Suzuki",
    "Subaru",
    "Volvo",
    "MG",
    "Geely",
    "Chery",
    "Changan",
    "GAC",
    "BYD",
    "Exeed",
    "Jetour",
    "Jaecoo",
    "Omoda",
    "BAIC",
    "Haval",
    "GWM",
    "Ora",
    "Hongqi",
    "Infiniti",
    "Peugeot",
    "Renault",
    "Maserati",
    "Bentley",
    "Aston Martin",
    "Ferrari",
    "Lamborghini",
    "McLaren",
    "MINI",
]


# =========================================================
# SPEC PATTERNS
# =========================================================

SPEC_PATTERNS = {

    "Engine": (
        r"(?:engine|displacement|capacity)"
        r"\s*[:\-]?\s*([^\n|]{2,100})"
    ),

    "Fuel / Powertrain": (
        r"(?:fuel type|fuel|powertrain|propulsion)"
        r"\s*[:\-]?\s*([^\n|]{2,100})"
    ),

    "Max Power": (
        r"(?:maximum power|max\.?\s*power|max power|power output)"
        r"\s*[:\-]?\s*([^\n|]{2,100})"
    ),

    "Max Torque": (
        r"(?:maximum torque|max\.?\s*torque|max torque|torque output)"
        r"\s*[:\-]?\s*([^\n|]{2,100})"
    ),

    "Transmission": (
        r"(?:transmission|gearbox)"
        r"\s*[:\-]?\s*([^\n|]{2,100})"
    ),

    "Battery": (
        r"(?:battery capacity|battery pack size|battery)"
        r"\s*[:\-]?\s*([^\n|]{2,100})"
    ),

    "Electric Range": (
        r"(?:electric range|driving range|range)"
        r"\s*[:\-]?\s*([^\n|]{2,100})"
    ),
}


# =========================================================
# BASIC FUNCTIONS
# =========================================================

def clean(text):
    return re.sub(
        r"\s+",
        " ",
        text or ""
    ).strip()


def normalize_url(url):

    url = url.strip()

    if url.startswith(("http://", "https://")):
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
        timeout=25,
        allow_redirects=True
    )

    response.raise_for_status()

    return (
        response.url,
        response.text
    )


# =========================================================
# MAKE DETECTION
# =========================================================

def infer_make(
    soup,
    url,
    manual_make
):

    # ถ้าผู้ใช้กรอก Make เอง
    if manual_make.strip():
        return manual_make.strip()

    title = ""

    if soup.title and soup.title.string:
        title = clean(
            soup.title.string
        )

    site_name = ""

    meta = soup.find(
        "meta",
        {
            "property": "og:site_name"
        }
    )

    if meta:
        site_name = clean(
            meta.get(
                "content",
                ""
            )
        )

    host = (
        urlparse(url)
        .netloc
        .replace("www.", "")
    )

    blob = (
        host
        + " "
        + title
        + " "
        + site_name
    ).lower()

    # หา Brand จากชื่อเว็บ
    for brand in BRANDS:

        token = (
            brand
            .lower()
            .replace("-", " ")
        )

        if (
            token in blob
            or token.replace(" ", "")
            in blob.replace("-", "").replace(".", "")
        ):
            return brand

    # fallback
    first = host.split(".")[0]

    first = (
        first
        .replace("-ksa", "")
        .replace("-qatar", "")
        .replace("qatar", "")
    )

    return (
        first
        .replace("-", " ")
        .title()
    )


# =========================================================
# MODEL DETECTION FROM URL
# =========================================================

def get_model_slug(href):

    path = (
        unquote(
            urlparse(href).path
        )
        .strip("/")
    )

    parts = [
        part
        for part in path.split("/")
        if part
    ]

    if not parts:
        return ""

    lower_parts = [
        part.lower()
        for part in parts
    ]

    # เช่น
    # /vehicles/yaris
    # /models/corolla
    # /cars/camry

    for key in [
        "vehicles",
        "vehicle",
        "models",
        "model",
        "cars",
        "car",
    ]:

        if key in lower_parts:

            index = lower_parts.index(
                key
            )

            if index + 1 < len(parts):

                candidate = parts[
                    index + 1
                ]

                if (
                    candidate.lower()
                    not in GENERIC_PATH
                ):
                    return candidate

    candidate = parts[-1]

    if candidate.lower() in GENERIC_PATH:
        return ""

    if "." in candidate:
        return ""

    return candidate


def pretty_model_name(slug):

    slug = re.sub(
        r"[-_]+",
        " ",
        slug
    ).strip()

    words = []

    for word in slug.split():

        # เช่น
        # gr86
        # bz4x
        # cx90

        if re.search(
            r"\d",
            word
        ):

            if len(word) <= 8:
                words.append(
                    word.upper()
                )

            else:
                words.append(
                    word.title()
                )

        elif len(word) <= 3:

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


# =========================================================
# FIND MODEL LINKS
# =========================================================

def find_models(
    soup,
    base_url,
    make
):

    host = (
        urlparse(base_url)
        .netloc
        .lower()
        .replace("www.", "")
    )

    rows = []

    for link in soup.find_all(
        "a",
        href=True
    ):

        href = urljoin(
            base_url,
            link["href"]
        )

        link_host = (
            urlparse(href)
            .netloc
            .lower()
            .replace("www.", "")
        )

        # เอาเฉพาะเว็บเดียวกัน
        if link_host != host:
            continue

        text = clean(
            link.get_text(
                " ",
                strip=True
            )
        )

        path = (
            urlparse(href)
            .path
            .lower()
        )

        # ต้องดูเหมือน URL ของรถ
        vehicle_route = any(
            route in path
            for route in [
                "/vehicles/",
                "/vehicle/",
                "/models/",
                "/model/",
                "/cars/",
                "/car/",
            ]
        )

        if not vehicle_route:
            continue

        slug = get_model_slug(
            href
        )

        if not slug:
            continue

        # =====================================
        # จุดสำคัญของ V2
        #
        # ถ้าเว็บเขียนว่า Overview
        # แต่ URL เป็น /vehicles/yaris
        #
        # ให้ใช้ Yaris
        # =====================================

        if (
            not text
            or text.lower() in NOISE
            or len(text) > 70
        ):

            model = pretty_model_name(
                slug
            )

            detected_from = (
                "URL slug"
            )

        else:

            model = text

            detected_from = (
                "Link text"
            )

        if not model:
            continue

        if model.lower() in NOISE:
            continue

        rows.append(
            [
                make,
                model,
                href,
                detected_from,
            ]
        )

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

    # ลบ URL ซ้ำ
    df = df.drop_duplicates(
        subset=[
            "Model URL"
        ]
    )

    # ถ้ายังเจอคำ Overview
    # ให้ย้อนกลับไปใช้ URL slug

    bad_rows = (
        df["Model"]
        .str
        .lower()
        .isin(NOISE)
    )

    df.loc[
        bad_rows,
        "Model"
    ] = (
        df.loc[
            bad_rows,
            "Model URL"
        ]
        .map(
            lambda u:
            pretty_model_name(
                get_model_slug(u)
            )
        )
    )

    # กรอง noise อีกรอบ
    df = df[
        ~df["Model"]
        .str
        .lower()
        .isin(NOISE)
    ]

    return (
        df
        .sort_values(
            [
                "Model",
                "Model URL",
            ]
        )
        .reset_index(
            drop=True
        )
    )


# =========================================================
# SPEC EXTRACTION
# =========================================================

@st.cache_data(
    ttl=600,
    show_spinner=False
)
def extract_specs(url):

    try:

        final_url, html = fetch(
            url
        )

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        text = soup.get_text(
            "\n",
            strip=True
        )

        result = {
            "Source URL":
            final_url
        }

        for (
            field,
            pattern
        ) in SPEC_PATTERNS.items():

            match = re.search(
                pattern,
                text,
                re.I
            )

            if match:

                result[field] = clean(
                    match.group(1)
                )

            else:

                result[field] = ""

        return result

    except Exception as error:

        return {
            "Source URL":
            url,

            "Error":
            str(error)
        }


# =========================================================
# EXCEL EXPORT
# =========================================================

def make_excel(
    models,
    specs,
    source_url
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
            and not specs.empty
        ):

            specs.to_excel(
                writer,
                index=False,
                sheet_name="Specs"
            )

        methodology = pd.DataFrame(
            [
                {
                    "Source":
                    source_url,

                    "Rule":
                    (
                        "Research assistance. "
                        "Verify current model/spec "
                        "against OEM source before production use."
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
# USER INTERFACE
# =========================================================

st.title(
    "🚗 Automotive Web Research Tool V2"
)

st.caption(
    "OEM URL → Make → Model → Specs → Excel"
)


# Sidebar
manual_make = st.sidebar.text_input(
    "Make (optional)",
    placeholder="Leave blank for auto-detect"
)

max_pages = st.sidebar.slider(
    "Max model pages for spec scan",
    min_value=1,
    max_value=30,
    value=10
)


# URL input
url = st.text_input(
    "Website URL",
    placeholder="https://www.toyota.com.sa/en"
)


# =========================================================
# CHECK WEBSITE
# =========================================================

if st.button(
    "🔎 Check website",
    type="primary",
    use_container_width=True
):

    if not url.strip():

        st.error(
            "Enter a website URL."
        )

        st.stop()

    try:

        final_url, html = fetch(
            normalize_url(url)
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

        models_df = find_models(
            soup,
            final_url,
            make
        )

        st.session_state.models = (
            models_df
        )

        st.session_state.source = (
            final_url
        )

        st.session_state.specdf = (
            pd.DataFrame()
        )

    except Exception as error:

        st.error(
            f"Could not read website: {error}"
        )


# =========================================================
# RESULTS
# =========================================================

if "models" in st.session_state:

    models_df = (
        st.session_state.models
    )

    col1, col2 = st.columns(
        2
    )

    if not models_df.empty:

        col1.metric(
            "Make",
            models_df[
                "Make"
            ].iloc[0]
        )

    else:

        col1.metric(
            "Make",
            "-"
        )

    col2.metric(
        "Detected model links",
        len(models_df)
    )

    st.subheader(
        "1. Models"
    )

    if models_df.empty:

        st.warning(
            "No model routes detected. "
            "This website may require JavaScript rendering."
        )

    else:

        editable_df = (
            models_df.assign(
                Inspect=False
            )
        )

        edited = st.data_editor(
            editable_df,
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


        # =====================================
        # SPEC SCAN BUTTON
        # =====================================

        if st.button(
            "⚙️ Inspect selected model pages"
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
                    "Tick at least one model."
                )

            else:

                spec_rows = []

                progress = st.progress(
                    0
                )

                total = len(
                    selected
                )

                for index, (
                    _,
                    row
                ) in enumerate(
                    selected.iterrows()
                ):

                    result = {
                        "Make":
                        row["Make"],

                        "Model":
                        row["Model"]
                    }

                    specs = extract_specs(
                        row[
                            "Model URL"
                        ]
                    )

                    result.update(
                        specs
                    )

                    spec_rows.append(
                        result
                    )

                    progress.progress(
                        (index + 1)
                        / total
                    )

                st.session_state.specdf = (
                    pd.DataFrame(
                        spec_rows
                    )
                )


# =========================================================
# SPEC TABLE
# =========================================================

    if (
        "specdf"
        in st.session_state
        and
        not st.session_state.specdf.empty
    ):

        st.subheader(
            "2. Spec candidates"
        )

        st.dataframe(
            st.session_state.specdf,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# EXCEL DOWNLOAD
# =========================================================

    specs_df = (
        st.session_state.get(
            "specdf",
            pd.DataFrame()
        )
    )

    excel_file = make_excel(
        models_df,
        specs_df,
        st.session_state.source
    )

    st.download_button(
        "⬇️ Download Excel",
        data=excel_file,
        file_name=(
            "automotive_web_research_v2.xlsx"
        ),
        mime=(
            "application/"
            "vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        use_container_width=True
    )


st.caption(
    "V2: generic labels such as Overview / Explore "
    "are replaced with model names detected from the vehicle URL."
)
