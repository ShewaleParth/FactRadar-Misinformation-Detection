import jsPDF from "jspdf";
import html2canvas from "html2canvas";

export default async function generatePDF(result) {
  if (!result) return;

  const pdf = new jsPDF("p", "pt", "a4");
  
  // Title
  pdf.setFontSize(22);
  pdf.text("Fact-Check Report", 40, 50);

  pdf.setFontSize(12);
  pdf.text(`Claim: ${result.claim}`, 40, 100);
  pdf.text(`Final Verdict: ${result.final_label}`, 40, 130);
  pdf.text(`Trust Score: ${result.trust_score}%`, 40, 160);

  pdf.text("Model Decisions:", 40, 200);
  pdf.text(`- ML (MNLI): ${result.ml_label}`, 60, 220);
  pdf.text(`- Gemini: ${result.gemini_label}`, 60, 240);
  pdf.text(`- LLaMA: ${result.openrouter_label}`, 60, 260);

  pdf.setFontSize(14);
  pdf.text("Summary:", 40, 310);
  pdf.setFontSize(11);
  pdf.text(result.summary, 40, 330, { maxWidth: 520 });

  pdf.setFontSize(14);
  pdf.text("Evidence Sources:", 40, 450);
  pdf.setFontSize(11);

  let y = 470;
  result.evidence.forEach((ev, idx) => {
    pdf.text(`${idx + 1}. ${ev.title}`, 40, y);
    pdf.text(ev.link, 40, y + 15);
    y += 40;
  });

  pdf.save("FactCheck_Report.pdf");
}
