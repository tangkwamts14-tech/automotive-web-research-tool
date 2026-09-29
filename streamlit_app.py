import io
import re
import json
import shutil
from urllib.parse import urljoin, urlparse, unquote

import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="Automotive Web Research Tool V5",
    page_icon="🚗",
    layout="wide",
)

st.title("🚗 Automotive Web Research Tool V5")

st.caption(
    "Browser → Make → Model Card → Model URL → Flexible Specs → Excel"
)


# =========================================================
# BRANDS
# =========================================================

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


# =========================================================
# FILTERS
# =========================================================

NOISE = {
    "",
    "home",
    "overview",
    "learn more",
    "read more",
    "discover",
    "discover more",
    "explore",
    "explore more",
    "view more",
    "view details",
    "details",
    "gallery",
    "offers",
    "services",
    "owners",
    "news",
    "events",
    "contact",
    "contact us",
    "connect",
    "about",
    "about us",
    "shopping tools",
    "request a quote",
    "request a call",
    "request a test drive",
    "test drive",
    "find a dealer",
    "dealer",
    "dealers",
    "build",
    "configure",
    "configurator",
    "vehicles",
    "vehicle",
    "models",
    "model",
    "cars",
    "car",
    "all models",
    "all vehicles",
    "see all vehicles",
    "see all models",
    "brochure",
    "download brochure",
    "menu",
    "search",
    "privacy",
    "terms",
    "login",
    "sign in",
    "country",
    "language",
    "saudi arabia aljabr",
    "saudi arabia",
    "aljabr",
}


BAD_PHRASES = [
    "vat included",
    "request a quote",
    "request a call",
    "request a test drive",
    "shopping tools",
    "customer service",
    "find a dealer",
    "accessories",
    "warranty",
    "cookie",
    "privacy",
    "terms",
    "country",
    "language",
    "saudi arabia aljabr",
]


CTA_WORDS = [
    "learn more",
    "view details",
    "discover",
    "explore",
    "details",
    "overview",
    "read more",
    "more",
]


# =========================================================
# SPEC FIELDS
# =========================================================

SPEC_ALIASES = {

    "Variant / Grade": [
        "variant",
        "grade",
        "trim",
        "version",
    ],

    "Body Type": [
        "body type",
        "body style",
        "vehicle type",
    ],

    "Engine / Motor": [
        "engine",
        "engine type",
        "motor",
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
        "maximum power",
        "max power",
        "power output",
        "engine power",
        "motor power",
        "horsepower",
    ],

    "Max Torque": [
        "maximum torque",
        "max torque",
        "torque output",
        "engine torque",
        "motor torque",
    ],

    "Transmission": [
        "transmission",
        "transmission type",
        "gearbox",
        "gear type",
    ],

    "Drivetrain": [
        "drivetrain",
        "drive type",
        "drive system",
        "driven wheels",
        "wheel drive",
    ],

    "Battery Capacity": [
        "battery capacity",
        "battery pack capacity",
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

    "AC Charging": [
        "ac charging",
        "ac charger",
        "ac charge",
    ],

    "DC Charging": [
        "dc charging",
        "dc fast charging",
        "fast charging",
        "dc charger",
    ],

    "Charging Time": [
        "charging time",
        "charge time",
    ],

    "Fuel Economy": [
        "fuel economy",
        "fuel consumption",
        "combined consumption",
        "mileage",
    ],

    "Fuel Tank": [
        "fuel tank",
        "fuel tank capacity",
        "tank capacity",
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

    "Cargo Capacity": [
        "cargo capacity",
        "cargo volume",
        "luggage capacity",
        "boot capacity",
    ],

    "Kerb Weight": [
        "kerb weight",
        "curb weight",
        "vehicle weight",
    ],

    "Gross Weight": [
        "gross vehicle weight",
        "gross weight",
        "gvw",
        "gvwr",
    ],

    "Wheels / Tires": [
        "wheel size",
        "wheels",
        "tire size",
        "tyre size",
        "tires",
        "tyres",
    ],

    "Drive Modes": [
        "drive modes",
        "driving modes",
        "terrain modes",
    ],

    "Acceleration": [
        "acceleration",
        "0-100",
        "0–100",
        "0 to 100",
    ],

    "Top Speed": [
        "top speed",
        "maximum speed",
        "max speed",
    ],
}


# =========================================================
# BASIC FUNCTIONS
# =========================================================

def clean(value):

    return re.sub(
        r"\s+",
        " ",
        str(value or "")
    ).strip(" \n\r\t:-|")


def normalize_url(url):

    url = clean(url)

    if url.startswith(
        ("http://", "https://")
    ):
        return url

    return "https://" + url


def same_domain(url1, url2):

    a = (
        urlparse(url1)
        .netloc
        .lower()
        .replace("www.", "")
    )

    b = (
        urlparse(url2)
        .netloc
        .lower()
        .replace("www.", "")
    )

    return a == b


# =========================================================
# CHROMIUM
# =========================================================

def find_chromium():

    candidates = [
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("google-chrome"),
        shutil.which("google-chrome-stable"),
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
    ]

    for candidate in candidates:

        if candidate:
            return candidate

    return None


# =========================================================
# RENDER WEBSITE
# =========================================================

def render_page(url, wait_ms=3500):

    chromium_path = find_chromium()

    with sync_playwright() as p:

        options = {
            "headless": True,
            "args": [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        }

        if chromium_path:
            options[
                "executable_path"
            ] = chromium_path

        browser = (
            p.chromium.launch(
                **options
            )
        )

        context = (
            browser.new_context(
                viewport={
                    "width": 1440,
                    "height": 1200,
                },

                user_agent=(
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "Chrome/124 Safari/537.36"
                ),

                locale="en-US",
            )
        )

        page = (
            context.new_page()
        )

        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000,
        )

        try:

            page.wait_for_load_state(
                "networkidle",
                timeout=15000
            )

        except Exception:

            pass

        page.wait_for_timeout(
            wait_ms
        )


        # -----------------------------------------------
        # COOKIE
        # -----------------------------------------------

        for label in [
            "Accept",
            "Accept All",
            "Allow All",
            "Agree",
            "I Agree",
        ]:

            try:

                button = (
                    page.get_by_role(
                        "button",
                        name=re.compile(
                            rf"^{re.escape(label)}$",
                            re.I
                        )
                    )
                )

                if button.count() > 0:

                    button.first.click(
                        timeout=1000
                    )

                    page.wait_for_timeout(
                        500
                    )

                    break

            except Exception:

                pass


        # -----------------------------------------------
        # Try opening vehicle/model menu
        # -----------------------------------------------

        for menu_name in [
            "Vehicle",
            "Vehicles",
            "Models",
            "Our Models",
            "All Models",
            "Cars",
        ]:

            try:

                menu = (
                    page.get_by_text(
                        menu_name,
                        exact=True
                    )
                )

                if menu.count() > 0:

                    menu.first.click(
                        timeout=1500
                    )

                    page.wait_for_timeout(
                        1200
                    )

                    break

            except Exception:

                pass


        # -----------------------------------------------
        # SCROLL
        # -----------------------------------------------

        try:

            height = page.evaluate(
                "document.body.scrollHeight"
            )

            for fraction in [
                0.20,
                0.40,
                0.60,
                0.80,
                1.00,
            ]:

                page.evaluate(
                    f"window.scrollTo(0, {int(height * fraction)})"
                )

                page.wait_for_timeout(
                    600
                )

            page.evaluate(
                "window.scrollTo(0, 0)"
            )

        except Exception:

            pass


        final_url = (
            page.url
        )

        html = (
            page.content()
        )

        visible_text = (
            page.locator(
                "body"
            )
            .inner_text(
                timeout=10000
            )
        )


        # -----------------------------------------------
        # IMPORTANT V5:
        # collect browser DOM elements with
        # text + href + parent text
        # -----------------------------------------------

        elements = page.locator(
            "a"
        ).evaluate_all(
            """
            els => els.map(a => {

                let parent = a.parentElement;

                let levels = [];

                for (let i = 0; i < 6 && parent; i++) {

                    levels.push({
                        tag: parent.tagName || '',
                        cls: parent.className || '',
                        text: (parent.innerText || '').trim()
                    });

                    parent = parent.parentElement;
                }

                return {

                    text:
                        (a.innerText || a.textContent || '').trim(),

                    href:
                        a.href || '',

                    aria:
                        a.getAttribute('aria-label') || '',

                    title:
                        a.getAttribute('title') || '',

                    parents:
                        levels
                };
            })
            """
        )

        browser.close()


    return {
        "url": final_url,
        "html": html,
        "text": visible_text,
        "elements": elements,
    }


# =========================================================
# MAKE
# =========================================================

def infer_make(
    soup,
    url,
    visible_text,
    manual_make,
):

    if clean(manual_make):

        return clean(
            manual_make
        )


    host = (
        urlparse(url)
        .netloc
        .lower()
        .replace("www.", "")
    )


    compact_host = re.sub(
        r"[^a-z0-9]",
        "",
        host
    )


    # -----------------------------------------------
    # DOMAIN FIRST
    # -----------------------------------------------

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


    # -----------------------------------------------
    # TITLE
    # -----------------------------------------------

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

        pattern = (
            r"(?<![A-Za-z0-9])"
            + re.escape(brand)
            + r"(?![A-Za-z0-9])"
        )

        if re.search(
            pattern,
            title,
            re.I
        ):

            return brand


    # -----------------------------------------------
    # PAGE START
    # -----------------------------------------------

    page_start = (
        clean(
            visible_text
        )[:2000]
    )


    for brand in sorted(
        BRANDS,
        key=len,
        reverse=True
    ):

        pattern = (
            r"(?<![A-Za-z0-9])"
            + re.escape(brand)
            + r"(?![A-Za-z0-9])"
        )

        if re.search(
            pattern,
            page_start,
            re.I
        ):

            return brand


    return (
        host
        .split(".")[0]
        .replace("-", " ")
        .title()
    )


# =========================================================
# MODEL NAME
# =========================================================

def clean_model_name(
    name,
    make
):

    name = clean(name)


    # Remove line after From SAR etc.
    name = re.sub(
        r"\bfrom\s+(?:sar|aed|qar|usd).*$",
        "",
        name,
        flags=re.I
    )


    # Remove CTA
    for cta in CTA_WORDS:

        name = re.sub(
            re.escape(cta),
            "",
            name,
            flags=re.I
        )


    # Remove The
    name = re.sub(
        r"^the\s+",
        "",
        name,
        flags=re.I
    )


    # Remove Make prefix
    name = re.sub(
        r"^"
        + re.escape(make)
        + r"\s+",
        "",
        name,
        flags=re.I
    )


    return clean(
        name
    )


def plausible_model(
    name,
    make
):

    name = (
        clean_model_name(
            name,
            make
        )
    )

    if not name:
        return False

    lower = (
        name.lower()
    )

    if lower in NOISE:
        return False

    if len(name) < 2:
        return False

    if len(name) > 40:
        return False

    if re.fullmatch(
        r"[\d\s.,]+",
        name
    ):
        return False

    if any(
        phrase in lower
        for phrase in BAD_PHRASES
    ):
        return False

    return True


# =========================================================
# EXTRACT MODEL NAME FROM CARD TEXT
# =========================================================

def model_from_card_text(
    text,
    make
):

    text = clean(text)

    if not text:
        return ""


    # Split card into lines
    raw_lines = re.split(
        r"[\n\r]+",
        str(text)
    )


    lines = []

    for line in raw_lines:

        line = clean(line)

        if not line:
            continue

        lower = (
            line.lower()
        )

        if lower in NOISE:
            continue

        if lower.startswith(
            "from "
        ):
            continue

        if "vat included" in lower:
            continue

        if lower in [
            "ice",
            "hev",
            "phev",
            "bev",
            "ev",
            "hybrid",
            "electric",
            "diesel",
            "gasoline",
            "petrol",
        ]:
            continue

        if plausible_model(
            line,
            make
        ):

            lines.append(
                clean_model_name(
                    line,
                    make
                )
            )


    if not lines:
        return ""


    # First sensible short line
    return lines[0]


# =========================================================
# FIND MODEL CARDS
# =========================================================

def discover_models(
    rendered,
    make
):

    base_url = (
        rendered["url"]
    )

    elements = (
        rendered["elements"]
    )

    rows = []


    # =====================================================
    # METHOD 1
    # CTA link → walk UP parents → find model card
    #
    # This is the main V5 fix.
    # =====================================================

    for element in elements:

        link_text = clean(
            element.get(
                "text",
                ""
            )
        )

        href = clean(
            element.get(
                "href",
                ""
            )
        )

        if not href:
            continue


        lower_link = (
            link_text.lower()
        )


        is_cta = (
            lower_link
            in CTA_WORDS
        )


        if not is_cta:
            continue


        if not same_domain(
            base_url,
            href
        ):
            continue


        parents = (
            element.get(
                "parents",
                []
            )
        )


        candidate = ""


        # Walk from nearest parent outward
        for parent in parents:

            parent_text = clean(
                parent.get(
                    "text",
                    ""
                )
            )

            if not parent_text:
                continue

            # Avoid giant containers
            if len(parent_text) > 600:
                continue


            possible = (
                model_from_card_text(
                    parent_text,
                    make
                )
            )


            if plausible_model(
                possible,
                make
            ):

                candidate = (
                    possible
                )

                break


        if candidate:

            rows.append(
                {
                    "Make":
                    make,

                    "Model":
                    candidate,

                    "Model URL":
                    href,

                    "Detected From":
                    "Model Card + CTA",
                }
            )


    # =====================================================
    # METHOD 2
    # Model-looking URLs
    # =====================================================

    for element in elements:

        href = clean(
            element.get(
                "href",
                ""
            )
        )

        text = clean(
            element.get(
                "text",
                ""
            )
        )


        if not href:
            continue


        if not same_domain(
            base_url,
            href
        ):
            continue


        path = (
            urlparse(href)
            .path
            .lower()
        )


        model_route = any(
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


        if not model_route:
            continue


        candidate = (
            clean_model_name(
                text,
                make
            )
        )


        if not plausible_model(
            candidate,
            make
        ):

            # URL fallback
            parts = [
                p
                for p
                in urlparse(
                    href
                ).path
                .strip("/")
                .split("/")
                if p
            ]


            if parts:

                candidate = (
                    unquote(
                        parts[-1]
                    )
                    .replace(
                        "-",
                        " "
                    )
                    .replace(
                        "_",
                        " "
                    )
                )

                candidate = clean(
                    candidate
                )

                candidate = " ".join(
                    word.upper()
                    if (
                        re.search(
                            r"\d",
                            word
                        )
                        or
                        len(word) <= 3
                    )
                    else
                    word.title()
                    for word
                    in candidate.split()
                )


        if plausible_model(
            candidate,
            make
        ):

            rows.append(
                {
                    "Make":
                    make,

                    "Model":
                    candidate,

                    "Model URL":
                    href,

                    "Detected From":
                    "Model URL",
                }
            )


    # =====================================================
    # CLEAN
    # =====================================================

    if not rows:

        return pd.DataFrame(
            columns=[
                "Make",
                "Model",
                "Model URL",
                "Detected From",
            ]
        )


    df = pd.DataFrame(
        rows
    )


    df["Model"] = (
        df["Model"]
        .map(
            lambda x:
            clean_model_name(
                x,
                make
            )
        )
    )


    df = df[
        df[
            "Model"
        ].map(
            lambda x:
            plausible_model(
                x,
                make
            )
        )
    ]


    # Remove homepage pretending to be model page
    home_path = (
        urlparse(
            base_url
        ).path.rstrip("/")
    )


    def real_model_url(url):

        path = (
            urlparse(
                url
            ).path.rstrip("/")
        )

        if (
            url == base_url
            or
            path == home_path
        ):
            return False

        return True


    df["Has Model URL"] = (
        df["Model URL"]
        .map(
            real_model_url
        )
    )


    # Prefer records that have actual model URL
    df = (
        df.sort_values(
            [
                "Model",
                "Has Model URL",
            ],
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
            keep="first"
        )
        .reset_index(
            drop=True
        )
    )


    return df


# =========================================================
# SPEC FIELD MATCHING
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
                label == alias
                or
                alias in label
            ):

                return field


    return None


# =========================================================
# STRUCTURED SPEC PAIRS
# =========================================================

def add_pair(
    pairs,
    label,
    value
):

    label = clean(
        label
    )

    value = clean(
        value
    )


    if not label:
        return

    if not value:
        return

    if len(label) > 100:
        return

    if len(value) > 400:
        return


    pairs.append(
        (
            label,
            value
        )
    )


def extract_pairs(
    soup
):

    pairs = []


    # TABLE
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


    # DT DD
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


    # Label : Value
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
            4
            <= len(text)
            <= 250
        ):

            match = re.match(
                r"^([^:]{2,80})"
                r"\s*:\s*"
                r"(.{1,160})$",
                text
            )


            if match:

                add_pair(
                    pairs,
                    match.group(1),
                    match.group(2)
                )


    # TWO CHILDREN
    for element in soup.find_all(
        [
            "div",
            "li",
        ]
    ):

        children = (
            element.find_all(
                recursive=False
            )
        )


        if len(children) == 2:

            label = clean(
                children[0]
                .get_text(
                    " ",
                    strip=True
                )
            )

            value = clean(
                children[1]
                .get_text(
                    " ",
                    strip=True
                )
            )


            if (
                len(label) <= 80
                and
                len(value) <= 300
            ):

                add_pair(
                    pairs,
                    label,
                    value
                )


    return pairs


# =========================================================
# FALLBACK SPEC PATTERNS
# =========================================================

FALLBACKS = {

    "Displacement": [

        r"(?i)\b([0-9,]+\s*cc)\b",

        r"(?i)\b([0-9.]+\s*(?:l|liter|litre))\s+engine\b",

    ],

    "Max Power": [

        (
            r"(?i)"
            r"(?:maximum|max\.?)?\s*"
            r"(?:power|output|horsepower)"
            r"\s*[:\-]?\s*"
            r"([0-9.,]+\s*(?:hp|bhp|ps|kw))"
        ),

    ],

    "Max Torque": [

        (
            r"(?i)"
            r"(?:maximum|max\.?)?\s*"
            r"torque"
            r"\s*[:\-]?\s*"
            r"([0-9.,]+\s*(?:nm|n\.m))"
        ),

    ],

    "Drivetrain": [

        r"(?i)\b(FWD|RWD|AWD|4WD|4X4|2WD)\b",

    ],

    "Battery Capacity": [

        (
            r"(?i)"
            r"(?:battery(?:\s+capacity|\s+pack|\s+size)?)"
            r"\s*[:\-]?\s*"
            r"([0-9.,]+\s*kwh)"
        ),

    ],

    "Electric Range": [

        (
            r"(?i)"
            r"(?:electric|ev|driving|wltp|nedc)?"
            r"\s*range"
            r"\s*[:\-]?\s*"
            r"([0-9.,]+\s*km)"
        ),

    ],

    "Fuel Economy": [

        r"(?i)\b([0-9.,]+\s*km\s*/\s*l)\b",

        r"(?i)\b([0-9.,]+\s*l\s*/\s*100\s*km)\b",

    ],

    "Top Speed": [

        (
            r"(?i)"
            r"(?:top|max(?:imum)?\s+speed)"
            r"\s*[:\-]?\s*"
            r"([0-9.,]+\s*km/?h)"
        ),

    ],
}


# =========================================================
# INSPECT MODEL
# =========================================================

def inspect_model(
    model_url,
    make,
    model,
):

    try:

        rendered = (
            render_page(
                model_url,
                wait_ms=3000
            )
        )


        soup = (
            BeautifulSoup(
                rendered["html"],
                "html.parser"
            )
        )


        result = {

            "Make":
            make,

            "Model":
            model,

            "Source URL":
            rendered["url"],
        }


        raw = []


        # -----------------------------------------------
        # STRUCTURED SPECS
        # -----------------------------------------------

        for (
            label,
            value
        ) in extract_pairs(
            soup
        ):

            field = (
                canonical_field(
                    label
                )
            )


            if field:

                if not result.get(
                    field
                ):

                    result[
                        field
                    ] = value


                raw.append(
                    f"{label}: {value}"
                )


        # -----------------------------------------------
        # VISIBLE TEXT
        # -----------------------------------------------

        text = clean(
            rendered[
                "text"
            ]
        )


        # -----------------------------------------------
        # FALLBACK
        # -----------------------------------------------

        for (
            field,
            patterns
        ) in FALLBACKS.items():

            if result.get(
                field
            ):
                continue


            for pattern in patterns:

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


        # -----------------------------------------------
        # TRANSMISSION
        # -----------------------------------------------

        if not result.get(
            "Transmission"
        ):

            patterns = [

                r"(?i)\b([0-9]+[- ]speed automatic)\b",

                r"(?i)\b([0-9]+[- ]speed manual)\b",

                r"(?i)\b([0-9]+[- ]speed DCT)\b",

                r"(?i)\b(CVT)\b",

                r"(?i)\b(e-CVT)\b",

                r"(?i)\b(DCT)\b",

                r"(?i)\b(automatic transmission)\b",

                r"(?i)\b(manual transmission)\b",
            ]


            for pattern in patterns:

                match = re.search(
                    pattern,
                    text
                )


                if match:

                    result[
                        "Transmission"
                    ] = clean(
                        match.group(1)
                    )

                    break


        # -----------------------------------------------
        # POWERTRAIN
        # -----------------------------------------------

        if not result.get(
            "Fuel / Powertrain"
        ):

            options = [

                "Plug-in Hybrid",
                "PHEV",
                "Hybrid",
                "HEV",
                "Battery Electric",
                "BEV",
                "Electric",
                "Diesel",
                "Gasoline",
                "Petrol",

            ]


            found = []


            for option in options:

                if re.search(
                    r"\b"
                    + re.escape(
                        option
                    )
                    + r"\b",
                    text,
                    re.I
                ):

                    found.append(
                        option
                    )


            if found:

                result[
                    "Fuel / Powertrain"
                ] = ", ".join(
                    dict.fromkeys(
                        found
                    )
                )


        result[
            "Raw Matched Specs"
        ] = " ; ".join(
            raw[:120]
        )


        return result


    except Exception as error:

        return {

            "Make":
            make,

            "Model":
            model,

            "Source URL":
            model_url,

            "Error":
            str(error),
        }


# =========================================================
# EXCEL
# =========================================================

def create_excel(
    models_df,
    specs_df,
    source_url
):

    output = (
        io.BytesIO()
    )


    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:


        models_df.to_excel(
            writer,
            index=False,
            sheet_name="Models"
        )


        if (
            specs_df is not None
            and
            not specs_df.empty
        ):

            specs_df.to_excel(
                writer,
                index=False,
                sheet_name="Specs"
            )


        pd.DataFrame(
            [
                {
                    "Source URL":
                    source_url,

                    "Method":
                    (
                        "Browser-rendered model card "
                        "and specification extraction."
                    ),

                    "Rule":
                    (
                        "Only fields detected on "
                        "the source are displayed. "
                        "Missing values remain blank."
                    ),
                }
            ]
        ).to_excel(
            writer,
            index=False,
            sheet_name="Methodology"
        )


    return (
        output.getvalue()
    )


# =========================================================
# SIDEBAR
# =========================================================

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


# =========================================================
# URL
# =========================================================

url = st.text_input(
    "Website URL",
    placeholder=(
        "https://www.kia.com/sa/en/main.html"
    )
)


# =========================================================
# CHECK
# =========================================================

if st.button(
    "🌐 Open website & find models",
    type="primary",
    use_container_width=True,
):

    if not clean(url):

        st.error(
            "Enter a website URL."
        )

        st.stop()


    try:

        with st.spinner(
            "Opening website, loading JavaScript and reading model cards..."
        ):

            rendered = (
                render_page(
                    normalize_url(
                        url
                    )
                )
            )


            soup = (
                BeautifulSoup(
                    rendered[
                        "html"
                    ],
                    "html.parser"
                )
            )


            make = (
                infer_make(
                    soup,
                    rendered[
                        "url"
                    ],
                    rendered[
                        "text"
                    ],
                    manual_make,
                )
            )


            models_df = (
                discover_models(
                    rendered,
                    make
                )
            )


            st.session_state[
                "models"
            ] = models_df


            st.session_state[
                "make"
            ] = make


            st.session_state[
                "source"
            ] = rendered[
                "url"
            ]


            st.session_state[
                "specdf"
            ] = pd.DataFrame()


            st.session_state[
                "text_length"
            ] = len(
                rendered[
                    "text"
                ]
            )


    except Exception as error:

        st.error(
            "Browser error"
        )

        st.code(
            str(error)
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


    c1, c2, c3 = (
        st.columns(3)
    )


    c1.metric(
        "Make",
        st.session_state.get(
            "make",
            "-"
        )
    )


    c2.metric(
        "Models found",
        len(
            models_df
        )
    )


    if not models_df.empty:

        valid_urls = int(
            models_df[
                "Has Model URL"
            ].sum()
        )

    else:

        valid_urls = 0


    c3.metric(
        "Models with URL",
        valid_urls
    )


    st.subheader(
        "1. Models found"
    )


    if models_df.empty:

        st.warning(
            "No reliable model cards found."
        )


    else:

        editable = (
            models_df.assign(
                Inspect=False
            )
        )


        edited = (
            st.data_editor(
                editable,
                hide_index=True,
                use_container_width=True,

                column_config={

                    "Inspect":
                    st.column_config.CheckboxColumn(
                        "Inspect specs"
                    ),

                    "Has Model URL":
                    st.column_config.CheckboxColumn(
                        "Valid URL"
                    ),
                },

                disabled=[
                    "Make",
                    "Model",
                    "Model URL",
                    "Detected From",
                    "Has Model URL",
                ],
            )
        )


        # =================================================
        # INSPECT
        # =================================================

        if st.button(
            "⚙️ Inspect selected models",
            use_container_width=True,
        ):

            selected = (
                edited[
                    (
                        edited[
                            "Inspect"
                        ] == True
                    )
                    &
                    (
                        edited[
                            "Has Model URL"
                        ] == True
                    )
                ]
                .head(
                    max_pages
                )
            )


            if selected.empty:

                st.warning(
                    "Select at least one model "
                    "that has a valid Model URL."
                )


            else:

                results = []

                progress = (
                    st.progress(0)
                )

                status = (
                    st.empty()
                )

                total = (
                    len(selected)
                )


                for (
                    number,
                    (_, row)
                ) in enumerate(
                    selected.iterrows(),
                    start=1
                ):

                    status.write(
                        f"Reading "
                        f"{row['Make']} "
                        f"{row['Model']} "
                        f"({number}/{total})..."
                    )


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
                        number
                        / total
                    )


                status.write(
                    "Finished."
                )


                st.session_state[
                    "specdf"
                ] = (
                    pd.DataFrame(
                        results
                    )
                )


    # =====================================================
    # SPECS
    # =====================================================

    specs_df = (
        st.session_state.get(
            "specdf",
            pd.DataFrame()
        )
    )


    if not specs_df.empty:

        st.subheader(
            "2. Specs found"
        )


        useful = []


        for column in (
            specs_df.columns
        ):

            if column in [
                "Make",
                "Model",
                "Source URL",
                "Error",
            ]:

                useful.append(
                    column
                )

                continue


            if (
                specs_df[
                    column
                ]
                .replace(
                    "",
                    pd.NA
                )
                .notna()
                .any()
            ):

                useful.append(
                    column
                )


        st.dataframe(
            specs_df[
                useful
            ],
            hide_index=True,
            use_container_width=True,
        )


    # =====================================================
    # EXCEL
    # =====================================================

    excel_file = (
        create_excel(
            models_df,
            specs_df,
            st.session_state.get(
                "source",
                ""
            ),
        )
    )


    st.download_button(
        "⬇️ Download Excel",
        data=excel_file,
        file_name=(
            "automotive_web_research_v5.xlsx"
        ),
        mime=(
            "application/"
            "vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        use_container_width=True,
    )


# =========================================================
# FOOTER
# =========================================================

st.info(
    "V5: model names are linked to their own vehicle cards. "
    "Only models with a real model URL can be inspected. "
    "Specs are flexible: available fields are shown; "
    "missing fields remain blank."
)
