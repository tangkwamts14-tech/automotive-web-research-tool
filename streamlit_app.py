import io, re
from urllib.parse import urljoin, urlparse
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(page_title="Automotive Web Research Tool", page_icon="🚗", layout="wide")
HEADERS={"User-Agent":"Mozilla/5.0 Chrome/124 Safari/537.36"}
NOISE={"home","about","contact","offers","services","owners","news","events","test drive","request a quote","quote","brochure","discover","explore","learn more","view more","view details","details","dealer","dealers","search","menu","privacy","terms","vehicles","models","new cars"}

PATTERNS={
"Engine":r"(?:engine|displacement|capacity)\s*[:\-]?\s*([^\n|]{2,80})",
"Fuel / Powertrain":r"(?:fuel type|fuel|powertrain|propulsion)\s*[:\-]?\s*([^\n|]{2,80})",
"Max Power":r"(?:maximum power|max\.?\s*power|max power|power output)\s*[:\-]?\s*([^\n|]{2,80})",
"Max Torque":r"(?:maximum torque|max\.?\s*torque|max torque|torque output)\s*[:\-]?\s*([^\n|]{2,80})",
"Transmission":r"(?:transmission|gearbox)\s*[:\-]?\s*([^\n|]{2,80})",
"Battery":r"(?:battery capacity|battery pack size|battery)\s*[:\-]?\s*([^\n|]{2,80})",
"Electric Range":r"(?:electric range|driving range|range)\s*[:\-]?\s*([^\n|]{2,80})",
"Body Type":r"(?:body type|body style)\s*[:\-]?\s*([^\n|]{2,80})"}

def norm(u):
    u=u.strip()
    return u if u.startswith(("http://","https://")) else "https://"+u

@st.cache_data(ttl=900,show_spinner=False)
def fetch(u):
    r=requests.get(u,headers=HEADERS,timeout=25,allow_redirects=True)
    r.raise_for_status()
    return r.url,r.text

def clean(x): return re.sub(r"\s+"," ",x or "").strip()

def infer_make(soup,url,manual):
    if manual.strip(): return manual.strip()
    og=soup.find("meta",{"property":"og:site_name"})
    if og and og.get("content"): return clean(og["content"])
    if soup.title and soup.title.string:
        return clean(soup.title.string.split("|")[0].split("-")[0])
    return urlparse(url).netloc.replace("www.","").split(".")[0].replace("-qatar","").title()

def candidates(soup,base,make):
    out=[]
    for a in soup.find_all("a",href=True):
        t=clean(a.get_text(" ",strip=True)); h=urljoin(base,a["href"])
        if not t or len(t)>80 or t.lower() in NOISE: continue
        if urlparse(h).scheme not in ("http","https"): continue
        score=0; hl=h.lower()
        if any(k in hl for k in ["/model","/vehicle","/car","/range"]): score+=2
        if make.lower() in hl: score+=1
        if 1<=len(t.split())<=8: score+=1
        if score>=2: out.append([make,t,h,score])
    df=pd.DataFrame(out,columns=["Make","Candidate Model / Link Text","Model URL","Score"])
    if not df.empty: df=df.drop_duplicates().sort_values(["Score","Candidate Model / Link Text"],ascending=[False,True])
    return df

@st.cache_data(ttl=900,show_spinner=False)
def specs(url):
    try:
        final,html=fetch(url); soup=BeautifulSoup(html,"html.parser")
        txt=soup.get_text("\n",strip=True); row={"Source URL":final}
        for k,p in PATTERNS.items():
            m=re.search(p,txt,re.I); row[k]=clean(m.group(1)) if m else ""
        return row
    except Exception as e: return {"Source URL":url,"Error":str(e)}

def excel_bytes(models,specdf,source):
    b=io.BytesIO()
    with pd.ExcelWriter(b,engine="openpyxl") as w:
        models.to_excel(w,index=False,sheet_name="Candidate Models")
        if specdf is not None and not specdf.empty: specdf.to_excel(w,index=False,sheet_name="Specs")
        pd.DataFrame([{"Source Page":source,"Note":"Research-assistance output; verify against source before database update."}]).to_excel(w,index=False,sheet_name="Methodology")
    return b.getvalue()

st.title("🚗 Automotive Web Research Tool")
st.caption("Paste OEM / official distributor URL → candidate models → selected specs → Excel")
manual=st.sidebar.text_input("Make (optional)",placeholder="Genesis")
limit=st.sidebar.slider("Max pages for spec scan",1,30,10)
st.sidebar.info("Dynamic / anti-bot sites may need a site-specific adapter.")
url=st.text_input("Website URL",placeholder="https://www.genesis.com/qa/en/main.html")

if st.button("🔎 Check website",type="primary",use_container_width=True):
    if not url.strip(): st.error("Enter a URL."); st.stop()
    try:
        final,html=fetch(norm(url)); soup=BeautifulSoup(html,"html.parser")
        make=infer_make(soup,final,manual); df=candidates(soup,final,make)
        st.session_state["models"]=df; st.session_state["source"]=final
        a,b,c=st.columns(3); a.metric("Make",make); b.metric("Candidate rows",len(df)); c.metric("Host",urlparse(final).netloc)
    except Exception as e:
        st.error(f"Could not read website: {e}"); st.stop()

if "models" in st.session_state:
    df=st.session_state["models"]
    st.subheader("1. Candidate model links")
    if df.empty:
        st.warning("No candidates detected. The page may use JavaScript/anti-bot or need a site-specific adapter.")
        st.session_state["specdf"]=pd.DataFrame()
    else:
        edit=st.data_editor(df.assign(Inspect=False),hide_index=True,use_container_width=True,
            column_config={"Inspect":st.column_config.CheckboxColumn("Inspect specs")},
            disabled=["Make","Candidate Model / Link Text","Model URL","Score"])
        if st.button("⚙️ Inspect selected pages"):
            chosen=edit[edit["Inspect"]==True].head(limit)
            if chosen.empty: st.warning("Select model rows first.")
            else:
                rows=[]
                for _,r in chosen.iterrows():
                    x={"Make":r["Make"],"Candidate Model":r["Candidate Model / Link Text"]}; x.update(specs(r["Model URL"])); rows.append(x)
                st.session_state["specdf"]=pd.DataFrame(rows)
    specdf=st.session_state.get("specdf",pd.DataFrame())
    if not specdf.empty:
        st.subheader("2. Extracted spec candidates"); st.dataframe(specdf,use_container_width=True,hide_index=True)
    st.download_button("⬇️ Download Excel",excel_bytes(df,specdf,st.session_state["source"]),
        "automotive_web_research.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
    st.caption("Always verify extracted model/spec candidates against the source URL.")
