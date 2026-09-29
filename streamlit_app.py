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
st.caption("App version: 2026-09-29 FULL-UI")


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
