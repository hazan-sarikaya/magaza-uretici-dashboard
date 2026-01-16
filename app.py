import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

st.set_page_config(page_title="Mağaza & Üretici Dashboard", layout="wide")
st.title("Mağaza & Üretici Dashboard")

if st.button("🔄 Veriyi Yenile"):
    st.cache_data.clear()

# CSV oku
@st.cache_data
def load_data():
    df = pd.read_csv("magazalar.csv", encoding="cp1254")
    df.columns = [c.strip() for c in df.columns]
    return df

df = load_data()

# Tip temizle (Türkçe karakter farklarına dayanıklı)
tip = df["TIPI"].astype(str).str.strip().str.lower()
tip = tip.replace({"ü":"u","ı":"i","ş":"s","ğ":"g","ö":"o","ç":"c"}, regex=True)

# Enlem/Boylam sayıya çevir
df["ENLEM"] = pd.to_numeric(df["ENLEM"], errors="coerce")
df["BOYLAM"] = pd.to_numeric(df["BOYLAM"], errors="coerce")
df = df.dropna(subset=["ENLEM", "BOYLAM"])

magazalar = df[tip == "magaza"].copy()
ureticiler = df[tip == "uretici"].copy()

# Mesafe fonksiyonu (km)
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

# Özet
st.subheader("Özet")
c1, c2, c3 = st.columns(3)
c1.metric("Toplam kayıt", len(df))
c2.metric("Mağaza", len(magazalar))
c3.metric("Üretici", len(ureticiler))

st.divider()

# =========================
# ✅ MAĞAZA (TEK INPUT) + seçili değilken TÜM TÜRKİYE
# =========================
st.subheader("Mağaza (Google gibi arama)")

if len(magazalar) == 0:
    st.error("Mağaza bulunamadı. TIPI alanında 'Magaza' yazdığından emin ol.")
    st.stop()

arama = st.text_input(
    "Mağaza adı veya kodunu yaz",
    placeholder="Yazmaya başla... (örn: kurtuluş, A0002)"
).strip()

m_df = magazalar.copy()
m_df["CARI_ISIM"] = m_df["CARI_ISIM"].astype(str)
m_df["CARI_KOD"] = m_df["CARI_KOD"].astype(str)

secili_magaza = None

if arama:
    arama_lower = arama.lower()
    sonuc = m_df[
        m_df["CARI_ISIM"].str.lower().str.contains(arama_lower, na=False) |
        m_df["CARI_KOD"].str.lower().str.contains(arama_lower, na=False)
    ].copy()

    if len(sonuc) == 0:
        st.warning("Eşleşen mağaza bulunamadı. Aşağıda tüm Türkiye görünmeye devam eder.")
    else:
        # Tek input hissi: label'ı gizliyoruz, dropdown sadece sonuçlar.
        secim_label = st.selectbox(
            "Sonuçlar",
            options=(sonuc["CARI_KOD"] + " | " + sonuc["CARI_ISIM"]).tolist(),
            label_visibility="collapsed"
        )
        secili_kod = secim_label.split(" | ")[0].strip()
        secili_magaza = magazalar[magazalar["CARI_KOD"].astype(str) == secili_kod].iloc[0]

# Seçili mağaza varsa bilgisi göster
if secili_magaza is not None:
    st.write("**Seçili mağaza bilgisi**")
    st.dataframe(pd.DataFrame([{
        "CARI_KOD": secili_magaza["CARI_KOD"],
        "CARI_ISIM": secili_magaza["CARI_ISIM"],
        "IL": secili_magaza.get("IL", ""),
        "ILCE": secili_magaza.get("ILCE", ""),
        "ADRES": secili_magaza.get("ADRES", ""),
        "ENLEM": secili_magaza["ENLEM"],
        "BOYLAM": secili_magaza["BOYLAM"],
    }]), use_container_width=True)
else:
    st.info("Mağaza seçili değil → aşağıda tüm Türkiye (tüm mağazalar + üreticiler) görünür.")

st.divider()

# =========================
# ✅ YAKIN ÜRETİCİLER (Seçili mağaza varsa)
# =========================
st.subheader("Yakındaki Üreticiler")

top_n = st.selectbox("En yakın kaç üretici gösterilsin?", options=[5, 10, 20, 50], index=1)
yaricap = st.slider("Yarıçap (km)", 1, 200, 30, 5)

yakin = pd.DataFrame()

if secili_magaza is None:
    st.warning("Yakın üretici hesabı için önce mağaza seçmelisin.")
else:
    m_lat = float(secili_magaza["ENLEM"])
    m_lon = float(secili_magaza["BOYLAM"])

    if len(ureticiler) > 0:
        u = ureticiler.copy()
        u["MESAFE_KM"] = haversine_km(m_lat, m_lon, u["ENLEM"].values, u["BOYLAM"].values)

        yakin = (
            u[u["MESAFE_KM"] <= yaricap]
            .sort_values("MESAFE_KM")
            .head(top_n)
        )

        st.write(f"Seçilen mağazaya **{yaricap} km** içinde **{len(yakin)}** üretici var (en yakın {top_n}).")

        st.dataframe(
            yakin[["CARI_KOD","CARI_ISIM","IL","ILCE","MESAFE_KM","ENLEM","BOYLAM"]] if len(yakin) else yakin,
            use_container_width=True
        )
    else:
        st.warning("Üretici bulunamadı (TIPI alanını kontrol et).")

st.divider()

# =========================
# ✅ HARİTA
# - Mağaza seçili değilse: Türkiye genel görünüm + cluster (mağaza+üretici)
# - Seçiliyse: seçili mağaza merkez + yakın üreticiler + yarıçap çemberi
# =========================
st.subheader("Harita")
st.write("DEBUG: Harita bölümüne geldim ✅")

if secili_magaza is None:
    tr_center = [39.0, 35.0]
    m = folium.Map(location=tr_center, zoom_start=6, tiles="OpenStreetMap")

    cluster_magaza = MarkerCluster(name="Mağazalar").add_to(m)
    cluster_uretici = MarkerCluster(name="Üreticiler").add_to(m)

    for _, row in magazalar.sample(min(2000, len(magazalar)), random_state=1).iterrows():
        folium.CircleMarker(
            location=[float(row["ENLEM"]), float(row["BOYLAM"])],
            radius=3,
            color="red",
            fill=True,
            fill_opacity=0.7,
            popup=f"Mağaza: {row.get('CARI_ISIM','')}"
        ).add_to(cluster_magaza)

    for _, row in ureticiler.sample(min(2000, len(ureticiler)), random_state=1).iterrows():
        folium.CircleMarker(
            location=[float(row["ENLEM"]), float(row["BOYLAM"])],
            radius=3,
            color="blue",
            fill=True,
            fill_opacity=0.7,
            popup=f"Üretici: {row.get('CARI_ISIM','')}"
        ).add_to(cluster_uretici)

    folium.LayerControl().add_to(m)
    st_folium(m, width=1200, height=650, returned_objects=[])

else:
    m_lat = float(secili_magaza["ENLEM"])
    m_lon = float(secili_magaza["BOYLAM"])

    m = folium.Map(location=[m_lat, m_lon], zoom_start=11, tiles="OpenStreetMap")

    # Mağaza (kırmızı)
    folium.Marker(
        [m_lat, m_lon],
        popup=f"Mağaza: {secili_magaza['CARI_ISIM']}",
        icon=folium.Icon(color="red"),
    ).add_to(m)

    # Yarıçap çemberi
    folium.Circle(
        location=[m_lat, m_lon],
        radius=yaricap * 1000,
        color="red",
        fill=False,
    ).add_to(m)

    # Yakındaki üreticiler (mavi)
    for _, row in yakin.iterrows():
        folium.CircleMarker(
            location=[float(row["ENLEM"]), float(row["BOYLAM"])],
            radius=6,
            popup=f"Üretici: {row['CARI_ISIM']} ({row['MESAFE_KM']:.1f} km)",
            color="blue",
            fill=True,
            fill_opacity=0.85,
        ).add_to(m)

    st_folium(m, width=1200, height=650, returned_objects=[])
