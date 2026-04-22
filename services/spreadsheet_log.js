function onEdit(e) {
  handleEdit(e);
}

function handleEdit(e) {
  if (!e) return;

  const sheet = e.range.getSheet();
  const sheetName = sheet.getName();
  const row = e.range.getRow();
  const col = e.range.getColumn();

  const ss = e.source;
  const logSheet = ss.getSheetByName("Log");
  if (!logSheet) return;

  const userSheet = ss.getSheetByName("DaftarUangKas");
  const user = userSheet.getRange("B2").getDisplayValue();

  // DAFTAR UANG KAS
  if (sheetName === "DaftarUangKas") {
    if (row < 4 || col < 3) return;
    if (e.value !== "TRUE" && e.value !== "FALSE") return;

    if (!user) {
      SpreadsheetApp.getUi().alert("⚠️ Pilih nama di B2 sebelum checklist!");
      e.range.setValue(false);
      return;
    }

    const nama = sheet.getRange(row, 2).getValue();
    const tanggal = sheet.getRange(3, col).getValue();
    const status = e.value === "TRUE" ? "CHECK" : "UNCHECK";

    logSheet.appendRow([
      nama,
      tanggal,
      getRealTime(),
      status,
      user
    ]);
  }

  // PENGELUARAN
  if (sheetName === "Pengeluaran") {
    if (row < 3 || (col !== 2 && col !== 3)) return;

    if (!user) {
      SpreadsheetApp.getUi().alert(
        "⚠️ Pilih nama di B2 (DaftarUangKas) sebelum input Pengeluaran!"
      );
      e.range.setValue("");
      return;
    }

    const tanggalCell = sheet.getRange(row, 1);
    if (!tanggalCell.getValue()) {
      tanggalCell.setValue(new Date()); // ini tetap boleh
    }

    const namaPIC = sheet.getRange(row, 2).getValue();
    const pembelian = sheet.getRange(row, 3).getValue();

    logSheet.appendRow([
      namaPIC,
      getRealTime(),
      getRealTime(),
      pembelian,
      user
    ]);
  }
}

// helper timezone
function getRealTime() {
  return Utilities.formatDate(
    new Date(),
    Session.getScriptTimeZone(),
    "yyyy-MM-dd HH:mm:ss"
  );
}

function authorizeApp() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  
  // akses sheet
  const sheets = ss.getSheets();
  
  // akses spesifik sheet
  const log = ss.getSheetByName("Log");
  if (log) {
    log.getLastRow();
  }

  SpreadsheetApp.getUi().alert("Authorization berhasil, silakan tutup ini.");
}