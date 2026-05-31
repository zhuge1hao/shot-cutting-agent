import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const reportPath = "E:/USE/codexhome/fenge/output/test/1/model_optimized/model_optimized_shot_report.json";
const outputDir = "E:/USE/codexhome/fenge/output/test/shot_text_excels";
const outputPath = path.join(outputDir, "test_01_shot_text_updated.xlsx");

const report = JSON.parse(await fs.readFile(reportPath, "utf8"));
const droppedShotIds = new Set(["ModelShot_015", "ModelShot_016"]);
const shots = report.shots.filter((shot) => !droppedShotIds.has(shot.shot_id));

const manual = {
  1: {
    structure: "健身场景/身材痛点",
    framework: "痛点警示开篇",
    copy: "为了两个人的和谐，建议女生把内裤换成梵克龙的天竺女士内裤",
    user: "从亲密关系和身材管理切入，容易代入更换女士内裤的理由",
    voice: "痛点口播开头，语气直接拉停留",
    sound: "开场 hit/字幕 pop",
    highlight: "开头同时抛出关系痛点和产品解决方向",
  },
  2: {
    structure: "产品平铺展示",
    framework: "产品核心卖点",
    copy: "梵克龙天竺女士内裤",
    user: "先看到产品本体，建立这是女士内裤卖点拆解",
    voice: "产品名轻带过，承接开头痛点",
    sound: "轻快转场 whoosh",
    highlight: "产品首次露出，明确主体",
  },
  4: {
    structure: "产品细节展示",
    framework: "主卖点留住人群",
    copy: "天竺内裤",
    user: "通过面料和版型细节判断舒适度",
    voice: "产品讲解型口播",
    sound: "布料摩擦/轻提示 ding",
    highlight: "用近景补充产品质感",
  },
  6: {
    structure: "生活场景口播",
    framework: "人群状态背书",
    copy: "这是我保持90斤的第五年",
    user: "用身材状态建立好奇和信任",
    voice: "第一人称分享式口播",
    sound: "轻节奏 BGM",
    highlight: "用结果状态给后续产品推荐做铺垫",
  },
  8: {
    structure: "模特上身展示",
    framework: "专业推荐背书",
    copy: "早上起来提前换上普拉提老师推荐的天竺女士内裤",
    user: "普拉提老师推荐会增加专业可信度",
    voice: "生活化口播，突出推荐来源",
    sound: "换装 swish",
    highlight: "用运动场景强化身材管理心智",
  },
  9: {
    structure: "包装展示",
    framework: "专业推荐背书",
    copy: "普拉提老师推荐的天竺女士内裤",
    user: "包装和推荐来源一起出现，降低陌生产品顾虑",
    voice: "产品背书口播",
    sound: "包装摩擦/提示 ding",
    highlight: "包装增强产品正规感",
  },
  11: {
    structure: "模特上身/镜前展示",
    framework: "人群定位",
    copy: "这是二胎后的我，果断把旧内裤全扔了",
    user: "二胎后身材管理人群容易代入",
    voice: "第一人称转变口播",
    sound: "转折 whoosh",
    highlight: "用二胎后状态做精准人群定位",
  },
  12: {
    structure: "礼盒包装",
    framework: "囤货背书",
    copy: "一口气买了6条梵克龙天竺女士内裤",
    user: "一次买多条会暗示产品好穿、值得复购",
    voice: "分享式口播，突出数量",
    sound: "开盒/金币音",
    highlight: "用囤货数量制造认可感",
  },
  14: {
    structure: "产品展开",
    framework: "痛点转解决方案",
    copy: "你要是也这样，就不要再穿低腰内裤了",
    user: "看到低腰痛点会联想到自己的穿着不适",
    voice: "建议式口播，语气明确",
    sound: "展开 swish",
    highlight: "从痛点进入换品类建议",
  },
  15: {
    structure: "痛点身材特写",
    framework: "痛点焦虑",
    copy: "你要是也这样",
    user: "用局部身材问题触发自我对照",
    voice: "短句停顿，制造代入",
    sound: "低音 hit",
    highlight: "视觉痛点直接，适合拉停留",
  },
  17: {
    structure: "包装展示",
    framework: "产品给到解决方案",
    copy: "你就穿这种内裤，收腹裤安全裤三合一的",
    user: "同时解决收腹、防走光和内裤替换需求",
    voice: "卖点讲解型口播",
    sound: "卖点弹出 pop",
    highlight: "三合一卖点明确，是核心转化信息",
  },
  19: {
    structure: "产品多维度展示",
    framework: "舒适度卖点",
    copy: "为了下半身的舒适，我一口气买了6条",
    user: "舒适需求强的人会被复购数量说服",
    voice: "真实分享型口播",
    sound: "布料摩擦/轻提示 ding",
    highlight: "用舒适和复购形成双重理由",
  },
  20: {
    structure: "产品多维度展示",
    framework: "强推荐收束",
    copy: "你要是也这样，那我强烈推荐你去穿这款内裤",
    user: "被前面痛点命中后更容易接受推荐",
    voice: "推荐式口播，尾音加强",
    sound: "确认 ding",
    highlight: "前一段卖点的转化建议",
  },
  21: {
    structure: "对话场景/身材变化",
    framework: "疑问好奇拉停留",
    copy: "最近练得不错啊，肚子都练没了",
    user: "别人视角夸身材变化，会激发继续看原因",
    voice: "剧情对话口播",
    sound: "对话 pop/轻快 BGM",
    highlight: "用夸赞制造变化悬念",
  },
  22: {
    structure: "口播反问",
    framework: "对前面疑问给出答案",
    copy: "哪有，我就是换条内裤",
    user: "答案反差感强，想知道内裤怎么影响体态",
    voice: "反差式回应",
    sound: "答案 ding",
    highlight: "用反差把注意力转到产品",
  },
  23: {
    structure: "对比画面",
    framework: "效果疑问",
    copy: "这还能瘦肚子的啊？",
    user: "反问制造停留，但不会直接夸大功效",
    voice: "疑问式口播",
    sound: "疑问 whoosh",
    highlight: "把收腹视觉效果包装成剧情疑问",
  },
  24: {
    structure: "无痕展示",
    framework: "产品证明",
    copy: "就算穿了这种紧身瑜伽裤，还没印子呢",
    user: "看到紧身裤无痕，会联想到夏天穿搭尴尬",
    voice: "证明型口播，跟画面同步",
    sound: "定格 hit/字幕 pop",
    highlight: "无痕卖点有直接视觉证据",
  },
  26: {
    structure: "生活对话冲突",
    framework: "剧情钩子",
    copy: "不是你搁家不穿内裤，你勾引谁呢？你有毛病吧？我穿了，只不过你看不出来而已",
    user: "冲突式对话拉停留，同时带出无痕卖点",
    voice: "男女对话/冲突式口播",
    sound: "对话切换 pop/轻冲突音效",
    highlight: "剧情冲突强，卖点自然露出",
  },
  28: {
    structure: "产品细节展示",
    framework: "穿搭痛点引入",
    copy: "天气热了，穿特别薄的裤子，每次内裤印子露出来老尴尬的",
    user: "夏天薄裤露印是高频生活痛点",
    voice: "痛点口播，语气生活化",
    sound: "尴尬停顿/提示 ding",
    highlight: "把无痕需求说得具体",
  },
  30: {
    structure: "产品拎起",
    framework: "无痕解决方案",
    copy: "我现在都穿这种无痕的奶皮子内裤",
    user: "从尴尬痛点自然转向无痕产品",
    voice: "推荐式口播",
    sound: "布料 swish",
    highlight: "无痕奶皮卖点正式出现",
  },
  31: {
    structure: "口播推荐",
    framework: "复购背书",
    copy: "我一次性囤了好多盒，我就特别喜欢他们家的内裤",
    user: "囤货行为会增加好穿、值得买的感受",
    voice: "真实分享型口播",
    sound: "金币音/盒子 pop",
    highlight: "用囤货做购买背书",
  },
  32: {
    structure: "快速产品展示",
    framework: "三合一卖点展示",
    copy: "粉底安全裤，内裤收腹裤安全裤三合一",
    user: "快速看到产品形态和功能组合，理解它不是普通女士内裤",
    voice: "卖点快节奏口播，跟随画面快速带过",
    sound: "快切 whoosh/字幕 pop",
    highlight: "快速补充产品外观和三合一定位",
  },
  33: {
    structure: "快速产品细节",
    framework: "隐形无痕卖点",
    copy: "粉底液的颜色又隐形又无痕",
    user: "粉底色接近肤色，能降低穿白薄透衣服的顾虑",
    voice: "产品讲解型口播，强调颜色和无痕",
    sound: "布料 swish/提示 ding",
    highlight: "用颜色和质感证明无痕卖点",
  },
  34: {
    structure: "快速上身展示",
    framework: "穿搭场景验证",
    copy: "咋没穿内裤就出门呢？我记得你挺透的",
    user: "透和没穿的误会制造好奇",
    voice: "剧情对话口播",
    sound: "疑问 whoosh",
    highlight: "用出门穿搭场景验证隐形无痕",
  },
  35: {
    structure: "快速产品上身展示",
    framework: "产品给到解决方案",
    copy: "我要给你们分享个好东西，就这个粉底安全裤，内裤收腹裤安全裤三合一的",
    user: "三合一可以同时解决透、露印和收腹需求",
    voice: "种草讲解型口播",
    sound: "卖点 pop/提示 ding",
    highlight: "粉底安全裤定位清晰",
  },
  37: {
    structure: "紧身穿搭展示",
    framework: "主卖点隐形无痕",
    copy: "这种粉底液的颜色又隐形又无痕",
    user: "颜色接近肤色，降低穿白薄透衣服的顾虑",
    voice: "卖点解释型口播",
    sound: "轻快 whoosh",
    highlight: "粉底色和无痕卖点结合",
  },
  39: {
    structure: "健身房对话",
    framework: "场景痛点+产品答案",
    copy: "哎，你健身怎么不穿内裤啊？我穿的是健身房人手一条的奶皮内裤",
    user: "健身紧身裤场景很具体，容易代入露边尴尬",
    voice: "场景对话口播",
    sound: "健身房环境声/对话 pop",
    highlight: "把无痕卖点放进健身场景验证",
  },
  40: {
    structure: "产品对比展示",
    framework: "无痕卖点证明",
    copy: "不像普通内裤露个边边，这很尴尬",
    user: "普通内裤露边是明确痛点，对比后更认可无痕",
    voice: "对比讲解型口播",
    sound: "对比 ding",
    highlight: "普通内裤和无痕内裤差异清楚",
  },
  42: {
    structure: "口播说明",
    framework: "当季穿搭痛点",
    copy: "夏天穿白薄透的衣服，再也不用担心露出内裤印儿",
    user: "白薄透穿搭人群会直接感到需要",
    voice: "痛点解决型口播",
    sound: "轻提示 ding",
    highlight: "夏季刚需场景明确",
  },
  43: {
    structure: "产品拉伸/底档细节",
    framework: "专业标准诉求",
    copy: "所有内裤商家，我希望你们能用这个标准来做女孩子的内裤底档",
    user: "用行业标准口吻提升专业感和信任感",
    voice: "专业建议型口播",
    sound: "强调 hit",
    highlight: "从普通种草升级为产品标准表达",
  },
  44: {
    structure: "底档对比",
    framework: "痛点证明",
    copy: "以前买的内裤底档都是这么短，这个地方磨得好难受",
    user: "底档短会磨得难受，是非常具体的穿着痛点",
    voice: "痛点解释型口播",
    sound: "布料摩擦/痛点 hit",
    highlight: "把底档长度问题讲清楚",
  },
  45: {
    structure: "产品细节/底档长度",
    framework: "产品证明",
    copy: "直到我买到了这条内裤，它的底档比普通内裤长了很多",
    user: "用长度对比证明能解决磨腿不适",
    voice: "结尾证明型口播",
    sound: "收束 ding",
    highlight: "最后用细节对比完成信任闭环",
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

function valueFor(shot, index, fieldKey) {
  const data = manual[Number(shot.shot_id.replace("ModelShot_", ""))] ?? {};
  if (fieldKey === "__shot__") return shot.shot_id;
  if (fieldKey === "__time__") return `${shot.start_time} - ${shot.end_time}`;
  return data[fieldKey] ?? "";
}

const workbook = Workbook.create();
const sheet = workbook.worksheets.add("Test_01");
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
    matrix[r][c + 1] = valueFor(shots[c], c, fields[r][1]);
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
    // Keep sheet values even if an evidence image is missing.
  }
}

await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(outputPath);
