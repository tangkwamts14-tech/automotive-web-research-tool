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
    page_title="Automotive Web Research Tool V4",
    page_icon="🚗",
    layout="wide",
)

st.title("🚗 Automotive Web Research Tool V4")
st.caption(
    "Browser rendering → Make → Models → Flexible Specs → Excel"
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
# WORDS / FILTERS
# =========================================================

SECTION_WORDS = [
    "vehicle",
    "vehicles",
    "model",
    "models",
    "our models",
    "all models",
    "cars",
    "our cars",
    "lineup",
    "line-up",
    "range",
    "explore models",
    "explore vehicles",
]

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
    "test drive",
    "request a test drive",
    "request a quote",
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
}


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
        "cc",
    ],

    "Cylinders": [
        "cylinders",
        "cylinder",
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
        "wheel",
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
# BASIC
# =========================================================

def clean(value):
    return re.sub(
        r"\s+",
        " ",
        str(value or "")
    ).strip(" \n\r\t:-|")


def normalize_url(url):
    url = clean(url)

    if url.startswith(("http://", "https://")):
        return url

    return "https://" + url


def same_domain(url1, url2):

    a = urlparse(url1).netloc.lower().replace("www.", "")
    b = urlparse(url2).netloc.lower().replace("www.", "")

    return a == b


# =========================================================
# FIND CHROMIUM
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
# BROWSER RENDERING
# =========================================================

def render_page(url, wait_ms=3500):

    chromium_path = find_chromium()

    with sync_playwright() as p:

        launch_args = {
            "headless": True,
            "args": [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        }

        if chromium_path:
            launch_args["executable_path"] = chromium_path

        browser = p.chromium.launch(
            **launch_args
        )

        context = browser.new_context(
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

        page = context.new_page()

        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000,
        )

        # Wait for JS applications
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

        # Try to click common cookie buttons
        cookie_words = [
            "Accept",
            "Accept All",
            "Allow All",
            "I Agree",
            "Agree",
        ]

        for word in cookie_words:

            try:
                button = page.get_by_role(
                    "button",
                    name=re.compile(
                        rf"^{re.escape(word)}$",
                        re.I
                    )
                )

                if button.count() > 0:
                    button.first.click(
                        timeout=1000
                    )
                    page.wait_for_timeout(500)
                    break

            except Exception:
                pass

        # Scroll so lazy-loaded model cards appear
        try:

            for _ in range(5):

                page.evaluate(
                    "window.scrollBy(0, document.body.scrollHeight / 5)"
                )

                page.wait_for_timeout(
                    600
                )

            page.evaluate(
                "window.scrollTo(0, 0)"
            )

        except Exception:
            pass

        final_url = page.url
        html = page.content()
        visible_text = page.locator(
            "body"
        ).inner_text(
            timeout=10000
        )

        links = page.locator(
            "a"
        ).evaluate_all(
            """
            els => els.map(a => ({
                text: (a.innerText || a.textContent || '').trim(),
                href: a.href || '',
                aria: a.getAttribute('aria-label') || '',
                title: a.getAttribute('title') || ''
            }))
            """
        )

        browser.close()

    return {
        "url": final_url,
        "html": html,
        "text": visible_text,
        "links": links,
    }


# =========================================================
# MAKE DETECTION
# =========================================================

def infer_make(
    soup,
    url,
    visible_text,
    manual_make,
):

    if clean(manual_make):
        return clean(manual_make)

    host = (
        urlparse(url)
        .netloc
        .lower()
        .replace("www.", "")
    )

    title = clean(
        soup.title.get_text(
            " ",
            strip=True
        )
        if soup.title
        else ""
    )

    site_name = ""

    meta = soup.find(
        "meta",
        attrs={
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

    # -----------------------------------------------------
    # Priority 1: domain
    # -----------------------------------------------------

    compact_host = re.sub(
        r"[^a-z0-9]",
        "",
        host
    )

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

    # -----------------------------------------------------
    # Priority 2: title / site name
    # Exact word boundaries
    # -----------------------------------------------------

    header_text = (
        title
        + " "
        + site_name
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
            header_text,
            re.I
        ):
            return brand

    # -----------------------------------------------------
    # Priority 3: first part of visible page
    # -----------------------------------------------------

    first_text = clean(
        visible_text
    )[:2500]

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
            first_text,
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
# URL → POSSIBLE MODEL
# =========================================================

def pretty_slug(slug):

    slug = unquote(slug)

    slug = re.sub(
        r"[-_]+",
        " ",
        slug
    )

    slug = clean(slug)

    words = []

    for word in slug.split():

        if (
            re.search(r"\d", word)
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

    return " ".join(words)


def model_from_url(url):

    path = (
        urlparse(url)
        .path
        .strip("/")
    )

    parts = [
        p
        for p in path.split("/")
        if p
    ]

    if not parts:
        return ""

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
        "new-cars",
        "new-vehicles",
        "all-models",
        "all-vehicles",
        "main.html",
        "index.html",
    }

    lower_parts = [
        p.lower()
        for p in parts
    ]

    route_words = [
        "vehicles",
        "vehicle",
        "models",
        "model",
        "cars",
        "car",
    ]

    for route in route_words:

        if route in lower_parts:

            i = lower_parts.index(
                route
            )

            if i + 1 < len(parts):

                candidate = (
                    parts[i + 1]
                )

                if (
                    candidate.lower()
                    not in bad
                ):

                    return pretty_slug(
                        candidate
                    )

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
# MODEL CLEANING
# =========================================================

def clean_model_name(
    name,
    make,
):

    name = clean(name)

    # Remove CTA
    for word in [
        "Learn More",
        "Explore",
        "Discover",
        "View Details",
        "Overview",
    ]:

        name = re.sub(
            re.escape(word),
            "",
            name,
            flags=re.I
        )

    # Remove "The Kia"
    name = re.sub(
        r"^the\s+",
        "",
        name,
        flags=re.I
    )

    name = re.sub(
        r"^"
        + re.escape(make)
        + r"\s+",
        "",
        name,
        flags=re.I
    )

    # Remove price text
    name = re.sub(
        r"\bfrom\b.*$",
        "",
        name,
        flags=re.I
    )

    name = clean(name)

    return name


def plausible_model(
    name,
    make,
):

    name = clean_model_name(
        name,
        make
    )

    if not name:
        return False

    if name.lower() in NOISE:
        return False

    if len(name) > 45:
        return False

    if len(name) < 2:
        return False

    if name.lower().startswith(
        (
            "http",
            "www.",
        )
    ):
        return False

    if re.fullmatch(
        r"[\d\s.,]+",
        name
    ):
        return False

    bad_phrases = [
        "vat included",
        "request",
        "contact",
        "service",
        "accessories",
        "shopping tools",
        "customer",
        "finance",
        "warranty",
        "cookie",
        "privacy",
        "terms",
        "country",
        "language",
    ]

    lower = name.lower()

    if any(
        phrase in lower
        for phrase in bad_phrases
    ):
        return False

    return True


# =========================================================
# DISCOVER MODELS
# =========================================================

def discover_models(
    rendered,
    make,
):

    base_url = rendered["url"]
    html = rendered["html"]
    links = rendered["links"]

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    rows = []


    # -----------------------------------------------------
    # METHOD 1:
    # Browser-rendered links
    # -----------------------------------------------------

    for item in links:

        href = clean(
            item.get(
                "href",
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

        text = clean(
            item.get(
                "text",
                ""
            )
        )

        aria = clean(
            item.get(
                "aria",
                ""
            )
        )

        title = clean(
            item.get(
                "title",
                ""
            )
        )

        path = (
            urlparse(href)
            .path
            .lower()
        )

        url_signal = any(
            token in path
            for token in [
                "/vehicle/",
                "/vehicles/",
                "/model/",
                "/models/",
                "/car/",
                "/cars/",
            ]
        )

        text_signal = (
            plausible_model(
                text,
                make
            )
            and
            any(
                keyword
                in (
                    text
                    + " "
                    + aria
                    + " "
                    + title
                ).lower()
                for keyword
                in SECTION_WORDS
            )
        )

        if (
            text.lower() in NOISE
            or
            not text
        ):

            candidate = (
                model_from_url(
                    href
                )
            )

            source = (
                "Rendered URL"
            )

        else:

            candidate = (
                clean_model_name(
                    text,
                    make
                )
            )

            source = (
                "Rendered Link"
            )

        # URL itself looks like model route
        if (
            url_signal
            and
            not plausible_model(
                candidate,
                make
            )
        ):

            candidate = (
                model_from_url(
                    href
                )
            )

            source = (
                "Rendered URL"
            )

        if (
            url_signal
            and
            plausible_model(
                candidate,
                make
            )
        ):

            rows.append(
                {
                    "Make": make,
                    "Model": candidate,
                    "Model URL": href,
                    "Detected From": source,
                }
            )


    # -----------------------------------------------------
    # METHOD 2:
    # Rendered headings
    # -----------------------------------------------------

    for heading in soup.find_all(
        re.compile(
            "^h[1-6]$"
        )
    ):

        text = clean(
            heading.get_text(
                " ",
                strip=True
            )
        )

        if not text:
            continue

        # The Kia K4
        # Kia K8
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

            candidate = (
                clean_model_name(
                    match.group(1),
                    make
                )
            )

            if plausible_model(
                candidate,
                make
            ):

                parent = heading.parent

                nearby = None

                if parent:
                    nearby = (
                        parent.find(
                            "a",
                            href=True
                        )
                    )

                model_url = (
                    urljoin(
                        base_url,
                        nearby["href"]
                    )
                    if nearby
                    else base_url
                )

                rows.append(
                    {
                        "Make": make,
                        "Model": candidate,
                        "Model URL": model_url,
                        "Detected From": "Heading",
                    }
                )


    # -----------------------------------------------------
    # METHOD 3:
    # Cards - short text around Learn More
    # -----------------------------------------------------

    for link in soup.find_all(
        "a",
        href=True
    ):

        link_text = clean(
            link.get_text(
                " ",
                strip=True
            )
        ).lower()

        if link_text not in {
            "learn more",
            "discover",
            "explore",
            "view details",
            "details",
        }:
            continue

        parent = link

        for _ in range(4):

            parent = (
                parent.parent
                if parent
                else None
            )

            if not parent:
                break

            text = clean(
                parent.get_text(
                    " ",
                    strip=True
                )
            )

            # Look for short first line / heading
            heading = parent.find(
                [
                    "h2",
                    "h3",
                    "h4",
                    "h5",
                    "strong",
                ]
            )

            if heading:

                candidate = (
                    clean_model_name(
                        heading.get_text(
                            " ",
                            strip=True
                        ),
                        make
                    )
                )

                if plausible_model(
                    candidate,
                    make
                ):

                    rows.append(
                        {
                            "Make": make,
                            "Model": candidate,
                            "Model URL": urljoin(
                                base_url,
                                link["href"]
                            ),
                            "Detected From": "Rendered Card",
                        }
                    )

                    break


    # -----------------------------------------------------
    # METHOD 4:
    # JSON-LD
    # -----------------------------------------------------

    for script in soup.find_all(
        "script",
        type="application/ld+json"
    ):

        try:
            data = json.loads(
                script.string or ""
            )
        except Exception:
            continue

        stack = (
            data
            if isinstance(data, list)
            else [data]
        )

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
                    x in item_type
                    for x in [
                        "vehicle",
                        "car",
                        "product",
                    ]
                ):

                    candidate = (
                        clean_model_name(
                            item.get(
                                "name",
                                ""
                            ),
                            make
                        )
                    )

                    if plausible_model(
                        candidate,
                        make
                    ):

                        model_url = (
                            urljoin(
                                base_url,
                                clean(
                                    item.get(
                                        "url",
                                        ""
                                    )
                                )
                            )
                            or base_url
                        )

                        rows.append(
                            {
                                "Make": make,
                                "Model": candidate,
                                "Model URL": model_url,
                                "Detected From": "JSON-LD",
                            }
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


    # -----------------------------------------------------
    # CLEAN RESULTS
    # -----------------------------------------------------

    df = pd.DataFrame(
        rows
    )

    if df.empty:

        return pd.DataFrame(
            columns=[
                "Make",
                "Model",
                "Model URL",
                "Detected From",
            ]
        )

    df["Model"] = (
        df["Model"]
        .astype(str)
        .map(
            lambda x:
            clean_model_name(
                x,
                make
            )
        )
    )

    df = df[
        df["Model"].map(
            lambda x:
            plausible_model(
                x,
                make
            )
        )
    ]

    # Prefer a real unique URL
    df = (
        df.sort_values(
            [
                "Model",
                "Detected From",
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
# SPEC HELPERS
# =========================================================

def canonical_field(
    label
):

    label = clean(
        label
    ).lower()

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


def add_pair(
    pairs,
    label,
    value,
):

    label = clean(label)
    value = clean(value)

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


    # Tables
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


    # Definition lists
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


    # Common sibling label/value layouts
    for element in soup.find_all(
        [
            "div",
            "li",
            "p",
            "span",
        ]
    ):

        children = element.find_all(
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
                len(label) <= 80
                and
                len(value) <= 300
            ):

                add_pair(
                    pairs,
                    label,
                    value
                )


    # Label: value
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
            4 <= len(text) <= 250
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

    return pairs


# =========================================================
# REGEX FALLBACK SPECS
# =========================================================

FALLBACKS = {

    "Displacement": [
        r"(?i)\b([0-9.]+\s*(?:cc|cm3|cm³))\b",
        r"(?i)\b([0-9.]+\s*(?:l|litre|liter))\s+(?:engine)\b",
    ],

    "Max Power": [
        (
            r"(?i)"
            r"(?:maximum|max\.?|engine|motor)?\s*"
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

    "Acceleration": [
        (
            r"(?i)"
            r"(?:0\s*(?:-|–|to)\s*100\s*km/?h)"
            r"\s*[:\-]?\s*"
            r"([0-9.]+\s*(?:s|sec|seconds))"
        ),
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

        rendered = render_page(
            model_url,
            wait_ms=3000
        )

        soup = BeautifulSoup(
            rendered["html"],
            "html.parser"
        )

        result = {
            "Make": make,
            "Model": model,
            "Source URL": rendered["url"],
        }

        raw_specs = []


        # -------------------------------------------------
        # Structured specs
        # -------------------------------------------------

        for (
            label,
            value
        ) in extract_pairs(
            soup
        ):

            field = canonical_field(
                label
            )

            if field:

                if not result.get(
                    field
                ):

                    result[
                        field
                    ] = value

                raw_specs.append(
                    f"{label}: {value}"
                )


        # -------------------------------------------------
        # Visible browser text fallback
        # -------------------------------------------------

        text = clean(
            rendered["text"]
        )

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


        # -------------------------------------------------
        # Transmission fallback
        # -------------------------------------------------

        if not result.get(
            "Transmission"
        ):

            transmission_patterns = [
                r"(?i)\b([0-9]+[- ]speed automatic)\b",
                r"(?i)\b([0-9]+[- ]speed manual)\b",
                r"(?i)\b(CVT)\b",
                r"(?i)\b(e-CVT)\b",
                r"(?i)\b(DCT)\b",
                r"(?i)\b(automatic transmission)\b",
                r"(?i)\b(manual transmission)\b",
            ]

            for pattern in transmission_patterns:

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


        # -------------------------------------------------
        # Fuel / powertrain fallback
        # -------------------------------------------------

        if not result.get(
            "Fuel / Powertrain"
        ):

            powertrain_words = [
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

            for word in powertrain_words:

                if re.search(
                    r"\b"
                    + re.escape(word)
                    + r"\b",
                    text,
                    re.I
                ):

                    found.append(
                        word
                    )

            if found:

                result[
                    "Fuel / Powertrain"
                ] = ", ".join(
                    dict.fromkeys(
                        found
                    )
                )


        # -------------------------------------------------
        # Keep raw matched specs for researcher review
        # -------------------------------------------------

        result[
            "Raw Matched Specs"
        ] = " ; ".join(
            raw_specs[:120]
        )

        return result


    except Exception as error:

        return {
            "Make": make,
            "Model": model,
            "Source URL": model_url,
            "Error": str(error),
        }


# =========================================================
# EXCEL
# =========================================================

def create_excel(
    models_df,
    specs_df,
    source_url,
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

        if (
            specs_df is not None
            and
            not specs_df.empty
        ):

            specs_df.to_excel(
                writer,
                index=False,
                sheet_name="Specs",
            )

        methodology = pd.DataFrame(
            [
                {
                    "Source URL":
                    source_url,

                    "Method":
                    (
                        "Browser-rendered extraction "
                        "using Playwright."
                    ),

                    "Rule":
                    (
                        "Display only fields detected "
                        "on the source page. "
                        "Missing fields remain blank. "
                        "No values are invented."
                    ),
                }
            ]
        )

        methodology.to_excel(
            writer,
            index=False,
            sheet_name="Methodology",
        )

    return output.getvalue()


# =========================================================
# SIDEBAR
# =========================================================

manual_make = st.sidebar.text_input(
    "Make (optional)",
    placeholder="Auto-detect if blank",
)

max_pages = st.sidebar.slider(
    "Max model pages for spec scan",
    min_value=1,
    max_value=50,
    value=10,
)


# =========================================================
# URL
# =========================================================

url = st.text_input(
    "Website URL",
    placeholder=(
        "https://www.kia.com/sa/en/main.html"
    ),
)


# =========================================================
# CHECK WEBSITE
# =========================================================

if st.button(
    "🌐 Open website & find models",
    type="primary",
    use_container_width=True,
):

    if not clean(url):

        st.error(
            "Please enter a website URL."
        )

        st.stop()

    try:

        with st.spinner(
            "Opening website in browser and waiting for JavaScript..."
        ):

            rendered = render_page(
                normalize_url(
                    url
                )
            )

            soup = BeautifulSoup(
                rendered["html"],
                "html.parser"
            )

            make = infer_make(
                soup,
                rendered["url"],
                rendered["text"],
                manual_make,
            )

            models_df = discover_models(
                rendered,
                make,
            )

            st.session_state[
                "models"
            ] = models_df

            st.session_state[
                "make"
            ] = make

            st.session_state[
                "source"
            ] = rendered["url"]

            st.session_state[
                "specdf"
            ] = pd.DataFrame()

            st.session_state[
                "page_text_length"
            ] = len(
                rendered["text"]
            )

    except Exception as error:

        st.error(
            "Browser error:"
        )

        st.code(
            str(error)
        )


# =========================================================
# RESULTS
# =========================================================

if "models" in st.session_state:

    models_df = (
        st.session_state[
            "models"
        ]
    )

    c1, c2, c3 = st.columns(
        3
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

    c3.metric(
        "Rendered text",
        f"{st.session_state.get('page_text_length', 0):,} chars"
    )


    st.subheader(
        "1. Models found"
    )


    if models_df.empty:

        st.warning(
            "The browser loaded the website, "
            "but no reliable model candidates were found."
        )

        st.info(
            "This may mean the model list is inside "
            "a special menu, iframe, API, or requires "
            "another site-specific discovery method."
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
                ),
            },

            disabled=[
                "Make",
                "Model",
                "Model URL",
                "Detected From",
            ],
        )


        # =================================================
        # SPEC SCAN
        # =================================================

        if st.button(
            "⚙️ Inspect selected models",
            use_container_width=True,
        ):

            selected = (
                edited[
                    edited[
                        "Inspect"
                    ] == True
                ]
                .head(
                    max_pages
                )
            )

            if selected.empty:

                st.warning(
                    "Select at least one model first."
                )

            else:

                results = []

                progress = (
                    st.progress(
                        0
                    )
                )

                status = (
                    st.empty()
                )

                total = len(
                    selected
                )

                for (
                    number,
                    (_, row)
                ) in enumerate(
                    selected.iterrows(),
                    start=1
                ):

                    status.write(
                        f"Reading {row['Make']} {row['Model']} "
                        f"({number}/{total})..."
                    )

                    result = inspect_model(
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
                ] = pd.DataFrame(
                    results
                )


    # =====================================================
    # SPECS
    # =====================================================

    specs_df = st.session_state.get(
        "specdf",
        pd.DataFrame()
    )

    if not specs_df.empty:

        st.subheader(
            "2. Specs found"
        )

        # Only display columns that actually contain data
        useful_columns = []

        for column in specs_df.columns:

            if column in [
                "Make",
                "Model",
                "Source URL",
                "Error",
            ]:

                useful_columns.append(
                    column
                )

                continue

            values = (
                specs_df[column]
                .replace(
                    "",
                    pd.NA
                )
            )

            if values.notna().any():

                useful_columns.append(
                    column
                )

        st.dataframe(
            specs_df[
                useful_columns
            ],
            hide_index=True,
            use_container_width=True,
        )


    # =====================================================
    # DOWNLOAD
    # =====================================================

    excel = create_excel(
        models_df,
        specs_df,
        st.session_state.get(
            "source",
            ""
        ),
    )

    st.download_button(
        "⬇️ Download Excel",
        data=excel,
        file_name=(
            "automotive_web_research_v4.xlsx"
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
    "V4 uses a real browser engine so JavaScript-loaded "
    "vehicle lists can be read. Specs are flexible: "
    "fields found on the source are shown; missing fields "
    "are left blank."
)
