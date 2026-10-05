# OVERVIEW — An Intelligent Personalized Agent for Individual Financial Planning

> **Dokumen kerja yang dapat diubah.** Ini adalah ringkasan ide dan arah awal proyek untuk dibaca oleh tim dan Opencode. Fitur, prioritas, dan pilihan teknologi yang diberi label **Usulan** belum menjadi keputusan final. Perbarui bagian yang relevan ketika hasil diskusi tim sudah tersedia.

## 1. Ringkasan ide

**An Intelligent Personalized Agent for Individual Financial Planning** adalah ide aplikasi yang membantu seseorang memahami kondisi keuangannya, menetapkan tujuan, dan memperoleh panduan perencanaan yang disesuaikan dengan informasi yang ia berikan.

Pengalaman yang diusulkan menggabungkan tampilan ringkasan keuangan, pengelolaan tujuan, rencana atau langkah berikutnya, dan—jika disetujui tim—assistant percakapan. Sistem harus menjelaskan informasi atau asumsi yang mendasari panduannya. Pengguna tetap memegang kendali untuk memeriksa, mengoreksi, atau mengabaikan suatu saran.

**Versi satu kalimat:** aplikasi perencanaan keuangan pribadi yang membantu pengguna mengubah informasi dan tujuan keuangannya menjadi gambaran yang lebih jelas serta langkah-langkah yang mudah ditinjau.

## 2. Status informasi proyek

### Yang sudah diketahui

- Nama/ide proyek: **An Intelligent Personalized Agent For Individual Financial Planning**.
- Tim masih mendiskusikan fitur apa yang akan dimasukkan.
- Pengerjaan dimulai dari frontend: rancangan dibuat menggunakan Stitch AI, lalu diimplementasikan dengan bantuan Opencode.
- Dokumen ini adalah gambaran awal, bukan spesifikasi final yang sudah disetujui.

### Usulan yang perlu dikonfirmasi

- **Pengguna utama:** individu yang ingin memahami keuangan dan mengelola satu atau lebih tujuan.
- **Platform awal:** aplikasi web responsif, bukan aplikasi native iOS/Android.
- **Fokus MVP:** dashboard, tujuan, alur input/onboarding yang minimal, serta tampilan rencana atau assistant jika itu memang fitur inti proyek.
- **Perhitungan keuangan:** menjadi tanggung jawab backend/domain logic yang ditinjau tim; frontend menampilkan hasil dan membantu validasi input, bukan menjadi sumber kebenaran perhitungan.
- **Sumber data awal:** kemungkinan input manual atau data demo yang jelas diberi label. Integrasi rekening belum diasumsikan.

### Belum diputuskan

Target pengguna dan negara; mata uang; metrik keuangan yang ditampilkan; rumus perhitungan; fitur final; batasan panduan AI; autentikasi; privasi/retensi data; brand; serta stack final.

## 3. Masalah dan peluang — hipotesis proyek

Sebagai hipotesis awal, sebagian orang mungkin kesulitan menyatukan informasi keuangan, melihat kemajuan terhadap tujuan, dan menentukan langkah selanjutnya. Aplikasi ini dapat membantu dengan menyajikan informasi secara terstruktur dan menjelaskan panduan berdasarkan data yang tersedia.

Hipotesis ini **belum tervalidasi melalui riset pengguna**. Jangan menganggapnya sebagai temuan penelitian atau menambahkan klaim pemasaran tentang pengguna tanpa bukti.

## 4. Tujuan produk — usulan

1. Membantu pengguna mengatur dan memahami informasi keuangan pribadinya.
2. Membantu pengguna menetapkan dan memantau tujuan keuangan.
3. Menyajikan panduan yang relevan, transparan, dan dapat ditinjau pengguna.
4. Membangun pengalaman yang mudah dipahami, inklusif, dan menghormati sensitivitas data keuangan.

Keberhasilan produk dan metrik pengukurannya masih perlu ditentukan bersama tim.

## 5. Pengalaman pengguna yang dibayangkan

1. Pengguna memahami tujuan aplikasi sebelum diminta mengisi data pribadi.
2. Pengguna masuk atau mencoba mode demo, sesuai keputusan tim.
3. Pengguna mengatur preferensi dasar dan mengisi data minimum yang diperlukan untuk fitur yang dipilih.
4. Dashboard menunjukkan informasi yang tersedia serta data yang belum lengkap—tanpa menganggap data yang hilang sebagai nol.
5. Pengguna membuat atau meninjau satu tujuan.
6. Pengguna membaca rencana atau berinteraksi dengan assistant jika fitur tersebut termasuk dalam MVP.
7. Pengguna dapat melihat penjelasan/asumsi yang disediakan sistem, memperbaiki input, dan memilih sendiri apakah akan mengikuti langkah yang disarankan.
8. Pengguna dapat mengelola preferensi dan kontrol privasi yang benar-benar didukung aplikasi.

## 6. Kandidat area produk

Daftar berikut adalah **ide untuk dibahas**, bukan daftar fitur yang sudah disetujui.

| Area | Tujuan | Status awal |
|---|---|---|
| Onboarding dan preferensi | Menjelaskan produk, memilih preferensi dasar, dan meminta data yang memang diperlukan. | Usulan MVP; field dan consent belum ditentukan. |
| Dashboard | Menampilkan ringkasan, kemajuan tujuan, dan tindakan yang relevan. | Usulan MVP; metrik/rumus TBD. |
| Tujuan keuangan | Membuat, melihat, dan memperbarui tujuan. | Usulan MVP; kategori dan aturan belum ditentukan. |
| Rencana personal | Menampilkan rekomendasi/langkah berikutnya beserta konteks yang tersedia. | Kandidat MVP; perlu keputusan batas panduan dan aturan domain. |
| Assistant percakapan | Memungkinkan pengguna bertanya dan menerima respons yang terkait dengan konteksnya. | Kandidat MVP; konfirmasi apakah ini fitur inti. |
| Profil dan privasi | Mengelola preferensi dan kontrol atas informasi pengguna sesuai kemampuan backend. | Usulan jika akun/data personal disimpan. |
| Anggaran/transaksi | Melihat pengeluaran dan aktivitas terperinci. | Belum termasuk sampai sumber data dan manfaatnya dikonfirmasi. |
| Koneksi bank/investasi | Mengimpor data dari lembaga keuangan. | Tidak diasumsikan untuk MVP; memerlukan keputusan dan tinjauan terpisah. |

## 7. Batasan produk dan prinsip kepercayaan

- Jangan menjanjikan hasil keuangan, imbal hasil, penghematan, atau keberhasilan tujuan.
- Jangan mengarang saldo, metrik, formula, sumber data, atau alasan rekomendasi.
- Bedakan dengan jelas **fakta**, **input pengguna**, **data contoh**, dan **panduan yang dihasilkan AI**.
- Jika data atau asumsi tidak tersedia, tampilkan status tidak diketahui atau minta klarifikasi; jangan menutupinya dengan angka contoh.
- Semua angka pada mockup harus ditandai sebagai **Data contoh** atau label setara.
- Jangan membuat klaim seperti “terenkripsi”, “dihapus permanen”, atau “tidak digunakan untuk AI” sebelum perilaku sistem dan kata-katanya dikonfirmasi.
- Jangan menambahkan integrasi bank, pembelian/penjualan produk keuangan, pembayaran, atau eksekusi transaksi tanpa keputusan eksplisit tim.
- Naskah privasi, disclaimer, dan batas penggunaan AI harus disetujui pemilik produk serta pihak yang sesuai sebelum dipakai sebagai teks final.

## 8. Rekomendasi teknologi awal

Pilihan berikut mengikuti rekomendasi diskusi awal dan **belum dianggap keputusan final**.

| Bagian | Rekomendasi awal | Catatan |
|---|---|---|
| Frontend | **Next.js + React + TypeScript** | Cocok sebagai fondasi web yang dapat berkembang. Gunakan komponen yang dapat dipakai ulang dan desain responsif. React + TypeScript SPA juga masuk akal bila tim ingin prototipe yang lebih sederhana. |
| Styling/UI | Design tokens dan komponen aksesibel; Tailwind CSS opsional | Pilih pendekatan yang paling dikuasai tim. Jangan menganggap library UI tertentu wajib. |
| Backend | **Python + FastAPI** | Rekomendasi awal untuk produktivitas dan kemungkinan integrasi data/AI. Rust dapat dipilih jika pengalaman tim atau kebutuhan performa memang mendukungnya. |
| Database | **PostgreSQL** | Rekomendasi awal untuk aplikasi multi-user dengan data terstruktur. MySQL juga pilihan valid bila lebih sesuai pengalaman tim. SQLite lebih cocok untuk prototipe lokal atau penggunaan sederhana, bukan asumsi default untuk layanan multi-user produksi. |
| Arsitektur | Mulai dari satu aplikasi backend modular | Hindari microservices sebelum ada kebutuhan nyata. Perhitungan yang penting harus punya aturan jelas dan pengujian. |

**Catatan:** Untuk tahap frontend sekarang, jangan membangun integrasi backend atau menetapkan kontrak API yang belum disepakati. Gunakan data mock yang ditandai jelas dan dapat diganti dengan data API nantinya.

## 9. Panduan kerja untuk Opencode

Saat mengerjakan repository proyek ini:

1. Gunakan file ini sebagai konteks arah produk, dan baca `frontend-requirements.md` sebelum membangun layar atau alur frontend.
2. Anggap label **Usulan**, **TBD**, **Kandidat**, dan **Open point** sebagai hal yang belum disetujui. Jangan diam-diam mengubahnya menjadi keputusan produk.
3. Jika diperlukan agar prototipe bisa berjalan, pilih asumsi teknis yang paling sederhana dan mudah diganti; catat asumsi tersebut di dokumentasi atau komentar yang relevan.
4. Jangan membuat rumus, rekomendasi finansial, atau data personal fiktif seolah-olah nyata. Untuk demo, gunakan data sintetis dengan label yang terlihat.
5. Jangan menyimpan secret/API key di kode frontend atau mengirim data ke layanan eksternal yang belum dipilih tim.
6. Pisahkan tampilan dari sumber data dan aturan domain agar mock data dapat diganti tanpa menulis ulang seluruh UI.
7. Implementasikan komponen reusable, state loading/empty/error/success, layout responsif, serta aksesibilitas dasar sejak awal.
8. Buat perubahan secara bertahap: jelaskan file/fitur yang akan disentuh, implementasikan satu bagian kecil, lalu jalankan pemeriksaan yang tersedia (lint, typecheck, test, atau build).
9. Hindari menambahkan scope baru, dependensi besar, atau integrasi eksternal tanpa alasan dan catatan yang jelas.
10. Perbarui dokumen ini dan/atau `frontend-requirements.md` ketika keputusan tim mengubah arah atau scope; jangan menghapus penanda TBD sebelum keputusan benar-benar dibuat.

## 10. Tahapan pengembangan yang disarankan

### Tahap 1 — Konfirmasi arah

- Sepakati target pengguna, negara/locale, tujuan MVP, dan apakah hasilnya prototipe atau aplikasi fungsional.
- Tentukan data yang diminta, metrik yang ditampilkan, dan batas assistant.
- Pilih layar yang benar-benar masuk ke versi pertama.

### Tahap 2 — Desain Stitch

- Buat alur dan layar utama, termasuk variasi desktop dan mobile.
- Gunakan placeholder dan data contoh berlabel.
- Tinjau struktur navigasi, formulir, visualisasi, dan state bersama tim.

### Tahap 3 — Implementasi frontend

- Siapkan fondasi project, routing, design tokens, komponen, dan layout responsif.
- Implementasikan layar yang telah disepakati menggunakan mock data.
- Tambahkan validasi input dan state loading, empty, error, dan success.

### Tahap 4 — Integrasi backend dan pengujian

- Sepakati kontrak API dan kepemilikan perhitungan sebelum integrasi.
- Ganti data mock dengan data backend secara bertahap.
- Uji alur utama, aksesibilitas, format mata uang/tanggal, keamanan tampilan, dan responsivitas.

## 11. Keputusan tim yang paling penting

Sebelum scope MVP dibekukan, tim sebaiknya memutuskan:

1. Siapa pengguna utama dan di negara/region mana aplikasi akan digunakan?
2. Apakah target pertama adalah prototype Stitch, prototype frontend interaktif, atau produk dengan backend?
3. Data apa yang dimasukkan pengguna dan dari mana data tersebut berasal?
4. Metrik keuangan apa yang ditampilkan, serta siapa yang menetapkan dan menguji rumusnya?
5. Apakah tujuan keuangan termasuk fitur inti? Apa field dan aturan progresnya?
6. Apakah assistant percakapan inti produk? Panduan jenis apa yang boleh diberikannya?
7. Apakah produk berbasis akun atau menyediakan mode demo?
8. Apa persyaratan privasi, retensi, penghapusan, dan consent yang berlaku?
9. Bahasa, brand, mata uang, browser, dan target aksesibilitas apa yang harus didukung?

Rincian pertanyaan dapat diperluas atau dipangkas setelah diskusi tim. Untuk persyaratan frontend dan acceptance criteria yang lebih lengkap, lihat `frontend-requirements.md`.

---

## Cara memperbarui dokumen ini

- Ganti teks di bagian **Usulan** setelah tim menyepakatinya.
- Ubah status menjadi **Diputuskan** hanya jika ada keputusan nyata.
- Hapus atau pindahkan fitur yang ditolak ke bagian “Tidak termasuk”.
- Catat tanggal/versi dan keputusan penting di bawah ini agar perubahan arah mudah dilacak.

### Riwayat perubahan

| Versi | Tanggal | Perubahan |
|---|---|---|
| 0.1 | 2026-10-02 | Draft awal untuk memberi konteks proyek kepada tim dan Opencode. |
