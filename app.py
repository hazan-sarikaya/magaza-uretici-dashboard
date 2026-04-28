import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from pathlib import Path
from io import BytesIO


# =========================
# EXCEL EXPORT
# =========================
def dataframe_to_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Veri")
    output.seek(0)
    return output.getvalue()


st.set_page_config(page_title="Mağaza & Üretici & Büfe Dashboard", layout="wide")


# =========================
# LOGIN / GUVENLIK
# =========================
def check_login(username, password):
    try:
        secrets_dict = st.secrets.to_dict()
        auth_section = secrets_dict.get("auth", {})
        users = {str(k).strip(): str(v).strip() for k, v in auth_section.items()}

        username = str(username).strip()
        password = str(password).strip()

        return users.get(username) == password
    except Exception as e:
        st.error(f"Secrets okunamadı: {e}")
        return False


def login_screen():
    st.markdown(
        """
        <style>
        .main > div {
            padding-top: 1.5rem;
        }
        .login-wrap {
            max-width: 1000px;
            margin: 30px auto;
            padding: 0;
        }
        .login-left {
            background: linear-gradient(135deg, #fff7f2 0%, #fff 100%);
            padding: 40px 30px;
            height: 100%;
            text-align: center;
        }
        .login-right {
            padding: 40px 30px 30px 30px;
        }
        .login-title {
            font-size: 30px;
            font-weight: 700;
            margin-bottom: 8px;
            color: #222;
        }
        .login-subtitle {
            font-size: 15px;
            color: #666;
            margin-bottom: 24px;
        }
        .mini-note {
            color: #888;
            font-size: 13px;
            margin-top: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown('<div class="login-left">', unsafe_allow_html=True)

        logo_path = Path("favori_logo.png")
        if logo_path.exists():
            st.image(str(logo_path), width=400)
        else:
            st.markdown("## FAVORİ GIDA")
            st.info("Logo için klasöre `favori_logo.png` ekle.")

        st.markdown(
            """
            <div style="margin-top:20px;">
                <div style="font-size:34px; font-weight:800; color:#f25c19; line-height:1.15;">
                    Türkiye'nin her yerindeyiz
                </div>
                <div style="margin-top:14px; color:#666; font-size:16px;">
                    Mağaza, üretici ve büfe verilerine güvenli erişim
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="login-right">', unsafe_allow_html=True)
        st.markdown('<div class="login-title">Giriş Yap</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="login-subtitle">Lütfen kullanıcı adı ve şifrenizi giriniz.</div>',
            unsafe_allow_html=True,
        )

        username = st.text_input("Kullanıcı Adı")
        password = st.text_input("Şifre", type="password")

        c1, c2 = st.columns([1, 2])
        with c1:
            login_btn = st.button("Giriş Yap", use_container_width=True)

        if login_btn:
            if check_login(username, password):
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                st.success("Giriş başarılı. Yükleniyor...")
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre hatalı.")

        st.markdown(
            '<div class="mini-note">Yetkisiz erişimler engellenir.</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def logout_button():
    c1, c2 = st.columns([6, 1])
    with c2:
        if st.button("Çıkış Yap"):
            st.session_state["authenticated"] = False
            st.session_state["username"] = None
            st.rerun()


if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    login_screen()
    st.stop()


# =========================
# UYGULAMA BASLIĞI
# =========================
st.title("Mağaza & Üretici & Büfe Dashboard")
st.caption(f"Giriş yapan kullanıcı: {st.session_state.get('username', '')}")
logout_button()

if st.button("🔄 Veriyi Yenile"):
    st.cache_data.clear()


# =========================
# YARDIMCI FONKSİYONLAR
# =========================
def normalize_text(value):
    s = str(value).strip()
    replacements = {
        "İ": "I",
        "ı": "i",
        "Ş": "S",
        "ş": "s",
        "Ğ": "G",
        "ğ": "g",
        "Ü": "U",
        "ü": "u",
        "Ö": "O",
        "ö": "o",
        "Ç": "C",
        "ç": "c",
        "\u0307": "",
        "\xa0": " ",
    }
    for old, new in replacements.items():
        s = s.replace(old, new)
    return s.strip().lower()


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c


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
    b = pd.read_excel("BUFE.xlsx", engine="openpyxl")
    b.columns = [str(c).strip() for c in b.columns]

    rename_map = {}
    for col in b.columns:
        c = normalize_text(col)

        if c in ["bufe adi", "bufe adı"]:
            rename_map[col] = "BUFE_ADI"
        elif c in ["ilce", "ilce/bolge"]:
            rename_map[col] = "ILCE"
        elif c in ["mahalle"]:
            rename_map[col] = "MAHALLE"
        elif c in ["bolge", "bolgesi", "bolge adi"]:
            rename_map[col] = "BOLGE"
        elif c in ["adres", "acik adres", "açik adres"]:
            rename_map[col] = "ADRES"
        elif c in ["x", "enlem", "latitude", "lat"]:
            rename_map[col] = "ENLEM"
        elif c in ["y", "boylam", "longitude", "lon", "lng"]:
            rename_map[col] = "BOYLAM"

    b = b.rename(columns=rename_map)

    for col in ["BUFE_ADI", "ILCE", "MAHALLE", "BOLGE", "ADRES", "ENLEM", "BOYLAM"]:
        if col not in b.columns:
            b[col] = np.nan

    text_cols = ["BUFE_ADI", "ILCE", "MAHALLE", "BOLGE", "ADRES"]
    for col in text_cols:
        b[col] = b[col].astype(str).str.strip()
        b[col] = b[col].replace(
            {"nan": None, "None": None, "none": None, "NaN": None, "": None}
        )

    b["ENLEM"] = pd.to_numeric(b["ENLEM"], errors="coerce")
    b["BOYLAM"] = pd.to_numeric(b["BOYLAM"], errors="coerce")
    b = b.dropna(subset=["ENLEM", "BOYLAM"]).copy()

    return b


df = load_data()
bufeler = load_bufe()

df.columns = [str(c).strip() for c in df.columns]

required_main_cols = ["TIPI", "ENLEM", "BOYLAM", "CARI_KOD", "CARI_ISIM"]
for col in required_main_cols:
    if col not in df.columns:
        st.error(f"magazalar.csv içinde '{col}' kolonu bulunamadı.")
        st.stop()

tip = df["TIPI"].astype(str).apply(normalize_text)

df["ENLEM"] = pd.to_numeric(df["ENLEM"], errors="coerce")
df["BOYLAM"] = pd.to_numeric(df["BOYLAM"], errors="coerce")
df = df.dropna(subset=["ENLEM", "BOYLAM"]).copy()

magazalar = df[tip == "magaza"].copy()
ureticiler = df[tip == "uretici"].copy()

for optional_col in ["IL", "ILCE", "ADRES"]:
    if optional_col not in magazalar.columns:
        magazalar[optional_col] = ""
    if optional_col not in ureticiler.columns:
        ureticiler[optional_col] = ""


# =========================
# SAYFA SECIMI
# =========================
sayfa = st.sidebar.radio(
    "Sayfa Seç",
    ["Tek Mağaza Analizi", "Tüm Mağazalar Analizi"]
)


# =========================================================
# SAYFA 1: TEK MAGAZA ANALIZI
# =========================================================
if sayfa == "Tek Mağaza Analizi":

    # =========================
    # OZET
    # =========================
    st.subheader("Özet")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam kayıt", len(df))
    c2.metric("Mağaza", len(magazalar))
    c3.metric("Üretici", len(ureticiler))
    c4.metric("Büfe", len(bufeler))

    st.divider()

    # =========================
    # MAGAZA SECIMI
    # =========================
    st.subheader("Mağaza Seçimi")

    if len(magazalar) == 0:
        st.error("Mağaza bulunamadı. TIPI alanında 'Magaza' yazdığından emin ol.")
        st.stop()

    m_df = magazalar.copy()
    m_df["CARI_ISIM"] = m_df["CARI_ISIM"].astype(str)
    m_df["CARI_KOD"] = m_df["CARI_KOD"].astype(str)

    arama = st.text_input(
        "Mağaza adı veya kodunu yaz",
        placeholder="Yazmaya başla... (örn: kurtuluş, A0002)"
    ).strip()

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
    # YAKIN KAYITLAR
    # =========================
    yakin_ureticiler = pd.DataFrame()
    yakin_bufeler = pd.DataFrame()

    st.subheader("Seçili Mağazanın Yakınındaki Üreticiler")

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

                excel_data_ureticiler = dataframe_to_excel_bytes(
                    yakin_ureticiler[["CARI_KOD", "CARI_ISIM", "IL", "ILCE", "MESAFE_KM", "ENLEM", "BOYLAM"]]
                )

                st.download_button(
                    label="Üreticileri Excel Olarak İndir",
                    data=excel_data_ureticiler,
                    file_name="yakin_ureticiler.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("Bu yarıçap içinde üretici bulunamadı.")
        else:
            st.warning("Üretici bulunamadı (TIPI alanını kontrol et).")

    st.divider()

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

                excel_data = dataframe_to_excel_bytes(
                    yakin_bufeler[["BUFE_ADI", "ILCE", "MAHALLE", "BOLGE", "ADRES", "MESAFE_KM", "ENLEM", "BOYLAM"]]
                )

                st.download_button(
                    label="Büfeleri Excel Olarak İndir",
                    data=excel_data,
                    file_name="yakin_bufeler.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("Bu yarıçap içinde büfe bulunamadı.")
        else:
            st.warning("Büfe dosyasında geçerli koordinatlı kayıt bulunamadı.")

    st.divider()

    # =========================
    # HARİTA
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

        for _, row in bufeler.iterrows():
            folium.CircleMarker(
                location=[float(row["ENLEM"]), float(row["BOYLAM"])],
                radius=4,
                color="green",
                fill=True,
                fill_opacity=0.85,
                popup=(
                    f"Büfe: {row.get('BUFE_ADI', '')}<br>"
                    f"İlçe: {row.get('ILCE', '')}<br>"
                    f"Mahalle: {row.get('MAHALLE', '')}<br>"
                    f"Bölge: {row.get('BOLGE', '')}"
                )
            ).add_to(bufe_group)

        magaza_group.add_to(m)
        uretici_group.add_to(m)
        bufe_group.add_to(m)

        legend_html = """
        <div style="
            position: fixed;
            bottom: 50px;
            left: 50px;
            z-index: 9999;
            background-color: white;
            border: 2px solid grey;
            border-radius: 10px;
            padding: 12px 14px;
            font-size: 14px;
            box-shadow: 2px 2px 8px rgba(0,0,0,0.2);
        ">
            <div style="font-weight: bold; margin-bottom: 8px;">Harita Açıklaması</div>
            <div style="margin-bottom: 6px;">
                <span style="display: inline-block; width: 12px; height: 12px; background: red; border-radius: 50%; margin-right: 8px;"></span>
                Mağazalar
            </div>
            <div style="margin-bottom: 6px;">
                <span style="display: inline-block; width: 12px; height: 12px; background: blue; border-radius: 50%; margin-right: 8px;"></span>
                Üreticiler
            </div>
            <div>
                <span style="display: inline-block; width: 12px; height: 12px; background: green; border-radius: 50%; margin-right: 8px;"></span>
                Büfeler
            </div>
        </div>
        """

        m.get_root().html.add_child(folium.Element(legend_html))

        folium.LayerControl(collapsed=False).add_to(m)
        st_folium(m, width=1200, height=650, returned_objects=[])

    else:
        m_lat = float(secili_magaza["ENLEM"])
        m_lon = float(secili_magaza["BOYLAM"])

        m = folium.Map(location=[m_lat, m_lon], zoom_start=11, tiles="OpenStreetMap")

        folium.Marker(
            [m_lat, m_lon],
            popup=f"Mağaza: {secili_magaza['CARI_ISIM']}",
            icon=folium.Icon(color="red"),
        ).add_to(m)

        folium.Circle(
            location=[m_lat, m_lon],
            radius=yaricap * 1000,
            color="red",
            fill=False,
        ).add_to(m)

        for _, row in yakin_ureticiler.iterrows():
            folium.CircleMarker(
                location=[float(row["ENLEM"]), float(row["BOYLAM"])],
                radius=6,
                popup=f"Üretici: {row['CARI_ISIM']} ({row['MESAFE_KM']:.1f} km)",
                color="blue",
                fill=True,
                fill_opacity=0.85,
            ).add_to(m)

        for _, row in yakin_bufeler.iterrows():
            folium.CircleMarker(
                location=[float(row["ENLEM"]), float(row["BOYLAM"])],
                radius=6,
                popup=(
                    f"Büfe: {row['BUFE_ADI']} ({row['MESAFE_KM']:.1f} km)<br>"
                    f"İlçe: {row.get('ILCE', '')}<br>"
                    f"Mahalle: {row.get('MAHALLE', '')}<br>"
                    f"Bölge: {row.get('BOLGE', '')}"
                ),
                color="green",
                fill=True,
                fill_opacity=0.85,
            ).add_to(m)

        st_folium(m, width=1200, height=650, returned_objects=[])


# =========================================================
# SAYFA 2: TUM MAGAZALAR ANALIZI
# =========================================================
elif sayfa == "Tüm Mağazalar Analizi":

    st.subheader("Tüm Mağazalar İçin Yakınlık Analizi")

    st.info(
        "Bu sayfada mağaza seçmeden, tüm mağazalar için yakın üretici ve büfe listesi oluşturulur."
    )

    c1, c2 = st.columns(2)

    with c1:
        tum_top_n = st.selectbox(
            "Her mağaza için en yakın kaç kayıt gelsin?",
            options=[1, 3, 5, 10],
            index=1
        )

    with c2:
        tum_yaricap = st.slider(
            "Yarıçap (km)",
            min_value=1,
            max_value=200,
            value=30,
            step=5
        )

    sadece_tip = st.multiselect(
        "Rapor tipi",
        options=["Üretici", "Büfe"],
        default=["Üretici", "Büfe"]
    )

    analiz_baslat = st.button("Tüm Mağazalar İçin Analizi Başlat")

    if analiz_baslat:
        sonuclar = []

        progress = st.progress(0)
        toplam_magaza = len(magazalar)

        for i, (_, magaza) in enumerate(magazalar.iterrows(), start=1):
            m_lat = float(magaza["ENLEM"])
            m_lon = float(magaza["BOYLAM"])

            # Yakın üreticiler
            if "Üretici" in sadece_tip and len(ureticiler) > 0:
                u = ureticiler.copy()
                u["MESAFE_KM"] = haversine_km(
                    m_lat,
                    m_lon,
                    u["ENLEM"].values,
                    u["BOYLAM"].values
                )

                yakin_u = (
                    u[u["MESAFE_KM"] <= tum_yaricap]
                    .sort_values("MESAFE_KM")
                    .head(tum_top_n)
                    .copy()
                )

                for _, row in yakin_u.iterrows():
                    sonuclar.append({
                        "MAGAZA_KOD": magaza.get("CARI_KOD", ""),
                        "MAGAZA_ADI": magaza.get("CARI_ISIM", ""),
                        "MAGAZA_IL": magaza.get("IL", ""),
                        "MAGAZA_ILCE": magaza.get("ILCE", ""),
                        "YAKIN_TIP": "Üretici",
                        "YAKIN_KOD": row.get("CARI_KOD", ""),
                        "YAKIN_AD": row.get("CARI_ISIM", ""),
                        "YAKIN_IL": row.get("IL", ""),
                        "YAKIN_ILCE": row.get("ILCE", ""),
                        "MESAFE_KM": round(row.get("MESAFE_KM", 0), 2),
                        "YAKIN_ENLEM": row.get("ENLEM", ""),
                        "YAKIN_BOYLAM": row.get("BOYLAM", ""),
                    })

            # Yakın büfeler
            if "Büfe" in sadece_tip and len(bufeler) > 0:
                b = bufeler.copy()
                b["MESAFE_KM"] = haversine_km(
                    m_lat,
                    m_lon,
                    b["ENLEM"].values,
                    b["BOYLAM"].values
                )

                yakin_b = (
                    b[b["MESAFE_KM"] <= tum_yaricap]
                    .sort_values("MESAFE_KM")
                    .head(tum_top_n)
                    .copy()
                )

                for _, row in yakin_b.iterrows():
                    sonuclar.append({
                        "MAGAZA_KOD": magaza.get("CARI_KOD", ""),
                        "MAGAZA_ADI": magaza.get("CARI_ISIM", ""),
                        "MAGAZA_IL": magaza.get("IL", ""),
                        "MAGAZA_ILCE": magaza.get("ILCE", ""),
                        "YAKIN_TIP": "Büfe",
                        "YAKIN_KOD": "",
                        "YAKIN_AD": row.get("BUFE_ADI", ""),
                        "YAKIN_IL": "",
                        "YAKIN_ILCE": row.get("ILCE", ""),
                        "YAKIN_MAHALLE": row.get("MAHALLE", ""),
                        "YAKIN_BOLGE": row.get("BOLGE", ""),
                        "MESAFE_KM": round(row.get("MESAFE_KM", 0), 2),
                        "YAKIN_ENLEM": row.get("ENLEM", ""),
                        "YAKIN_BOYLAM": row.get("BOYLAM", ""),
                    })

            progress.progress(i / toplam_magaza)

        sonuc_df = pd.DataFrame(sonuclar)

        st.write(f"Toplam **{len(sonuc_df)}** yakın kayıt bulundu.")

        if len(sonuc_df) > 0:
            st.dataframe(sonuc_df, use_container_width=True)

            excel_data = dataframe_to_excel_bytes(sonuc_df)

            st.download_button(
                label="Tüm Mağazalar Yakınlık Raporunu Excel Olarak İndir",
                data=excel_data,
                file_name="tum_magazalar_yakinlik_raporu.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("Seçilen yarıçap içinde kayıt bulunamadı.")