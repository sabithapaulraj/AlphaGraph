import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Component for individual news analysis card
const NewsCard = ({ analysis }) => {
  const getSentimentColor = (sentiment) => {
    switch (sentiment) {
      case 'BULLISH': return 'text-green-600 bg-green-50';
      case 'BEARISH': return 'text-red-600 bg-red-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const getImpactColor = (score) => {
    if (score >= 8) return 'text-red-600 bg-red-100';
    if (score >= 6) return 'text-orange-600 bg-orange-100';
    if (score >= 4) return 'text-yellow-600 bg-yellow-100';
    return 'text-green-600 bg-green-100';
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-4 border-l-4 border-blue-500">
      <div className="flex justify-between items-start mb-3">
        <h3 className="text-lg font-semibold text-gray-900 line-clamp-2">
          {analysis.headline}
        </h3>
        <div className="flex space-x-2 ml-4">
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getSentimentColor(analysis.sentiment_label)}`}>
            {analysis.sentiment_label}
          </span>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getImpactColor(analysis.impact_score)}`}>
            Impact: {analysis.impact_score}/10
          </span>
        </div>
      </div>
      
      <p className="text-gray-600 text-sm mb-3 line-clamp-3">
        {analysis.content}
      </p>
      
      {analysis.mentioned_companies && analysis.mentioned_companies.length > 0 && (
        <div className="mb-3">
          <span className="text-sm font-medium text-gray-700">Companies: </span>
          <div className="flex flex-wrap gap-1 mt-1">
            {analysis.mentioned_companies.map((company, idx) => (
              <span key={idx} className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">
                {company}
              </span>
            ))}
          </div>
        </div>
      )}
      
      {analysis.key_points && analysis.key_points.length > 0 && (
        <div className="mb-3">
          <span className="text-sm font-medium text-gray-700">Key Points:</span>
          <ul className="list-disc list-inside text-sm text-gray-600 mt-1">
            {analysis.key_points.slice(0, 3).map((point, idx) => (
              <li key={idx} className="mb-1">{point}</li>
            ))}
          </ul>
        </div>
      )}
      
      <div className="flex justify-between items-center text-xs text-gray-500">
        <span>Source: {analysis.source}</span>
        <span>{new Date(analysis.analysis_timestamp).toLocaleString()}</span>
      </div>
    </div>
  );
};

// Component for trending companies
const TrendingCompanies = ({ trending }) => {
  const getSentimentIcon = (sentiment) => {
    if (sentiment > 0.2) return '📈';
    if (sentiment < -0.2) return '📉';
    return '➡️';
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">🔥 Trending Companies (24h)</h2>
      {trending.length === 0 ? (
        <p className="text-gray-500 text-center py-4">No trending data available</p>
      ) : (
        <div className="space-y-3">
          {trending.slice(0, 8).map((item, idx) => (
            <div key={idx} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center space-x-3">
                <span className="text-lg">{getSentimentIcon(item.avg_sentiment)}</span>
                <div>
                  <span className="font-medium text-gray-900">{item._id}</span>
                  <div className="text-sm text-gray-500">
                    {item.count} mentions • Impact: {item.avg_impact?.toFixed(1) || 'N/A'}
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className={`text-sm font-medium ${
                  item.avg_sentiment > 0.2 ? 'text-green-600' : 
                  item.avg_sentiment < -0.2 ? 'text-red-600' : 'text-gray-600'
                }`}>
                  {item.avg_sentiment > 0 ? '+' : ''}{(item.avg_sentiment * 100).toFixed(0)}%
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// Main Dashboard Component
const Dashboard = () => {
  const [analyses, setAnalyses] = useState([]);
  const [trending, setTrending] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [newArticle, setNewArticle] = useState({
    headline: '',
    content: '',
    source: 'Manual Entry'
  });

  // Load dashboard data
  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [analysesRes, trendingRes, companiesRes] = await Promise.all([
        axios.get(`${API}/news/recent?limit=10`),
        axios.get(`${API}/trends`),
        axios.get(`${API}/companies`)
      ]);
      
      setAnalyses(analysesRes.data);
      setTrending(trendingRes.data.trending_companies || []);
      setCompanies(companiesRes.data.companies || []);
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Populate sample data for demo
  const populateSampleData = async () => {
    try {
      setAnalyzing(true);
      await axios.post(`${API}/demo/populate`);
      await loadDashboardData();
    } catch (error) {
      console.error('Error populating sample data:', error);
    } finally {
      setAnalyzing(false);
    }
  };

  // Analyze new article
  const analyzeArticle = async () => {
    if (!newArticle.headline.trim() || !newArticle.content.trim()) {
      alert('Please provide both headline and content');
      return;
    }

    try {
      setAnalyzing(true);
      const response = await axios.post(`${API}/analyze`, newArticle);
      setAnalyses([response.data, ...analyses.slice(0, 9)]);
      setNewArticle({ headline: '', content: '', source: 'Manual Entry' });
      
      // Refresh trending data
      const trendingRes = await axios.get(`${API}/trends`);
      setTrending(trendingRes.data.trending_companies || []);
    } catch (error) {
      console.error('Error analyzing article:', error);
      alert('Analysis failed. Please try again.');
    } finally {
      setAnalyzing(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading AlphaGraph...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-xl">α</span>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">AlphaGraph</h1>
                <p className="text-sm text-gray-500">AI-Powered Financial News Analytics</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={loadDashboardData}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                disabled={loading}
              >
                🔄 Refresh
              </button>
              {analyses.length === 0 && (
                <button
                  onClick={populateSampleData}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                  disabled={analyzing}
                >
                  {analyzing ? '🤖 Analyzing...' : '📊 Load Sample Data'}
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content - News Analysis */}
          <div className="lg:col-span-2">
            {/* Add New Article Form */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-8">
              <h2 className="text-xl font-bold text-gray-900 mb-4">🔍 Analyze News Article</h2>
              <div className="space-y-4">
                <input
                  type="text"
                  placeholder="Enter news headline..."
                  value={newArticle.headline}
                  onChange={(e) => setNewArticle({...newArticle, headline: e.target.value})}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <textarea
                  placeholder="Paste news article content here..."
                  value={newArticle.content}
                  onChange={(e) => setNewArticle({...newArticle, content: e.target.value})}
                  rows={4}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                />
                <div className="flex justify-between items-center">
                  <input
                    type="text"
                    placeholder="Source (e.g., Bloomberg, Reuters)"
                    value={newArticle.source}
                    onChange={(e) => setNewArticle({...newArticle, source: e.target.value})}
                    className="flex-1 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent mr-4"
                  />
                  <button
                    onClick={analyzeArticle}
                    disabled={analyzing || !newArticle.headline.trim() || !newArticle.content.trim()}
                    className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
                  >
                    {analyzing ? '🤖 Analyzing...' : '🚀 Analyze'}
                  </button>
                </div>
              </div>
            </div>

            {/* Recent Analysis */}
            <div>
              <h2 className="text-xl font-bold text-gray-900 mb-6">📈 Recent Analysis</h2>
              {analyses.length === 0 ? (
                <div className="bg-white rounded-lg shadow-md p-8 text-center">
                  <div className="text-6xl mb-4">📰</div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No Analysis Yet</h3>
                  <p className="text-gray-500 mb-4">
                    Get started by analyzing a news article above or loading sample data.
                  </p>
                </div>
              ) : (
                <div>
                  {analyses.map((analysis, idx) => (
                    <NewsCard key={analysis.id || idx} analysis={analysis} />
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-8">
            {/* Trending Companies */}
            <TrendingCompanies trending={trending} />

            {/* Tracked Companies */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">🏢 Tracked Companies</h2>
              <div className="text-sm text-gray-500 mb-4">
                Monitoring {companies.length} Fortune 500 companies
              </div>
              <div className="max-h-64 overflow-y-auto">
                <div className="space-y-2">
                  {companies.slice(0, 15).map((company, idx) => (
                    <div key={idx} className="flex justify-between items-center p-2 hover:bg-gray-50 rounded">
                      <div>
                        <div className="font-medium text-sm">{company.symbol}</div>
                        <div className="text-xs text-gray-500 truncate">{company.name}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              {companies.length > 15 && (
                <div className="text-xs text-gray-500 text-center mt-2">
                  +{companies.length - 15} more companies
                </div>
              )}
            </div>

            {/* Stats Card */}
            <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg shadow-md p-6 text-white">
              <h2 className="text-lg font-bold mb-4">📊 Platform Stats</h2>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span>Total Analyses:</span>
                  <span className="font-bold">{analyses.length}</span>
                </div>
                <div className="flex justify-between">
                  <span>Companies Tracked:</span>
                  <span className="font-bold">{companies.length}</span>
                </div>
                <div className="flex justify-between">
                  <span>AI Model:</span>
                  <span className="font-bold">Gemini Pro</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <Dashboard />
    </div>
  );
}

export default App;