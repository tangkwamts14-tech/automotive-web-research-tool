import io
import re
import shutil
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(page_title='Automotive Website Research', page_icon='🚗', layout='wide')
st.title('🚗 Automotive Website Research')
st.caption('Website URL → Models → Variants → Specifications → Excel')
st.caption('App version: 2026-09-30 FINAL-TESTED')

HEADERS={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'}
BRANDS=['Acura','Alfa Romeo','Aston Martin','Audi','BAIC','Bentley','Bestune','BMW','BYD','Cadillac','Changan','Chery','Chevrolet','Chrysler','Denza','Dodge','Exeed','FAW','Ferrari','Fiat','Ford','Foton','GAC','Geely','Genesis','GMC','Great Wall','GWM','Haval','Honda','Hongqi','Hyundai','iCAUR','Ineos','Infiniti','Isuzu','JAC','Jaecoo','Jaguar','Jeep','Jetour','Kia','Lamborghini','Land Rover','Lexus','Lincoln','Lotus','Maserati','Mazda','McLaren','Mercedes-Benz','MG','MINI','Mitsubishi','Nissan','Omoda','Ora','Peugeot','Porsche','RAM','Renault','Rolls-Royce','Skoda','Soueast','Ssangyong','Subaru','Suzuki','Tata','Tesla','Toyota','Volkswagen','Volvo','Yangwang']
BAD={'','home','brand','gallery','features','specification','specifications','overview','vehicle','vehicles','model','models','cars','car','offers','owners','services','contact','learn more','discover'}


def clean(v): return re.sub(r'\s+',' ',str(v or '')).strip()
def normalize_url(u):
    u=clean(u)
    return u if u.startswith(('http://','https://')) else 'https://'+u
def host(u): return urlparse(u).netloc.lower().replace('www.','')
def same_site(a,b): return host(a)==host(b)


def browser_page(url):
    from playwright.sync_api import sync_playwright
    path=shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    with sync_playwright() as p:
        opts={'headless':True,'args':['--no-sandbox','--disable-dev-shm-usage','--disable-blink-features=AutomationControlled']}
        if path: opts['executable_path']=path
        browser=p.chromium.launch(**opts)
        page=browser.new_page(user_agent=HEADERS['User-Agent'],viewport={'width':1440,'height':1200})
        try:
            page.goto(url,wait_until='domcontentloaded',timeout=60000)
            try: page.wait_for_load_state('networkidle',timeout=12000)
            except Exception: pass
            page.wait_for_timeout(1200)
            return page.url,BeautifulSoup(page.content(),'html.parser')
        finally: browser.close()


def get_page(url):
    url=normalize_url(url)
    try:
        r=requests.get(url,headers=HEADERS,timeout=30,allow_redirects=True)
        if r.status_code in (401,403,429): raise RuntimeError(f'HTTP {r.status_code}')
        r.raise_for_status()
        soup=BeautifulSoup(r.text,'html.parser')
        if len(clean(soup.get_text(' ',strip=True)))<200: raise RuntimeError('browser rendering required')
        return r.url,soup
    except Exception:
        return browser_page(url)


def detect_make(soup,url):
    h=re.sub(r'[^a-z0-9]','',host(url))
    title=clean(soup.title.get_text(' ',strip=True) if soup.title else '')
    for b in sorted(BRANDS,key=len,reverse=True):
        k=re.sub(r'[^a-z0-9]','',b.lower())
        if k in h or re.search(r'(?<![A-Za-z0-9])'+re.escape(b)+r'(?![A-Za-z0-9])',title,re.I): return b
    return host(url).split('.')[0].title()


def model_from_url(url):
    parts=[x for x in urlparse(url).path.split('/') if x]
    ignore={'en','ar','showroom','model','models','vehicle','vehicles','cars','car','gallery.html','features.html','overview.html','specification.html','specifications.html','full-specs','corolla-specs'}
    usable=[x for x in parts if x.lower() not in ignore]
    if not usable:return ''
    v=re.sub(r'\.(html?|php)$','',usable[-1],flags=re.I).replace('-',' ').replace('_',' ')
    return clean(' '.join(w.upper() if len(w)<=3 or re.search(r'\d',w) else w.title() for w in v.split()))


def valid_model(m,make):
    m=clean(m); low=m.lower()
    return bool(m and low not in BAD and low!=make.lower() and len(m)<=45 and not re.fullmatch(r'[\d\s.,]+',m))


def find_models(soup,base_url,make):
    out=[]
    for a in soup.find_all('a',href=True):
        href=urljoin(base_url,a.get('href'))
        if not same_site(base_url,href):continue
        path=urlparse(href).path.lower()
        if not any(x in path for x in ['/showroom/','/models/','/model/','/vehicles/','/vehicle/']):continue
        m=model_from_url(href); anchor=clean(a.get_text(' ',strip=True))
        if not valid_model(m,make): m=anchor if valid_model(anchor,make) else ''
        if m: out.append({'Make':make,'Model':m,'Model URL':href})
    if not out:return pd.DataFrame(columns=['Make','Model','Model URL'])
    df=pd.DataFrame(out)
    def score(u):
        u=u.lower(); return 20*('/showroom/' in u)+15*('/vehicles/' in u)+15*('/models/' in u)+10*('gallery' in u)+8*('overview' in u)+5*('specification' in u)
    df['_s']=df['Model URL'].map(score)
