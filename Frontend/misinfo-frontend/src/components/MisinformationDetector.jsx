import React, { useState } from 'react';
import { AlertCircle, CheckCircle, HelpCircle, Search, ExternalLink, Shield, Brain, Zap } from 'lucide-react';

export default function MisinformationDetector() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const getLabelColor = (label) => {
    switch (label) {
      case 'REAL':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'MISINFORMATION':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'UNCERTAIN':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
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
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: url.trim() }),
      });

      if (!response.ok) {
        throw new Error('Failed to analyze claim');
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message || 'An error occurred while analyzing the claim');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !loading) {
      handleSubmit();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      <div className="max-w-6xl mx-auto p-6">
        {/* Header */}
        <div className="text-center mb-8 pt-8">
          <div className="flex items-center justify-center mb-4">
            <Shield className="w-12 h-12 text-blue-600 mr-3" />
            <h1 className="text-4xl font-bold text-gray-800">
              Misinformation Detector
            </h1>
          </div>
          <p className="text-gray-600 text-lg">
            AI-powered fact-checking using ensemble learning and medical research databases
          </p>
        </div>

        {/* Search Input */}
        <div className="bg-white rounded-2xl shadow-lg p-8 mb-8">
          <div className="flex gap-3">
            <div className="flex-1">
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Enter a claim or URL to fact-check..."
                className="w-full px-6 py-4 text-lg border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:outline-none transition"
                disabled={loading}
              />
            </div>
            <button
              onClick={handleSubmit}
              disabled={loading}
              className="px-8 py-4 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition flex items-center gap-2"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  Analyzing...
                </>
              ) : (
                <>
                  <Search className="w-5 h-5" />
                  Analyze
                </>
              )}
            </button>
          </div>

          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 flex items-center gap-2">
              <AlertCircle className="w-5 h-5" />
              {error}
            </div>
          )}
        </div>

        {/* Results */}
        {result && (
          <div className="space-y-6">
            {/* Final Verdict */}
            <div className={`bg-white rounded-2xl shadow-lg p-8 border-2 ${getLabelColor(result.final_label)}`}>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  {getLabelIcon(result.final_label)}
                  <h2 className="text-2xl font-bold">Final Verdict: {result.final_label}</h2>
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-600">Trust Score</div>
                  <div className="text-3xl font-bold">{result.trust_score}%</div>
                </div>
              </div>
              <div className="bg-white bg-opacity-50 rounded-lg p-4 mt-4">
                <p className="text-sm font-semibold text-gray-700 mb-1">Analyzed Claim:</p>
                <p className="text-gray-800">{result.claim}</p>
              </div>
            </div>



            {/* Summary */}
            <div className="bg-white rounded-2xl shadow-lg p-8">
              <h3 className="text-xl font-bold text-gray-800 mb-4">Evidence Summary</h3>
              <p className="text-gray-700 leading-relaxed">{result.summary}</p>
            </div>

            {/* Evidence Sources */}
            <div className="bg-white rounded-2xl shadow-lg p-8">
              <h3 className="text-xl font-bold text-gray-800 mb-6">Evidence Sources</h3>
              <div className="space-y-4">
                {result.evidence.map((ev, idx) => (
                  <div key={idx} className="p-5 border border-gray-200 rounded-xl hover:border-blue-300 transition">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <h4 className="font-semibold text-gray-800 mb-2">{ev.title}</h4>
                        <p className="text-sm text-gray-600 mb-3">{ev.snippet}</p>
                        <a
                          href={ev.link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-700 text-sm font-medium"
                        >
                          View Source
                          <ExternalLink className="w-4 h-4" />
                        </a>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Info Footer */}
        {!result && !loading && (
          <div className="bg-white rounded-2xl shadow-lg p-8 mt-8">
            <h3 className="text-lg font-bold text-gray-800 mb-4">How It Works</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-3">
                  <Search className="w-6 h-6 text-blue-600" />
                </div>
                <h4 className="font-semibold text-gray-800 mb-2">Evidence Retrieval</h4>
                <p className="text-sm text-gray-600">
                  Searches trusted medical sources including CDC, WHO, NIH, and leading medical institutions
                </p>
              </div>
              <div>
                <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-3">
                  <Brain className="w-6 h-6 text-purple-600" />
                </div>
                <h4 className="font-semibold text-gray-800 mb-2">AI Analysis</h4>
                <p className="text-sm text-gray-600">
                  Three AI models independently analyze the claim against evidence using natural language inference
                </p>
              </div>
              <div>
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-3">
                  <Shield className="w-6 h-6 text-green-600" />
                </div>
                <h4 className="font-semibold text-gray-800 mb-2">Ensemble Decision</h4>
                <p className="text-sm text-gray-600">
                  Results are combined using ensemble learning to provide the most accurate verdict
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}