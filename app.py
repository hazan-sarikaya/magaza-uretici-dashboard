import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

st.set_page_config(page_title="Mağaza & Üretici & Büfe Dashboard", layout="wide")
st.title("Mağaza & Üretici & Büfe Dashboard")

if st.button("🔄 Veriyi Yenile"):
    st.cache_data.clear()


# =========================
# VERİ OKUMA
# =========================
@st.cache_data
def load_data():
    df = pd.read_csv("magazalar.csv", encoding="cp1254")
    df.columns = [str(c).strip() for c in df.columns]
    return df


@st.cache_data
def load_bufe():
    b = pd.read_excel("BUFE.xlsx")
    b.columns = [str(c).strip() for c in b.columns]

    # Beklenen kolon isimlerini standartlaştır
    rename_map = {}
    for col in b.columns:
        c = str(col).strip().lower()

        if c == "büfe adı" or c == "bufe adı" or c == "büfe adi" or c == "bufe adi":
            rename_map[col] = "BUFE_ADI"
        elif c == "ilçe" or c == "ilce":
            rename_map[col] = "ILCE"
        elif c == "mahalle":
            rename_map[col] = "MAHALLE"
        elif c == "bölge" or c == "bolge":
            rename_map[col] = "BOLGE"
        elif c == "adres":
            rename_map[col] = "ADRES"
        elif c == "x":
            rename_map[col] = "ENLEM"
        elif c == "y":
            rename_map[col] = "BOYLAM"

    b = b.rename(columns=rename_map)

    # Eksik kolonlar varsa oluştur
    for col in ["BUFE_ADI", "ILCE", "MAHALLE", "BOLGE", "ADRES", "ENLEM", "BOYLAM"]:
        if col not in b.columns:
            b[col] = np.nan

    b["ENLEM"] = pd.to_numeric(b["ENLEM"], errors="coerce")
    b["BOYLAM"] = pd.to_numeric(b["BOYLAM"], errors="coerce")
    b = b.dropna(subset=["ENLEM", "BOYLAM"]).copy()

    return b


df = load_data()
bufeler = load_bufe()

# =========================
# TEMİZLİK
# =========================
# TIPI alanını Türkçe karakter dayanıklı temizle
tip = df["TIPI"].astype(str).str.strip().str.lower()
tip = tip.replace(
    {
        "ü": "u",
        "ı": "i",
        "ş": "s",
        "ğ": "g",
        "ö": "o",
        "ç": "c",
    },
    regex=True
)

# Enlem/Boylam sayıya çevir
df["ENLEM"] = pd.to_numeric(df["ENLEM"], errors="coerce")
df["BOYLAM"] = pd.to_numeric(df["BOYLAM"], errors="coerce")
df = df.dropna(subset=["ENLEM", "BOYLAM"]).copy()

magazalar = df[tip == "magaza"].copy()
ureticiler = df[tip == "uretici"].copy()


# =========================
# MESAFE FONKSİYONU
# =========================
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c


# =========================
# ÖZET
# =========================
st.subheader("Özet")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Toplam kayıt", len(df))
c2.metric("Mağaza", len(magazalar))
c3.metric("Üretici", len(ureticiler))
c4.metric("Büfe", len(bufeler))

st.divider()


# =========================
# MAĞAZA SEÇİMİ
# =========================
st.subheader("Mağaza Seçimi")

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
        secim_label = st.selectbox(
            "Sonuçlar",
            options=(sonuc["CARI_KOD"] + " | " + sonuc["CARI_ISIM"]).tolist(),
            label_visibility="collapsed"
        )
        secili_kod = secim_label.split(" | ")[0].strip()
        secili_magaza = magazalar[magazalar["CARI_KOD"].astype(str) == secili_kod].iloc[0]

if secili_magaza is not None:
    st.write("**Seçili mağaza bilgisi**")
    st.dataframe(
        pd.DataFrame([{
            "CARI_KOD": secili_magaza["CARI_KOD"],
            "CARI_ISIM": secili_magaza["CARI_ISIM"],
            "IL": secili_magaza.get("IL", ""),
            "ILCE": secili_magaza.get("ILCE", ""),
            "ADRES": secili_magaza.get("ADRES", ""),
            "ENLEM": secili_magaza["ENLEM"],
            "BOYLAM": secili_magaza["BOYLAM"],
        }]),
        use_container_width=True
    )
else:
    st.info("Mağaza seçili değil ise, tüm Türkiye görünür.")

st.divider()


# =========================
# PARAMETRELER
# =========================
st.subheader("Yakın Kayıt Ayarları")
c1, c2 = st.columns(2)
with c1:
    top_n = st.selectbox("En yakın kaç kayıt gösterilsin?", options=[5, 10, 20, 50], index=1)
with c2:
    yaricap = st.slider("Yarıçap (km)", 1, 200, 30, 5)

st.divider()


# =========================
# YAKIN ÜRETİCİLER
# =========================
st.subheader("Seçili Mağazanın Yakınındaki Üreticiler")

yakin_ureticiler = pd.DataFrame()
yakin_bufeler = pd.DataFrame()

if secili_magaza is None:
    st.warning("Yakın üretici ve büfe bilgisi için önce mağaza seçmelisiniz.")
else:
    m_lat = float(secili_magaza["ENLEM"])
    m_lon = float(secili_magaza["BOYLAM"])

    if len(ureticiler) > 0:
        u = ureticiler.copy()
        u["MESAFE_KM"] = haversine_km(m_lat, m_lon, u["ENLEM"].values, u["BOYLAM"].values)

        yakin_ureticiler = (
            u[u["MESAFE_KM"] <= yaricap]
            .sort_values("MESAFE_KM")
            .head(top_n)
            .copy()
        )

        st.write(
            f"Seçilen mağazaya **{yaricap} km** içinde **{len(yakin_ureticiler)}** en yakın üretici bilgisi aşağıda listelenmiştir:"
        )

        if len(yakin_ureticiler) > 0:
            st.dataframe(
                yakin_ureticiler[["CARI_KOD", "CARI_ISIM", "IL", "ILCE", "MESAFE_KM", "ENLEM", "BOYLAM"]],
                use_container_width=True
            )
        else:
            st.info("Bu yarıçap içinde üretici bulunamadı.")
    else:
        st.warning("Üretici bulunamadı (TIPI alanını kontrol et).")

st.divider()


# =========================
# YAKIN BÜFELER
# =========================
st.subheader("Seçili Mağazanın Yakınındaki Büfeler")

if secili_magaza is None:
    st.warning("Yakın büfe bilgisi için önce mağaza seçmelisiniz.")
else:
    if len(bufeler) > 0:
        b = bufeler.copy()
        b["MESAFE_KM"] = haversine_km(m_lat, m_lon, b["ENLEM"].values, b["BOYLAM"].values)

        yakin_bufeler = (
            b[b["MESAFE_KM"] <= yaricap]
            .sort_values("MESAFE_KM")
            .head(top_n)
            .copy()
        )

        st.write(
            f"Seçilen mağazaya **{yaricap} km** içinde **{len(yakin_bufeler)}** en yakın büfe bilgisi aşağıda listelenmiştir:"
        )

        if len(yakin_bufeler) > 0:
            st.dataframe(
                yakin_bufeler[["BUFE_ADI", "ILCE", "MAHALLE", "BOLGE", "ADRES", "MESAFE_KM", "ENLEM", "BOYLAM"]],
                use_container_width=True
            )
        else:
            st.info("Bu yarıçap içinde büfe bulunamadı.")
    else:
        st.warning("Büfe dosyasında geçerli koordinatlı kayıt bulunamadı.")

st.divider()


# =========================
# HARİTA
# - Mağaza seçili değilse: Türkiye genel görünüm + cluster
# - Seçiliyse: mağaza merkez + yakın üreticiler + yakın büfeler + yarıçap
# =========================
st.subheader("Harita")

if secili_magaza is None:
    tr_center = [39.0, 35.0]
    m = folium.Map(location=tr_center, zoom_start=6, tiles="OpenStreetMap")

    magaza_group = folium.FeatureGroup(name="Mağazalar")
    uretici_group = folium.FeatureGroup(name="Üreticiler")
    bufe_group = folium.FeatureGroup(name="Büfeler")

    cluster_magaza = MarkerCluster().add_to(magaza_group)
    cluster_uretici = MarkerCluster().add_to(uretici_group)
    cluster_bufe = MarkerCluster().add_to(bufe_group)

    for _, row in magazalar.sample(min(2000, len(magazalar)), random_state=1).iterrows():
        folium.CircleMarker(
            location=[float(row["ENLEM"]), float(row["BOYLAM"])],
            radius=3,
            color="red",
            fill=True,
            fill_opacity=0.7,
            popup=f"Mağaza: {row.get('CARI_ISIM', '')}"
        ).add_to(cluster_magaza)

    for _, row in ureticiler.sample(min(2000, len(ureticiler)), random_state=1).iterrows():
        folium.CircleMarker(
            location=[float(row["ENLEM"]), float(row["BOYLAM"])],
            radius=3,
            color="blue",
            fill=True,
            fill_opacity=0.7,
            popup=f"Üretici: {row.get('CARI_ISIM', '')}"
        ).add_to(cluster_uretici)

    for _, row in bufeler.sample(min(2000, len(bufeler)), random_state=1).iterrows():
        folium.CircleMarker(
            location=[float(row["ENLEM"]), float(row["BOYLAM"])],
            radius=3,
            color="green",
            fill=True,
            fill_opacity=0.7,
            popup=f"Büfe: {row.get('BUFE_ADI', '')}"
        ).add_to(cluster_bufe)

    magaza_group.add_to(m)
    uretici_group.add_to(m)
    bufe_group.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    st_folium(m, width=1200, height=650, returned_objects=[])

else:
    m_lat = float(secili_magaza["ENLEM"])
    m_lon = float(secili_magaza["BOYLAM"])

    m = folium.Map(location=[m_lat, m_lon], zoom_start=11, tiles="OpenStreetMap")

    # Seçili mağaza
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

    # Yakın üreticiler
    for _, row in yakin_ureticiler.iterrows():
        folium.CircleMarker(
            location=[float(row["ENLEM"]), float(row["BOYLAM"])],
            radius=6,
            popup=f"Üretici: {row['CARI_ISIM']} ({row['MESAFE_KM']:.1f} km)",
            color="blue",
            fill=True,
            fill_opacity=0.85,
        ).add_to(m)

    # Yakın büfeler
    for _, row in yakin_bufeler.iterrows():
        folium.CircleMarker(
            location=[float(row["ENLEM"]), float(row["BOYLAM"])],
            radius=6,
            popup=f"Büfe: {row['BUFE_ADI']} ({row['MESAFE_KM']:.1f} km)",
            color="green",
            fill=True,
            fill_opacity=0.85,
        ).add_to(m)

    st_folium(m, width=1200, height=650, returned_objects=[])