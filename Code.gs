/**
 * Fungsi utama Web App (doPost) - Menerima data dari Streamlit,
 * membuat salinan template berdasarkan ID yang diterima, mengisi salinan,
 * dan mengembalikan status beserta URL dokumen baru.
 * @param {Object} e Objek event Apps Script yang berisi data POST.
 * @return {ContentService.TextOutput} Respons JSON ke Streamlit.
 */
function doPost(e) {
  var responseJson = {}; // Objek untuk respons

  try {
    Logger.log("Menerima permintaan POST...");
    // 1. Parse data JSON yang masuk dari Streamlit
    var payload = JSON.parse(e.postData.contents);
    Logger.log("Payload diterima: " + JSON.stringify(payload));

    var templateId = payload.google_doc_id; // Ambil ID template dari payload
    var dataToFill = payload.data_to_fill;   // Ambil data sebenarnya dari payload

    // Validasi input dasar
    if (!templateId || typeof templateId !== 'string') {
      throw new Error("Payload JSON harus menyertakan 'google_doc_id' (string).");
    }
    if (!dataToFill || typeof dataToFill !== 'object') {
      throw new Error("Payload JSON harus menyertakan 'data_to_fill' (object).");
    }
    Logger.log("Payload valid. ID Template: " + templateId);

    // 2. Tentukan folder tujuan (GANTI DENGAN ID FOLDER ANDA)
    var destinationFolderId = '1JujV6g6HwH4KJh05iHzU83n-UFJRbXhq';
    var folder = DriveApp.getFolderById(destinationFolderId);
    if (!folder) {
        throw new Error("Folder tujuan Google Drive dengan ID '" + destinationFolderId + "' tidak ditemukan atau tidak dapat diakses.");
    }
    Logger.log("Folder tujuan ditemukan: " + folder.getName());

    // 3. Buat nama file baru
    var baseName = dataToFill.Title || "Dokumen Baru Tanpa Judul";
    // Tambahkan timestamp agar nama file unik
    var timestamp = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy-MM-dd HH:mm:ss");
    var newFileName = baseName + " - " + timestamp;
    Logger.log("Nama file baru: " + newFileName);

    // 4. Buat SALINAN dari template yang ID-nya dikirimkan
    var templateFile = DriveApp.getFileById(templateId);
    if (!templateFile) {
        throw new Error("Template Google Doc dengan ID '" + templateId + "' tidak ditemukan atau tidak dapat diakses.");
    }
    var newFile = templateFile.makeCopy(newFileName, folder);
    var newDocId = newFile.getId();
    var newDocUrl = newFile.getUrl();
    Logger.log("Salinan template berhasil dibuat. ID Baru: " + newDocId);

    // 5. Panggil fungsi inti untuk mengisi placeholder di DOKUMEN SALINAN
    fillTemplate(newDocId, dataToFill); // Kirim ID salinan

    // 6. Siapkan respons sukses
    responseJson = {
      "status": "success",
      "message": "Dokumen baru berhasil dibuat dan diisi dari template.",
      "docUrl": newDocUrl // Kembalikan URL dokumen BARU
    };
    Logger.log("Proses berhasil. Mengirim respons sukses.");

  } catch (error) {
    // 7. Jika terjadi kesalahan, siapkan respons error
    var errorMessage = "Error di Apps Script: " + error.message + (error.lineNumber ? " di baris " + error.lineNumber : "") + ". Detail: " + error.stack;
    Logger.log("Terjadi Error: " + errorMessage); // Log error untuk debugging
    responseJson = {
      "status": "error",
      "message": errorMessage
    };
  }

  // 8. Kirim kembali respons JSON ke Streamlit
  return ContentService
    .createTextOutput(JSON.stringify(responseJson))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * Fungsi inti untuk mengisi placeholder di dokumen Google Docs.
 * @param {string} docId ID dokumen yang akan diisi (salinan).
 * @param {Object} data Data JSON (hanya bagian 'data_to_fill') untuk placeholder.
 */
function fillTemplate(docId, data) {
  var doc = DocumentApp.openById(docId);
  if (!doc) {
      // Ini seharusnya tidak terjadi jika penyalinan berhasil, tapi sebagai pengaman
      Logger.log("Error Kritis: Gagal membuka dokumen salinan dengan ID '" + docId + "' untuk diisi.");
      throw new Error("Gagal membuka dokumen salinan dengan ID '" + docId + "'.");
  }
  var body = doc.getBody();
  Logger.log("Memulai proses penggantian placeholder untuk dokumen: " + doc.getName());

  // --- Penanganan Tabel Dinamis 'Bukti_BA' ---
  if (data.Bukti_BA && Array.isArray(data.Bukti_BA) && data.Bukti_BA.length > 0) {
    Logger.log("Mencoba mengisi tabel dinamis 'Bukti_BA'...");
    const firstPlaceholderElement = body.findText('{{Bukti_BA_NO}}');
    if (firstPlaceholderElement) {
      Logger.log("Placeholder '{{Bukti_BA_NO}}' ditemukan.");
      var element = firstPlaceholderElement.getElement();
      var parent = element.getParent(); // Paragraph
      if (parent && parent.getType() === DocumentApp.ElementType.PARAGRAPH) parent = parent.getParent(); // TableCell
      if (parent && parent.getType() === DocumentApp.ElementType.TABLE_CELL) var templateRow = parent.getParent(); // TableRow

      if (templateRow && templateRow.getType() === DocumentApp.ElementType.TABLE_ROW) {
        Logger.log("Baris template tabel ditemukan.");
        var table = templateRow.getParent(); // Table
        var templateRowIndex = table.getChildIndex(templateRow);

        data.Bukti_BA.forEach((rowData, index) => {
          Logger.log("Menyalin dan mengisi baris ke-" + (index + 1) + " untuk tabel Bukti_BA.");
          var newRow = templateRow.copy();
          table.insertTableRow(templateRowIndex + index + 1, newRow);
          newRow.replaceText('{{Bukti_BA_NO}}', rowData.NO || '');
          newRow.replaceText('{{Bukti_BA_OBJEK}}', rowData.OBJEK || '');
          // Pastikan jumlah dikonversi ke String
          newRow.replaceText('{{Bukti_BA_JUMLAH}}', String(rowData.JUMLAH || ''));
          newRow.replaceText('{{Bukti_BA_DETAIL}}', rowData.DETAIL || '');
        });
        Logger.log("Menghapus baris template asli tabel Bukti_BA.");
        templateRow.removeFromParent();
      } else {
         Logger.log("Peringatan: Placeholder tabel '{{Bukti_BA_NO}}' ditemukan, tetapi struktur induknya bukan baris tabel.");
      }
    } else {
       Logger.log("Peringatan: Placeholder tabel '{{Bukti_BA_NO}}' tidak ditemukan. Lewati pengisian tabel Bukti_BA.");
    }
  } else {
    Logger.log("Tidak ada data tabel 'Bukti_BA' atau formatnya salah. Lewati pengisian tabel.");
  }

  // --- Penanganan Placeholder Standar & Daftar Bernomor ---
  Logger.log("Memulai penggantian placeholder teks standar...");
  var replacementCount = 0;
  for (var key in data) {
    // Lewati data tabel karena sudah ditangani
    if (key === 'Bukti_BA') continue;

    var placeholder = '{{' + key + '}}'; // Pastikan format ini konsisten
    var value = data[key];
    // Konversi nilai null/undefined/angka/boolean ke string agar replaceText tidak error
    var valueString = (value === null || typeof value === 'undefined') ? '' : String(value);

    // Penanganan khusus untuk daftar bernomor dari 'Alasan_detail'
    if (key === 'Alasan_detail' && typeof valueString === 'string' && valueString.includes(';\n')) {
      Logger.log("Mencoba mengisi daftar bernomor untuk 'Alasan_detail'...");
      var searchResult = body.findText(placeholder);
      if (searchResult) {
        Logger.log("Placeholder '{{Alasan_detail}}' ditemukan.");
        var listItemElement = searchResult.getElement().getParent(); // Dapatkan elemen ListItem
        // Validasi apakah benar-benar ListItem
        if (listItemElement && listItemElement.getType() === DocumentApp.ElementType.LIST_ITEM) {
          var listIndex = body.getChildIndex(listItemElement);
          listItemElement.removeFromParent(); // Hapus item placeholder

          var reasons = valueString.split(';\n');
          Logger.log("Memecah Alasan_detail menjadi " + reasons.length + " item.");
          // Sisipkan dari belakang agar urutan benar
          for (var i = reasons.length - 1; i >= 0; i--) {
            var cleanReason = reasons[i].trim();
            if (cleanReason) {
              Logger.log("Menyisipkan item daftar: " + cleanReason);
              // Masukkan sebagai ListItem baru dan set tipe glyph
              body.insertListItem(listIndex, cleanReason).setGlyphType(DocumentApp.GlyphType.NUMBER);
            }
          }
          replacementCount++;
        } else {
             Logger.log("Peringatan: Placeholder 'Alasan_detail' ditemukan, tetapi induknya bukan ListItem. Melakukan replaceText biasa.");
             if (body.replaceText(placeholder, valueString) > 0) replacementCount++;
        }
      } else {
          Logger.log("Peringatan: Placeholder '{{Alasan_detail}}' tidak ditemukan.");
      }
    } else {
      // Ganti placeholder teks biasa
      // body.replaceText mengembalikan jumlah penggantian yang dilakukan
      var count = body.replaceText(placeholder, valueString);
      if (count > 0) {
        // Logger.log("Mengganti '" + placeholder + "' dengan '" + valueString.substring(0, 50) + "...'"); // Log penggantian (opsional, bisa sangat verbose)
        replacementCount += count;
      } else {
        // Log jika placeholder tidak ditemukan (kecuali untuk yang hasil kalkulasi)
        if (!key.includes('_CALCULATED')) { // Jangan log warning untuk placeholder hasil kalkulasi
             Logger.log("Peringatan: Placeholder '" + placeholder + "' tidak ditemukan di dokumen.");
        }
      }
    }
  }
  Logger.log("Total penggantian placeholder teks standar: " + replacementCount);

  doc.saveAndClose(); // Simpan dan tutup dokumen salinan
  Logger.log("Pengisian placeholder selesai dan dokumen disimpan untuk: " + doc.getName());
}

// --- Fungsi runTest (Opsional untuk Pengujian Internal) ---
// Fungsi ini TIDAK akan dipanggil oleh Web App, hanya untuk testing dari editor
function runTest() {
  Logger.log("Memulai pengujian internal dengan membuat salinan...");
  var testPayload = {
    "google_doc_id": "1bvOMTAZdfD_GbA8zKf7UoySk5tzz1D-oW7Uod_1hXws", // ID Template Asli
    "data_to_fill": {
        // --- Letakkan data JSON lengkap Anda di sini untuk pengujian ---
        // Contoh data minimal:
        "CC": "Uji Coba CC",
        "Jabatan_penerima": "Uji Coba Jabatan Penerima",
        "Title": "Uji Coba Pengadaan",
        "Kenapa": "Uji coba justifikasi.",
        "BA": "TEST/BA/001",
        "Isi_BA": "Ini adalah ringkasan uji coba Isi BA.",
        "inti_BA": "Inti BA Uji Coba.",
        "Bukti_BA": [
            {"NO": "T1", "OBJEK": "Objek Uji 1", "JUMLAH": "10", "DETAIL": "Detail uji coba baris 1."},
            {"NO": "T2", "OBJEK": "Objek Uji 2", "JUMLAH": "5", "DETAIL": "Detail uji coba baris 2."}
        ],
        "Alasan": "Ini adalah alasan pentingnya uji coba.",
        "Budget_2025": 50000000,
        "Terpakai": 5000000,
        "Usulan_anggaran": 10000000,
        "Anggaran_kalimat": "Sepuluh Juta Rupiah (Uji Coba)",
        "Pos_anggaran": "TEST/POS/01",
        "Tanggal": Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "dd MMMM yyyy"),
        "RKAP_2025": 1000000000,
        "Nilai_Kontrak_PO_2025": 500000000,
        "PR": 100000000,
        "Budget_pembuatan_RAB_dan_RKS": 50000000,
        "Jabatan_CC": "Uji Coba Jabatan CC",
        "Pembelian": "Barang Uji Coba",
        "Jumlah_Pembelian": 15,
        "Satuan_Pembelian": "Buah",
        "Alasan_detail": "Alasan detail A;\nAlasan detail B;\nAlasan detail C (uji coba)."
    }
  };

  // Lakukan perhitungan manual untuk data uji coba (karena runTest tidak memanggil perform_calculations Python)
  testPayload.data_to_fill["Sisa_anggaran_proyek"] = testPayload.data_to_fill.Budget_2025 - testPayload.data_to_fill.Terpakai - testPayload.data_to_fill.Usulan_anggaran;
  var sisa_dept = testPayload.data_to_fill.RKAP_2025 - (testPayload.data_to_fill.Nilai_Kontrak_PO_2025 + testPayload.data_to_fill.PR + testPayload.data_to_fill.Budget_pembuatan_RAB_dan_RKS);
  testPayload.data_to_fill["Sisa_anggaran_departemen"] = sisa_dept;
  testPayload.data_to_fill["Persen_RKAP"] = (sisa_dept / testPayload.data_to_fill.RKAP_2025 * 100).toFixed(2) + '%';


  // Simulasikan objek event 'e'
  var mockEvent = { postData: { contents: JSON.stringify(testPayload) } };

  // Panggil doPost dengan data simulasi
  Logger.log("Memanggil doPost dengan data uji coba...");
  var result = doPost(mockEvent);

  // Log hasil yang akan dikirim kembali
  Logger.log("Hasil Pengujian (Respons JSON):");
  Logger.log(result.getContent());
}