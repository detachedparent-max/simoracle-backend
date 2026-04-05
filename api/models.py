"""
Pydantic models for API request/response validation
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# Prediction Models
class PredictionCreate(BaseModel):
    oracle: str
    event: str
    probability: float = Field(ge=0.0, le=1.0)
    action: str
    confidence: int = Field(ge=0, le=10)
    market_id: Optional[str] = None
    platform: Optional[str] = None


class PredictionResponse(BaseModel):
    id: str
    oracle: str
    event: str
    probability: float
    action: str
    confidence: int
    timestamp: str
    outcome: Optional[str] = None
    outcome_timestamp: Optional[str] = None
    market_id: Optional[str] = None
    platform: Optional[str] = None


class PredictionListResponse(BaseModel):
    predictions: List[PredictionResponse]
    total: int
    limit: int
    offset: int


# Reasoning Models
class CatalystInfo(BaseModel):
    primary: str
    secondary: Optional[str] = None


class ReasoningLogResponse(BaseModel):
    id: str
    prediction_id: str
    model: str
    catalyst_primary: str
    catalyst_secondary: Optional[str] = None
    confidence_driver: Optional[str] = None
    data_sources: List[str]
    consensus_status: str
    reasoning_text: Optional[str] = None
    timestamp: str


class PredictionReasoningResponse(BaseModel):
    prediction_id: str
    event: str
    oracle: str
    probability: float
    action: str
    confidence: int
    created_at: str
    outcome: Optional[str] = None
    causal_chain: List[Dict[str, Any]]
    model_consensus: str
    reasoning_summary: str


# Position Models
class PositionResponse(BaseModel):
    id: str
    market_id: str
    market_name: str
    shares: int
    entry_price: float
    current_price: float
    pnl: float
    pnl_pct: float
    timestamp: str


class UserPositionsResponse(BaseModel):
    positions: List[PositionResponse]
    total_pnl: float
    total_pnl_pct: float


# Analytics Models
class WhaleActivityResponse(BaseModel):
    score: int = Field(ge=0, le=100)
    description: str
    details: Dict[str, Any]
    signals: List[Dict[str, Any]]


class ArbitrageOpportunityResponse(BaseModel):
    market_id: str
    platform1: str
    platform2: str
    price1: float
    price2: float
    spread_pct: float
    liquidity1_usd: float
    liquidity2_usd: float
    action: str
    estimated_profit_usd: float
    confidence: int = Field(ge=0, le=100)
    timestamp: str


class ArbitrageListResponse(BaseModel):
    opportunities: List[ArbitrageOpportunityResponse]
    total: int
    scan_timestamp: str


class InsiderSignalResponse(BaseModel):
    prediction_id: str
    signal_type: str
    confidence_change_pct: float
    old_confidence: int
    new_confidence: int
    model_agreement: int
    description: str
    strength: int = Field(ge=0, le=100)
    timestamp: str


class InsiderSignalsResponse(BaseModel):
    signals: List[InsiderSignalResponse]
    total: int
    scan_timestamp: str


# Orderbook Models
class OrderLevel(BaseModel):
    price: float
    qty: int


class OrderbookResponse(BaseModel):
    market_id: str
    bids: List[OrderLevel]
    asks: List[OrderLevel]
    mid_price: float
    timestamp: str


# Backtesting Models
class BacktestCreate(BaseModel):
    strategy: str
    date_range: str
    csv_file: Optional[str] = None  # Will receive as multipart


class BacktestResultsResponse(BaseModel):
    backtest_id: str
    strategy: str
    date_range: str
    accuracy: float
    calibration: float
    total_trades: int
    winning_trades: int
    win_rate: float
    profit_projection: float
    timestamp: str


# Export Models
class ReasoningExportResponse(BaseModel):
    export_timestamp: str
    total_predictions: int
    oracle_filter: Optional[str] = None
    predictions: List[Dict[str, Any]]


# Health/Status Models
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    database_ready: bool
    kalshi_connected: Optional[bool] = None


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: str
