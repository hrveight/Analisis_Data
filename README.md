# 📊 PSDKP Insight Engine

Dashboard Analisis Data

## 🎯 Tentang Aplikasi

**PSDKP Insight Engine** adalah dashboard analisis data interaktif yang dirancang khusus untuk membantu pengambilan keputusan berbasis data di lingkungan Pengawasan Sumber Daya Kelautan dan Perikanan (PSDKP).

### Fitur Utama

- 📈 **Analisis Korelasi** - Temukan hubungan antar variabel dengan uji statistik otomatis
- 📊 **Perbandingan Kelompok** - Bandingkan kinerja antar wilayah/unit dengan metode yang tepat
- 📉 **Analisis Tren** - Identifikasi pola perubahan dari waktu ke waktu
- 🔍 **Statistik Deskriptif** - Pahami karakteristik data dengan visualisasi interaktif
- 🤖 **Auto Statistical Test** - Sistem otomatis memilih metode statistik yang sesuai dengan data

## 📖 Cara Menggunakan

### 1. **Input Data**
   - Upload file Excel (.xlsx, .xls) atau CSV (.csv)
   - Pastikan baris pertama adalah header/nama kolom
   - Sistem akan otomatis mendeteksi tipe data setiap kolom
   - Konfirmasi atau ubah tipe data jika diperlukan

### 2. **Pilih Analisis**
   
   Pilih salah satu dari 4 jenis analisis:
   
   - **Korelasi**: Cek hubungan antara dua variabel numerik
     - Contoh: "Apakah jumlah patroli berhubungan dengan temuan pelanggaran?"
   
   - **Perbandingan Kelompok**: Bandingkan nilai antar kategori
     - Contoh: "Apakah kinerja Stasiun A berbeda dengan Stasiun B?"
   
   - **Tren Waktu**: Analisis pola perubahan temporal
     - Contoh: "Apakah jumlah pelanggaran meningkat dari bulan ke bulan?"
   
   - **Distribusi**: Lihat sebaran dan statistik dasar variabel
     - Contoh: "Bagaimana distribusi jumlah patroli per bulan?"

### 3. **Interpretasi Hasil**
   - Lihat visualisasi interaktif
   - Baca interpretasi dalam bahasa yang mudah dipahami
   - Periksa hasil uji statistik dan asumsi
   - Dapatkan rekomendasi tindak lanjut

## 📊 Format Data yang Didukung

### Excel (.xlsx, .xls)
```
| Tanggal    | Wilayah  | Jumlah Patroli | Temuan |
|------------|----------|----------------|--------|
| 2024-01-01 | Utara    | 15             | 3      |
| 2024-01-02 | Selatan  | 12             | 2      |
```

### CSV (.csv)
```csv
Tanggal,Wilayah,Jumlah Patroli,Temuan
2024-01-01,Utara,15,3
2024-01-02,Selatan,12,2
```

**Syarat:**
- Baris pertama harus berisi nama kolom (header)
- Minimal 10 baris data untuk hasil optimal
- Tidak ada baris kosong di tengah data

## 🧪 Metode Statistik yang Digunakan

| Analisis | Metode Parametrik | Metode Non-Parametrik |
|----------|-------------------|----------------------|
| Korelasi | Pearson | Spearman |
| 2 Kelompok | Independent t-test | Mann-Whitney U |
| 3+ Kelompok | One-way ANOVA | Kruskal-Wallis H |
| Tren | - | Spearman Rank Correlation |

*Sistem otomatis memilih metode yang tepat berdasarkan uji normalitas (Shapiro-Wilk)*