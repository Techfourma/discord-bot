function handleEditTrigger(e) {
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
    const tanggal = sheet.getRange(3, col).getDisplayValue(); // <-- fix: getDisplayValue()
    const status = e.value === "TRUE" ? "CHECK" : "UNCHECK";

    const nextRow = getNextEmptyRow(logSheet);
    logSheet.getRange(nextRow, 1, 1, 5).setValues([[nama, tanggal, getRealTime(), status, user]]);
  }

  // PENGELUARAN
  if (sheetName === "Pengeluaran") {
    if (row < 3 || col !== 3) return;

    if (!user) {
      SpreadsheetApp.getUi().alert(
        "⚠️ Pilih nama di B2 (DaftarUangKas) sebelum input Pengeluaran!"
      );
      e.range.setValue("");
      return;
    }

    const tanggalCell = sheet.getRange(row, 1);
    if (!tanggalCell.getValue()) {
      tanggalCell.setValue(new Date());
    }

    const namaPIC = sheet.getRange(row, 2).getValue();
    const pembelian = sheet.getRange(row, 3).getValue();

    const nextRow = getNextEmptyRow(logSheet);
    logSheet.getRange(nextRow, 1, 1, 5).setValues([[namaPIC, getRealTime(), getRealTime(), pembelian, user]]);
  }
}

function getNextEmptyRow(logSheet) {
  const colAValues = logSheet.getRange("A:A").getValues();
  for (let i = 1; i < colAValues.length; i++) {
    if (colAValues[i][0] === "") {
      return i + 1;
    }
  }
  return colAValues.length + 1;
}

function getRealTime() {
  return Utilities.formatDate(
    new Date(),
    Session.getScriptTimeZone(),
    "yyyy-MM-dd HH:mm:ss"
  );
}

function clearTestLog() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const logSheet = ss.getSheetByName("Log");

  const colAValues = logSheet.getRange("A:A").getValues();
  let lastDataRow = 1;
  for (let i = 1; i < colAValues.length; i++) {
    if (colAValues[i][0] !== "") lastDataRow = i + 1;
  }

  if (lastDataRow > 1) {
    logSheet.getRange(2, 1, lastDataRow - 1, 6).clearContent();
    SpreadsheetApp.getUi().alert("✅ Log berhasil dibersihkan!");
  } else {
    SpreadsheetApp.getUi().alert("Log sudah kosong.");
  }
}

function createEditTrigger() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  ScriptApp.getProjectTriggers().forEach(trigger => {
    if (trigger.getHandlerFunction() === "handleEditTrigger") {
      ScriptApp.deleteTrigger(trigger);
    }
  });

  ScriptApp.newTrigger("handleEditTrigger")
    .forSpreadsheet(ss)
    .onEdit()
    .create();

  SpreadsheetApp.getUi().alert("✅ Trigger berhasil dipasang!");
}

function authorizeApp() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const log = ss.getSheetByName("Log");
  if (log) log.getLastRow();
  SpreadsheetApp.getUi().alert("Authorization berhasil, silakan tutup ini.");
}