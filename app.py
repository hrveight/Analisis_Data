import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats
from datetime import datetime
import io

# ==================== CONFIG ====================
st.set_page_config(
    page_title="PSDKP Insight Engine",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== STYLING ====================
st.markdown("""
<style>
    .main {padding: 1rem 2rem;}
    .stMetric {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .stMetric label {color: white !important;}
    .stMetric [data-testid="stMetricValue"] {color: white !important;}
    .info-box {
        background-color: #e7f3ff;
        border-left: 4px solid #2196f3;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
    .assumption-box {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        padding: 1rem;
        border-radius: 4px;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ==================== SESSION STATE ====================
if 'df' not in st.session_state:
    st.session_state.df = None
if 'df_raw' not in st.session_state:
    st.session_state.df_raw = None
if 'column_types' not in st.session_state:
    st.session_state.column_types = {}
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'selected_analysis' not in st.session_state:
    st.session_state.selected_analysis = None

# ==================== HELPER FUNCTIONS ====================

def read_file(uploaded_file):
    """Baca file CSV atau Excel dengan handling error"""
    try:
        name = uploaded_file.name.lower()
        if name.endswith('.csv'):
            raw = uploaded_file.getvalue()
            try:
                df = pd.read_csv(io.BytesIO(raw))
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(raw), encoding='latin-1')
            except:
                df = pd.read_csv(io.BytesIO(raw), sep=';')
            return df, None
        elif name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(uploaded_file, engine='openpyxl')
            return df, None
        else:
            return None, "Format tidak didukung"
    except Exception as e:
        return None, f"Error: {str(e)}"

def infer_column_type(series):
    """Deteksi otomatis tipe kolom"""
    if pd.api.types.is_bool_dtype(series):
        return 'Boolean'
    
    if pd.api.types.is_datetime64_any_dtype(series):
        return 'Tanggal'
    
    if pd.api.types.is_numeric_dtype(series):
        return 'Angka'
    
    if series.dtype == object:
        sample = series.dropna().head(20)
        if len(sample) > 0:
            try:
                parsed = pd.to_datetime(sample, errors='coerce', dayfirst=True)
                if parsed.notna().mean() >= 0.7:
                    return 'Tanggal'
            except:
                pass
    
    return 'Teks/Kategori'

def apply_column_types(df, type_mapping):
    """Konversi tipe kolom sesuai pilihan user"""
    warnings = []
    df_new = df.copy()
    
    for col, dtype in type_mapping.items():
        try:
            if dtype == 'Angka':
                df_new[col] = pd.to_numeric(df_new[col], errors='coerce')
                null_pct = df_new[col].isna().mean() * 100
                if null_pct > 30:
                    warnings.append(f"Kolom '{col}': {null_pct:.0f}% gagal dikonversi ke angka")
            
            elif dtype == 'Tanggal':
                df_new[col] = pd.to_datetime(df_new[col], errors='coerce', dayfirst=True)
                null_pct = df_new[col].isna().mean() * 100
                if null_pct > 30:
                    warnings.append(f"Kolom '{col}': {null_pct:.0f}% gagal dikonversi ke tanggal")
            
            elif dtype == 'Teks/Kategori':
                df_new[col] = df_new[col].astype(str)
            
            elif dtype == 'Boolean':
                s = df_new[col]
                if pd.api.types.is_numeric_dtype(s):
                    df_new[col] = s.astype('Int64').map({1: True, 0: False})
                else:
                    ss = s.astype(str).str.lower().str.strip()
                    df_new[col] = ss.map({
                        'true': True, 'false': False, '1': True, '0': False,
                        'ya': True, 'tidak': False, 'y': True, 'n': False
                    })
        except Exception as e:
            warnings.append(f"Gagal konversi '{col}': {str(e)}")
    
    return df_new, warnings

def get_columns_by_type(df, type_mapping):
    """Ambil nama kolom berdasarkan tipe"""
    numeric = [col for col, t in type_mapping.items() if t == 'Angka']
    date = [col for col, t in type_mapping.items() if t == 'Tanggal']
    category = [col for col, t in type_mapping.items() if t == 'Teks/Kategori']
    return numeric, date, category

# ==================== ANALYSIS FUNCTIONS ====================

def analyze_correlation(df, x_col, y_col):
    """Analisis korelasi dengan uji asumsi"""
    data_clean = df[[x_col, y_col]].dropna()
    x = data_clean[x_col].values
    y = data_clean[y_col].values
    n = len(x)
    
    if n < 8:
        return {'error': 'Data terlalu sedikit (minimal 8 pasangan data)'}
    
    _, p_norm_x = stats.shapiro(x[:min(n, 5000)])
    _, p_norm_y = stats.shapiro(y[:min(n, 5000)])
    is_normal = (p_norm_x > 0.05) and (p_norm_y > 0.05)
    
    if is_normal:
        r, p_val = stats.pearsonr(x, y)
        method = 'Pearson'
        method_explain = 'Mengukur hubungan linear antara dua variabel'
    else:
        r, p_val = stats.spearmanr(x, y)
        method = 'Spearman'
        method_explain = 'Mengukur hubungan monoton (rank-based), lebih robust terhadap outlier'
    
    abs_r = abs(r)
    if abs_r > 0.7:
        strength = 'sangat kuat'
        practical = 'Hubungan ini cukup kuat untuk dijadikan dasar strategi atau prediksi.'
    elif abs_r > 0.5:
        strength = 'kuat'
        practical = 'Ada hubungan yang cukup konsisten, bisa dipertimbangkan dalam perencanaan.'
    elif abs_r > 0.3:
        strength = 'sedang'
        practical = 'Hubungan terlihat tapi tidak dominan. Pertimbangkan faktor lain juga.'
    else:
        strength = 'lemah atau tidak ada'
        practical = 'Hubungan sangat lemah. Variabel-variabel ini relatif independen.'
    
    direction = 'positif' if r > 0 else 'negatif'
    significance = 'signifikan' if p_val < 0.05 else 'tidak signifikan'
    
    return {
        'x': x, 'y': y, 'n': n,
        'method': method,
        'method_explain': method_explain,
        'r': r, 'p_value': p_val,
        'is_normal': is_normal,
        'p_norm_x': p_norm_x,
        'p_norm_y': p_norm_y,
        'strength': strength,
        'direction': direction,
        'significance': significance,
        'practical': practical,
        'stats': {
            'mean_x': x.mean(),
            'mean_y': y.mean(),
            'std_x': x.std(),
            'std_y': y.std()
        }
    }

def analyze_group_comparison(df, group_col, value_col):
    """Perbandingan kelompok dengan uji statistik"""
    data_clean = df[[group_col, value_col]].dropna()
    
    top_groups = data_clean[group_col].value_counts().head(10).index
    data_clean = data_clean[data_clean[group_col].isin(top_groups)]
    
    summary = data_clean.groupby(group_col)[value_col].agg([
        ('Jumlah Data', 'count'),
        ('Total', 'sum'),
        ('Rata-rata', 'mean'),
        ('Median', 'median'),
        ('Std Dev', 'std'),
        ('Min', 'min'),
        ('Max', 'max')
    ]).round(2).reset_index()
    
    groups = [data_clean[data_clean[group_col] == g][value_col].values 
              for g in top_groups]
    
    normal_flags = []
    for arr in groups:
        if len(arr) >= 3:
            _, p = stats.shapiro(arr[:min(len(arr), 5000)])
            normal_flags.append(p > 0.05)
    is_normal = all(normal_flags) if normal_flags else False
    
    if len(groups) == 2:
        if is_normal:
            stat, p_val = stats.ttest_ind(groups[0], groups[1], equal_var=False)
            test_name = 'Independent t-test'
            test_explain = 'Membandingkan rata-rata dua kelompok'
        else:
            stat, p_val = stats.mannwhitneyu(groups[0], groups[1])
            test_name = 'Mann-Whitney U test'
            test_explain = 'Membandingkan median dua kelompok (non-parametrik)'
    else:
        if is_normal:
            stat, p_val = stats.f_oneway(*groups)
            test_name = 'One-way ANOVA'
            test_explain = 'Membandingkan rata-rata lebih dari dua kelompok'
        else:
            stat, p_val = stats.kruskal(*groups)
            test_name = 'Kruskal-Wallis H test'
            test_explain = 'Membandingkan median lebih dari dua kelompok (non-parametrik)'
    
    significance = 'signifikan' if p_val < 0.05 else 'tidak signifikan'
    
    return {
        'summary': summary,
        'test_name': test_name,
        'test_explain': test_explain,
        'stat': stat,
        'p_value': p_val,
        'is_normal': is_normal,
        'significance': significance,
        'n_groups': len(groups)
    }

def analyze_trend(df, date_col, value_col, freq='M'):
    """Analisis tren waktu"""
    data_clean = df[[date_col, value_col]].dropna().copy()
    data_clean[date_col] = pd.to_datetime(data_clean[date_col])
    data_clean = data_clean.sort_values(date_col)
    
    ts = data_clean.set_index(date_col)[value_col].resample(freq).sum(min_count=1)
    ts_clean = ts.dropna()
    
    if len(ts_clean) < 3:
        return {'error': 'Data terlalu sedikit untuk analisis tren'}
    
    x_time = np.arange(len(ts_clean))
    r, p_val = stats.spearmanr(x_time, ts_clean.values)
    
    first_val = ts_clean.iloc[0]
    last_val = ts_clean.iloc[-1]
    change = last_val - first_val
    change_pct = (change / first_val * 100) if first_val != 0 else 0
    
    if r > 0.3 and p_val < 0.05:
        trend_desc = 'naik'
        trend_strength = 'kuat' if abs(r) > 0.7 else 'sedang'
    elif r < -0.3 and p_val < 0.05:
        trend_desc = 'turun'
        trend_strength = 'kuat' if abs(r) > 0.7 else 'sedang'
    else:
        trend_desc = 'stabil/fluktuatif'
        trend_strength = 'lemah'
    
    return {
        'ts': ts_clean,
        'dates': ts_clean.index,
        'values': ts_clean.values,
        'r': r,
        'p_value': p_val,
        'trend_desc': trend_desc,
        'trend_strength': trend_strength,
        'first_val': first_val,
        'last_val': last_val,
        'change': change,
        'change_pct': change_pct,
        'mean': ts_clean.mean(),
        'std': ts_clean.std(),
        'n_periods': len(ts_clean)
    }

def analyze_distribution(df, var_col):
    """Analisis distribusi variabel numerik"""
    values = df[var_col].dropna().values
    
    if len(values) < 3:
        return {'error': 'Data terlalu sedikit'}
    
    mean_val = values.mean()
    median_val = np.median(values)
    std_val = values.std()
    min_val = values.min()
    max_val = values.max()
    q1 = np.percentile(values, 25)
    q3 = np.percentile(values, 75)
    iqr = q3 - q1
    cv = (std_val / mean_val * 100) if mean_val != 0 else 0
    
    _, p_norm = stats.shapiro(values[:min(len(values), 5000)])
    is_normal = p_norm > 0.05
    
    if mean_val > median_val + std_val * 0.5:
        skewness = 'miring kanan (positif)'
        skew_detail = 'Ada beberapa nilai yang sangat tinggi'
    elif mean_val < median_val - std_val * 0.5:
        skewness = 'miring kiri (negatif)'
        skew_detail = 'Ada beberapa nilai yang sangat rendah'
    else:
        skewness = 'relatif simetris'
        skew_detail = 'Distribusi mendekati normal'
    
    if cv < 20:
        variability = 'sangat konsisten'
    elif cv < 40:
        variability = 'cukup konsisten'
    else:
        variability = 'sangat beragam'
    
    return {
        'values': values,
        'n': len(values),
        'mean': mean_val,
        'median': median_val,
        'std': std_val,
        'min': min_val,
        'max': max_val,
        'q1': q1,
        'q3': q3,
        'iqr': iqr,
        'cv': cv,
        'range': max_val - min_val,
        'is_normal': is_normal,
        'p_norm': p_norm,
        'skewness': skewness,
        'skew_detail': skew_detail,
        'variability': variability
    }

# ==================== NAVIGATION ====================
st.sidebar.title("PSDKP Insight Engine")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigasi",
    ["Intro", "Input Data", "Analisis", "Hasil", "Kesimpulan"],
    key="navigation"
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
**Tips:**
- Upload Excel/CSV dengan header di baris pertama
- Minimal 10 baris data untuk hasil optimal
- Pastikan tipe kolom sudah benar sebelum analisis
""")

# ==================== PAGE 1: INTRO ====================
if page == "Intro":
    st.title("PSDKP Insight Engine")
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 2rem; border-radius: 10px; color: white; margin-bottom: 2rem;'>
        <h2 style='color: white; margin: 0;'>Dashboard Analisis Data untuk Pengawasan Kelautan & Perikanan</h2>
        <p style='font-size: 1.1rem; margin-top: 1rem;'>
        Alat bantu analisis cepat dengan pendekatan statistik yang solid namun mudah dipahami
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### Untuk Siapa Dashboard Ini?
        
        Dashboard ini dirancang untuk semua divisi di PSDKP: Stasiun/Pangkalan, KPP, Operasi/VMS, Sekretariat, dan Ditjen Pusat.
        
        ### Yang Bisa Dilakukan:
        
        **1. Hubungan Antar Variabel**
        - Apakah ada hubungan antara jumlah patroli dengan temuan pelanggaran?
        - Metode: Korelasi (Pearson/Spearman) dengan uji asumsi
        
        **2. Perbandingan Kelompok**
        - Bandingkan kinerja antar wilayah/pangkalan/unit
        - Metode: t-test, ANOVA, atau uji non-parametrik
        
        **3. Analisis Tren Waktu**
        - Lihat pola perubahan dari bulan ke bulan, triwulan, atau tahun
        - Metode: Time series dengan uji tren
        
        **4. Sebaran Data**
        - Lihat distribusi dan statistik dasar variabel
        - Metode: Statistik deskriptif dengan uji normalitas
        """)
    
    with col2:
        st.markdown("""
        ### Cara Kerja Dashboard
        
        **Langkah 1: Input Data**
        - Upload file Excel (.xlsx) atau CSV (.csv)
        - Sistem deteksi otomatis tipe kolom (Angka/Teks/Tanggal)
        - Konfirmasi & sesuaikan jika perlu
        
        **Langkah 2: Pilih Analisis**
        - Pilih jenis analisis sesuai tujuan
        - Pilih variabel yang ingin dianalisis
        - Sistem otomatis memilih metode statistik yang tepat
        
        **Langkah 3: Lihat Hasil**
        - Visualisasi interaktif (grafik, tabel)
        - Hasil uji statistik dengan interpretasi
        - Uji asumsi dijelaskan dengan bahasa sederhana
        
        **Langkah 4: Kesimpulan**
        - Ringkasan temuan utama
        - Rekomendasi tindak lanjut
        - Alert & catatan penting
        
        ### Keunggulan Dashboard
        
        - Otomatis pilih metode statistik yang tepat
        - Uji asumsi dijelaskan dengan jelas
        - Interpretasi mudah dipahami
        - Bahasa Indonesia & konteks PSDKP
        """)
    
    st.markdown("""
    <div class="success-box">
        Klik "Input Data" di menu samping untuk upload file dan mulai analisis.
    </div>
    """, unsafe_allow_html=True)

# ==================== PAGE 2: INPUT DATA ====================
elif page == "Input Data":
    st.header("Input Data")
    
    st.markdown("""
    <div class="info-box">
        <strong>Format yang Didukung:</strong> Excel (.xlsx, .xls), CSV (.csv)<br>
        <strong>Syarat:</strong> Baris pertama harus header/nama kolom, minimal 10 baris data
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Upload File Data Anda",
        type=['xlsx', 'xls', 'csv'],
        help="Pilih file Excel atau CSV"
    )
    
    if uploaded_file is not None:
        df, error = read_file(uploaded_file)
        
        if error:
            st.error(f"Error: {error}")
        else:
            st.session_state.df_raw = df
            
            st.success(f"File berhasil dibaca: {len(df):,} baris × {len(df.columns)} kolom")
            
            st.subheader("Preview Data")
            st.dataframe(df.head(20), use_container_width=True)
            st.caption(f"Menampilkan 20 dari {len(df):,} baris")
            
            st.subheader("Konfirmasi Tipe Data Kolom")
            st.markdown("""
            <div class="info-box">
                Sistem sudah mendeteksi tipe data otomatis. Periksa dan ubah jika ada yang salah.
            </div>
            """, unsafe_allow_html=True)
            
            type_options = ['Angka', 'Teks/Kategori', 'Tanggal', 'Boolean']
            column_types = {}
            
            cols_per_row = 3
            for i in range(0, len(df.columns), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, col in enumerate(df.columns[i:i+cols_per_row]):
                    with cols[j]:
                        inferred = infer_column_type(df[col])
                        st.markdown(f"**{col}**")
                        st.caption(f"Contoh: {df[col].dropna().iloc[0] if len(df[col].dropna()) > 0 else 'N/A'}")
                        
                        column_types[col] = st.selectbox(
                            "Tipe",
                            type_options,
                            index=type_options.index(inferred) if inferred in type_options else 1,
                            key=f"type_{col}",
                            label_visibility="collapsed"
                        )
            
            st.session_state.column_types = column_types
            
            if st.button("Simpan & Terapkan Tipe Data", type="primary", use_container_width=True):
                df_processed, warnings = apply_column_types(df, column_types)
                st.session_state.df = df_processed
                
                st.success("Tipe data berhasil diterapkan")
                
                if warnings:
                    with st.expander("Peringatan Konversi", expanded=True):
                        for w in warnings:
                            st.warning(w)
                
                num_cols, date_cols, cat_cols = get_columns_by_type(df_processed, column_types)
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Kolom Angka", len(num_cols))
                col2.metric("Kolom Tanggal", len(date_cols))
                col3.metric("Kolom Kategori", len(cat_cols))
                
                st.markdown("""
                <div class="success-box">
                    Data siap dianalisis. Lanjut ke "Analisis" untuk memilih jenis analisis.
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Belum ada file yang diupload. Pilih file untuk memulai.")

# ==================== PAGE 3: ANALISIS ====================
elif page == "Analisis":
    st.header("Analisis Data")
    
    if st.session_state.df is None:
        st.warning("Belum ada data. Upload dan terapkan tipe data di 'Input Data' dulu.")
    else:
        df = st.session_state.df
        types = st.session_state.column_types
        num_cols, date_cols, cat_cols = get_columns_by_type(df, types)
        
        st.subheader("Statistik Deskriptif")
        st.markdown("""
        <div class="info-box">
            Pahami dulu karakteristik dasar data Anda melalui statistik deskriptif.
        </div>
        """, unsafe_allow_html=True)
        
        desc_type = st.radio(
            "Pilih jenis variabel untuk analisis deskriptif:",
            ["Variabel Numerik (Angka)", "Variabel Kategorikal (Teks)"],
            horizontal=True
        )
        
        if desc_type == "Variabel Numerik (Angka)":
            if len(num_cols) == 0:
                st.warning("Tidak ada kolom numerik dalam data.")
            else:
                selected_num = st.multiselect(
                    "Pilih variabel numerik (bisa lebih dari satu):",
                    num_cols,
                    default=num_cols[:min(3, len(num_cols))]
                )
                
                if selected_num:
                    st.markdown("---")
                    st.markdown("### Ukuran Pemusatan Data")
                    
                    for var in selected_num:
                        with st.expander(f"{var}", expanded=len(selected_num) == 1):
                            data = df[var].dropna()
                            
                            if len(data) == 0:
                                st.warning("Semua data kosong untuk variabel ini")
                                continue
                            
                            mean_val = data.mean()
                            median_val = data.median()
                            try:
                                mode_val = data.mode()[0] if len(data.mode()) > 0 else "Tidak ada"
                                mode_count = (data == mode_val).sum() if mode_val != "Tidak ada" else 0
                            except:
                                mode_val = "Tidak ada"
                                mode_count = 0
                            
                            col1, col2, col3 = st.columns(3)
                            col1.metric("Mean (Rata-rata)", f"{mean_val:.2f}")
                            col2.metric("Median (Nilai Tengah)", f"{median_val:.2f}")
                            col3.metric("Modus (Paling Sering)", f"{mode_val}" if mode_val == "Tidak ada" else f"{mode_val:.2f} ({mode_count}x)")
                            
                            st.markdown(f"""
                            **Interpretasi:**
                            - Mean ({mean_val:.2f}): Nilai rata-rata semua data. Sensitif terhadap nilai ekstrim.
                            - Median ({median_val:.2f}): Nilai tengah, lebih robust terhadap outlier.
                            - {'Perbedaan Mean-Median: Mean > Median menunjukkan ada nilai tinggi yang menarik rata-rata ke atas (distribusi miring kanan).' if mean_val > median_val + 0.1 * data.std() else 'Perbedaan Mean-Median: Mean < Median menunjukkan ada nilai rendah yang menarik rata-rata ke bawah (distribusi miring kiri).' if mean_val < median_val - 0.1 * data.std() else 'Mean ≈ Median: Distribusi relatif simetris.'}
                            """)
                            
                            st.markdown("---")
                            st.markdown("### Ukuran Penyebaran Data")
                            
                            std_val = data.std()
                            var_val = data.var()
                            range_val = data.max() - data.min()
                            q1 = data.quantile(0.25)
                            q2 = data.quantile(0.50)
                            q3 = data.quantile(0.75)
                            iqr = q3 - q1
                            cv = (std_val / mean_val * 100) if mean_val != 0 else 0
                            
                            col1, col2, col3, col4 = st.columns(4)
                            col1.metric("Std Dev", f"{std_val:.2f}")
                            col2.metric("Varians", f"{var_val:.2f}")
                            col3.metric("Range", f"{range_val:.2f}")
                            col4.metric("IQR", f"{iqr:.2f}")
                            
                            st.markdown(f"""
                            **Kuartil:**
                            - Q1 (25%): {q1:.2f} - 25% data di bawah nilai ini
                            - Q2 (50%): {q2:.2f} - Median
                            - Q3 (75%): {q3:.2f} - 75% data di bawah nilai ini
                            - IQR (Q3-Q1): {iqr:.2f} - Rentang 50% data tengah
                            
                            **Interpretasi:**
                            - Koefisien Variasi: {cv:.1f}% - {'Sangat konsisten (CV < 20%)' if cv < 20 else 'Cukup konsisten (20% ≤ CV < 40%)' if cv < 40 else 'Beragam (40% ≤ CV < 60%)' if cv < 60 else 'Sangat beragam (CV ≥ 60%)'}
                            - Range: {range_val:.2f} - Rentang dari nilai minimum ({data.min():.2f}) hingga maksimum ({data.max():.2f})
                            """)
                            
                            st.markdown("---")
                            st.markdown("### Bentuk Distribusi")
                            
                            from scipy.stats import skew, kurtosis
                            skewness = skew(data)
                            kurt = kurtosis(data)
                            
                            col1, col2 = st.columns(2)
                            col1.metric("Skewness (Kemiringan)", f"{skewness:.3f}")
                            col2.metric("Kurtosis (Keruncingan)", f"{kurt:.3f}")
                            
                            if skewness > 0.5:
                                skew_interpret = "Miring Kanan (Positif): Data cenderung berkumpul di nilai rendah dengan ekor panjang ke kanan"
                            elif skewness < -0.5:
                                skew_interpret = "Miring Kiri (Negatif): Data cenderung berkumpul di nilai tinggi dengan ekor panjang ke kiri"
                            else:
                                skew_interpret = "Relatif Simetris: Distribusi mendekati normal"
                            
                            if kurt > 3:
                                kurt_interpret = "Leptokurtik (Runcing): Distribusi lebih runcing dari normal"
                            elif kurt < -3:
                                kurt_interpret = "Platykurtik (Datar): Distribusi lebih datar dari normal"
                            else:
                                kurt_interpret = "Mesokurtik: Distribusi mendekati normal"
                            
                            st.markdown(f"""
                            **Interpretasi:**
                            - {skew_interpret}
                            - {kurt_interpret}
                            """)
                            
                            st.markdown("---")
                            st.markdown("### Visualisasi Distribusi")
                            
                            fig_hist = go.Figure()
                            fig_hist.add_trace(go.Histogram(
                                x=data,
                                nbinsx=30,
                                name=var,
                                marker_color='#667eea',
                                opacity=0.7
                            ))
                            fig_hist.add_vline(x=mean_val, line_dash="dash", line_color="red", 
                                             annotation_text=f"Mean: {mean_val:.2f}")
                            fig_hist.add_vline(x=median_val, line_dash="dash", line_color="green", 
                                             annotation_text=f"Median: {median_val:.2f}")
                            fig_hist.update_layout(
                                title=f"Distribusi {var}",
                                xaxis_title=var,
                                yaxis_title="Frekuensi",
                                showlegend=False,
                                height=400
                            )
                            st.plotly_chart(fig_hist, use_container_width=True)
                            
                            fig_box = go.Figure()
                            fig_box.add_trace(go.Box(
                                y=data,
                                name=var,
                                marker_color='#764ba2',
                                boxmean='sd'
                            ))
                            fig_box.update_layout(
                                title=f"Box Plot: {var}",
                                yaxis_title=var,
                                height=400
                            )
                            st.plotly_chart(fig_box, use_container_width=True)
                            
                            lower_bound = q1 - 1.5 * iqr
                            upper_bound = q3 + 1.5 * iqr
                            outliers = data[(data < lower_bound) | (data > upper_bound)]
                            
                            if len(outliers) > 0:
                                st.warning(f"Terdeteksi {len(outliers)} outlier ({len(outliers)/len(data)*100:.1f}% dari data)")
                                st.caption(f"Nilai di luar range [{lower_bound:.2f}, {upper_bound:.2f}]")
                            else:
                                st.success("Tidak ada outlier terdeteksi (metode IQR)")
        
        else:
            if len(cat_cols) == 0:
                st.warning("Tidak ada kolom kategorikal dalam data.")
            else:
                selected_cat = st.selectbox("Pilih variabel kategorikal:", cat_cols)
                
                if selected_cat:
                    st.markdown("---")
                    data = df[selected_cat].dropna()
                    
                    freq_table = data.value_counts().reset_index()
                    freq_table.columns = ['Kategori', 'Frekuensi']
                    freq_table['Proporsi'] = (freq_table['Frekuensi'] / freq_table['Frekuensi'].sum() * 100).round(2)
                    freq_table['Proporsi_str'] = freq_table['Proporsi'].apply(lambda x: f"{x:.2f}%")
                    
                    st.markdown("### Tabel Distribusi Frekuensi")
                    st.dataframe(freq_table, use_container_width=True)
                    
                    st.markdown(f"""
                    **Interpretasi:**
                    - Total kategori unik: {len(freq_table)}
                    - Kategori terbanyak: {freq_table.iloc[0]['Kategori']} ({freq_table.iloc[0]['Frekuensi']} data, {freq_table.iloc[0]['Proporsi']:.1f}%)
                    - Kategori paling sedikit: {freq_table.iloc[-1]['Kategori']} ({freq_table.iloc[-1]['Frekuensi']} data, {freq_table.iloc[-1]['Proporsi']:.1f}%)
                    """)
                    
                    st.markdown("---")
                    st.markdown("### Visualisasi")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fig_bar = px.bar(
                            freq_table.head(15),
                            x='Kategori',
                            y='Frekuensi',
                            text='Proporsi_str',
                            title=f"Frekuensi {selected_cat} (Top 15)",
                            color='Frekuensi',
                            color_continuous_scale='Blues'
                        )
                        fig_bar.update_traces(textposition='outside')
                        st.plotly_chart(fig_bar, use_container_width=True)
                    
                    with col2:
                        fig_pie = px.pie(
                            freq_table.head(10),
                            values='Frekuensi',
                            names='Kategori',
                            title=f"Proporsi {selected_cat} (Top 10)",
                            hole=0.3
                        )
                        st.plotly_chart(fig_pie, use_container_width=True)
                    
                    st.markdown("---")
                    st.markdown("### Ukuran Relatif")
                    
                    total = freq_table['Frekuensi'].sum()
                    top_3 = freq_table.head(3)
                    top_3_total = top_3['Frekuensi'].sum()
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Data", f"{total:,}")
                    col2.metric("Top 3 Coverage", f"{top_3_total/total*100:.1f}%")
                    col3.metric("Kategori Unik", len(freq_table))
                    
                    st.markdown(f"""
                    **Interpretasi Konsentrasi:**
                    - Top 3 kategori mencakup {top_3_total/total*100:.1f}% dari total data
                    - {'Data sangat terkonsentrasi di beberapa kategori' if top_3_total/total > 0.7 else 'Data cukup tersebar di berbagai kategori' if top_3_total/total > 0.5 else 'Data tersebar merata di banyak kategori'}
                    """)
        
        st.markdown("---")
        st.markdown("---")
        
        st.subheader("Analisis Lanjutan (Opsional)")
        
        st.markdown("""
        <div class="info-box">
            Setelah memahami karakteristik data, Anda bisa melakukan analisis lanjutan untuk menjawab pertanyaan spesifik.
        </div>
        """, unsafe_allow_html=True)
        
        analysis_type = st.selectbox(
            "Apa yang ingin Anda ketahui?",
            [
                "-- Pilih Tujuan Analisis --",
                "Apakah ada hubungan antara dua faktor? (Korelasi)",
                "Apakah ada perbedaan antar kelompok? (Perbandingan)",
                "Bagaimana pola perubahan dari waktu ke waktu? (Tren)",
            ]
        )
        
        st.markdown("---")
        
        if "hubungan" in analysis_type.lower():
            st.subheader("Analisis Hubungan Antar Variabel")
            
            st.markdown("""
            **Contoh pertanyaan:** Apakah semakin banyak patroli, semakin banyak temuan pelanggaran?
            """)
            
            if len(num_cols) < 2:
                st.error("Membutuhkan minimal 2 kolom angka untuk analisis ini")
            else:
                col1, col2 = st.columns(2)
                with col1:
                    x_var = st.selectbox("Variabel 1 (X)", num_cols, key="corr_x")
                with col2:
                    y_var = st.selectbox("Variabel 2 (Y)", [c for c in num_cols if c != x_var], key="corr_y")
                
                if st.button("Jalankan Analisis Korelasi", type="primary", use_container_width=True):
                    with st.spinner("Menganalisis data..."):
                        result = analyze_correlation(df, x_var, y_var)
                        
                        if 'error' in result:
                            st.error(f"{result['error']}")
                        else:
                            st.session_state.analysis_results = {
                                'type': 'correlation',
                                'x_var': x_var,
                                'y_var': y_var,
                                'result': result
                            }
                            st.success("Analisis selesai! Lihat tab 'Hasil'")
        
        elif "perbedaan" in analysis_type.lower():
            st.subheader("Analisis Perbandingan Kelompok")
            
            st.markdown("""
            **Contoh pertanyaan:** Apakah kinerja Stasiun A berbeda dengan Stasiun B?
            """)
            
            if len(cat_cols) == 0 or len(num_cols) == 0:
                st.error("Membutuhkan minimal 1 kolom kategori dan 1 kolom angka")
            else:
                col1, col2 = st.columns(2)
                with col1:
                    group_var = st.selectbox("Kelompok Pembanding", cat_cols, key="comp_group")
                with col2:
                    value_var = st.selectbox("Nilai yang Dibandingkan", num_cols, key="comp_value")
                
                if st.button("Jalankan Analisis Perbandingan", type="primary", use_container_width=True):
                    with st.spinner("Menganalisis data..."):
                        result = analyze_group_comparison(df, group_var, value_var)
                        
                        if 'error' in result:
                            st.error(f"{result['error']}")
                        else:
                            st.session_state.analysis_results = {
                                'type': 'comparison',
                                'group_var': group_var,
                                'value_var': value_var,
                                'result': result
                            }
                            st.success("Analisis selesai! Lihat tab 'Hasil'")
        
        elif "waktu" in analysis_type.lower():
            st.subheader("Analisis Tren Waktu")
            
            st.markdown("""
            **Contoh pertanyaan:** Apakah jumlah pelanggaran meningkat dari bulan ke bulan?
            """)
            
            if len(date_cols) == 0 or len(num_cols) == 0:
                st.error("Membutuhkan minimal 1 kolom tanggal dan 1 kolom angka")
            else:
                col1, col2, col3 = st.columns(3)
                with col1:
                    date_var = st.selectbox("Kolom Waktu", date_cols, key="trend_date")
                with col2:
                    value_var = st.selectbox("Nilai yang Dianalisis", num_cols, key="trend_value")
                with col3:
                    freq = st.selectbox("Ringkas Per", 
                                       ["Harian", "Mingguan", "Bulanan", "Triwulan", "Tahunan"],
                                       index=2)
                
                freq_map = {
                    "Harian": "D",
                    "Mingguan": "W",
                    "Bulanan": "M",
                    "Triwulan": "Q",
                    "Tahunan": "Y"
                }
                
                if st.button("Jalankan Analisis Tren", type="primary", use_container_width=True):
                    with st.spinner("Menganalisis data..."):
                        result = analyze_trend(df, date_var, value_var, freq_map[freq])
                        
                        if 'error' in result:
                            st.error(f"{result['error']}")
                        else:
                            st.session_state.analysis_results = {
                                'type': 'trend',
                                'date_var': date_var,
                                'value_var': value_var,
                                'freq': freq,
                                'result': result
                            }
                            st.success("Analisis selesai! Lihat tab 'Hasil'")

# ==================== PAGE 4: HASIL ====================
elif page == "Hasil":
    st.header("Hasil Analisis")
    
    if st.session_state.analysis_results is None:
        st.info("Belum ada hasil. Jalankan analisis di tab 'Analisis' dulu.")
    else:
        res = st.session_state.analysis_results
        
        if res['type'] == 'correlation':
            r = res['result']
            st.subheader(f"Hubungan: {res['x_var']} vs {res['y_var']}")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Korelasi (r)", f"{r['r']:.3f}")
            col2.metric("P-value", f"{r['p_value']:.4f}")
            col3.metric("Jumlah Data", f"{r['n']:,}")
            col4.metric("Metode", r['method'])
            
            fig = px.scatter(
                x=r['x'], y=r['y'],
                labels={'x': res['x_var'], 'y': res['y_var']},
                title=f"Scatter Plot: {res['x_var']} vs {res['y_var']}",
                trendline="ols",
                trendline_color_override="red"
            )
            fig.update_traces(marker=dict(size=8, opacity=0.6, color='#667eea'))
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("### Interpretasi")
            st.markdown(f"""
            Terdapat hubungan {r['direction']} dengan kekuatan {r['strength']} (r = {r['r']:.3f}).
            
            Hubungan ini {r['significance']} secara statistik (p = {r['p_value']:.4f}, alpha = 0.05).
            
            **Arti Praktis:** {r['practical']}
            """)
            
            with st.expander("Uji Asumsi & Metode Statistik"):
                st.markdown(f"""
                <div class="assumption-box">
                    <strong>Metode yang Digunakan: {r['method']} Correlation</strong><br>
                    {r['method_explain']}<br><br>
                    
                    <strong>Uji Normalitas (Shapiro-Wilk):</strong><br>
                    • {res['x_var']}: p = {r['p_norm_x']:.4f} {'✅ Normal' if r['p_norm_x'] > 0.05 else '⚠️ Tidak Normal'}<br>
                    • {res['y_var']}: p = {r['p_norm_y']:.4f} {'✅ Normal' if r['p_norm_y'] > 0.05 else '⚠️ Tidak Normal'}<br><br>
                    
                    <strong>Kenapa {r['method']}?</strong><br>
                    {'Data kedua variabel mendekati distribusi normal, sehingga Pearson (linear correlation) adalah pilihan yang tepat.' if r['is_normal'] else 'Data tidak normal, sehingga Spearman (rank-based correlation) lebih robust dan cocok untuk data ini.'}
                </div>
                """, unsafe_allow_html=True)
        
        elif res['type'] == 'comparison':
            r = res['result']
            st.subheader(f"Perbandingan: {res['value_var']} per {res['group_var']}")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Uji Statistik", f"{r['stat']:.3f}")
            col2.metric("P-value", f"{r['p_value']:.4f}")
            col3.metric("Jumlah Kelompok", r['n_groups'])
            
            fig = px.bar(
                r['summary'], 
                x=res['group_var'], 
                y='Rata-rata',
                title=f"Rata-rata {res['value_var']} per {res['group_var']}",
                text='Rata-rata',
                color='Rata-rata',
                color_continuous_scale='Blues'
            )
            fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("### Ringkasan Statistik per Kelompok")
            st.dataframe(r['summary'], use_container_width=True)
            
            st.markdown("### Interpretasi")
            sorted_df = r['summary'].sort_values('Rata-rata', ascending=False)
            top = sorted_df.iloc[0]
            bottom = sorted_df.iloc[-1]
            
            st.markdown(f"""
            Kelompok "{top[res['group_var']]}" memiliki rata-rata tertinggi ({top['Rata-rata']:.2f}), 
            sedangkan "{bottom[res['group_var']]}" memiliki rata-rata terendah ({bottom['Rata-rata']:.2f}).
            
            Perbedaan antar kelompok {r['significance']} secara statistik (p = {r['p_value']:.4f}).
            
            {'Artinya: Perbedaan yang terlihat bukan hanya kebetulan, ada indikasi kuat bahwa kelompok-kelompok ini memang berbeda.' if r['p_value'] < 0.05 else 'Artinya: Perbedaan yang terlihat bisa jadi karena variasi acak, belum cukup bukti untuk menyimpulkan ada perbedaan yang konsisten.'}
            """)
            
            with st.expander("Uji Asumsi & Metode Statistik"):
                st.markdown(f"""
                <div class="assumption-box">
                    <strong>Metode yang Digunakan: {r['test_name']}</strong><br>
                    {r['test_explain']}<br><br>
                    
                    <strong>Kenapa {r['test_name']}?</strong><br>
                    {'Data setiap kelompok mendekati distribusi normal, sehingga uji parametrik (t-test/ANOVA) dapat digunakan.' if r['is_normal'] else 'Data tidak normal di beberapa/semua kelompok, sehingga uji non-parametrik (Mann-Whitney/Kruskal-Wallis) lebih tepat karena tidak mengasumsikan normalitas.'}
                </div>
                """, unsafe_allow_html=True)
        
        elif res['type'] == 'trend':
            r = res['result']
            st.subheader(f"Tren: {res['value_var']} dari Waktu ke Waktu")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Nilai Awal", f"{r['first_val']:.2f}")
            col2.metric("Nilai Akhir", f"{r['last_val']:.2f}")
            col3.metric("Perubahan", f"{r['change']:+.2f} ({r['change_pct']:+.1f}%)")
            col4.metric("Periode", r['n_periods'])
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=r['dates'], 
                y=r['values'],
                mode='lines+markers',
                name=res['value_var'],
                line=dict(color='#667eea', width=3),
                marker=dict(size=8)
            ))
            fig.update_layout(
                title=f"Tren {res['value_var']} ({res['freq']})",
                xaxis_title="Periode",
                yaxis_title=res['value_var'],
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("### Interpretasi")
            st.markdown(f"""
            Tren menunjukkan pola {r['trend_desc']} dengan kekuatan {r['trend_strength']} (r = {r['r']:.3f}, p = {r['p_value']:.4f}).
            
            Dari periode awal ke akhir, terjadi perubahan sebesar {r['change']:+.2f} ({r['change_pct']:+.1f}%).
            
            {'Artinya: Ada pola perubahan yang konsisten dari waktu ke waktu, bukan hanya fluktuasi acak.' if r['p_value'] < 0.05 else 'Artinya: Polanya belum cukup konsisten untuk disebut tren yang jelas, mungkin lebih ke fluktuasi.'}
            """)
            
            with st.expander("Statistik Tambahan"):
                col1, col2, col3 = st.columns(3)
                col1.metric("Rata-rata", f"{r['mean']:.2f}")
                col2.metric("Std Dev", f"{r['std']:.2f}")
                col3.metric("Variabilitas", f"{(r['std']/r['mean']*100):.1f}%")
            
            with st.expander("Metode Statistik"):
                st.markdown("""
                <div class="assumption-box">
                    <strong>Metode: Spearman Rank Correlation dengan Time Index</strong><br>
                    Mengukur apakah ada tren monoton (naik/turun konsisten) dari waktu ke waktu.<br><br>
                    
                    <strong>Interpretasi r:</strong><br>
                    • r > 0.3 dan p < 0.05 = Tren naik yang signifikan<br>
                    • r < -0.3 dan p < 0.05 = Tren turun yang signifikan<br>
                    • Lainnya = Tidak ada tren yang jelas (stabil/fluktuatif)
                </div>
                """, unsafe_allow_html=True)

# ==================== PAGE 5: KESIMPULAN ====================
elif page == "Kesimpulan":
    st.header("Kesimpulan & Rekomendasi")
    
    if st.session_state.analysis_results is None:
        st.info("Belum ada hasil untuk disimpulkan. Jalankan analisis dulu.")
    else:
        res = st.session_state.analysis_results
        
        st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 10px; color: white; margin-bottom: 2rem;'>
            <h2 style='color: white; margin: 0;'>Ringkasan Temuan Utama</h2>
        </div>
        """, unsafe_allow_html=True)
        
        if res['type'] == 'correlation':
            r = res['result']
            
            st.markdown(f"""
            **Jenis Analisis:** Hubungan Antar Variabel (Korelasi {r['method']})
            
            **Variabel:** `{res['x_var']}` vs `{res['y_var']}`
            
            **Temuan Kunci:**
            - Korelasi: {r['r']:.3f} ({r['strength']}, {r['direction']})
            - Signifikansi: {r['significance']} (p = {r['p_value']:.4f})
            - Berdasarkan {r['n']:,} pasang data
            """)
            
            st.markdown("### Rekomendasi Tindak Lanjut")
            
            if abs(r['r']) > 0.5 and r['p_value'] < 0.05:
                st.markdown("""
                <div class="success-box">
                    <strong>Hubungan Kuat Terdeteksi</strong><br><br>
                    <strong>Yang Bisa Dilakukan:</strong><br>
                    1. Strategi: Fokus peningkatan pada variabel X untuk mempengaruhi variabel Y<br>
                    2. Prediksi: Gunakan variabel X sebagai indikator untuk memperkirakan Y<br>
                    3. Monitoring: Pantau kedua variabel secara bersamaan untuk deteksi dini<br>
                    4. Analisis Lanjut: Cari faktor penyebab kenapa kedua variabel berhubungan<br>
                    5. Validasi: Uji hubungan ini di periode atau wilayah lain untuk konfirmasi
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="info-box">
                    <strong>Hubungan Lemah/Tidak Signifikan</strong><br><br>
                    <strong>Yang Perlu Dipertimbangkan:</strong><br>
                    1. Cari variabel lain yang mungkin lebih berpengaruh<br>
                    2. Periksa apakah ada variabel moderator<br>
                    3. Evaluasi kualitas data - apakah ada noise atau kesalahan pengukuran?<br>
                    4. Pertimbangkan hubungan non-linear
                </div>
                """, unsafe_allow_html=True)
        
        elif res['type'] == 'comparison':
            r = res['result']
            sorted_df = r['summary'].sort_values('Rata-rata', ascending=False)
            top = sorted_df.iloc[0]
            bottom = sorted_df.iloc[-1]
            
            st.markdown(f"""
            **Jenis Analisis:** Perbandingan Kelompok ({r['test_name']})
            
            **Variabel:** `{res['value_var']}` dibandingkan antar `{res['group_var']}`
            
            **Temuan Kunci:**
            - Kelompok terbaik: {top[res['group_var']]} (rata-rata {top['Rata-rata']:.2f})
            - Kelompok terendah: {bottom[res['group_var']]} (rata-rata {bottom['Rata-rata']:.2f})
            - Perbedaan: {r['significance']} (p = {r['p_value']:.4f})
            - Total kelompok dibandingkan: {r['n_groups']}
            """)
            
            st.markdown("### Rekomendasi Tindak Lanjut")
            
            if r['p_value'] < 0.05:
                st.markdown(f"""
                <div class="success-box">
                    <strong>Ada Perbedaan Signifikan Antar Kelompok</strong><br><br>
                    <strong>Langkah Strategis:</strong><br>
                    1. Investigasi: Cari tahu kenapa {top[res['group_var']]} unggul - apa best practice yang bisa ditiru?<br>
                    2. Benchmarking: Jadikan {top[res['group_var']]} sebagai benchmark untuk kelompok lain<br>
                    3. Alokasi Sumber Daya: Evaluasi apakah kelompok dengan performa rendah butuh dukungan tambahan<br>
                    4. Analisis Akar Masalah: Untuk {bottom[res['group_var']]}, cari tahu apa kendala utamanya<br>
                    5. Target Improvement: Set target realistis untuk kelompok menengah-bawah untuk naik level
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="info-box">
                    <strong>Perbedaan Tidak Signifikan</strong><br><br>
                    <strong>Interpretasi:</strong><br>
                    Meski ada perbedaan angka, secara statistik perbedaan ini bisa jadi karena variasi acak.<br><br>
                    <strong>Yang Bisa Dilakukan:</strong><br>
                    1. Jika perbedaan terlihat kecil, ini bisa jadi hal baik (konsistensi antar kelompok)<br>
                    2. Evaluasi apakah standar/SOP sudah diterapkan merata<br>
                    3. Pertimbangkan faktor lain yang mungkin lebih membedakan kelompok
                </div>
                """, unsafe_allow_html=True)
        
        elif res['type'] == 'trend':
            r = res['result']
            
            st.markdown(f"""
            **Jenis Analisis:** Tren Waktu
            
            **Variabel:** `{res['value_var']}` dari waktu ke waktu
            
            **Temuan Kunci:**
            - Tren: {r['trend_desc']} ({r['trend_strength']})
            - Perubahan: {r['change']:+.2f} ({r['change_pct']:+.1f}%)
            - Nilai awal: {r['first_val']:.2f}, Nilai akhir: {r['last_val']:.2f}
            - Signifikansi: p = {r['p_value']:.4f}
            """)
            
            st.markdown("### Rekomendasi Tindak Lanjut")
            
            if r['p_value'] < 0.05:
                if r['trend_desc'] == 'naik':
                    st.markdown("""
                    <div class="success-box">
                        <strong>Tren Naik Terdeteksi</strong><br><br>
                        <strong>Langkah Strategis:</strong><br>
                        1. Identifikasi faktor pendorong tren positif ini<br>
                        2. Perkuat program/kegiatan yang mendukung tren naik<br>
                        3. Monitor apakah tren akan berkelanjutan atau mencapai plateau<br>
                        4. Dokumentasikan best practice untuk replikasi
                    </div>
                    """, unsafe_allow_html=True)
                elif r['trend_desc'] == 'turun':
                    st.markdown("""
                    <div class="warning-box">
                        <strong>Tren Turun Terdeteksi</strong><br><br>
                        <strong>Langkah Strategis:</strong><br>
                        1. Investigasi penyebab penurunan - apakah faktor internal atau eksternal?<br>
                        2. Evaluasi program/kebijakan yang mungkin perlu diperbaiki<br>
                        3. Set target untuk membalikkan tren negatif<br>
                        4. Monitor progress secara berkala
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="info-box">
                    <strong>Tren Tidak Jelas/Stabil</strong><br><br>
                    <strong>Interpretasi:</strong><br>
                    Data menunjukkan fluktuasi tanpa pola naik/turun yang konsisten.<br><br>
                    <strong>Yang Bisa Dilakukan:</strong><br>
                    1. Stabilitas bisa jadi hal positif - menunjukkan konsistensi<br>
                    2. Periksa apakah ada pola musiman atau siklikal<br>
                    3. Evaluasi apakah perlu intervensi untuk meningkatkan performa
                </div>
                """, unsafe_allow_html=True)

# ==================== FOOTER ====================
st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style='font-size: 0.8rem; color: #666;'>
    <strong>PSDKP Insight Engine</strong><br>
    Version 1.0<br>
    <em>Data-Driven Decision Making</em>
</div>
""", unsafe_allow_html=True)