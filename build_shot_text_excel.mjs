import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = "E:/USE/codexhome/fenge";
const csvPath = path.join(root, "output", "video_shot_text_ocr.csv");
const outputPath = path.join(root, "output", "video_shot_text_ocr.xlsx");

const csvText = await fs.readFile(csvPath, "utf8");
const workbook = await Workbook.fromCSV(csvText, { sheetName: "镜头文案" });
const sheet = workbook.worksheets.getItem("镜头文案");
sheet.showGridLines = false;
sheet.freezePanes.freezeRows(1);
sheet.getRange("A1").values = [["视频编号"]];

const used = sheet.getUsedRange();
const rowCount = used.rowCount;
const colCount = used.columnCount;
const tableRange = `A1:P${rowCount}`;
const table = sheet.tables.add(tableRange, true, "ShotTextOcrTable");
table.style = "TableStyleMedium2";
table.showFilterButton = true;

sheet.getRange("A1:P1").format = {
  fill: "#0F766E",
  font: { bold: true, color: "#FFFFFF" },
  wrapText: true,
};

const widths = {
  A: 70,
  B: 115,
  C: 105,
  D: 105,
  E: 105,
  F: 70,
  G: 70,
  H: 135,
  I: 430,
  J: 120,
  K: 105,
  L: 70,
  M: 430,
  N: 420,
  O: 420,
  P: 420,
};
for (const [col, width] of Object.entries(widths)) {
  sheet.getRange(`${col}:${col}`).format.columnWidthPx = width;
}

sheet.getRange(`A1:P${rowCount}`).format = {
  wrapText: true,
};
sheet.getRange(`A2:P${rowCount}`).format.rowHeightPx = 78;
sheet.getRange(`A1:P1`).format.rowHeightPx = 34;
sheet.getRange(`K2:K${rowCount}`).setNumberFormat("0.0000");

const summary = workbook.worksheets.add("汇总");
summary.showGridLines = false;
summary.getRange("A1").values = [["视频文案 OCR 导出汇总"]];
summary.getRange("A1:D1").merge();
summary.getRange("A1:D1").format = {
  fill: "#0F766E",
  font: { bold: true, color: "#FFFFFF" },
};
summary.getRange("A3:D3").values = [["指标", "数值", "说明", "文件"]];
summary.getRange("A3:D3").format = {
  fill: "#D1FAE5",
  font: { bold: true, color: "#064E3B" },
};
summary.getRange("A4:D8").values = [
  ["视频数量", 11, "已处理 output/1 到 output/11", ""],
  ["镜头行数", rowCount - 1, "按 reference_optimized 切分结果逐镜头导出", ""],
  ["OCR来源", "证据帧", "每个镜头使用 evidence_frame 做 OCR", ""],
  ["OCR模型", "RapidOCR", "中文/英文画面文案识别", ""],
  ["CSV源文件", "video_shot_text_ocr.csv", "Excel 由该 CSV 转换生成", csvPath],
];
summary.getRange("A:D").format.columnWidthPx = 190;
summary.getRange("C:C").format.columnWidthPx = 360;
summary.getRange("D:D").format.columnWidthPx = 520;
summary.getRange("A1:D8").format.wrapText = true;

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 50 },
});
if (errors.ndjson && errors.ndjson.includes("#")) {
  console.log(errors.ndjson);
}

await fs.mkdir(path.dirname(outputPath), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(outputPath);
