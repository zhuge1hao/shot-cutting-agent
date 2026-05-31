import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const testRoot = "E:/USE/codexhome/fenge/output/test";
const outputDir = path.join(testRoot, "shot_text_excels");
const outputPath = path.join(outputDir, "test_5_5_underwear_shot_text.xlsx");

const entries = await fs.readdir(testRoot, { withFileTypes: true });
const videoDirName = entries.find((entry) => entry.isDirectory() && entry.name.startsWith("5.5+"))?.name;
if (!videoDirName) throw new Error("Cannot find output folder for 5.5+ video.");

const reportPath = path.join(testRoot, videoDirName, "model_optimized", "model_optimized_shot_report.json");
const report = JSON.parse(await fs.readFile(reportPath, "utf8"));
const droppedShotIds = new Set(["ModelShot_031"]);
const shots = report.shots.filter((shot) => !droppedShotIds.has(shot.shot_id));

const manual = {
  1: {
    structure: "开盒/囤货画面",
    framework: "疑问好奇拉停留",
    copy: "笑死，闺蜜说我是不是出息了，内裤都半打半打地买",
    user: "半打半打买女士内裤反常识，容易好奇为什么值得囤",
    voice: "吐槽式开头，语气轻松带笑",
    sound: "开场 pop/轻快 BGM",
    highlight: "用闺蜜吐槽建立囤货钩子",
  },
  2: {
    structure: "独立包装展示",
    framework: "价格反差铺垫",
    copy: "平常一件十几二十几的我哪里舍得啊",
    user: "用户会先对价格产生共鸣，理解囤货不是冲动消费",
    voice: "生活化解释口播",
    sound: "包装摩擦/提示 ding",
    highlight: "把价格敏感人群留住",
  },
  3: {
    structure: "产品拿起/颜色展示",
    framework: "活动卖点",
    copy: "遇上品牌精品冲销量，到手6条，你看看才啥价",
    user: "6条组合和低价形成强性价比信号",
    voice: "活动强调型口播",
    sound: "金币音/价格 ding",
    highlight: "把囤货理由落到价格利益点",
  },
  4: {
    structure: "快速产品细节",
    framework: "多色选择展示",
    copy: "到手6条",
    user: "看到颜色和数量，确认是女士内裤套装",
    voice: "短句带过，承接价格卖点",
    sound: "快切 whoosh",
    highlight: "快速补充套装数量感",
  },
  5: {
    structure: "多条叠放展示",
    framework: "囤货背书",
    copy: "我是真忍不住",
    user: "多条拿在手里强化好价囤货的真实感",
    voice: "真实分享式口播",
    sound: "布料 swish",
    highlight: "用数量视觉强化购买冲动",
  },
  6: {
    structure: "6条平铺",
    framework: "套装价值展示",
    copy: "到手6条",
    user: "一眼看到6条，性价比更直观",
    voice: "产品数量确认",
    sound: "陈列 pop",
    highlight: "套装数量是本条视频核心卖点之一",
  },
  7: {
    structure: "女士内裤正面展示",
    framework: "产品主体确认",
    copy: "胶树加精品冲销量",
    user: "先确认产品不是普通散装，而是品牌女士内裤",
    voice: "品牌活动口播",
    sound: "轻提示 ding",
    highlight: "产品主体清晰露出",
  },
  8: {
    structure: "女士内裤平铺展示",
    framework: "版型展示",
    copy: "",
    user: "",
    voice: "",
    sound: "轻快 BGM",
    highlight: "用平铺画面承接版型信息",
  },
  9: {
    structure: "女士内裤细节展示",
    framework: "产品细节承接",
    copy: "",
    user: "",
    voice: "",
    sound: "布料摩擦",
    highlight: "保持产品展示节奏",
  },
  10: {
    structure: "多色拿起展示",
    framework: "花色/颜色展示",
    copy: "小碎花图案一条比一条好看",
    user: "多色多花型让用户感觉套装实用、不单调",
    voice: "惊喜式口播",
    sound: "快切 pop",
    highlight: "花色丰富提升购买理由",
  },
  11: {
    structure: "小碎花近景",
    framework: "颜值卖点",
    copy: "小碎花图案一条比一条好看",
    user: "好看的花色降低基础款内裤的无聊感",
    voice: "夸赞式口播",
    sound: "轻提示 ding",
    highlight: "颜值卖点直接可见",
  },
  12: {
    structure: "包装盒/密封袋",
    framework: "独立包装卖点",
    copy: "每一件都做了独立密封包装",
    user: "独立密封会让用户更放心卫生和新品状态",
    voice: "信任背书口播",
    sound: "包装摩擦/确认 ding",
    highlight: "从价格卖点转入卫生信任",
  },
  13: {
    structure: "独立密封包装",
    framework: "打消顾虑，增加信任度",
    copy: "拆了就没法复原",
    user: "包装不可复原能降低买到二手内裤的担心",
    voice: "解释型口播，语气笃定",
    sound: "撕开/包装声",
    highlight: "用包装状态证明安全感",
  },
  14: {
    structure: "包装细节近景",
    framework: "卫生顾虑解决",
    copy: "完全不用担心会买到二手内裤的可能",
    user: "二手内裤顾虑被直接打消，信任感增强",
    voice: "信任强调型口播",
    sound: "提示 ding",
    highlight: "强信任点，适合重点标注",
  },
  15: {
    structure: "密封包装按压",
    framework: "包装证明",
    copy: "",
    user: "",
    voice: "",
    sound: "包装按压声",
    highlight: "用手部动作补充密封证明",
  },
  16: {
    structure: "新疆棉产品展示",
    framework: "面料卖点",
    copy: "新疆棉的内裤真的巨软糯啊",
    user: "新疆棉和软糯触感会提升舒适期待",
    voice: "惊喜式产品讲解",
    sound: "布料 swish",
    highlight: "面料卖点开始出现",
  },
  17: {
    structure: "手摸面料",
    framework: "触感证明",
    copy: "真不夸张，闻着都一股棉花香",
    user: "触摸和闻香让面料卖点更有真实感",
    voice: "真实体验口播",
    sound: "布料摩擦/轻快 BGM",
    highlight: "用感官描述增强可信度",
  },
  18: {
    structure: "小碎花面料近景",
    framework: "面料+颜值展示",
    copy: "新疆棉的内裤真的巨软糯",
    user: "近景能同时感知柔软和花色",
    voice: "卖点补充口播",
    sound: "轻提示 ding",
    highlight: "面料质感和花色一起展示",
  },
  19: {
    structure: "展开/版型展示",
    framework: "版型细节展示",
    copy: "",
    user: "",
    voice: "",
    sound: "展开 swish",
    highlight: "产品展开后版型更清楚",
  },
  20: {
    structure: "内里/底档展示",
    framework: "底档卖点引入",
    copy: "底档不仅加长加宽",
    user: "底档加长加宽能联想到穿着不磨、不夹、更舒服",
    voice: "专业卖点讲解",
    sound: "重点 hit/布料声",
    highlight: "进入女士内裤关键功能点",
  },
  21: {
    structure: "底档面料近景",
    framework: "卫生功能卖点",
    copy: "还是32A一斤的，更能呵护咱们女生小花园的卫生环境",
    user: "底档材质和卫生环境是女性用户强关注点",
    voice: "专业背书口播",
    sound: "提示 ding",
    highlight: "把底档从舒适升级到卫生信任",
  },
  22: {
    structure: "底档拉伸/触摸",
    framework: "底档细节证明",
    copy: "底档加长加宽",
    user: "通过手部拉伸确认底档面积和柔软度",
    voice: "细节证明型口播",
    sound: "布料拉伸 swish",
    highlight: "视觉证明底档卖点",
  },
  23: {
    structure: "底档局部近景",
    framework: "产品核心卖点",
    copy: "呵护女生小花园的卫生环境",
    user: "私密部位卫生表达能提升购买重视程度",
    voice: "谨慎专业口播",
    sound: "低音量提示 ding",
    highlight: "女性私密护理诉求明确",
  },
  24: {
    structure: "腰口/弹力展示",
    framework: "舒适度卖点",
    copy: "",
    user: "",
    voice: "",
    sound: "弹力拉伸声",
    highlight: "补充腰口舒适和版型信息",
  },
  25: {
    structure: "腰口细节近景",
    framework: "做工细节展示",
    copy: "",
    user: "",
    voice: "",
    sound: "布料摩擦",
    highlight: "腰口和做工细节增强产品质感",
  },
  26: {
    structure: "多色叠放展示",
    framework: "多色选择展示",
    copy: "小碎花图案一条比一条好看啊哈",
    user: "多条花色有选择感，也强化6条套装价值",
    voice: "轻松夸赞式口播",
    sound: "快切 pop",
    highlight: "再次强化花色丰富",
  },
  27: {
    structure: "多条产品快速展示",
    framework: "套装价值强化",
    copy: "关键六条还不到40",
    user: "价格对比强，容易产生薅羊毛冲动",
    voice: "价格强调型口播",
    sound: "金币音/价格 ding",
    highlight: "核心价格锚点出现",
  },
  28: {
    structure: "产品平铺/价格承接",
    framework: "活动留人",
    copy: "难得遇上品牌有羊毛",
    user: "品牌活动稀缺感会推动马上购买",
    voice: "促销收束口播",
    sound: "活动提示 ding",
    highlight: "把好价归因到品牌活动",
  },
  29: {
    structure: "产品细节扫过",
    framework: "购买动作引导",
    copy: "那我可不得赶紧薅啊",
    user: "用户被好价和卖点说服后，容易接受马上入手",
    voice: "收尾种草口播",
    sound: "收束 hit",
    highlight: "形成购买冲动收束",
  },
  30: {
    structure: "6条平铺收尾",
    framework: "价格利益点收尾",
    copy: "六条还不到40",
    user: "最后再次看到6条和价格，强化性价比记忆",
    voice: "结尾复述利益点",
    sound: "结尾 ding",
    highlight: "用套装全貌完成收尾",
  },
};

const fields = [
  ["镜头", "__shot__"],
  ["时间", "__time__"],
  ["视频结构（画面）", "structure"],
  ["文案框架", "framework"],
  ["文案", "copy"],
  ["用户视角", "user"],
  ["配音", "voice"],
  ["音效39个", "sound"],
  ["视频亮点", "highlight"],
];

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

function shotNumber(shot) {
  return Number(String(shot.shot_id).replace("ModelShot_", ""));
}

function valueFor(shot, fieldKey) {
  const data = manual[shotNumber(shot)] ?? {};
  if (fieldKey === "__shot__") return shot.shot_id;
  if (fieldKey === "__time__") return `${shot.start_time} - ${shot.end_time}`;
  return data[fieldKey] ?? "";
}

const workbook = Workbook.create();
const sheet = workbook.worksheets.add("Test_5_5");
sheet.showGridLines = false;
sheet.freezePanes.freezeRows(1);
sheet.freezePanes.freezeColumns(1);

const rowCount = fields.length;
const colCount = shots.length + 1;
const matrix = Array.from({ length: rowCount }, () => Array.from({ length: colCount }, () => ""));
for (let r = 0; r < rowCount; r += 1) {
  matrix[r][0] = fields[r][0];
}
for (let c = 0; c < shots.length; c += 1) {
  for (let r = 0; r < rowCount; r += 1) {
    matrix[r][c + 1] = valueFor(shots[c], fields[r][1]);
  }
}

sheet.getRangeByIndexes(0, 0, rowCount, colCount).values = matrix;
const lastCol = columnName(colCount - 1);

sheet.getRange("A1:A9").format = {
  fill: "#0F766E",
  font: { bold: true, color: "#FFFFFF" },
  wrapText: true,
};
sheet.getRange(`B1:${lastCol}9`).format.wrapText = true;
sheet.getRange(`A1:${lastCol}9`).format.borders = {
  preset: "inside",
  style: "thin",
  color: "#CBD5E1",
};
sheet.getRange(`A1:${lastCol}9`).format.borders = {
  preset: "outside",
  style: "thin",
  color: "#64748B",
};

sheet.getRange("A:A").format.columnWidthPx = 140;
for (let c = 1; c < colCount; c += 1) {
  const col = columnName(c);
  sheet.getRange(`${col}:${col}`).format.columnWidthPx = 280;
}

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

for (let c = 0; c < shots.length; c += 1) {
  const evidence = shots[c].evidence_frame;
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
  } catch {
    // Keep text data even if an evidence image is missing.
  }
}

await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(outputPath);
