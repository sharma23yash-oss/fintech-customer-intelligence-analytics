// Renders report_content.json -> Fintech_Business_Insights_Report.docx  (US Letter, Arial)
// Run: node 14_build_report_docx.js   (after 14_prepare_report_content.py)
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun, Header, Footer,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType, ShadingType, PageNumber, PageBreak, TableOfContents,
} = require("docx");

const REPORTS = path.resolve(__dirname, "..", "..", "reports");
const blocks = JSON.parse(fs.readFileSync(path.join(REPORTS, "_build", "report_content.json"), "utf8"));
const FONT = "Arial";
const NAVY = "0D366B", BLUE = "1C5CAB", INK = "1B1B1A", MUTED = "52514E";
const CONTENT_W = 9360; // 6.5in at 1440 dxa/in
const border = { style: BorderStyle.SINGLE, size: 4, color: "D5D9DE" };
const borders = { top: border, bottom: border, left: border, right: border };

function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}
const run = (t, o = {}) => new TextRun({ text: t, font: FONT, size: 21, color: INK, ...o });

function table(b) {
  const total = b.widths.reduce((a, x) => a + x, 0);
  const cw = b.widths.map((w) => Math.round((w / total) * CONTENT_W));
  cw[cw.length - 1] += CONTENT_W - cw.reduce((a, x) => a + x, 0);
  const cell = (txt, i, head) =>
    new TableCell({
      width: { size: cw[i], type: WidthType.DXA }, borders,
      shading: head ? { fill: BLUE, type: ShadingType.CLEAR, color: "auto" } : undefined,
      margins: { top: 50, bottom: 50, left: 80, right: 80 },
      children: [new Paragraph({
        alignment: (b.align[i] === "r") ? AlignmentType.RIGHT : AlignmentType.LEFT,
        children: [new TextRun({ text: String(txt), font: FONT, size: head ? 17 : 17, bold: head, color: head ? "FFFFFF" : INK })],
      })],
    });
  const rows = [new TableRow({ tableHeader: true, cantSplit: true, children: b.header.map((h, i) => cell(h, i, true)) })];
  b.rows.forEach((r, ri) => rows.push(new TableRow({ cantSplit: true, children: r.map((v, i) => cell(v, i, false)) })));
  const out = [];
  if (b.caption) out.push(new Paragraph({ keepNext: true, spacing: { before: 160, after: 60 }, children: [run(b.caption, { size: 18, bold: true, color: MUTED })] }));
  out.push(new Table({ width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: cw, rows }));
  out.push(new Paragraph({ spacing: { after: 120 }, children: [] }));
  return out;
}

const children = [];
// Title block
children.push(new Paragraph({ spacing: { before: 0, after: 80 }, children: [new TextRun({ text: "Fintech Business Insights Report", font: FONT, size: 44, bold: true, color: NAVY })] }));
children.push(new Paragraph({ spacing: { after: 60 }, children: [run("Customer acquisition, funnel, retention, campaigns and support: growth analytics on a synthetic retail-brokerage dataset", { size: 24, color: MUTED })] }));
children.push(new Paragraph({ spacing: { after: 60 }, children: [run("Prepared by Yash Sharma  |  Portfolio project  |  Snapshot date 2026-10-31", { size: 19, color: MUTED })] }));
children.push(new Paragraph({
  spacing: { before: 120, after: 200 }, border: { top: { style: BorderStyle.SINGLE, size: 8, color: BLUE, space: 6 } },
  children: [run("SYNTHETIC DATA: fictional dataset of 10,000 users. Not real customer, company or market data. No revenue, profit or ROI is calculated.", { size: 19, bold: true, color: "9A3412" })],
}));
children.push(new Paragraph({ spacing: { before: 120, after: 100 }, children: [run("Contents", { size: 26, bold: true, color: NAVY })] }));
["1. Executive summary", "2. Business context", "3. Data and methodology", "4. Acquisition", "5. Conversion funnel", "6. Retention", "7. Customer segmentation", "8. Campaign performance", "9. Customer support", "10. Proposed growth experiments", "11. Strategic recommendations", "12. Limitations and next steps"]
  .forEach((t) => children.push(new Paragraph({ spacing: { after: 50 }, children: [run(t, { size: 22 })] })));
children.push(new Paragraph({ children: [new PageBreak()] }));

for (const b of blocks) {
  if (b.type === "h1") {
    children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: b.text })] }));
  } else if (b.type === "h2") {
    children.push(new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: b.text })] }));
  } else if (b.type === "p") {
    children.push(new Paragraph({ spacing: { after: 120, line: 288 }, children: [run(b.text)] }));
  } else if (b.type === "note") {
    children.push(new Paragraph({
      spacing: { before: 60, after: 140, line: 276 }, shading: { fill: "FFF4CC", type: ShadingType.CLEAR, color: "auto" },
      border: { left: { style: BorderStyle.SINGLE, size: 18, color: "EDA100", space: 8 } }, indent: { left: 140 },
      children: [run(b.text, { size: 19 })],
    }));
  } else if (b.type === "bullets") {
    b.items.forEach((t) => children.push(new Paragraph({ numbering: { reference: "bul", level: 0 }, spacing: { after: 70, line: 276 }, children: [run(t)] })));
    children.push(new Paragraph({ spacing: { after: 60 }, children: [] }));
  } else if (b.type === "table") {
    children.push(...table(b));
  } else if (b.type === "img") {
    const { w, h } = pngSize(b.file);
    const wpx = Math.round(b.width * 96), hpx = Math.round(wpx * h / w);
    children.push(new Paragraph({ keepNext: true, alignment: AlignmentType.CENTER, spacing: { before: 120, after: 40 },
      children: [new ImageRun({ type: "png", data: fs.readFileSync(b.file), transformation: { width: wpx, height: hpx },
        altText: { title: b.caption, description: b.caption, name: path.basename(b.file) } })] }));
    children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 }, children: [run(b.caption, { size: 17, italics: true, color: MUTED })] }));
  }
}

const doc = new Document({
  creator: "Yash Sharma", title: "Fintech Business Insights Report (synthetic data)",
  styles: {
    default: { document: { run: { font: FONT, size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 32, bold: true, color: NAVY }, paragraph: { spacing: { before: 320, after: 140 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 25, bold: true, color: BLUE }, paragraph: { spacing: { before: 220, after: 100 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1300, bottom: 1200, left: 1440, right: 1440 } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [run("Fintech Growth Analytics  |  SYNTHETIC DATA", { size: 16, color: MUTED })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [run("Page ", { size: 16, color: MUTED }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: MUTED })] })] }) },
    children,
  }],
});
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(path.join(REPORTS, "Fintech_Business_Insights_Report.docx"), buf); console.log("docx written"); });
