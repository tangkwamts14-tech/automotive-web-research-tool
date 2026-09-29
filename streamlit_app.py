import io
import re
import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

st.set_page_config(
    page_title="Automotive Website Research",
    page_icon="🚗",
    layout="wide"
)

st.title("🚗 Automotive Website Research")
st.caption("Paste an automotive website URL → Research → View data → Download Excel")


# =========================================================
# SETTINGS
# =========================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/124 Safari/537.36"
    )
}

CTA_WORDS = [
    "explore more",
    "learn more",
    "discover more",
    "discover",
    "view details",
    "view model",
    "more details",
]

SPEC_WORDS = [
    "specification",
    "specifications",
    "technical specifications",
    "technical specification",
    "specs",
]

NOISE = {
    "home",
    "vehicles",
    "vehicle",
    "models",
    "all models",
    "all vehicles",
    "offers",
    "owners",
    "services",
    "shopping tools",
    "about",
    "contact",
    "find a dealer",
    "request a quote",
    "test drive",
    "learn more",
    "explore more",
    "discover",
    "discover more",
}


# =========================================================
# HELPERS
# =========================================================

def clean(x):
    return re.sub(r"\s+", " ", str(x or "")).strip()


def normal_url(url):
    url = clean(url)

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    return url


def same_site(a, b):

    aa = urlparse(a).netloc.lower().replace("www.", "")
    bb = urlparse(b).netloc.lower().replace("www.", "")

    return aa == bb


def get_page(url):

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
        allow_redirects=True,
    )

    response.raise_for_status()

    return (
        response.url,
        BeautifulSoup(response.text, "html.parser")
    )


# =========================================================
# MAKE
# =========================================================

def detect_make(soup, url):

    title = clean(
        soup.title.get_text(" ", strip=True)
        if soup.title
        else ""
    )

    host = (
        urlparse(url)
        .netloc
        .lower()
        .replace("www.", "")
    )

    known = [
        "Kia",
        "Toyota",
        "Honda",
        "Hyundai",
        "Nissan",
        "Ford",
        "Chevrolet",
        "BMW",
        "Audi",
        "Mercedes-Benz",
        "Lexus",
        "Mazda",
        "Mitsubishi",
        "Suzuki",
        "Volkswagen",
        "Volvo",
        "Porsche",
        "Jeep",
        "GMC",
        "Cadillac",
        "Genesis",
        "Geely",
        "Chery",
        "Changan",
        "BYD",
        "GAC",
        "MG",
        "JAC",
        "Jetour",
        "Jaecoo",
        "Omoda",
        "Haval",
        "GWM",
        "Hongqi",
        "Exeed",
        "Peugeot",
        "Renault",
    ]

    for brand in known:

        key = re.sub(
            r"[^a-z0-9]",
            "",
            brand.lower()
        )

        domain = re.sub(
            r"[^a-z0-9]",
            "",
            host
        )

        if key in domain:
            return brand

    for brand in known:

        if re.search(
            r"\b" + re.escape(brand) + r"\b",
            title,
            re.I
        ):
            return brand

    return host.split(".")[0].title()


# =========================================================
# MODEL NAME FROM TEXT
# =========================================================

def model_name_from_text(text, make):

    text = clean(text)

    text = re.sub(
        r"^the\s+",
        "",
        text,
        flags=re.I
    )

    text = re.sub(
        r"^" + re.escape(make) + r"\s+",
        "",
        text,
        flags=re.I
    )

    text = re.split(
        r"\bfrom\s+(?:sar|qar|aed|usd)\b",
        text,
        flags=re.I
    )[0]

    return clean(text)


def valid_model(name, make):

    name = clean(name)

    if not name:
        return False

    if name.lower() in NOISE:
        return False

    if name.lower() == make.lower():
        return False

    if len(name) < 2 or len(name) > 45:
        return False

    if re.fullmatch(r"[\d\s.,]+", name):
        return False

    return True


# =========================================================
# FIND MODELS
# =========================================================

def find_models(soup, base_url, make):

    rows = []

    # -----------------------------------------------------
    # METHOD 1
    # Heading → nearby Explore/Learn More
    # -----------------------------------------------------

    for heading in soup.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6"]
    ):

        heading_text = clean(
            heading.get_text(" ", strip=True)
        )

        if not heading_text:
            continue

        model = model_name_from_text(
            heading_text,
            make
        )

        if not valid_model(model, make):
            continue

        container = heading

        found_url = ""

        # climb up only a few levels
        for _ in range(5):

            if not container:
                break

            links = container.find_all(
                "a",
                href=True
            )

            for a in links:

                label = clean(
                    a.get_text(" ", strip=True)
                ).lower()

                if any(
                    word in label
                    for word in CTA_WORDS
                ):

                    candidate_url = urljoin(
                        base_url,
                        a.get("href")
                    )

                    if same_site(
                        base_url,
                        candidate_url
                    ):
                        found_url = candidate_url
                        break

            if found_url:
                break

            container = container.parent

        if found_url:

            rows.append({
                "Make": make,
                "Model": model,
                "Model URL": found_url,
                "Detected From": "Heading + CTA",
            })

    # -----------------------------------------------------
    # METHOD 2
    # Links that look like model pages
    # -----------------------------------------------------

    for a in soup.find_all("a", href=True):

        href = urljoin(
            base_url,
            a["href"]
        )

        if not same_site(base_url, href):
            continue

        path = urlparse(href).path.lower()

        looks_like_vehicle = any(
            x in path
            for x in [
                "/showroom/",
                "/models/",
                "/model/",
                "/vehicles/",
                "/vehicle/",
                "/cars/",
            ]
        )

        if not looks_like_vehicle:
            continue

        text = clean(
            a.get_text(" ", strip=True)
        )

        model = model_name_from_text(
            text,
            make
        )

        if not valid_model(model, make):

            parts = [
                p for p in
                urlparse(href).path.split("/")
                if p
            ]

            if parts:

                ignore = {
                    "showroom",
                    "models",
                    "model",
                    "vehicles",
                    "vehicle",
                    "cars",
                    "gallery.html",
                    "overview.html",
                    "specification.html",
                    "specifications.html",
                }

                usable = [
                    p for p in parts
                    if p.lower() not in ignore
                ]

                if usable:

                    model = (
                        usable[-1]
                        .replace("-", " ")
                        .replace("_", " ")
                        .upper()
                    )

        if valid_model(model, make):

            rows.append({
                "Make": make,
                "Model": model,
                "Model URL": href,
                "Detected From": "Vehicle URL",
            })

    if not rows:

        return pd.DataFrame(
            columns=[
                "Make",
                "Model",
                "Model URL",
                "Detected From"
            ]
        )

    df = pd.DataFrame(rows)

    # Remove obvious CTA names accidentally detected
    df = df[
        ~df["Model"]
        .str.lower()
        .isin(NOISE)
    ]

    # Prefer shortest useful URL per model
    df["URL Length"] = (
        df["Model URL"]
        .str.len()
    )

    df = (
        df.sort_values(
            ["Model", "URL Length"]
        )
        .drop_duplicates(
            ["Make", "Model"],
            keep="first"
        )
        .drop(
            columns=["URL Length"]
        )
        .reset_index(drop=True)
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

    for a in soup.find_all(
        "a",
        href=True
    ):

        label = clean(
            a.get_text(" ", strip=True)
        ).lower()

        href_text = (
            a["href"].lower()
        )

        if (
            any(x in label for x in SPEC_WORDS)
            or
            "specification" in href_text
            or
            "/spec" in href_text
        ):

            return urljoin(
                final_url,
                a["href"]
            )

    # Kia-style fallback
    if "gallery.html" in final_url:

        return final_url.replace(
            "gallery.html",
            "specification.html"
        )

    if "overview.html" in final_url:

        return final_url.replace(
            "overview.html",
            "specification.html"
        )

    return final_url


# =========================================================
# EXTRACT FLEXIBLE SPECS
# =========================================================

def extract_specs(model_url, make, model):

    spec_url = find_spec_page(
        model_url
    )

    try:

        final_url, soup = get_page(
            spec_url
        )

    except Exception as e:

        return [{
            "Make": make,
            "Model": model,
            "Source URL": spec_url,
            "Error": str(e)
        }]

    pairs = []

    # -----------------------------------------------------
    # TABLE
    # -----------------------------------------------------

    for tr in soup.find_all("tr"):

        cells = [
            clean(
                x.get_text(
                    " ",
                    strip=True
                )
            )
            for x in tr.find_all(
                ["th", "td"]
            )
        ]

        if len(cells) >= 2:

            pairs.append(
                (
                    cells[0],
                    " | ".join(cells[1:])
                )
            )

    # -----------------------------------------------------
    # DT / DD
    # -----------------------------------------------------

    for dt in soup.find_all("dt"):

        dd = dt.find_next_sibling("dd")

        if dd:

            pairs.append(
                (
                    clean(
                        dt.get_text(
                            " ",
                            strip=True
                        )
                    ),
                    clean(
                        dd.get_text(
                            " ",
                            strip=True
                        )
                    )
                )
            )

    # -----------------------------------------------------
    # HTML blocks
    # -----------------------------------------------------

    for tag in soup.find_all(
        ["li", "p", "div"]
    ):

        children = tag.find_all(
            recursive=False
        )

        if len(children) == 2:

            label = clean(
                children[0].get_text(
                    " ",
                    strip=True
                )
            )

            value = clean(
                children[1].get_text(
                    " ",
                    strip=True
                )
            )

            if (
                label
                and value
                and len(label) <= 80
                and len(value) <= 250
                and label != value
            ):

                pairs.append(
                    (label, value)
                )

    # -----------------------------------------------------
    # COLLECT ALL FIELDS
    # -----------------------------------------------------

    result = {
        "Make": make,
        "Model": model,
        "Source URL": final_url,
    }

    used = set()

    for label, value in pairs:

        label = clean(label)
        value = clean(value)

        if not label or not value:
            continue

        if label.lower() in NOISE:
            continue

        key = label

        # prevent duplicate Excel column names
        if key in used:

            if result.get(key) == value:
                continue

            number = 2

            while f"{key} ({number})" in used:
                number += 1

            key = f"{key} ({number})"

        result[key] = value
        used.add(key)

    # -----------------------------------------------------
    # TEXT FALLBACKS
    # -----------------------------------------------------

    page_text = clean(
        soup.get_text(" ", strip=True)
    )

    patterns = {
        "Displacement": [
            r"\b([0-9,]+\s*cc)\b",
            r"\b([0-9.]+\s*[Ll])\s+engine\b",
        ],

        "Max Power": [
            r"(?i)(?:power|horsepower)[^0-9]{0,20}([0-9.]+\s*(?:hp|ps|kw|bhp))"
        ],

        "Max Torque": [
            r"(?i)torque[^0-9]{0,20}([0-9.]+\s*(?:nm|n\.m))"
        ],

        "Battery Capacity": [
            r"(?i)battery[^0-9]{0,30}([0-9.]+\s*kwh)"
        ],

        "Electric Range": [
            r"(?i)(?:range)[^0-9]{0,20}([0-9.]+\s*km)"
        ],

        "Wheelbase": [
            r"(?i)wheelbase[^0-9]{0,20}([0-9,.]+\s*mm)"
        ],

        "Top Speed": [
            r"(?i)(?:top|max(?:imum)?)\s+speed[^0-9]{0,20}([0-9.]+\s*km/?h)"
        ],
    }

    for field, regexes in patterns.items():

        if field in result:
            continue

        for pattern in regexes:

            m = re.search(
                pattern,
                page_text
            )

            if m:

                result[field] = clean(
                    m.group(1)
                )

                break

    return [result]


# =========================================================
# EXCEL
# =========================================================

def make_excel(models, specs):

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

        if not specs.empty:

            specs.to_excel(
                writer,
                index=False,
                sheet_name="Specs"
            )

    return output.getvalue()


# =========================================================
# UI
# =========================================================

url = st.text_input(
    "Website URL",
    placeholder="https://www.kia.com/sa/en/main.html"
)

if st.button(
    "🔎 Research Website",
    type="primary",
    use_container_width=True
):

    if not clean(url):

        st.warning(
            "ใส่ URL ก่อน"
        )

        st.stop()

    try:

        with st.spinner(
            "กำลังอ่านเว็บไซต์..."
        ):

            final_url, soup = get_page(
                normal_url(url)
            )

            make = detect_make(
                soup,
                final_url
            )

            models = find_models(
                soup,
                final_url,
                make
            )

            st.session_state["make"] = make
            st.session_state["models"] = models
            st.session_state["specs"] = pd.DataFrame()

    except Exception as e:

        st.error(str(e))


# =========================================================
# SHOW MODELS
# =========================================================

if "models" in st.session_state:

    models = st.session_state["models"]

    c1, c2 = st.columns(2)

    c1.metric(
        "Make",
        st.session_state["make"]
    )

    c2.metric(
        "Models found",
        len(models)
    )

    st.subheader(
        "Models"
    )

    if models.empty:

        st.warning(
            "ยังไม่พบ Model จากเว็บไซต์นี้"
        )

    else:

        choose = models.copy()

        choose.insert(
            0,
            "Research Specs",
            False
        )

        edited = st.data_editor(
            choose,
            hide_index=True,
            use_container_width=True,
            disabled=[
                "Make",
                "Model",
                "Model URL",
                "Detected From"
            ]
        )

        if st.button(
            "⚙️ Get Specs",
            use_container_width=True
        ):

            selected = edited[
                edited["Research Specs"] == True
            ]

            if selected.empty:

                st.warning(
                    "ติ๊กรุ่นที่ต้องการก่อน"
                )

            else:

                all_specs = []

                progress = st.progress(0)

                for i, (_, row) in enumerate(
                    selected.iterrows(),
                    start=1
                ):

                    with st.spinner(
                        f"กำลังอ่าน {row['Make']} {row['Model']}..."
                    ):

                        all_specs.extend(
                            extract_specs(
                                row["Model URL"],
                                row["Make"],
                                row["Model"]
                            )
                        )

                    progress.progress(
                        i / len(selected)
                    )

                st.session_state["specs"] = (
                    pd.DataFrame(
                        all_specs
                    )
                )


# =========================================================
# SHOW SPECS
# =========================================================

if (
    "specs" in st.session_state
    and
    not st.session_state["specs"].empty
):

    specs = st.session_state["specs"]

    st.subheader(
        "Research Results"
    )

    # Remove completely empty columns
    specs = specs.dropna(
        axis=1,
        how="all"
    )

    st.dataframe(
        specs,
        hide_index=True,
        use_container_width=True
    )

    excel = make_excel(
        st.session_state["models"],
        specs
    )

    st.download_button(
        "⬇️ Download Excel",
        excel,
        "automotive_research.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
