# Feri FLAC Archive

Addon BitChord yang mencari item audio di Internet Archive dan hanya memilih file `.flac` untuk mode FLAC Lossless.

## Jalankan lokal
1. Install Python 3.10 atau lebih baru.
2. Jalankan `pip install -r requirements.txt`.
3. Jalankan `python server.py`.
4. Tes `http://127.0.0.1:8080/manifest.json`, `/health`, dan `/search?q=bach`.

## Pasang ke BitChord
Deploy project ini ke layanan hosting Python yang memberi URL HTTPS publik.
Di BitChord buka **Settings → Sources → Add an addon**, lalu masukkan:
`https://ALAMAT-HOSTING/manifest.json`

## Catatan penting
- Addon hanya memilih file yang namanya berakhiran `.flac`; MP3 tidak dikonversi menjadi FLAC.
- Internet Archive berisi materi yang beragam. Gunakan hanya rekaman yang berstatus domain publik atau memang memiliki izin distribusi/streaming.
- Tidak semua item menyediakan metadata sample rate dan bit depth. Jika tidak ada, respons memakai nilai perkiraan default untuk metadata tersebut. Itu bukan bukti spesifikasi audio sebenarnya.
- Addon ini versi awal dan belum mengaktifkan verifikasi `bitchordAuth` terbaru BitChord. Ikuti dokumentasi resmi BitChord untuk menambahkan verifier sebelum dipublikasikan luas.
- Ketersediaan dan pemutaran tetap bergantung pada metadata serta server file Internet Archive.
