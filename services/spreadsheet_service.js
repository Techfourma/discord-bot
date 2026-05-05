function doGet(e) {
  var action = e.parameter.action;
  var name   = e.parameter.name || "";
  Logger.log("=== ACTION: " + action + " | NAME: " + name + " ===");

  if (action === "getStudents")      return getStudentsData();
  if (action === "getDashboard")     return getDashboardData();
  if (action === "getStudent")       return getSingleStudentData(name);
  if (action === "getPengeluaran")   return getPengeluaranData();
  if (action === "getShareholders")  return getShareholdersData(); // ← BARU
  if (action === "test") {
    return jsonOut({ status: "ok", message: "API berjalan!", timestamp: new Date().toISOString() });
  }

  return jsonOut({ error: "Invalid action", received: action });
}

// ─────────────────────────────────────────────────────────────
// GET ALL STUDENTS
// ─────────────────────────────────────────────────────────────
function getStudentsData() {
  try {
    var sheet = getSheet("DaftarUangKas") || getSheet("DaftarUangkas") || findSheetByKeyword(["DAFTAR", "UANG KAS"]);
    if (!sheet) return errorOut("Sheet tidak ditemukan");

    var data = sheet.getDataRange().getValues();
    Logger.log("Rows: " + data.length + " | Cols: " + (data[0] ? data[0].length : 0));

    if (data.length < 4) return errorOut("Data tidak cukup");

    // Row index 2 (baris ke-3) = header tanggal
    var headerRow = data[2];
    var dateColumns = buildDateColumns(headerRow);

    Logger.log("Date columns found: " + Object.keys(dateColumns).length);
    if (Object.keys(dateColumns).length === 0) {
      Logger.log("Sample headers: " + JSON.stringify(headerRow.slice(0, 10)));
    }

    var students = [];
    // Data mulai baris ke-4 (index 3)
    for (var r = 3; r < data.length; r++) {
      var row  = data[r];
      if (!row[1] || String(row[1]).trim() === "") continue;

      var no   = String(row[0] || "").trim();
      var name = String(row[1]).trim();
      var paid = [], unpaid = [];

      for (var c in dateColumns) {
        var dateStr = dateColumns[c];
        var cell    = row[parseInt(c)];
        Logger.log("  Row " + (r+1) + " Col " + c + " = [" + cell + "] type=" + typeof cell);

        if (isCellChecked(cell)) {
          paid.push(dateStr);
        } else {
          unpaid.push(dateStr);
        }
      }

      students.push({
        no:             no,
        name:           name,
        row:            r + 1,
        paid_dates:     paid.sort(),
        unpaid_dates:   unpaid.sort(),
        total_paid:     paid.length,
        total_unpaid:   unpaid.length
      });
    }

    Logger.log("Students: " + students.length);
    if (students.length > 0) Logger.log("First: " + JSON.stringify(students[0]));

    return successOut({ students: students, count: students.length });

  } catch (err) {
    Logger.log("ERROR: " + err);
    return errorOut("Error: " + err.toString());
  }
}

function getSingleStudentData(queryName) {
  try {
    var sheet = getSheet("DaftarUangKas") || getSheet("DaftarUangkas") || findSheetByKeyword(["DAFTAR", "UANG KAS"]);
    if (!sheet) return errorOut("Sheet tidak ditemukan");

    var data        = sheet.getDataRange().getValues();
    var headerRow   = data[2];
    var dateColumns = buildDateColumns(headerRow);

    var query = queryName.toLowerCase().trim();
    var found = null;

    for (var r = 3; r < data.length; r++) {
      var row  = data[r];
      if (!row[1]) continue;
      var name = String(row[1]).trim();

      if (name.toLowerCase().indexOf(query) >= 0 || query.indexOf(name.toLowerCase().split(" ")[0]) >= 0) {
        var paid = [], unpaid = [];
        for (var c in dateColumns) {
          var cell = row[parseInt(c)];
          if (isCellChecked(cell)) paid.push(dateColumns[c]);
          else unpaid.push(dateColumns[c]);
        }
        found = {
          no:           String(row[0] || "").trim(),
          name:         name,
          paid_dates:   paid.sort(),
          unpaid_dates: unpaid.sort(),
          total_paid:   paid.length,
          total_unpaid: unpaid.length
        };
        break;
      }
    }

    if (!found) return errorOut("Mahasiswa tidak ditemukan: " + queryName);
    return successOut(found);

  } catch (err) {
    return errorOut("Error: " + err.toString());
  }
}

// ─────────────────────────────────────────────────────────────
// GET PENGELUARAN
// Membaca sheet "Pengeluaran" dan mengembalikan semua baris data.
// Struktur sheet:
//   Baris 1 : Judul  "DAFTAR PENGELUARAN"
//   Baris 2 : Header kolom → Tanggal | Nama PIC | Pembelian | Kategori | Harga | Lampiran | Deskripsi
//   Baris 3+ : Data
// ─────────────────────────────────────────────────────────────
function getPengeluaranData() {
  try {
    var sheet = getSheet("Pengeluaran") || findSheetByKeyword(["PENGELUARAN"]);
    if (!sheet) return errorOut("Sheet 'Pengeluaran' tidak ditemukan");

    var data = sheet.getDataRange().getValues();
    Logger.log("Pengeluaran rows: " + data.length);

    // Cari baris header (baris yang mengandung kata "Tanggal" di kolom pertama)
    var headerRowIdx = -1;
    for (var i = 0; i < data.length; i++) {
      var firstCell = String(data[i][0]).trim().toLowerCase();
      if (firstCell === "tanggal") {
        headerRowIdx = i;
        break;
      }
    }

    // Fallback: asumsikan header di baris ke-2 (index 1) seperti di screenshot
    if (headerRowIdx === -1) headerRowIdx = 1;

    Logger.log("Header row index: " + headerRowIdx);

    // Mapping header → index kolom (fleksibel terhadap urutan kolom)
    var headerRow = data[headerRowIdx];
    var colMap = {};
    for (var j = 0; j < headerRow.length; j++) {
      var h = String(headerRow[j]).trim().toLowerCase();
      if (h === "tanggal")   colMap.tanggal   = j;
      if (h === "nama pic")  colMap.nama_pic  = j;
      if (h === "pembelian") colMap.pembelian = j;
      if (h === "kategori")  colMap.kategori  = j;
      if (h === "harga")     colMap.harga     = j;
      if (h === "lampiran")  colMap.lampiran  = j;
      if (h === "deskripsi") colMap.deskripsi = j;
    }
    Logger.log("Column map: " + JSON.stringify(colMap));

    var pengeluaran = [];

    for (var r = headerRowIdx + 1; r < data.length; r++) {
      var row = data[r];

      // Skip baris kosong (cek kolom pembelian atau tanggal)
      var pembelianVal = colMap.pembelian !== undefined ? String(row[colMap.pembelian]).trim() : "";
      var tanggalVal   = colMap.tanggal   !== undefined ? row[colMap.tanggal] : "";
      if (!pembelianVal && !tanggalVal) continue;

      // Format tanggal
      var tanggalStr = "";
      if (tanggalVal) {
        if (tanggalVal instanceof Date) {
          tanggalStr = Utilities.formatDate(tanggalVal, "Asia/Jakarta", "EEEE, dd MMMM yyyy");
        } else {
          tanggalStr = String(tanggalVal).trim();
        }
      }

      // Parse harga — bisa berupa angka langsung atau string "Rp265,000"
      var hargaRaw  = colMap.harga !== undefined ? row[colMap.harga] : 0;
      var hargaNum  = 0;
      if (typeof hargaRaw === "number") {
        hargaNum = hargaRaw;
      } else {
        var cleaned = String(hargaRaw).replace(/[^0-9]/g, "");
        hargaNum = cleaned ? parseInt(cleaned) : 0;
      }

      pengeluaran.push({
        tanggal  : tanggalStr,
        nama_pic : colMap.nama_pic  !== undefined ? String(row[colMap.nama_pic]).trim()  : "",
        pembelian: colMap.pembelian !== undefined ? String(row[colMap.pembelian]).trim() : "",
        kategori : colMap.kategori  !== undefined ? String(row[colMap.kategori]).trim()  : "",
        harga    : hargaNum,
        lampiran : colMap.lampiran  !== undefined ? String(row[colMap.lampiran]).trim()  : "",
        deskripsi: colMap.deskripsi !== undefined ? String(row[colMap.deskripsi]).trim() : "",
      });
    }

    Logger.log("Pengeluaran items: " + pengeluaran.length);
    return successOut({ pengeluaran: pengeluaran, count: pengeluaran.length });

  } catch (err) {
    Logger.log("ERROR getPengeluaran: " + err);
    return errorOut("Error: " + err.toString());
  }
}

// GET SHAREHOLDERS
function getShareholdersData() {
  try {
    var sheet = getSheet("Dashboard") || findSheetByKeyword(["DASHBOARD"]);
    if (!sheet) return errorOut("Sheet 'Dashboard' tidak ditemukan");

    var data = sheet.getDataRange().getValues();
    Logger.log("Dashboard rows for shareholders: " + data.length);

    // Cari baris header tabel Shareholders (mengandung "NAME" dan "FUNDS")
    var headerRowIdx = -1;
    for (var i = 0; i < data.length; i++) {
      var rowText = data[i].join(" ").toUpperCase();
      if (rowText.indexOf("NAME") >= 0 && rowText.indexOf("FUNDS") >= 0) {
        headerRowIdx = i;
        break;
      }
    }

    if (headerRowIdx === -1) {
      return errorOut("Tabel Shareholders tidak ditemukan di sheet Dashboard");
    }

    Logger.log("Shareholders header row: " + headerRowIdx);

    // Mapping kolom dari baris header
    var headerRow = data[headerRowIdx];
    var colName = -1, colFunds = -1, colPercent = -1;
    for (var j = 0; j < headerRow.length; j++) {
      var h = String(headerRow[j]).trim().toUpperCase();
      if (h === "NAME")    colName    = j;
      if (h === "FUNDS")   colFunds   = j;
      if (h === "PERCENT") colPercent = j;
    }

    Logger.log("Cols → NAME:" + colName + " FUNDS:" + colFunds + " PERCENT:" + colPercent);

    if (colName === -1 || colFunds === -1) {
      return errorOut("Kolom NAME atau FUNDS tidak ditemukan");
    }

    var shareholders = [];
    var total_funds  = 0;

    for (var r = headerRowIdx + 1; r < data.length; r++) {
      var row      = data[r];
      var nameVal  = colName  >= 0 ? String(row[colName]).trim()  : "";
      var fundsRaw = colFunds >= 0 ? row[colFunds] : 0;

      // Berhenti jika baris kosong atau keluar dari area tabel
      if (!nameVal) break;

      // Baris TOTAL — simpan sebagai total, jangan masuk list shareholders
      if (nameVal.toUpperCase() === "TOTAL") {
        var totalRaw = typeof fundsRaw === "number" ? fundsRaw : parseFloat(String(fundsRaw).replace(/[^0-9.]/g, "")) || 0;
        total_funds  = totalRaw;
        continue;
      }

      // Parse funds
      var fundsNum = 0;
      if (typeof fundsRaw === "number") {
        fundsNum = fundsRaw;
      } else {
        var cleanedF = String(fundsRaw).replace(/[^0-9]/g, "");
        fundsNum = cleanedF ? parseInt(cleanedF) : 0;
      }

      // Parse percent — bisa berupa number (0.5483) atau string "54.83%"
      var percentNum = 0;
      if (colPercent >= 0) {
        var percentRaw = row[colPercent];
        if (typeof percentRaw === "number") {
          // Google Sheets menyimpan persentase sebagai desimal (0.5483 = 54.83%)
          percentNum = percentRaw <= 1 ? percentRaw * 100 : percentRaw;
        } else {
          var cleanedP = String(percentRaw).replace(/[^0-9.]/g, "");
          percentNum = cleanedP ? parseFloat(cleanedP) : 0;
        }
      }

      shareholders.push({
        name:    nameVal,
        funds:   fundsNum,
        percent: Math.round(percentNum * 100) / 100  // bulatkan 2 desimal
      });
    }

    // Hitung total dari funds jika belum ada
    if (total_funds === 0 && shareholders.length > 0) {
      total_funds = shareholders.reduce(function(sum, s) { return sum + s.funds; }, 0);
    }

    Logger.log("Shareholders found: " + shareholders.length + " | Total: " + total_funds);
    return successOut({
      shareholders: shareholders,
      total_funds:  total_funds,
      count:        shareholders.length
    });

  } catch (err) {
    Logger.log("ERROR getShareholders: " + err);
    return errorOut("Error: " + err.toString());
  }
}

// ─────────────────────────────────────────────────────────────
// DASHBOARD
// ─────────────────────────────────────────────────────────────
function getDashboardData() {
  try {
    var sheet = getSheet("Dashboard") || findSheetByKeyword(["DASHBOARD"]);
    if (!sheet) {
      return successOut({ total_pemasukan: 0, total_pengeluaran: 0, sisa_uang_kas: 0, status: "UNKNOWN" });
    }

    var data   = sheet.getDataRange().getValues();
    var result = { total_pemasukan: 0, total_pengeluaran: 0, sisa_uang_kas: 0, status: "UNKNOWN" };

    for (var i = 0; i < data.length; i++) {
      var rowText = data[i].join(" ").toLowerCase();
      if (rowText.indexOf("total pemasukan")  >= 0) result.total_pemasukan  = parseRupiah(data[i]);
      else if (rowText.indexOf("total pengeluaran") >= 0) result.total_pengeluaran = parseRupiah(data[i]);
      else if (rowText.indexOf("sisa uang kas")     >= 0) result.sisa_uang_kas     = parseRupiah(data[i]);
      else if (rowText.indexOf("status")            >= 0) {
        for (var j = 0; j < data[i].length; j++) {
          var c = String(data[i][j]).toLowerCase();
          if (c.indexOf("aman") >= 0)    { result.status = "AMAN";    break; }
          if (c.indexOf("warning") >= 0) { result.status = "WARNING"; break; }
          if (c.indexOf("bahaya") >= 0)  { result.status = "BAHAYA";  break; }
        }
      }
    }

    return successOut(result);
  } catch (err) {
    return errorOut("Error: " + err.toString());
  }
}

// ─────────────────────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────────────────────

/** Cek apakah cell checkbox dicentang */
function isCellChecked(cell) {
  if (cell === true)  return true;
  if (cell === false) return false;
  var s = String(cell).trim().toLowerCase();
  return (s === "true" || s === "✓" || s === "✅" || s === "✔" || s === "x" || s === "v" || s === "1");
}

/** Bangun map { colIndex: "yyyy-MM-dd" } dari baris header */
function buildDateColumns(headerRow) {
  var cols = {};
  for (var i = 2; i < headerRow.length; i++) {
    var cell = headerRow[i];
    if (!cell) continue;
    var dateStr = parseDateFromHeader(cell);
    if (dateStr) {
      cols[i] = dateStr;
      Logger.log("  ✓ Col " + i + " → " + dateStr);
    } else {
      Logger.log("  ✗ Col " + i + " → cannot parse: [" + cell + "] type=" + typeof cell);
    }
  }
  return cols;
}

function parseDateFromHeader(cell) {
  // Kalau cell adalah Date object dari Sheets
  if (cell instanceof Date) {
    var d = Utilities.formatDate(cell, "Asia/Jakarta", "yyyy-MM-dd");
    Logger.log("Date object: " + d);
    return d;
  }

  var text = String(cell).trim();
  if (!text) return null;

  var monthMap = {
    'january':1,'february':2,'march':3,'april':4,'may':5,'june':6,
    'july':7,'august':8,'september':9,'october':10,'november':11,'december':12,
    'januari':1,'februari':2,'maret':3,'mei':5,'juni':6,
    'juli':7,'agustus':8,'oktober':10,'desember':12
  };

  // "7 March 2026" atau "7 Maret 2026"
  var m = text.match(/(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})/);
  if (m) {
    var mon = monthMap[m[2].toLowerCase()];
    if (mon !== undefined) {
      return Utilities.formatDate(new Date(parseInt(m[3]), mon-1, parseInt(m[1])), "Asia/Jakarta", "yyyy-MM-dd");
    }
  }

  // "7/3/2026"
  m = text.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (m) {
    return Utilities.formatDate(new Date(parseInt(m[3]), parseInt(m[2])-1, parseInt(m[1])), "Asia/Jakarta", "yyyy-MM-dd");
  }

  // "2026-03-07"
  m = text.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (m) return text;

  return null;
}

function parseRupiah(row) {
  for (var i = 0; i < row.length; i++) {
    var c = String(row[i]).replace(/[^0-9-]/g, "");
    if (c && c !== "-") return parseInt(c) || 0;
  }
  return 0;
}

function getSheet(name) {
  try {
    return SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(name);
  } catch(e) { return null; }
}

function findSheetByKeyword(keywords) {
  var sheets = SpreadsheetApp.openById(SPREADSHEET_ID).getSheets();
  for (var i = 0; i < sheets.length; i++) {
    var n = sheets[i].getName().toUpperCase();
    for (var k = 0; k < keywords.length; k++) {
      if (n.indexOf(keywords[k]) >= 0) return sheets[i];
    }
  }
  return null;
}

function jsonOut(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
function successOut(data) { return jsonOut({ success: true,  data: data }); }
function errorOut(msg)     { return jsonOut({ success: false, error: msg  }); }