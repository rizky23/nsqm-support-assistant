from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class BaseResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class TelcoAPIRequest(BaseModel):
    msisdn: str = Field(..., description="Mobile number")
    start_time: str = Field(..., description="Start time YYYY-MM-DD HH:mm")
    end_time: str = Field(..., description="End time YYYY-MM-DD HH:mm")

class UserInfoData(BaseModel):
    msisdn: str
    imsi: str
    device_model: Optional[str] = None
    device_brand: Optional[str] = None
    device_mode: Optional[str] = None
    roaming_status: Optional[str] = None

class QualityMetrics(BaseModel):
    total_traffic: float
    response_delay_experience: float
    total_client_rtt: float
    download_throughput: Optional[float] = None
    web_page_loading_delay: Optional[float] = None

class HistoryRecord(BaseModel):
    utc: str
    text: str
    total_traffic: float
    latency: float
    score: int

class AnalysisResult(BaseModel):
    msisdn: str
    analysis_type: str
    insights: List[str]
    metrics: Dict[str, Any]
    recommendations: List[str]
    follow_up_suggestions: List[str] = []  # ← TAMBAH BARIS INI
    timestamp: datetime = Field(default_factory=datetime.now)
