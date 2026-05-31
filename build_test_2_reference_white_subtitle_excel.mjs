import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const rowsPath = "E:/USE/codexhome/fenge/output/test/2/reference_optimized/white_subtitle_ocr.json";
const outputDir = "E:/USE/codexhome/fenge/output/test/shot_text_excels";
const outputPath = path.join(outputDir, "test_02_reference_calibrated_white_subtitle_shot_text.xlsx");

const rows = JSON.parse(await fs.readFile(rowsPath, "utf8"));

const fields = [
  ["镜头", "__shot__"],
  ["时间", "__time__"],
  ["视频结构（画面）", "__visual_structure__"],
  ["文案框架", "__copy_framework__"],
  ["文案", "__copy_text__"],
  ["用户视角", "__user_perspective__"],
  ["配音", "__voiceover__"],
  ["音效39个", "__sound_effect__"],
  ["视频亮点", "__highlight__"],
];

function cell(v) {
  if (v === undefined || v === null) return "";
  return String(v).trim();
}

function isPictureText(text) {
  if (!text) return false;
  return /检验检测|判定依据|委托方|页共|DESIGNER|UFEEL\?|PREMIUM|RE个内裤|抗菌柔蚕丝/.test(text);
}

function cleanSubtitle(row) {
  let text = cell(row.white_subtitle);
  if (!text || isPictureText(text)) return "";
  text = text
    .replace(/REMIUM\??/gi, "")
    .replace(/PREMIUM\??/gi, "")
    .replace(/折开/g, "拆开")
    .replace(/自已/g, "自己")
    .replace(/底裆/g, "底档")
    .replace(/\?/g, "")
    .replace(/[，,、]{2,}/g, "，")
    .replace(/^[，,、。.\s]+|[，,、。.\s]+$/g, "")
    .trim();
  return text;
}

function shotNum(row) {
  const match = String(row.shot_id).match(/(\d+)/);
  return match ? Number(match[1]) : NaN;
}

function classify(row, index) {
  const text = cleanSubtitle(row);
  const n = shotNum(row);
  const repeated = row.__cleanRepeated === true || row.subtitle_same_prev === true;
  const isQuestion = /为什么|是不是|谁|什么|怎么|哪有|不知道|你要是|我说真的|很多人都不知道/.test(text);
  const isOffer = /买单|拍一发|3|活动|买|对象|老公/.test(text);
  const isPackage = /拆开|独立|密封|洗|复原|包装/.test(text);
  const isTrust = /大品牌|抗菌|检验|女性健康|专为|设计/.test(text);
  const isPain = /肚子|肉肉|三角裤|遭了|底档|加长|加宽|分泌物|透|薄|裤子|裙子|穿黄|穿脏/.test(text);
  const isProduct = /Ufeel|ufeel|收腹|提臀|内裤|安全裤|镂空|蕾丝|面料|弹力|3D|动态|吸臀|底档|三角裤|普拉提/i.test(text);
  const isScene = /老婆|媳妇|在家|对象|老公|飞机|空姐|裙子|裤子|普拉提|瑜伽/.test(text);
  const isCompare = /越大|越明显|不一样|之前|普通|黑色/.test(text);
  return { text, n, repeated, isQuestion, isOffer, isPackage, isTrust, isPain, isProduct, isScene, isCompare };
}

function meaningful(c) {
  if (!c.text || c.repeated) return false;
  const compact = c.text.replace(/[，。！？,.!?、\s]/g, "");
  if (compact.length < 5 && !c.isQuestion && !c.isOffer) return false;
  if (/^(因为|Ufeel家的|我说真的|屁股越大|穿它一次)$/.test(compact)) return false;
  return true;
}

function visualStructure(row, index) {
  const c = classify(row, index);
  if (!meaningful(c)) return "";
  if (c.n <= 2) return "吸睛镜头";
  if (/飞机|空姐/.test(c.text)) return "同行爆款/人群画面";
  if (/一个月前|现在买|买单|拍一发/.test(c.text)) return "活动卖点画面";
  if (/镂空|蕾丝/.test(c.text)) return "产品细节展示";
  if (/肚子|收腹效果|梨形|屁股|吸臀/.test(c.text)) return "身材痛点/效果展示";
  if (/不要拆开|拆开就能穿|密封包装/.test(c.text)) return "包装袋/卫生证明";
  if (/女性健康|穿黄|穿脏|反反复复/.test(c.text)) return "健康痛点画面";
  if (/三合一|安全裤/.test(c.text)) return "产品结构展示";
  if (/双层微压|面料|弹力|3D|底档|加长|加宽|抗菌/.test(c.text)) return "产品核心细节";
  if (/裤子和裙子|再薄再透|黑色/.test(c.text)) return "穿搭场景验证";
  if (c.isScene) return "生活场景口播";
  if (c.isProduct) return "产品卖点展示";
  return "口播字幕画面";
}

function copyFramework(row, index) {
  const c = classify(row, index);
  if (!meaningful(c)) return "";
  if (c.n <= 3 || c.isQuestion) return "疑问好奇拉停留";
  if (/一个月前|现在买|买单|拍一发/.test(c.text)) return "活动留人";
  if (/两种|不买/.test(c.text)) return "人群分层钩子";
  if (/镂空|蕾丝|收腹效果|梨形|三合一|双层微压|弹力|3D|底档|抗菌/.test(c.text)) return "产品核心卖点";
  if (/拆开|密封|洗/.test(c.text)) return "方便快捷/卫生卖点";
  if (/女性健康|穿黄|穿脏|反反复复|三角裤|肚子/.test(c.text)) return "痛点焦虑";
  if (/大品牌|专为/.test(c.text)) return "打消顾虑，增加信任度";
  if (/裤子和裙子|再薄再透|黑色/.test(c.text)) return "穿搭场景验证";
  if (c.isScene) return "代入生活定位话术";
  return "口播信息补充";
}

function userPerspective(row, index) {
  const c = classify(row, index);
  if (!meaningful(c)) return "";
  if (/老婆只穿|飞机|空姐/.test(c.text)) return "用反常识和好身材画面制造好奇";
  if (/买单|拍一发|现在买/.test(c.text)) return "价格和活动刺激购买意愿";
  if (/肚子|收腹|梨形|屁股|吸臀|双层微压/.test(c.text)) return "看到身材痛点会联想到自己的收腹提臀需求";
  if (/拆开|密封|洗/.test(c.text)) return "拆开即穿和独立包装能降低卫生顾虑";
  if (/女性健康|穿黄|穿脏|反反复复|抗菌|底档/.test(c.text)) return "私密健康和底档舒适是女性用户强关注点";
  if (/三合一|安全裤/.test(c.text)) return "一个产品同时解决内裤、收腹和防走光需求";
  if (/裤子和裙子|再薄再透|黑色/.test(c.text)) return "薄透穿搭和颜色选择让用户判断是否适合自己";
  if (/大品牌/.test(c.text)) return "品牌背书会增加对产品品质的认可";
  return "";
}

function voiceover(row, index) {
  const c = classify(row, index);
  if (!meaningful(c)) return "";
  if (c.isQuestion) return "疑问式口播，前半句拉好奇";
  if (c.isOffer) return "活动强调型口播，突出利益点";
  if (c.isPain) return "痛点讲解型口播，语气直接";
  if (c.isTrust) return "专业背书口播，语气笃定";
  if (c.isProduct) return "产品讲解型口播，跟随画面点卖点";
  return "生活化口播，语气自然";
}

function soundEffect(row, index) {
  const c = classify(row, index);
  if (!meaningful(c)) return "";
  if (c.isOffer) return "金币音/价格 ding";
  if (c.isQuestion) return "疑问 whoosh/字幕 pop";
  if (c.isPackage) return "包装摩擦/拆袋子音";
  if (/弹力|面料|底档|加长|加宽/.test(c.text)) return "布料 swish/拉伸声";
  if (c.isPain) return "痛点 hit/提示 ding";
  return "轻快 BGM/字幕 pop";
}

function highlight(row, index) {
  const c = classify(row, index);
  if (!meaningful(c)) return "";
  if (c.n <= 3) return "开头用疑问和反常识建立停留";
  if (c.isOffer) return "活动利益点明确，可作为转化节点";
  if (c.isPackage) return "卫生顾虑被直接打消";
  if (/双层微压|3D|底档|抗菌|弹力/.test(c.text)) return "产品证明强，适合重点字幕强化";
  if (/三合一|收腹|提臀|安全裤/.test(c.text)) return "核心功能卖点清楚";
  if (/裤子和裙子|再薄再透|黑色/.test(c.text)) return "穿搭验证能承接用户真实使用场景";
  return "承接镜头，维持卖点节奏";
}

function columnName(indexZeroBased) {
  let n = indexZeroBased + 1;
  let name = "";
  while (n > 0) {
    const rem = (n - 1) % 26;
    name = String.fromCharCode(65 + rem) + name;
    n = Math.floor((n - 1) / 26);
  }
  return name;
}

async function dataUrlFromFile(filePath) {
  const bytes = await fs.readFile(filePath);
  return `data:image/jpeg;base64,${Buffer.from(bytes).toString("base64")}`;
}

function valueFor(row, key, index) {
  if (key === "__shot__") return row.shot_id;
  if (key === "__time__") return `${row.start_time} - ${row.end_time}`;
  if (key === "__visual_structure__") return visualStructure(row, index);
  if (key === "__copy_framework__") return copyFramework(row, index);
  if (key === "__copy_text__") {
    const c = classify(row, index);
    return meaningful(c) ? c.text : "";
  }
  if (key === "__user_perspective__") return userPerspective(row, index);
  if (key === "__voiceover__") return voiceover(row, index);
  if (key === "__sound_effect__") return soundEffect(row, index);
  if (key === "__highlight__") return highlight(row, index);
  return "";
}

let prevClean = "";
for (const row of rows) {
  const text = cleanSubtitle(row);
  row.__cleanRepeated = Boolean(text && text === prevClean);
  if (text) prevClean = text;
}

const workbook = Workbook.create();
const sheet = workbook.worksheets.add("Test_02_Ref");
sheet.showGridLines = false;
sheet.freezePanes.freezeRows(1);
sheet.freezePanes.freezeColumns(1);

const rowCount = fields.length;
const colCount = rows.length + 1;
const matrix = Array.from({ length: rowCount }, () => Array.from({ length: colCount }, () => ""));
for (let r = 0; r < rowCount; r += 1) matrix[r][0] = fields[r][0];
for (let c = 0; c < rows.length; c += 1) {
  for (let r = 0; r < rowCount; r += 1) matrix[r][c + 1] = valueFor(rows[c], fields[r][1], c);
}

sheet.getRangeByIndexes(0, 0, rowCount, colCount).values = matrix;
const lastCol = columnName(colCount - 1);

sheet.getRange("A1:A9").format = {
  fill: "#0F766E",
  font: { bold: true, color: "#FFFFFF" },
  wrapText: true,
};
sheet.getRange(`B1:${lastCol}9`).format.wrapText = true;
sheet.getRange(`A1:${lastCol}9`).format.borders = { preset: "inside", style: "thin", color: "#CBD5E1" };
sheet.getRange(`A1:${lastCol}9`).format.borders = { preset: "outside", style: "thin", color: "#64748B" };
sheet.getRange("A:A").format.columnWidthPx = 140;
for (let c = 1; c < colCount; c += 1) sheet.getRange(`${columnName(c)}:${columnName(c)}`).format.columnWidthPx = 280;
sheet.getRange("1:1").format.rowHeightPx = 230;
sheet.getRange("2:2").format.rowHeightPx = 42;
sheet.getRange("3:4").format.rowHeightPx = 82;
sheet.getRange("5:5").format.rowHeightPx = 260;
sheet.getRange("6:9").format.rowHeightPx = 104;
sheet.getRange("A1:A9").format.horizontalAlignment = "center";
sheet.getRange("A1:A9").format.verticalAlignment = "middle";
sheet.getRange(`B1:${lastCol}1`).format.horizontalAlignment = "center";
sheet.getRange(`B1:${lastCol}1`).format.verticalAlignment = "top";
sheet.getRange(`B2:${lastCol}9`).format.verticalAlignment = "top";

for (let c = 0; c < rows.length; c += 1) {
  const evidence = rows[c].evidence_frame;
  if (!evidence) continue;
  try {
    const dataUrl = await dataUrlFromFile(evidence);
    sheet.images.add({
      dataUrl,
      anchor: {
        from: { row: 0, col: c + 1, rowOffsetPx: 48, colOffsetPx: 80 },
        extent: { widthPx: 120, heightPx: 160 },
      },
    });
  } catch {}
}

await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(outputPath);
