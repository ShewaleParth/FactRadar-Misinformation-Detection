import React, { useState } from 'react';
import {
  AlertCircle,
  CheckCircle,
  HelpCircle,
  Search,
  ExternalLink,
  Shield
} from 'lucide-react';

import WhyExplanation from './WhyExplanation';
import ThemeToggle from './ThemeToggle';
import generatePDF from './PDFReport';

export default function MisinformationDetector() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const getLabelColor = (label) => {
    switch (label) {
      case 'REAL':
        return 'text-green-600 bg-green-50 border-green-200 dark:bg-green-900/40 dark:text-green-300';
      case 'MISINFORMATION':
        return 'text-red-600 bg-red-50 border-red-200 dark:bg-red-900/40 dark:text-red-300';
      case 'UNCERTAIN':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200 dark:bg-yellow-900/40 dark:text-yellow-300';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200 dark:bg-gray-800 dark:text-gray-300';
    }
  };

  const getLabelIcon = (label) => {
    switch (label) {
      case 'REAL':
        return <CheckCircle className="w-5 h-5" />;
      case 'MISINFORMATION':
        return <AlertCircle className="w-5 h-5" />;
      case 'UNCERTAIN':
        return <HelpCircle className="w-5 h-5" />;
      default:
        return <HelpCircle className="w-5 h-5" />;
    }
  };

  const handleSubmit = async () => {
    setError('');
    setResult(null);

    if (!url.trim()) {
      setError('Please enter a claim or URL');
      return;
    }

    setLoading(true);

    try {
      const response = await fetch('http://localhost:8000/detect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() }),
      });

      if (!response.ok) throw new Error('Failed to analyze claim');

      const data = await response.json();
      setResult(data);

    } catch (err) {
      setError(err.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !loading) handleSubmit();
  };

  return (
    <div
      className="min-h-screen bg-gradient-to-br 
      from-blue-50 via-white to-purple-50 
      dark:from-gray-900 dark:via-gray-950 dark:to-black 
      transition-all duration-300"
    >
      <div className="max-w-6xl mx-auto p-6">

        {/* Theme Toggle */}
        <div className="flex justify-end mb-4">
          <ThemeToggle />
        </div>

        {/* Header */}
        <div className="text-center mb-8 pt-2">
          <div className="flex items-center justify-center mb-4">
            <Shield className="w-12 h-12 text-blue-600 dark:text-blue-400 mr-3" />
            <h1 className="text-4xl font-bold text-gray-800 dark:text-gray-100">
              Misinformation Detector
            </h1>
          </div>
          <p className="text-gray-600 dark:text-gray-300 text-lg">
            AI-powered fact-checking using ensemble learning and verified research sources
          </p>
        </div>

        {/* Input */}
        <div
          className="bg-white dark:bg-gray-900 rounded-2xl shadow-lg 
          p-8 mb-8 border border-gray-200 dark:border-gray-700"
        >
          <div className="flex gap-3">
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Enter a claim or URL to fact-check..."
              className="w-full px-6 py-4 text-lg border-2 border-gray-200 
              dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100 
              rounded-xl focus:border-blue-500 dark:focus:border-blue-400 
              transition"
              disabled={loading}
            />

            <button
              onClick={handleSubmit}
              disabled={loading}
              className="px-8 py-4 bg-blue-600 text-white rounded-xl font-semibold 
              hover:bg-blue-700 disabled:bg-gray-400 
              transition flex items-center gap-2"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  Analyzing...
                </>
              ) : (
                <>
                  <Search className="w-5 h-5" /> Analyze
                </>
              )}
            </button>
          </div>

          {error && (
            <div
              className="mt-4 p-4 bg-red-50 dark:bg-red-900/40 
              border border-red-200 dark:border-red-700 
              rounded-lg text-red-700 dark:text-red-300 
              flex items-center gap-2"
            >
              <AlertCircle className="w-5 h-5" /> {error}
            </div>
          )}
        </div>

        {/* Results */}
        {result && (
          <div className="space-y-6">

            {/* Verdict */}
            <div
              className={`rounded-2xl shadow-lg p-8 border-2 ${getLabelColor(
                result.final_label
              )}`}
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  {getLabelIcon(result.final_label)}
                  <h2 className="text-2xl font-bold dark:text-gray-100">
                    Final Verdict: {result.final_label}
                  </h2>
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-600 dark:text-gray-300">Trust Score</p>
                  <p className="text-3xl font-bold dark:text-gray-100">
                    {result.trust_score}%
                  </p>
                </div>
              </div>

              <div
                className="bg-white dark:bg-gray-800 rounded-lg p-4 mt-4 
                border border-gray-200 dark:border-gray-700"
              >
                <p className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">
                  Analyzed Claim:
                </p>
                <p className="text-gray-800 dark:text-gray-100">{result.claim}</p>
              </div>
            </div>

            {/* Summary */}
            <div
              className="bg-white dark:bg-gray-900 rounded-2xl shadow-lg p-8 
              border border-gray-200 dark:border-gray-700"
            >
              <h3 className="text-xl font-bold text-gray-800 dark:text-gray-100 mb-4">
                Evidence Summary
              </h3>
              <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
                {result.summary}
              </p>
            </div>

            {/* Why Explanation */}
            <WhyExplanation result={result} />

            {/* PDF Download */}
            <div className="flex justify-end">
              <button
                onClick={() => generatePDF(result)}
                className="px-6 py-3 bg-green-600 text-white rounded-xl font-semibold 
                hover:bg-green-700 transition"
              >
                Download PDF Report
              </button>
            </div>

            {/* Evidence */}
            <div
              className="bg-white dark:bg-gray-900 rounded-2xl shadow-lg p-8 
              border border-gray-200 dark:border-gray-700"
            >
              <h3 className="text-xl font-bold text-gray-800 dark:text-gray-100 mb-6">
                Evidence Sources
              </h3>

              <div className="space-y-4">
                {result.evidence.map((ev, idx) => (
                  <div
                    key={idx}
                    className="p-5 border border-gray-200 dark:border-gray-700 
                    rounded-xl hover:border-blue-300 dark:hover:border-blue-500 
                    transition"
                  >
                    <h4 className="font-semibold text-gray-800 dark:text-gray-100 mb-2">
                      {ev.title}
                    </h4>
                    <p className="text-sm text-gray-600 dark:text-gray-300 mb-3">
                      {ev.snippet}
                    </p>

                    <a
                      href={ev.link}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 
                      text-blue-600 dark:text-blue-400 hover:text-blue-700 
                      dark:hover:text-blue-300 text-sm font-medium"
                    >
                      View Source <ExternalLink className="w-4 h-4" />
                    </a>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
