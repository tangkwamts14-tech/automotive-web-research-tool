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
st.caption("App version: 2026-09-30 FIXED-FULL-UI")


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
