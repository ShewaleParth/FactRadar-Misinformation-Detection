import React from "react";
import { Brain, Info } from "lucide-react";

export default function WhyExplanation({ result }) {
  if (!result) return null;

  const { ml_label, gemini_label, openrouter_label, final_label } = result;

  const explanation = `
Based on independent analysis from three reasoning engines:

• The ML (MNLI) engine classified the claim as: ${ml_label}.
• Google's Gemini model classified the claim as: ${gemini_label}.
• LLaMA cross-validation classified the claim as: ${openrouter_label}.

The system selected the final verdict "${final_label}" using ensemble voting.
This means the majority of AI agents agreed on this outcome, leading to a 
high-confidence classification backed by evidence from verified medical sources.
  `.trim();

  return (
    <div className="bg-white rounded-2xl shadow-lg p-8 border-l-4 border-blue-500">
      <div className="flex items-center gap-3 mb-3">
        <Brain className="w-6 h-6 text-blue-600" />
        <h3 className="text-xl font-bold text-gray-800">Why This Verdict?</h3>
      </div>
      <p className="text-gray-700 leading-relaxed whitespace-pre-line">
        {explanation}
      </p>
    </div>
  );
}
