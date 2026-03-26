var SPREADSHEET_ID = "YOUR_SPREADSHEET_ID_HERE";

function doGet(e) {
  var action = e.parameter.action;
  var name   = e.parameter.name || "";
  Logger.log("=== ACTION: " + action + " | NAME: " + name + " ===");

  if (action === "getStudents")   return getStudentsData();
  if (action === "getDashboard")  return getDashboardData();
  if (action === "getStudent")    return getSingleStudentData(name);
  if (action === "test") {
    return jsonOut({ status: "ok", message: "API berjalan!", timestamp: new Date().toISOString() });
  }

  return jsonOut({ error: "Invalid action", received: action });
}

// GET ALL STUDENTS
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

// DASHBOARD
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

// HELPERS
function isCellChecked(cell) {
  if (cell === true)  return true;
  if (cell === false) return false;
  var s = String(cell).trim().toLowerCase();
  return (s === "true" || s === "✓" || s === "✅" || s === "✔" || s === "x" || s === "v" || s === "1");
}

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