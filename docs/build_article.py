"""Build the documentary article with ReportLab, without importing ML code.

Run with a document runtime containing reportlab and pypdf; those dependencies
are deliberately separate from the project's validated inference environment.
"""

import csv
import hashlib
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate,
    Paragraph, Preformatted, Spacer, Table, TableStyle, Flowable, CondPageBreak,
)
from reportlab.platypus.tableofcontents import TableOfContents


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "articles"
VALIDATION = ROOT / "docs" / "validation"
TEMPLATE = ROOT / "docs" / "artigo_recife_rain_nowcasting.md"
PDF_PATH = OUT / "artigo_recife_rain_nowcasting.pdf"
TEAL = colors.HexColor("#165950")
INK = colors.HexColor("#233432")
LIGHT = colors.HexColor("#F0F5F3")
WIDTH = A4[0] - 40 * mm


def records(name):
    with (VALIDATION / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def md_table(headers, rows):
    return "\n".join([
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
        *("| " + " | ".join(map(str, row)) + " |" for row in rows),
    ])


def dec(value, digits=3):
    return f"{float(value):.{digits}f}".replace(".", ",")


def count(value):
    return f"{int(value):,}".replace(",", ".")


def materialize():
    current = records("corrected_final_evaluation_results.csv")
    historical = records("final_results_comparison.csv")
    audit = records("temporal_boundary_audit.csv")
    config = json.loads((VALIDATION / "validated_configurations.json").read_text(encoding="utf-8"))
    metadata = json.loads((ROOT / "models" / "model_metadata.json").read_text(encoding="utf-8"))
    checks = json.loads((VALIDATION / "productionization_checks.json").read_text(encoding="utf-8"))
    assert len(current) == len(historical) == 6 and len(audit) == 30
    assert sum(len(v) for v in [metadata["feature_columns"]]) == 20
    assert all(int(r["removed_samples"]) == int(r["horizon_hours"]) and int(r["removed_positives"]) == 0 for r in audit)
    assert checks["tests"]["original_notebook_environment"]["tests_run"] == 38
    assert checks["tests"]["clean_runtime_environment"]["skips"] == 0
    for row in current:
        h = row["horizon_hours"]
        assert float(row["threshold"]) == config["configurations"][h]["threshold"]
        assert row["model"] == config["configurations"][h]["model_name"]
        assert int(row["true_positives"]) + int(row["false_negatives"]) == int(row["test_positives"]) == 38
    names = {"logistic_regression": "LR", "random_forest": "RF"}
    replacement = {}
    replacement["CONFIG_TABLE"] = md_table(
        ["Horizonte", "Família", "C", "Profundidade RF", "Folha mínima RF", "Threshold"],
        [[f"+{h}h", names[c["model_name"]], dec(c["C"], 2) if "C" in c else "-",
          "None" if c.get("max_depth", "-") is None else c.get("max_depth", "-"),
          c.get("min_samples_leaf", "-"), dec(c["threshold"], 2)] for h, c in config["configurations"].items()],
    )
    replacement["COUNTS_TABLE"] = md_table(
        ["Horizonte", "Treino", "Positivos treino", "Teste", "Positivos teste"],
        [[f"+{r['horizon_hours']}h", count(r["train_samples"]), r["train_positives"], count(r["test_samples"]), r["test_positives"]] for r in current],
    )
    metrics = ["precision", "recall", "f1", "csi", "average_precision", "roc_auc"]
    replacement["METRICS_TABLE"] = md_table(
        ["Horizonte", "Precisão", "Recall", "F1", "CSI", "AP", "ROC-AUC"],
        [[f"+{r['horizon_hours']}h", *[dec(r[k]) for k in metrics]] for r in current],
    )
    confusion = ["true_positives", "false_positives", "false_negatives", "true_negatives"]
    replacement["CONFUSION_TABLE"] = md_table(
        ["Horizonte", "TP", "FP", "FN", "TN"],
        [[f"+{r['horizon_hours']}h", *[count(r[k]) for k in confusion]] for r in current],
    )
    replacement["HISTORY_CONFIG_TABLE"] = md_table(
        ["Horizonte", "Família antiga", "Threshold antigo", "Família corrigida", "Threshold corrigido"],
        [[f"+{r['horizon_hours']}h", names[r["model_historical"]], dec(r["threshold_historical"], 2),
          names[r["model_corrected"]], dec(r["threshold_corrected"], 2)] for r in historical],
    )
    replacement["HISTORY_METRICS_TABLE"] = md_table(
        ["Horizonte", "Precisão", "Recall", "F1", "CSI", "AP", "ROC-AUC"],
        [[f"+{r['horizon_hours']}h", *[f"{dec(r[k+'_historical'])} / {dec(r[k+'_corrected'])}" for k in metrics]] for r in historical],
    )
    replacement["HISTORY_CONFUSION_TABLE"] = md_table(
        ["Horizonte", "TP", "FP", "FN", "TN"],
        [[f"+{r['horizon_hours']}h", *[f"{count(r[k+'_historical'])} / {count(r[k+'_corrected'])}" for k in confusion]] for r in historical],
    )
    descriptions = [
        "Precipitação corrente em t", "Temperatura corrente em t", "Umidade relativa corrente em t",
        "Pressão atmosférica na estação em t", "Seno do ciclo da hora UTC (24h)",
        "Cosseno do ciclo da hora UTC (24h)", "Seno do ciclo anual (dia UTC / 365,25)",
        "Cosseno do ciclo anual (dia UTC / 365,25)", "Precipitação em t-1h",
        "Precipitação em t-2h", "Precipitação em t-3h", "Precipitação em t-6h",
        "Soma de precipitação em t-2h até t", "Soma de precipitação em t-5h até t",
        "Temperatura em t-1h", "Umidade relativa em t-1h", "Pressão na estação em t-1h",
        "Temperatura em t menos t-1h", "Umidade em t menos t-1h", "Pressão em t menos t-1h",
    ]
    replacement["FEATURE_TABLE"] = md_table(
        ["Ordem", "Feature", "Definição"],
        [[i, name, description] for i, (name, description) in enumerate(zip(metadata["feature_columns"], descriptions), 1)],
    )
    periods = {
        "2018_to_2019_train": "Fold 1: treino 2018",
        "2018_to_2019_validation": "Fold 1: validação 2019",
        "2018_2019_to_2020_train": "Fold 2: treino 2018-2019",
        "2018_2019_to_2020_validation": "Fold 2: validação 2020",
        "final_train_2018_2020": "Treino final 2018-2020",
    }
    replacement["BOUNDARY_COUNTS_TABLE"] = md_table(
        ["Uso da partição", "+1h", "+2h", "+3h", "+4h", "+5h", "+6h"],
        [[label, *[f"{count(r['corrected_samples'])} / {r['corrected_positives']}" for r in sorted(audit, key=lambda x: int(x['horizon_hours'])) if r['period'] == period]]
         for period, label in periods.items()],
    )
    dependencies = [line.strip().split("==") for line in (ROOT / "requirements.txt").read_text().splitlines() if "==" in line]
    replacement["DEPENDENCY_TABLE"] = md_table(["Pacote de execução", "Versão"], dependencies)
    replacement["ARCHITECTURE_FIGURE"] = "![Arquitetura científica e inferência](article:architecture)"
    replacement["APPLICATION_FIGURE"] = "![Protótipo com entrada sintética](../../docs/figures/application-prototype.jpg)"
    content = TEMPLATE.read_text(encoding="utf-8")
    for name, value in replacement.items():
        assert "{{" + name + "}}" in content
        content = content.replace("{{" + name + "}}", value)
    assert "{{" not in content
    return content.rstrip() + "\n", config, metadata, checks


def inline(text):
    result = escape(text)
    result = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", result)
    result = re.sub(r"https://[^\s<]+", lambda m: f'<link href="{m[0].rstrip(chr(46))}" color="#165950">{m[0]}</link>', result)
    return result


class Architecture(Flowable):
    def __init__(self):
        super().__init__()
        self.width, self.height = WIDTH, 210

    def draw(self):
        c = self.canv
        box_width = (WIDTH - 20) / 2
        columns = [
            (0, "Pesquisa histórica (offline)", ["Observações auditadas 2018-2021", "Features e alvos com fronteiras seguras", "Validação pré-2021 e escolhas congeladas", "Ajuste 2018-2020; teste histórico 2021", "Seis artefatos + metadados"]),
            (box_width + 20, "Inferência implementada", ["Histórico fornecido de t-6h até t", "20 features causais e validação", "Carregamento dos seis artefatos", "Scores + thresholds fixos", "Interface web + JSON"]),
        ]
        for x, title, boxes in columns:
            c.setFont("Sans-Bold", 10)
            c.setFillColor(TEAL)
            c.drawCentredString(x + box_width/2, 199, title)
            for i, label in enumerate(boxes):
                y = 161 - i*35
                c.setStrokeColor(colors.HexColor("#A7C4BB"))
                c.setFillColor(LIGHT)
                c.roundRect(x, y, box_width, 27, 5, fill=1, stroke=1)
                c.setFillColor(INK)
                c.setFont("Sans", 8)
                c.drawCentredString(x + box_width/2, y+10, label)
                if i < 4:
                    c.setStrokeColor(TEAL)
                    cx = x + box_width/2
                    c.line(cx, y, cx, y-8)
                    c.line(cx, y-8, cx-2.5, y-5)
                    c.line(cx, y-8, cx+2.5, y-5)


def styles():
    for name, filename in [("Serif", "times.ttf"), ("Serif-Bold", "timesbd.ttf"), ("Serif-Italic", "timesi.ttf"),
                           ("Sans", "arial.ttf"), ("Sans-Bold", "arialbd.ttf")]:
        pdfmetrics.registerFont(TTFont(name, str(Path("C:/Windows/Fonts") / filename)))
    pdfmetrics.registerFontFamily("Serif", normal="Serif", bold="Serif-Bold", italic="Serif-Italic", boldItalic="Serif-Bold")
    pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="Sans-Bold", italic="Sans", boldItalic="Sans-Bold")
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("ArticleBody", fontName="Serif", fontSize=11.2, leading=15.4, alignment=TA_JUSTIFY,
                         textColor=INK, spaceAfter=8, allowWidows=0, allowOrphans=0, splitLongWords=1))
    s.add(ParagraphStyle("ArticleTitle", fontName="Sans-Bold", fontSize=23, leading=28,
                         textColor=TEAL, spaceAfter=18))
    s.add(ParagraphStyle("ArticleSection", fontName="Sans-Bold", fontSize=14.5, leading=19,
                         textColor=TEAL, spaceBefore=6, spaceAfter=13, keepWithNext=True))
    s.add(ParagraphStyle("ArticleSub", fontName="Sans-Bold", fontSize=11.2, leading=15,
                         textColor=TEAL, spaceBefore=11, spaceAfter=8, keepWithNext=True))
    s.add(ParagraphStyle("ArticleCaption", fontName="Serif-Italic", fontSize=9, leading=12,
                         textColor=INK, spaceAfter=11, alignment=TA_LEFT))
    s.add(ParagraphStyle("ArticleReference", fontName="Serif", fontSize=9.5, leading=12.5,
                         textColor=INK, spaceAfter=6, alignment=TA_LEFT, splitLongWords=1))
    s.add(ParagraphStyle("TableBody", fontName="Sans", fontSize=8.4, leading=11.3,
                         textColor=INK, alignment=TA_LEFT, splitLongWords=1))
    s.add(ParagraphStyle("TableHeader", parent=s["TableBody"], fontName="Sans-Bold", textColor=colors.white))
    s.add(ParagraphStyle("ArticleCode", fontName="Courier", fontSize=8.0, leading=11,
                         leftIndent=8, rightIndent=8, backColor=LIGHT, borderPadding=8, spaceBefore=6, spaceAfter=12))
    return s


def make_table(lines, s):
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
    rows = [row for row in rows if not all(re.fullmatch(r"[:\-]+", cell) for cell in row)]
    column_count = len(rows[0])
    # Reserve more room for explanatory/path columns; keep numerical comparisons legible.
    if column_count == 2:
        weights = [0.42, 0.58]
    elif rows[0][0] == "Ordem":
        weights = [0.10, 0.45, 0.45]
    elif rows[0][0] == "Cluster":
        weights = [0.09, 0.23, 0.12, 0.12, 0.13, 0.16, 0.15]
    elif rows[0][0] == "Uso da partição":
        weights = [0.28] + [0.12]*6
    elif rows[0][0].startswith("Uso da partição e"):
        weights = [0.40] + [0.10]*6
    elif column_count == 3:
        weights = [0.36, 0.12, 0.52]
    else:
        weights = [1/column_count]*column_count
    paragraphs = [[Paragraph(inline(cell), s["TableHeader"] if i == 0 else s["TableBody"]) for cell in row] for i, row in enumerate(rows)]
    table = Table(paragraphs, colWidths=[WIDTH*weight for weight in weights], repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), TEAL), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, LIGHT]),
        ("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6), ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7), ("LINEBELOW", (0,-1), (-1,-1), .5, TEAL),
    ]))
    return table


class ArticleDocument(BaseDocTemplate):
    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name == "ArticleSection":
            text = flowable.getPlainText()
            if text != "Sumário":
                key = "section-" + hashlib.sha256(text.encode()).hexdigest()[:12]
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, level=0, closed=False)
                self.notify("TOCEntry", (0, text, self.page, key))


def page_frame(canvas, document):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(TEAL)
    canvas.setFont("Sans-Bold", 8)
    canvas.drawString(20*mm, h-13*mm, "RECIFE RAIN NOWCASTING ML")
    canvas.setFont("Sans", 8)
    canvas.drawRightString(w-20*mm, h-13*mm, "ARTIGO TÉCNICO | 13/10/2026")
    canvas.setStrokeColor(colors.HexColor("#B7CBC5"))
    canvas.line(20*mm, h-15*mm, w-20*mm, h-15*mm)
    canvas.line(20*mm, 15*mm, w-20*mm, 15*mm)
    canvas.setFillColor(INK)
    canvas.setFont("Sans", 7.4)
    canvas.drawString(20*mm, 10.5*mm, "A301 Recife | Metodologia corrigida e protótipo local")
    canvas.drawRightString(w-20*mm, 10.5*mm, str(document.page))
    canvas.restoreState()


def render(content):
    s = styles()
    doc = ArticleDocument(str(PDF_PATH), pagesize=A4, leftMargin=20*mm, rightMargin=20*mm,
                          topMargin=22*mm, bottomMargin=21*mm, title="Previsão de chuva severa em Recife com aprendizado de máquina",
                          author="Projeto Recife Rain Nowcasting ML", subject="Metodologia, resultados e desenvolvimento da aplicação",
                          pageCompression=1)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates(PageTemplate(id="article", frames=frame, onPage=page_frame))
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle("TocEntry", fontName="Sans", fontSize=9.5, leading=13.5,
                                     textColor=INK, spaceBefore=5, leftIndent=0, firstLineIndent=0)]
    story = []
    lines = content.splitlines()
    i = 0
    sections = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("# "):
            story.append(Paragraph(inline(line[2:]), s["ArticleTitle"]))
        elif line.startswith("## "):
            if sections == 1:
                story.extend([PageBreak(), Paragraph("Sumário", s["ArticleSection"]), toc, PageBreak()])
            elif sections > 1:
                if line.startswith("## Apêndice A"):
                    story.append(PageBreak())
                else:
                    story.extend([Spacer(1,14), CondPageBreak(165)])
            story.append(Paragraph(inline(line[3:]), s["ArticleSection"]))
            sections += 1
        elif line.startswith("### "):
            story.append(Paragraph(inline(line[4:]), s["ArticleSub"]))
        elif line.startswith("```"):
            block = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            assert all(len(code_line) <= 98 for code_line in block), "Code line too long"
            story.append(Preformatted("\n".join(block), s["ArticleCode"]))
        elif line.startswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i])
                i += 1
            caption = None
            lookahead = i
            while lookahead < len(lines) and not lines[lookahead].strip():
                lookahead += 1
            if lookahead < len(lines) and lines[lookahead].startswith("Tabela "):
                caption = Paragraph(inline(lines[lookahead]), s["ArticleCaption"])
                i = lookahead+1
            table = make_table(block, s)
            story.append(KeepTogether([table, Spacer(1,5), caption]) if caption else table)
            story.append(Spacer(1,8))
            continue
        elif line.startswith("!["):
            if "article:architecture" in line:
                graphic = Architecture()
            else:
                image_path = ROOT / "docs" / "figures" / "application-prototype.jpg"
                graphic = Image(str(image_path))
                factor = min(WIDTH/graphic.imageWidth, 475/graphic.imageHeight)
                graphic.drawWidth, graphic.drawHeight = graphic.imageWidth*factor, graphic.imageHeight*factor
            lookahead = i+1
            while lookahead < len(lines) and not lines[lookahead].strip():
                lookahead += 1
            group = [graphic, Spacer(1,7)]
            if lookahead < len(lines) and lines[lookahead].startswith("Figura "):
                group.append(Paragraph(inline(lines[lookahead]), s["ArticleCaption"]))
                i = lookahead
            story.append(KeepTogether(group))
        else:
            if re.match(r"\[R\d+\] ", line):
                style = s["ArticleReference"]
            else:
                style = s["ArticleCaption"] if line.startswith(("Figura ", "Tabela ")) else s["ArticleBody"]
            story.append(Paragraph(inline(line), style))
        i += 1
    doc.multiBuild(story)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    protected = [ROOT / "models" / f"model_{h}h.joblib" for h in range(1,7)] + [
        ROOT / "models" / "model_metadata.json", VALIDATION / "validated_configurations.json",
        VALIDATION / "corrected_final_evaluation_results.csv",
    ]
    before = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
    content, config, metadata, checks = materialize()
    (OUT / "artigo_recife_rain_nowcasting.md").write_text(content, encoding="utf-8")
    render(content)
    reader = PdfReader(PDF_PATH)
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "{{" not in extracted and "TBD" not in extracted
    assert all(feature in extracted for feature in metadata["feature_columns"])
    assert all(title in extracted for title in ["Referências", "Apêndice A", "Apêndice F", "38", "0,225", "dados atuais"])
    assert before == {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
    report = {
        "document_date": "2026-10-13", "pages": len(reader.pages), "words": len(content.split()),
        "pdf_sha256": hashlib.sha256(PDF_PATH.read_bytes()).hexdigest(),
        "all_20_features_present": True, "tables_derived_from_frozen_csvs": True,
        "all_30_boundary_cases_checked": True, "protected_scientific_files_unchanged": before,
        "recorded_software_tests_not_rerun": checks["tests"], "model_training_or_selection_run": False,
        "visual_review": "pending", "methodology_changed": False,
    }
    (OUT / "validacao_artigo.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"pdf": str(PDF_PATH), "pages": report["pages"], "words": report["words"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
