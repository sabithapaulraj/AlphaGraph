from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import asyncio
import json
import httpx
import re
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="AlphaGraph - Financial News Analysis API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configuration
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
if not GEMINI_API_KEY:
    logging.warning("GEMINI_API_KEY not found in environment variables")

# Fortune 500 and popular companies
TRACKED_COMPANIES = [
    # US Fortune 500 Tech Giants
    {"symbol": "AAPL", "name": "Apple Inc."},
    {"symbol": "GOOGL", "name": "Alphabet Inc."},
    {"symbol": "MSFT", "name": "Microsoft Corporation"},
    {"symbol": "AMZN", "name": "Amazon.com Inc."},
    {"symbol": "TSLA", "name": "Tesla Inc."},
    {"symbol": "META", "name": "Meta Platforms Inc."},
    {"symbol": "NVDA", "name": "NVIDIA Corporation"},
    {"symbol": "NFLX", "name": "Netflix Inc."},
    {"symbol": "CRM", "name": "Salesforce Inc."},
    {"symbol": "ORCL", "name": "Oracle Corporation"},
    
    # Financial Services
    {"symbol": "JPM", "name": "JPMorgan Chase & Co."},
    {"symbol": "BAC", "name": "Bank of America Corp."},
    {"symbol": "WFC", "name": "Wells Fargo & Company"},
    {"symbol": "GS", "name": "Goldman Sachs Group Inc."},
    {"symbol": "MS", "name": "Morgan Stanley"},
    
    # Healthcare & Pharma
    {"symbol": "JNJ", "name": "Johnson & Johnson"},
    {"symbol": "PFE", "name": "Pfizer Inc."},
    {"symbol": "UNH", "name": "UnitedHealth Group Inc."},
    {"symbol": "CVS", "name": "CVS Health Corporation"},
    {"symbol": "ABBV", "name": "AbbVie Inc."},
    
    # Indian Companies (ADRs)
    {"symbol": "INFY", "name": "Infosys Limited"},
    {"symbol": "WIT", "name": "Wipro Limited"},
    {"symbol": "HDB", "name": "HDFC Bank Limited"},
    {"symbol": "IBN", "name": "ICICI Bank Limited"},
    {"symbol": "TTM", "name": "Tata Motors Limited"},
]

# Define Models
class NewsAnalysis(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    headline: str
    content: str
    source: str
    url: Optional[str] = None
    published_date: datetime
    mentioned_companies: List[str] = []
    sentiment_score: float = 0.0  # -1 to 1 scale
    sentiment_label: str = "NEUTRAL"  # BULLISH, BEARISH, NEUTRAL
    impact_score: float = 0.0  # 1 to 10 scale
    key_points: List[str] = []
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)

class CompanyMention(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    company_name: str
    mentions_count: int = 0
    avg_sentiment: float = 0.0
    latest_news: List[str] = []
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class TrendAnalysis(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trend_topic: str
    companies_involved: List[str] = []
    sentiment_trend: str = "NEUTRAL"
    news_count: int = 0
    time_period: str = "24h"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AnalysisRequest(BaseModel):
    headline: str
    content: str
    source: str = "manual"
    url: Optional[str] = None

# AI Analysis Service
class FinancialAnalysisService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    async def analyze_news(self, headline: str, content: str) -> Dict[str, Any]:
        """Analyze news article using Gemini AI"""
        if not self.api_key:
            raise HTTPException(500, "Gemini API key not configured")
        
        try:
            # Create LLM chat instance for this analysis
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"analysis_{uuid.uuid4()}",
                system_message="""You are an expert financial analyst specializing in market sentiment analysis and company identification. 

Your task is to analyze financial news and provide structured insights. Always respond with valid JSON only, no other text.

Analyze the given news and return a JSON object with these exact fields:
{
    "sentiment_score": float between -1.0 and 1.0 (-1 very bearish, 0 neutral, 1 very bullish),
    "sentiment_label": "BULLISH" or "BEARISH" or "NEUTRAL",
    "impact_score": integer between 1 and 10 (1 low impact, 10 high impact on stock prices),
    "mentioned_companies": [list of company names and stock symbols found in the text],
    "key_points": [list of 3-5 key insights that could affect stock prices],
    "reasoning": "brief explanation of the sentiment and impact assessment"
}

Focus on:
- Market-moving information
- Company-specific news
- Industry trends
- Economic indicators
- Regulatory changes
- Earnings and financial performance"""
            ).with_model("gemini", "gemini-2.5-pro-preview-05-06").with_max_tokens(2048)
            
            # Prepare analysis prompt
            analysis_prompt = f"""
HEADLINE: {headline}

CONTENT: {content}

Please analyze this financial news and provide the structured JSON response as specified in your instructions.
"""
            
            user_message = UserMessage(text=analysis_prompt)
            response = await chat.send_message(user_message)
            
            # Parse the JSON response
            try:
                # Clean the response to extract JSON
                response_text = response.strip()
                if response_text.startswith('```json'):
                    response_text = response_text.split('```json')[1].split('```')[0]
                elif response_text.startswith('```'):
                    response_text = response_text.split('```')[1].split('```')[0]
                
                analysis_result = json.loads(response_text)
                
                # Validate required fields
                required_fields = ['sentiment_score', 'sentiment_label', 'impact_score', 'mentioned_companies', 'key_points']
                for field in required_fields:
                    if field not in analysis_result:
                        analysis_result[field] = self._get_default_value(field)
                
                return analysis_result
                
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse AI response as JSON: {e}")
                logging.error(f"Raw response: {response}")
                # Return default analysis
                return self._get_default_analysis()
                
        except Exception as e:
            logging.error(f"Error in AI analysis: {e}")
            return self._get_default_analysis()
    
    def _get_default_value(self, field: str):
        defaults = {
            'sentiment_score': 0.0,
            'sentiment_label': 'NEUTRAL',
            'impact_score': 5,
            'mentioned_companies': [],
            'key_points': []
        }
        return defaults.get(field, None)
    
    def _get_default_analysis(self):
        return {
            'sentiment_score': 0.0,
            'sentiment_label': 'NEUTRAL',
            'impact_score': 5,
            'mentioned_companies': [],
            'key_points': ['Analysis temporarily unavailable'],
            'reasoning': 'AI analysis service temporarily unavailable'
        }

# Initialize AI service
ai_service = FinancialAnalysisService(GEMINI_API_KEY)

# Sample news data for demo
SAMPLE_NEWS = [
    {
        "headline": "Apple Reports Record Q4 Earnings, iPhone Sales Surge 15%",
        "content": "Apple Inc. announced today that its fourth-quarter earnings exceeded expectations, driven by strong iPhone 15 sales and robust services revenue. The company reported revenue of $89.5 billion, up 8% year-over-year. CEO Tim Cook highlighted the success of the new iPhone lineup and growing adoption of Apple services across all product categories.",
        "source": "Financial Times",
        "url": "https://example.com/apple-earnings",
        "published_date": datetime.now() - timedelta(hours=2)
    },
    {
        "headline": "Tesla Stock Drops 12% After Production Delays Announcement",
        "content": "Tesla shares plummeted in after-hours trading following the company's announcement of production delays at its new Berlin facility. The electric vehicle maker cited supply chain disruptions and regulatory approvals as primary factors. Analysts are revising their delivery estimates for Q4, with some cutting targets by as much as 20%.",
        "source": "Reuters",
        "url": "https://example.com/tesla-delays",
        "published_date": datetime.now() - timedelta(hours=4)
    },
    {
        "headline": "Microsoft Azure Revenue Grows 30% as AI Demand Soars",
        "content": "Microsoft Corporation reported exceptional growth in its cloud computing division, with Azure revenue increasing 30% quarter-over-quarter. The surge is primarily attributed to increased demand for AI and machine learning services. The company's partnership with OpenAI continues to drive enterprise adoption of AI solutions.",
        "source": "Bloomberg",
        "url": "https://example.com/microsoft-azure",
        "published_date": datetime.now() - timedelta(hours=6)
    },
    {
        "headline": "Fed Signals Potential Rate Cut as Inflation Cools",
        "content": "Federal Reserve officials hinted at a possible interest rate reduction in the coming months as inflation continues to moderate. The latest CPI data showed a 3.2% year-over-year increase, down from 3.7% last month. Markets rallied on the news, with technology stocks leading the gains.",
        "source": "Wall Street Journal",
        "url": "https://example.com/fed-rates",
        "published_date": datetime.now() - timedelta(hours=8)
    }
]

# API Routes
@api_router.get("/")
async def root():
    return {"message": "AlphaGraph Financial Analysis API is running"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "gemini_configured": bool(GEMINI_API_KEY)}

@api_router.get("/companies")
async def get_tracked_companies():
    """Get list of tracked companies"""
    return {"companies": TRACKED_COMPANIES}

@api_router.post("/analyze", response_model=NewsAnalysis)
async def analyze_news_article(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """Analyze a news article and return insights"""
    try:
        # Perform AI analysis
        analysis_result = await ai_service.analyze_news(request.headline, request.content)
        
        # Create analysis object
        analysis = NewsAnalysis(
            headline=request.headline,
            content=request.content,
            source=request.source,
            url=request.url,
            published_date=datetime.now(),
            mentioned_companies=analysis_result.get('mentioned_companies', []),
            sentiment_score=analysis_result.get('sentiment_score', 0.0),
            sentiment_label=analysis_result.get('sentiment_label', 'NEUTRAL'),
            impact_score=analysis_result.get('impact_score', 5.0),
            key_points=analysis_result.get('key_points', [])
        )
        
        # Save to database in background
        background_tasks.add_task(save_analysis_to_db, analysis)
        
        return analysis
        
    except Exception as e:
        logging.error(f"Error analyzing news: {e}")
        raise HTTPException(500, f"Analysis failed: {str(e)}")

@api_router.get("/news/recent", response_model=List[NewsAnalysis])
async def get_recent_analysis(limit: int = 20):
    """Get recent news analysis"""
    try:
        # Get from database
        analyses = await db.news_analysis.find().sort("analysis_timestamp", -1).limit(limit).to_list(limit)
        return [NewsAnalysis(**analysis) for analysis in analyses]
    except Exception as e:
        logging.error(f"Error fetching recent analysis: {e}")
        return []

@api_router.get("/trends")
async def get_trending_topics():
    """Get trending topics and companies"""
    try:
        # Get company mentions from last 24 hours
        yesterday = datetime.now() - timedelta(days=1)
        
        pipeline = [
            {"$match": {"analysis_timestamp": {"$gte": yesterday}}},
            {"$unwind": "$mentioned_companies"},
            {"$group": {
                "_id": "$mentioned_companies",
                "count": {"$sum": 1},
                "avg_sentiment": {"$avg": "$sentiment_score"},
                "avg_impact": {"$avg": "$impact_score"}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        
        trending = await db.news_analysis.aggregate(pipeline).to_list(10)
        
        return {
            "trending_companies": trending,
            "analysis_period": "24h",
            "total_analyses": await db.news_analysis.count_documents({})
        }
    except Exception as e:
        logging.error(f"Error getting trends: {e}")
        return {"trending_companies": [], "analysis_period": "24h", "total_analyses": 0}

@api_router.get("/company/{symbol}")
async def get_company_analysis(symbol: str, days: int = 7):
    """Get analysis for a specific company"""
    try:
        # Get analyses mentioning this company
        since_date = datetime.now() - timedelta(days=days)
        
        analyses = await db.news_analysis.find({
            "mentioned_companies": {"$regex": symbol, "$options": "i"},
            "analysis_timestamp": {"$gte": since_date}
        }).sort("analysis_timestamp", -1).to_list(50)
        
        if not analyses:
            return {"symbol": symbol, "analyses": [], "summary": "No recent analysis found"}
        
        # Calculate summary stats
        avg_sentiment = sum(a.get('sentiment_score', 0) for a in analyses) / len(analyses)
        avg_impact = sum(a.get('impact_score', 0) for a in analyses) / len(analyses)
        
        return {
            "symbol": symbol,
            "analyses": [NewsAnalysis(**analysis) for analysis in analyses],
            "summary": {
                "total_mentions": len(analyses),
                "avg_sentiment_score": round(avg_sentiment, 2),
                "avg_impact_score": round(avg_impact, 1),
                "sentiment_label": "BULLISH" if avg_sentiment > 0.2 else "BEARISH" if avg_sentiment < -0.2 else "NEUTRAL",
                "analysis_period_days": days
            }
        }
    except Exception as e:
        logging.error(f"Error getting company analysis: {e}")
        raise HTTPException(500, f"Failed to get company analysis: {str(e)}")

@api_router.post("/demo/populate")
async def populate_sample_data():
    """Populate database with sample analyzed news for demo"""
    try:
        analyses = []
        
        for news_item in SAMPLE_NEWS:
            # Analyze each sample news item
            analysis_result = await ai_service.analyze_news(news_item["headline"], news_item["content"])
            
            analysis = NewsAnalysis(
                headline=news_item["headline"],
                content=news_item["content"],
                source=news_item["source"],
                url=news_item["url"],
                published_date=news_item["published_date"],
                mentioned_companies=analysis_result.get('mentioned_companies', []),
                sentiment_score=analysis_result.get('sentiment_score', 0.0),
                sentiment_label=analysis_result.get('sentiment_label', 'NEUTRAL'),
                impact_score=analysis_result.get('impact_score', 5.0),
                key_points=analysis_result.get('key_points', [])
            )
            
            analyses.append(analysis.dict())
        
        # Insert into database
        if analyses:
            await db.news_analysis.insert_many(analyses)
        
        return {"message": f"Successfully populated {len(analyses)} sample analyses", "analyses": len(analyses)}
        
    except Exception as e:
        logging.error(f"Error populating sample data: {e}")
        raise HTTPException(500, f"Failed to populate sample data: {str(e)}")

async def save_analysis_to_db(analysis: NewsAnalysis):
    """Background task to save analysis to database"""
    try:
        await db.news_analysis.insert_one(analysis.dict())
        logging.info(f"Saved analysis: {analysis.headline[:50]}...")
    except Exception as e:
        logging.error(f"Error saving analysis to database: {e}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()