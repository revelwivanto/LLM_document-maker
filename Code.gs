/**
 * Fungsi utama Web App (doPost) - Menerima DAFTAR data dari Streamlit,
 * membuat salinan untuk SETIAP template yang diterima, mengisi salinannya,
 * dan mengembalikan status beserta URL untuk SETIAP dokumen baru.
 * @param {Object} e Objek event Apps Script yang berisi data POST.
 * @return {ContentService.TextOutput} Respons JSON ke Streamlit.
 */
function doPost(e) {
  var allResults = []; // Array untuk menampung hasil dari setiap pembuatan dokumen
  var payload;

  try {
    Logger.log("Menerima permintaan POST...");
    // 1. Parse data JSON yang masuk dari Streamlit
    payload = JSON.parse(e.postData.contents);
    Logger.log("Payload diterima: " + JSON.stringify(payload));

    // 2. Validasi payload baru (mengharapkan array 'documents')
    if (!payload.documents || !Array.isArray(payload.documents)) {
      throw new Error("Payload JSON harus menyertakan array 'documents'.");
    }
    
    // 3. Tentukan folder tujuan (GANTI DENGAN ID FOLDER ANDA)
    var destinationFolderId = '1JujV6g6HwH4KJh05iHzU83n-UFJRbXhq';
    var folder = DriveApp.getFolderById(destinationFolderId);
    if (!folder) {
      throw new Error("Folder tujuan Google Drive dengan ID '" + destinationFolderId + "' tidak ditemukan atau tidak dapat diakses.");
    }
    Logger.log("Folder tujuan ditemukan: " + folder.getName());

    var timestamp = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy-MM-dd HH:mm:ss");

    // 4. Loop melalui setiap dokumen yang diminta dalam payload
    for (var i = 0; i < payload.documents.length; i++) {
      var docJob = payload.documents[i];
      var templateId = docJob.google_doc_id;
      var dataToFill = docJob.data_to_fill;
      

      try {
        // Validasi input dasar untuk setiap item
        if (!templateId || typeof templateId !== 'string') {
          throw new Error("Item dokumen ke-" + i + " tidak memiliki 'google_doc_id' (string) yang valid.");
        }
        if (!dataToFill || typeof dataToFill !== 'object') {
          throw new Error("Item dokumen ke-" + i + " tidak memiliki 'data_to_fill' (object) yang valid.");
        }
        Logger.log("Memproses item ke-" + i + ". ID Template: " + templateId);

        // 5. Buat nama file baru
        var baseName = templateId || ("Dokumen Baru Tanpa Judul " + (i+1));
        var newFileName = baseName + " - " + timestamp;
        Logger.log("Nama file baru: " + newFileName);

        // 6. Buat SALINAN dari template
        var templateFile = DriveApp.getFileById(templateId);
        if (!templateFile) {
          throw new Error("Template Google Doc dengan ID '" + templateId + "' tidak ditemukan atau tidak dapat diakses.");
        }
        var newFile = templateFile.makeCopy(newFileName, folder);
        var newDocId = newFile.getId();
        var newDocUrl = newFile.getUrl();
        Logger.log("Salinan template berhasil dibuat. ID Baru: " + newDocId);

        // 7. Panggil fungsi inti untuk mengisi placeholder di DOKUMEN SALINAN
        fillTemplate(newDocId, dataToFill); // Kirim ID salinan

        // 8. Tambahkan hasil sukses ke array
        allResults.push({
          "status": "success",
          "message": "Dokumen baru berhasil dibuat dan diisi.",
          "docUrl": newDocUrl,
          "fileName": newFileName,
          "templateId": templateId
        });
        Logger.log("Proses berhasil untuk item ke-" + i);

      } catch (innerError) {
        // 9. Jika terjadi kesalahan untuk SATU dokumen, log dan tambahkan ke hasil
        var innerErrorMessage = "Error memproses item ke-" + i + " (Template ID: " + (templateId || 'INVALID') + "): " + innerError.message + (innerError.lineNumber ? " di baris " + innerError.lineNumber : "") + ". Detail: " + innerError.stack;
        Logger.log("Terjadi Error Internal: " + innerErrorMessage);
        allResults.push({
          "status": "error",
          "message": innerErrorMessage,
          "templateId": (templateId || 'INVALID')
        });
      }
    } // Akhir dari loop for

    // 10. Kirim kembali respons JSON ke Streamlit
    Logger.log("Semua pekerjaan selesai. Mengirim respons gabungan.");
    return ContentService
      .createTextOutput(JSON.stringify({
        "status": "completed",
        "results": allResults // Kembalikan array berisi semua hasil
      }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    // 11. Jika terjadi kesalahan GLOBAL (misal: JSON tidak valid), siapkan respons error
    var errorMessage = "Error Global di Apps Script: " + error.message + (error.lineNumber ? " di baris " + error.lineNumber : "") + ". Detail: " + error.stack;
    Logger.log("Terjadi Error Global: " + errorMessage);
    var responseJson = {
      "status": "error",
      "message": errorMessage,
      "results": allResults // Kembalikan hasil yang mungkin sudah diproses sebelum error
    };
    return ContentService
      .createTextOutput(JSON.stringify(responseJson))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Fungsi inti untuk mengisi placeholder di dokumen Google Docs.
 * (FUNGSI INI TIDAK PERLU DIUBAH)
 * @param {string} docId ID dokumen yang akan diisi (salinan).
 * @param {Object} data Data JSON (hanya bagian 'data_to_fill') untuk placeholder.
 */
function fillTemplate(docId, data) {
  var doc = DocumentApp.openById(docId);
  if (!doc) {
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

  // --- Penanganan Tabel Dinamis 'Pembelian' ---
  if (data.Pembelian && Array.isArray(data.Pembelian) && data.Pembelian.length > 0) {
    Logger.log("Mencoba mengisi tabel dinamis 'Pembelian'...");
    const firstPlaceholderElement = body.findText('{{Pembelian_NO}}');
    if (firstPlaceholderElement) {
      Logger.log("Placeholder '{{Pembelian_NO}}' ditemukan.");
      var element = firstPlaceholderElement.getElement();
      var parent = element.getParent(); // Paragraph
      if (parent && parent.getType() === DocumentApp.ElementType.PARAGRAPH) parent = parent.getParent(); // TableCell
      if (parent && parent.getType() === DocumentApp.ElementType.TABLE_CELL) var templateRow = parent.getParent(); // TableRow

      if (templateRow && templateRow.getType() === DocumentApp.ElementType.TABLE_ROW) {
        Logger.log("Baris template tabel ditemukan.");
        var table = templateRow.getParent(); // Table
        var templateRowIndex = table.getChildIndex(templateRow);

        data.Pembelian.forEach((rowData, index) => {
          Logger.log("Menyalin dan mengisi baris ke-" + (index + 1) + " untuk tabel Pembelian.");
          var newRow = templateRow.copy();
          table.insertTableRow(templateRowIndex + index + 1, newRow);
          
          // Pastikan key (rowData.NO, rowData.OBJEK) cocok dengan data JSON Anda
          newRow.replaceText('{{Pembelian_NO}}',     (rowData.NO || ''));
          newRow.replaceText('{{Pembelian_OBJEK}}',  (rowData.OBJEK || ''));
          newRow.replaceText('{{Pembelian_JUMLAH}}', String(rowData.JUMLAH || ''));
          newRow.replaceText('{{Pembelian_UNIT}}',   String(rowData.UNIT || ''));
          newRow.replaceText('{{Pembelian_HARGA}}',   String(rowData.HARGA || ''));
          newRow.replaceText('{{Pembelian_DETAIL}}',   String(rowData.DETAIL || ''));
        });
        Logger.log("Menghapus baris template asli tabel Pembelian.");
        templateRow.removeFromParent();
      } else {
        Logger.log("Peringatan: Placeholder tabel '{{Pembelian_NO}}' ditemukan, tetapi struktur induknya bukan baris tabel.");
      }
    } else {
      Logger.log("Peringatan: Placeholder tabel '{{Pembelian_NO}}' tidak ditemukan. Lewati pengisian tabel Pembelian.");
    }
  } else {
    Logger.log("Tidak ada data tabel 'Pembelian' atau formatnya salah. Lewati pengisian tabel.");
  }

  // --- Penanganan Placeholder Standar & Daftar Bernomor ---
  Logger.log("Memulai penggantian placeholder teks standar...");
  var replacementCount = 0;
  for (var key in data) {
    if (key === 'Bukti_BA' || key === 'Pembelian') continue; // Lewati data tabel

    var placeholder = '{{' + key + '}}';
    var value = data[key];
    var valueString = (value === null || typeof value === 'undefined') ? '' : String(value);

    // Penanganan numbering
    if (key === 'Alasan_detail' && typeof valueString === 'string' && valueString.includes(';\n')) {
      Logger.log("Mencoba mengisi daftar bernomor untuk 'Alasan_detail'...");
      var searchResult = body.findText(placeholder);
      if (searchResult) {
        Logger.log("Placeholder '{{Alasan_detail}}' ditemukan.");
        var listItemElement = searchResult.getElement().getParent(); // Dapatkan elemen ListItem
        if (listItemElement && listItemElement.getType() === DocumentApp.ElementType.LIST_ITEM) {
          var listIndex = body.getChildIndex(listItemElement);
          listItemElement.removeFromParent(); // Hapus item placeholder

          var reasons = valueString.split(';\n');
          Logger.log("Memecah Alasan_detail menjadi " + reasons.length + " item.");
          for (var i = reasons.length - 1; i >= 0; i--) { // Sisipkan dari belakang
            var cleanReason = reasons[i].trim();
            if (cleanReason) {
              Logger.log("Menyisipkan item daftar: " + cleanReason);
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
      var count = body.replaceText(placeholder, valueString);
      if (count > 0) {
        replacementCount += count;
      } else {
        if (!key.includes('_CALCULATED')) {
          Logger.log("Peringatan: Placeholder '" + placeholder + "' tidak ditemukan di dokumen.");
        }
      }
    }
  }
  Logger.log("Total penggantian placeholder teks standar: " + replacementCount);

  doc.saveAndClose();
  Logger.log("Pengisian placeholder selesai dan dokumen disimpan untuk: " + doc.getName());
}

/**
 * --- runTest (Opsional untuk Pengujian Internal) ---
 * (DIMODIFIKASI untuk struktur payload baru)
 */
function runTest() {
  Logger.log("Memulai pengujian internal dengan payload multi-dokumen...");

  // Ini adalah data yang sama dengan sebelumnya, tetapi dibungkus untuk satu dokumen
  var dataDoc1 = {
    "CC": "Uji Coba CC",
    "Jabatan_penerima": "Uji Coba Jabatan Penerima",
    "Title": "Uji Coba Pengadaan (Dok 1)", // Nama diubah agar unik
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
    "Alasan_detail": "Alasan detail A;\nAlasan detail B;\nAlasan detail C (uji coba).",
    // Kalkulasi manual untuk pengujian
    "Sisa_anggaran_proyek": (50000000 - 5000000 - 10000000),
    "Sisa_anggaran_departemen": (1000000000 - (500000000 + 100000000 + 50000000)),
    "Persen_RKAP": ((1000000000 - (500000000 + 100000000 + 50000000)) / 1000000000 * 100).toFixed(2) + '%'
  };

  // Buat data tiruan untuk dokumen kedua
  var dataDoc2 = {
    "Title": "Uji Coba Dokumen Kedua (RAB)",
    "Usulan_anggaran": 12345678, // Hanya beberapa field untuk contoh
    "Anggaran_kalimat": "Dua Belas Juta Tiga Ratus (Uji Coba 2)",
    "Tanggal": Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "dd MMMM yyyy"),
    // ... field lain yang relevan untuk template RAB ...
  };

  var testPayload = {
    // Struktur payload baru: array 'documents'
    "documents": [
      {
        "google_doc_id": "1bvOMTAZdfD_GbA8zKf7UoySk5tzz1D-oW7Uod_1hXws", 
        "data_to_fill": dataDoc1
      }, 
      {
        "google_doc_id": "1D20-ubVxLfP6iGaxZDsmNxGg-MCL2jnsWq8dKd9ZSUA", 
        "data_to_fill": dataDoc2
      },
      {
        "google_doc_id": "1SCpgB0ZXmc5qC1R71r12Dcs6-IrUuVPYBdfz0WVAKng", 
        "data_to_fill": { "Title": "Uji Coba RKS" } 
      }
    ]
  };

  // Simulasikan objek event 'e'
  var mockEvent = { postData: { contents: JSON.stringify(testPayload) } };

  // Panggil doPost dengan data simulasi
  Logger.log("Memanggil doPost dengan data uji coba multi-dokumen...");
  var result = doPost(mockEvent);

  // Log hasil yang akan dikirim kembali
  Logger.log("Hasil Pengujian (Respons JSON):");
  Logger.log(result.getContent());
}