import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

function readOption(name, fallback = "") {
  const index = process.argv.indexOf(`--${name}`);
  if (index === -1) return fallback;
  return process.argv[index + 1] ?? fallback;
}

const root = path.resolve(readOption("root", process.cwd()));
const inputJson = path.resolve(
  readOption("input-json", path.join(root, "output", "shot_text_excels", "video_shot_text_ocr_with_thumbs.json")),
);
const outputDir = path.resolve(readOption("output-dir", path.join(root, "output", "shot_text_excels")));
const videoLink = readOption("video-link", "");

const rows = JSON.parse(await fs.readFile(inputJson, "utf8"));
const byVideo = new Map();
for (const row of rows) {
  const videoId = String(row["视频编号"]);
  if (!byVideo.has(videoId)) byVideo.set(videoId, []);
  byVideo.get(videoId).push(row);
}

const fields = [
  ["视频链接", "__video_link__"],
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

const brandNoise = /^(UFEEL|Ufeel|DESIGNER|PREMIUM|OPTIMALFEELING|UNDERWEARDESIGNERBRAND|AMAZINGTOUCH|BRAND|UFEELDESIGNER)$/i;
const complianceNoise =
  /剧情演绎仅?产品展示无不良(?:遇到)?没有减肥效果|注意甄别树立正确价值观|正常产品展示[·,，、]?\s*无不良引导|产品展示无不良引导|无不良引导/g;

function cell(v) {
  if (v === undefined || v === null) return "";
  return String(v).trim();
}

function cleanCopy(row) {
  if (Object.hasOwn(row, "__cleanText")) return row.__cleanText;
  const raw = cell(row["画面文案"]);
  if (!raw) return "";
  const parts = raw
    .split(/\r?\n+/)
    .map((item) => item.trim())
    .filter(Boolean)
    .filter((item) => !brandNoise.test(item.replace(/\s+/g, "")));
  let text = parts.length ? parts.join("，") : raw.replace(/\s+/g, " ").trim();
  text = text.replace(complianceNoise, "");
  text = text.replace(/(?:昨日之前|年日之前|日入)[，,、]?的世界/g, "");
  text = text.replace(/(^|[，,、])的世界(?=[，,、]|$)/g, "$1");
  text = text.replace(/^[，,、]?(品展示|暗示|赔)[，,、]?/g, "");
  text = text.replace(/[A-Za-z0-9/]{3,}/g, (match) => (/^ufeel$/i.test(match) ? match : ""));
  text = text
    .replace(/[，,、]{2,}/g, "，")
    .replace(/^[，,、。.\s]+|[，,、。.\s]+$/g, "")
    .replace(/\s+/g, " ")
    .trim();
  return text;
}

function has(text, pattern) {
  return pattern.test(text);
}

function classify(row, index, total) {
  const text = cleanCopy(row);
  const action = cell(row["关键动作标注"]);
  const repeated = cell(row["是否与上一镜头文案相同"]) === "是" || row.__cleanRepeated === true;
  const early = index < Math.max(3, Math.ceil(total * 0.12));
  const late = index >= Math.max(0, total - 3);
  const isQuestion = has(text, /为什么|问了|才知道|知道|到底|头一次|穿过吗|会有什么|怎么|真的吗|原来|只有两种/);
  const isPain = has(text, /大肚|肚子|肉肉|下垂|勒|喘不过气|痱子|发黄|黏糊|不舒服|私处|小花园|熬夜|腥辣|卡裆|露裤腿|尴尬|焦虑|不干爽|遮遮掩掩/);
  const isProduct = has(text, /Ufeel|u feel|ufeel|草本|美宅|桑蚕丝|蚕丝|内裤|收腹|提臀|底档|面料|抗菌|抑菌|无痕|隐形|镂空|蕾丝|高腰|弹力|三合一|安全裤|裤|包装|基底裤|肌底裤/i);
  const isTrust = has(text, /广东|普宁|出口|源头|工厂|制造基地|品质|专为|设计|专业|女性健康/);
  const isOffer = has(text, /买单|活动|福利|库存|拍一发|拍1发|价格|好几十|现在买|试试|一定要/);
  const isScene = has(text, /老婆|媳妇|女士|女人|女生|结婚后|停经后|穿裙子|夏天|运动|出汗|闺蜜|在家/);
  const isCompare = has(text, /穿前|穿后|对比|变化|越大|越明显/);
  const isPackage = has(text, /拆开|开袋|包装|密封|拿去洗/);
  const isCompliance = !text && has(cell(row["画面文案"]), /注意甄别|剧情演绎|不良引导|价值观|正常产品|合规/);
  const isFlash = has(action, /闪光|定格|快节奏/);
  const isPhysical = has(action, /物理状态|展开|开袋|状态改变/);
  return {
    text,
    action,
    repeated,
    early,
    late,
    isQuestion,
    isPain,
    isProduct,
    isTrust,
    isOffer,
    isScene,
    isCompare,
    isPackage,
    isCompliance,
    isFlash,
    isPhysical,
  };
}

function isMeaningfulCopy(c) {
  if (!c.text || c.repeated) return false;
  const compact = c.text.replace(/[，。！？,.!?、\s]/g, "");
  if (compact.length < 5 && !c.isQuestion && !c.isOffer) return false;
  if (/^(因为|所以|然后|但是|这个|这个呢|原来|现在)$/.test(compact)) return false;
  return true;
}

function visualStructure(row, index, total) {
  const c = classify(row, index, total);
  if (!isMeaningfulCopy(c) && !c.isPackage && !c.isCompare) return "";
  if (c.repeated && !c.isPackage && !c.isCompare) return "";
  if (c.isCompliance) return "合规提示画面";
  if (c.isCompare) return "对比画面";
  if (c.isPackage) return c.isPhysical ? "开袋/包装袋" : "包装袋";
  if (c.isPain && c.early) return "最直观的痛点画面";
  if (c.isPain && c.isScene) return "生活场景，痛点突出";
  if (c.isPain) return "痛点画面";
  if (c.isTrust) return "源头信任度+产品定位";
  if (c.isOffer && c.late) return "活动卖点结束";
  if (c.isOffer) return "活动卖点画面";
  if (has(c.text, /底档|抗菌|抑菌|加长|加宽/)) return "底档细节";
  if (has(c.text, /无痕|隐形|高弹|弹力|柔软|轻薄|颜色|面料/)) return "产品多维度展示";
  if (has(c.text, /收腹|提臀|小蛮腰|蜜桃臀|版型|包裹/)) return "上身效果展示";
  if (c.isScene && c.isQuestion) return "生活场景口播";
  if (c.isScene) return "模特上身/生活场景";
  if (c.isQuestion && c.early) return "吸睛镜头";
  if (c.isQuestion) return "口播讲解";
  if (c.isFlash) return "画面快闪";
  if (c.isProduct) return "产品卖点展示";
  return "";
}

function copyFramework(row, index, total) {
  const c = classify(row, index, total);
  if (!isMeaningfulCopy(c)) return "";
  if (c.isCompliance) return "合规提示";
  if (c.early && c.isPain) return "痛点警示开篇";
  if (c.early && c.isQuestion) return "疑问好奇拉停留";
  if (c.early && has(c.text, /只穿|头一次|疯了|你要是也这样/)) return "抛钩子";
  if (c.isOffer && c.late) return "活动留人";
  if (c.isOffer) return "活动卖点";
  if (c.isTrust) return "打消顾虑，增加信任度";
  if (c.isPain && c.isProduct) return "产品给到解决方案";
  if (c.isPain) return "痛点焦虑";
  if (c.isQuestion && c.isProduct) return "卖点+疑问好奇留人";
  if (c.isQuestion) return "疑问引好奇";
  if (has(c.text, /拆开就能穿|不要拆开|独立|密封|包装/)) return "方便快捷卖点";
  if (has(c.text, /桑蚕丝|抗菌|抑菌|底档|女性健康|私处|干净舒适/)) return "产品核心卖点";
  if (has(c.text, /收腹|提臀|无痕|隐形|镂空|蕾丝|高腰|弹力/)) return "主卖点留住人群";
  if (c.isScene) return "代入生活定位话术";
  if (c.isProduct) return "产品卖点";
  return "";
}

function userPerspective(row, index, total) {
  const c = classify(row, index, total);
  if (!isMeaningfulCopy(c)) return "";
  if (c.isCompliance) return "平台合规视角，提示理性识别内容";
  if (c.isPain && has(c.text, /肚|肉肉|下垂|收腹|提臀/)) return "看到身材痛点会联想到自己需求";
  if (c.isPain) return "代入个人日常场景，担心同类问题";
  if (c.isTrust) return "源头工厂和品质背书让人对产品产生认可";
  if (c.isOffer) return "刚好有活动，容易产生购买意愿";
  if (c.isQuestion && !c.isProduct) return "疑问增加好奇感，想继续看答案";
  if (has(c.text, /桑蚕丝|蚕丝|抗菌|抑菌|底档|面料|健康/)) return "了解到面料和底档卖点，觉得更干净舒适";
  if (has(c.text, /拆开|包装|密封|拿去洗/)) return "拆开就能穿方便快捷，降低购买顾虑";
  if (has(c.text, /收腹|提臀|无痕|隐形|弹力|轻薄|三合一|安全裤/)) return "了解到产品卖点，觉得能解决痛点，对产品产生认可";
  if (c.isScene) return "代入生活穿着场景，判断自己是否需要";
  if (index >= total - 2) return "结尾再次强化利益点，促进决策";
  return "";
}

function voiceover(row, index, total) {
  const c = classify(row, index, total);
  if (!c.text) return "可无配音，保留节奏音乐承接画面";
  if (c.isPain && c.early) return "痛点口播开头，语速快一点制造代入感";
  if (c.isQuestion) return "疑问式口播，前半句拉好奇，后半句给答案";
  if (c.isTrust) return "专业背书口播，语气笃定增加信任";
  if (c.isOffer) return "活动强调型口播，突出限时和利益点";
  if (c.isProduct) return "产品讲解型口播，跟随画面点出卖点";
  return "生活化口播，语气自然像真实分享";
}

function soundEffect(row, index, total) {
  const c = classify(row, index, total);
  if (c.isFlash) return "啪/定格 hit/快切 whoosh";
  if (c.isPackage) return "拆袋子音/包装摩擦";
  if (c.isPhysical) return "布料摩擦/展开 swish";
  if (c.isQuestion) return "疑问上扬 whoosh/答案 ding";
  if (c.isOffer) return "金币音/提示 ding/弹窗 pop";
  if (!c.text) return "轻节奏 BGM/环境声";
  return "字幕 pop/轻快节奏点";
}

function highlight(row, index, total) {
  const c = classify(row, index, total);
  if (index === 0) return "开头用钩子或痛点建立停留";
  if (c.isPain && c.early) return "痛点冲击强，容易让用户代入自己";
  if (c.isQuestion) return "信息未说透，能承接观众好奇继续看";
  if (c.isTrust) return "信任背书出现，降低用户顾虑";
  if (c.isOffer) return "利益点明确，可作为转化节点";
  if (c.isProduct) return "核心卖点出现，适合配字幕重点强化";
  if (index >= total - 2) return "结尾记忆点，适合收束和复述卖点";
  return "承接镜头，维持画面节奏和信息连续";
}

async function dataUrlFromFile(filePath) {
  const bytes = await fs.readFile(filePath);
  const b64 = Buffer.from(bytes).toString("base64");
  return `data:image/jpeg;base64,${b64}`;
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

function valueFor(row, key, index, total) {
  if (key === "__video_link__") return index === 0 ? videoLink : "";
  if (key === "__shot__") return cell(row["镜头编号"]);
  if (key === "__time__") return `${cell(row["起始时间"])} - ${cell(row["结束时间"])}`;
  if (key === "__visual_structure__") return visualStructure(row, index, total);
  if (key === "__copy_framework__") return copyFramework(row, index, total);
  if (key === "__copy_text__") {
    const c = classify(row, index, total);
    return isMeaningfulCopy(c) ? c.text : "";
  }
  if (key === "__user_perspective__") return userPerspective(row, index, total);
  if (key === "__voiceover__") return voiceover(row, index, total);
  if (key === "__sound_effect__") return soundEffect(row, index, total);
  if (key === "__highlight__") return highlight(row, index, total);
  return cell(row[key]);
}

async function buildWorkbook(videoId, videoRows) {
  const workbook = Workbook.create();
  const sheet = workbook.worksheets.add(`Video_${videoId}`);
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(2);
  sheet.freezePanes.freezeColumns(1);

  let previousText = "";
  for (const row of videoRows) {
    const text = cleanCopy(row);
    row.__cleanText = text;
    row.__cleanRepeated = Boolean(text && text === previousText);
    if (text) previousText = text;
  }

  const rowCount = fields.length;
  const colCount = videoRows.length + 1;
  const matrix = Array.from({ length: rowCount }, () => Array.from({ length: colCount }, () => ""));

  for (let r = 0; r < fields.length; r += 1) {
    matrix[r][0] = fields[r][0];
  }
  for (let c = 0; c < videoRows.length; c += 1) {
    for (let r = 0; r < fields.length; r += 1) {
      matrix[r][c + 1] = valueFor(videoRows[c], fields[r][1], c, videoRows.length);
    }
  }

  sheet.getRangeByIndexes(0, 0, rowCount, colCount).values = matrix;
  const lastCol = columnName(colCount - 1);

  sheet.getRange("A1:A10").format = {
    fill: "#0F766E",
    font: { bold: true, color: "#FFFFFF" },
    wrapText: true,
  };
  sheet.getRange(`B1:${lastCol}10`).format.wrapText = true;
  sheet.getRange(`A1:${lastCol}10`).format.borders = {
    preset: "inside",
    style: "thin",
    color: "#CBD5E1",
  };
  sheet.getRange(`A1:${lastCol}10`).format.borders = {
    preset: "outside",
    style: "thin",
    color: "#64748B",
  };

  sheet.getRange("A:A").format.columnWidthPx = 140;
  for (let c = 1; c < colCount; c += 1) {
    const col = columnName(c);
    sheet.getRange(`${col}:${col}`).format.columnWidthPx = 270;
  }

  sheet.getRange("1:1").format.rowHeightPx = 88;
  sheet.getRange("2:2").format.rowHeightPx = 230;
  sheet.getRange("3:3").format.rowHeightPx = 42;
  sheet.getRange("4:5").format.rowHeightPx = 78;
  sheet.getRange("6:6").format.rowHeightPx = 250;
  sheet.getRange("7:10").format.rowHeightPx = 96;
  sheet.getRange("A1:A10").format.horizontalAlignment = "center";
  sheet.getRange("A1:A10").format.verticalAlignment = "middle";
  sheet.getRange(`B2:${lastCol}2`).format.horizontalAlignment = "center";
  sheet.getRange(`B2:${lastCol}2`).format.verticalAlignment = "top";
  sheet.getRange(`B3:${lastCol}10`).format.verticalAlignment = "top";

  for (let c = 0; c < videoRows.length; c += 1) {
    const thumbPath = videoRows[c]["缩略图"];
    if (!thumbPath) continue;
    try {
      const dataUrl = await dataUrlFromFile(thumbPath);
      sheet.images.add({
        dataUrl,
        anchor: {
          from: { row: 1, col: c + 1, rowOffsetPx: 48, colOffsetPx: 75 },
          extent: { widthPx: 120, heightPx: 160 },
        },
      });
    } catch {
      // Keep text data even if thumbnail is missing.
    }
  }

  const outPath = path.join(outputDir, `video_${String(videoId).padStart(2, "0")}_shot_text.xlsx`);
  await fs.mkdir(outputDir, { recursive: true });
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(outPath);
  return outPath;
}

const outputs = [];
const orderedVideos = [...byVideo.keys()].sort((a, b) => Number(a) - Number(b));
for (const videoId of orderedVideos) {
  const out = await buildWorkbook(videoId, byVideo.get(videoId));
  outputs.push(out);
  console.log(out);
}

await fs.writeFile(
  path.join(outputDir, "individual_excel_manifest.json"),
  JSON.stringify(outputs, null, 2),
  "utf8",
);
