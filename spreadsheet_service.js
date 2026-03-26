var SPREADSHEET_ID = "YOUR_SPREADSHEET_ID_HERE";

function doGet(e) {
  var action = e.parameter.action;
  Logger.log("Action received: " + action);
  
  if (action == "getStudents") {
    return getStudentsData();
  } else if (action == "getDashboard") {
    return getDashboardData();
  } else if (action == "test") {
    return ContentService.createTextOutput(JSON.stringify({
      status: "ok", 
      message: "API berjalan!",
      timestamp: new Date().toISOString()
    }))
    .setMimeType(ContentService.MimeType.JSON);
  }
  
  return ContentService.createTextOutput(JSON.stringify({
    error: "Invalid action",
    received: action
  }))
  .setMimeType(ContentService.MimeType.JSON);
}

function getStudentsData() {
  try {
    var ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    var sheet = null;
    
    var sheets = ss.getSheets();
    Logger.log("Total sheets: " + sheets.length);
    
    for (var i = 0; i < sheets.length; i++) {
      var sheetName = sheets[i].getName().toUpperCase();
      Logger.log("Checking sheet: " + sheetName);
      if (sheetName.indexOf("DAFTAR") >= 0 || sheetName.indexOf("UANG KAS") >= 0) {
        sheet = sheets[i];
        Logger.log("Found sheet: " + sheet.getName());
        break;
      }
    }
    
    if (!sheet) {
      return errorResponse("Sheet tidak ditemukan");
    }
    
    var data = sheet.getDataRange().getValues();
    Logger.log("Total rows: " + data.length);
    
    if (data.length < 4) {
      return errorResponse("Data tidak cukup");
    }
    
    // Row 3 = header tanggal (index 2)
    var headerRow = data[2];
    var dateColumns = {};
    
    for (var i = 2; i < headerRow.length; i++) {
      var cell = headerRow[i];
      if (cell && isDateColumn(cell)) {
        var date = parseDateFromHeader(cell);
        if (date) {
          dateColumns[i] = date;
        }
      }
    }
    
    Logger.log("Date columns found: " + Object.keys(dateColumns).length);
    
    var students = [];
    
    // Mulai row 4 (index 3)
    for (var rowIdx = 3; rowIdx < data.length; rowIdx++) {
      var row = data[rowIdx];
      if (row.length < 2 || !row[1]) continue;
      
      var no = row[0] ? String(row[0]).trim() : "";
      var name = String(row[1]).trim();
      
      var paidDates = [];
      var unpaidDates = [];
      
      for (var colIdx in dateColumns) {
        var date = dateColumns[colIdx];
        var cellValue = row[colIdx];
        
        // Handle checkbox Google Sheets: TRUE = checked, FALSE/empty = unchecked
        var isPaid = false;
        
        if (cellValue === true) {
          isPaid = true;
          Logger.log("Checkbox TRUE for " + name + " on " + date);
        } else if (cellValue === "✓" || cellValue === "✅" || cellValue === "✔") {
          isPaid = true;
        } else if (cellValue === false || cellValue === "" || cellValue === null) {
          isPaid = false;
          Logger.log("Checkbox FALSE/empty for " + name + " on " + date);
        }
        
        if (isPaid) {
          paidDates.push(date);
        } else {
          unpaidDates.push(date);
        }
      }
      
      students.push({
        no: no,
        name: name,
        row: rowIdx + 1,
        paid_dates: paidDates.sort(),
        unpaid_dates: unpaidDates.sort(),
        total_paid: paidDates.length,
        total_unpaid: unpaidDates.length
      });
    }
    
    Logger.log("Students processed: " + students.length);
    
    return successResponse({students: students, count: students.length});
    
  } catch (e) {
    Logger.log("Error: " + e.toString());
    return errorResponse("Error: " + e.toString());
  }
}

function getDashboardData() {
  try {
    var ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    var sheet = null;
    
    var sheets = ss.getSheets();
    for (var i = 0; i < sheets.length; i++) {
      var sheetName = sheets[i].getName().toUpperCase();
      if (sheetName.indexOf("DASHBOARD") >= 0) {
        sheet = sheets[i];
        break;
      }
    }
    
    if (!sheet) {
      return successResponse({
        total_pemasukan: 0,
        total_pengeluaran: 0,
        sisa_uang_kas: 0,
        status: "UNKNOWN"
      });
    }
    
    var data = sheet.getDataRange().getValues();
    var result = {
      total_pemasukan: 0,
      total_pengeluaran: 0,
      sisa_uang_kas: 0,
      status: "UNKNOWN"
    };
    
    for (var i = 0; i < data.length; i++) {
      var row = data[i];
      var rowText = row.join(" ").toLowerCase();
      
      if (rowText.indexOf("total pemasukan") >= 0) {
        result.total_pemasukan = parseRupiah(row);
      }
      else if (rowText.indexOf("total pengeluaran") >= 0) {
        result.total_pengeluaran = parseRupiah(row);
      }
      else if (rowText.indexOf("sisa uang kas") >= 0) {
        result.sisa_uang_kas = parseRupiah(row);
      }
      else if (rowText.indexOf("status") >= 0) {
        for (var j = 0; j < row.length; j++) {
          var cell = String(row[j]).toLowerCase();
          if (cell.indexOf("aman") >= 0) {
            result.status = "AMAN";
            break;
          } else if (cell.indexOf("warning") >= 0) {
            result.status = "WARNING";
            break;
          } else if (cell.indexOf("bahaya") >= 0) {
            result.status = "BAHAYA";
            break;
          }
        }
      }
    }
    
    return successResponse(result);
    
  } catch (e) {
    return errorResponse("Error: " + e.toString());
  }
}

function isDateColumn(text) {
  var text = String(text).trim();
  return /\d{1,2}\s+[A-Za-z]+\s+\d{4}/.test(text) || /\d{1,2}\/\d{1,2}\/\d{4}/.test(text);
}

function parseDateFromHeader(text) {
  var text = String(text).trim();
  var monthMap = {
    'january': 0, 'february': 1, 'march': 2, 'april': 3, 'may': 4, 'june': 5,
    'july': 6, 'august': 7, 'september': 8, 'october': 9, 'november': 10, 'december': 11,
    'januari': 0, 'februari': 1, 'maret': 2, 'april': 3, 'mei': 4, 'juni': 5,
    'juli': 6, 'agustus': 7, 'september': 8, 'oktober': 9, 'november': 10, 'desember': 11
  };
  
  var match = text.match(/(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})/);
  if (match) {
    var day = parseInt(match[1]);
    var month = monthMap[match[2].toLowerCase()];
    var year = parseInt(match[3]);
    if (month !== undefined) {
      return Utilities.formatDate(new Date(year, month, day), "Asia/Jakarta", "yyyy-MM-dd");
    }
  }
  
  match = text.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (match) {
    var day = parseInt(match[1]);
    var month = parseInt(match[2]) - 1;
    var year = parseInt(match[3]);
    return Utilities.formatDate(new Date(year, month, day), "Asia/Jakarta", "yyyy-MM-dd");
  }
  
  return null;
}

function parseRupiah(row) {
  for (var i = 0; i < row.length; i++) {
    var cell = String(row[i]);
    var cleaned = cell.replace(/[^0-9-]/g, '');
    if (cleaned && cleaned !== '-') {
      return parseInt(cleaned) || 0;
    }
  }
  return 0;
}

function successResponse(data) {
  return ContentService.createTextOutput(JSON.stringify({success: true, data: data}))
    .setMimeType(ContentService.MimeType.JSON);
}

function errorResponse(message) {
  return ContentService.createTextOutput(JSON.stringify({success: false, error: message}))
    .setMimeType(ContentService.MimeType.JSON);
}