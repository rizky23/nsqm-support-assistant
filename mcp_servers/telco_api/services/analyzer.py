import statistics
from typing import Dict, Any, List, Tuple
from datetime import datetime
from shared.models.base_models import AnalysisResult
from shared.utils.logger import log
from pydantic import BaseModel

class TelcoDataAnalyzer:
    def __init__(self):
        pass
    
    def analyze_all_data(self, combined_data: Dict[str, Any]) -> AnalysisResult:
        """Comprehensive analysis of all API data"""
        insights = []
        metrics = {}
        recommendations = []
        
        # Extract data from APIs
        user_info = combined_data.get("user_info", {}).get("data", [])
        quality_data = combined_data.get("quality_data", {}).get("data", [])
        history_data = combined_data.get("history_data", {}).get("history", [])
        
        # Analyze user info
        device_insights = self._analyze_device_info(user_info)
        insights.extend(device_insights["insights"])
        recommendations.extend(device_insights["recommendations"])
        metrics.update(device_insights["metrics"])
        
        # Analyze quality metrics
        quality_insights = self._analyze_quality_metrics(quality_data)
        insights.extend(quality_insights["insights"])
        recommendations.extend(quality_insights["recommendations"])
        metrics.update(quality_insights["metrics"])
        
        # Analyze historical trends
        history_insights = self._analyze_history_trends(history_data)
        insights.extend(history_insights["insights"])
        recommendations.extend(history_insights["recommendations"])
        metrics.update(history_insights["metrics"])
        
        # Cross-analysis
        cross_insights = self._cross_analyze(user_info, quality_data, history_data)
        insights.extend(cross_insights["insights"])
        recommendations.extend(cross_insights["recommendations"])
        
        # ADD FOLLOW-UP SUGGESTIONS - TAMBAH INI
        follow_up_suggestions = []
        
        # Suggest RCA if issues detected
        issue_keywords = ["buruk", "spike", "high", "poor", "degradation", "issue"]
        if any(any(keyword in insight.lower() for keyword in issue_keywords) for insight in insights):
            follow_up_suggestions.append("Lakukan Root Cause Analysis (RCA) untuk investigasi lebih mendalam")
        
        # Suggest chart if traffic data available
        if history_data or any("traffic" in insight.lower() for insight in insights):
            follow_up_suggestions.append("Generate traffic chart untuk visualisasi data")
            
        # Suggest network analysis if quality issues
        if any("latency" in insight.lower() or "delay" in insight.lower() or "rtt" in insight.lower() for insight in insights):
            follow_up_suggestions.append("Analisis network issues untuk identifikasi masalah spesifik")
        
        # Always suggest if no specific issues found
        if not follow_up_suggestions:
            follow_up_suggestions.append("Generate traffic chart untuk monitoring rutin")

        return AnalysisResult(
            msisdn=combined_data.get("msisdn", "unknown"),
            analysis_type="comprehensive",
            insights=insights,
            metrics=metrics,
            recommendations=recommendations,
            follow_up_suggestions=follow_up_suggestions  # TAMBAH INI
        )
    
    def _analyze_device_info(self, user_info: List[Dict]) -> Dict[str, Any]:
        insights = []
        recommendations = []
        metrics = {}
        
        if not user_info:
            return {"insights": ["No user info available"], "recommendations": [], "metrics": {}}
        
        # Extract device information
        device_data = {}
        subscriber_data = {} 

        for section in user_info:
            if section.get("label") == "Device":
                for value in section.get("values", []):
                    device_data[value["label"]] = value["value"]
            elif section.get("label") == "Subscriber":
                for value in section.get("values", []):
                    subscriber_data[value["label"]] = value["value"]
        
        device_model = device_data.get("DeviceModel", "Unknown")
        device_brand = device_data.get("DeviceBrand", "Unknown")
        device_mode = device_data.get("DeviceMode", "Unknown")
        roam_status = subscriber_data.get("Roam", "Unknown")

        metrics.update({
            "device_model": device_model,
            "device_brand": device_brand,
            "device_capability": device_mode,
            "roam_status": roam_status
        })
        
        # HANYA BASIC INFO - TIDAK DUPLIKASI DENGAN RINGKASAN
        insights.append(f"Perangkat yang digunakan adalah {device_model}")
        insights.append(f"Kemampuan jaringan yang digunakan adalah {device_mode}")
        insights.append(f"Status roaming adalah {roam_status.lower()}")
        
        # Device-specific recommendations
        if "2G/3G" in device_mode and "LTE" not in device_mode:
            recommendations.append("Consider upgrading to 4G/5G capable device for better performance")
        
        if device_model == "--" or device_model == "Unknown":
            insights.append("Device information not available - may indicate compatibility issues")
        
        return {"insights": insights, "recommendations": recommendations, "metrics": metrics}
    
    def _analyze_quality_metrics(self, quality_data: List[Dict]) -> Dict[str, Any]:
        insights = []
        recommendations = []
        metrics = {}
        
        if not quality_data:
            return {"insights": ["Tidak ada data kualitas yang tersedia"], "recommendations": [], "metrics": {}}
        
        total_traffic = 0
        avg_delay = 0
        avg_rtt = 0
        
        for service in quality_data:
            service_name = service.get("servicename", "")
            counters = service.get("counter", [])
            
            for counter in counters:
                counter_name = counter.get("Counter", "")
                value = float(counter.get("Value", 0))
                unit = counter.get("Unit", "")
                
                if "Total Traffic" in counter_name:
                    total_traffic = value
                    metrics["total_traffic_mb"] = value
                elif "Response Delay Experience" in counter_name:
                    avg_delay = value
                    metrics["response_delay_percent"] = value
                elif "TotalClientRTTCCH" in counter_name:
                    avg_rtt = value
                    metrics["average_rtt_ms"] = value
        
        # DETAILED QUALITY INSIGHTS - TIDAK BASIC INFO
        insights.append(f"Total traffic sebesar {total_traffic} MB")
        insights.append(f"Response delay experience sebesar {avg_delay}%")
        insights.append(f"Average RTT sebesar {avg_rtt} ms")
        
        # Performance analysis
        if avg_rtt > 100:
            insights.append("High latency - network optimization needed")
            recommendations.append("Check network coverage and signal strength")
        elif avg_rtt > 50:
            insights.append("Moderate latency - acceptable performance")
        else:
            insights.append("Low latency - good network performance")
        
        if avg_delay < 95:
            insights.append("Poor response delay experience")
            recommendations.append("Network optimization needed")
        
        return {"insights": insights, "recommendations": recommendations, "metrics": metrics}
    
    def _analyze_history_trends(self, history_data: List[Dict]) -> Dict[str, Any]:
        insights = []
        recommendations = []
        metrics = {}
        TRAFFIC_THRESHOLD = 1.0    # 1 MB minimum untuk KQI analysis
        KQI_GOOD_THRESHOLD = 60    # KQI threshold bagus
        
        if not history_data:
            return {"insights": ["No historical data available"], "recommendations": [], "metrics": {}}
        
        # ADD DEBUG LINE HERE ↓
        log.info(f"KQI data found: {[r.get('TOTALSCORE') for r in history_data[:3]]}")
        log.info(f"Traffic data: {[r.get('TOTALTRAFFIC') for r in history_data[:3]]}")
        
        # Extract hourly data
        traffic_values = []
        latency_values = []
        score_values = []
        peak_hours = []
        
        for record in history_data:
            traffic = float(record.get("TOTALTRAFFIC", 0))
            latency = float(record.get("TOTALINTERNALLATENCYCCH", 0))
            score = int(record.get("TOTALSCORE", 0))
            hour = record.get("TEXT", "").split(" ")[1] if " " in record.get("TEXT", "") else ""
            
            traffic_values.append(traffic)
            if latency > 0:  # Only count non-zero latency
                latency_values.append(latency)
            if score > 0:
                score_values.append(score)
            
            if traffic > 50:  # Peak traffic threshold
                peak_hours.append(hour)
        
        # Calculate statistics
        if traffic_values:
            total_traffic = sum(traffic_values)
            avg_traffic = statistics.mean(traffic_values)
            max_traffic = max(traffic_values)
            
            metrics.update({
                "total_daily_traffic_mb": total_traffic,
                "average_hourly_traffic_mb": avg_traffic,
                "peak_traffic_mb": max_traffic
            })
            
            insights.append(f"Daily total traffic: {total_traffic:.2f} MB")
            insights.append(f"Peak hourly traffic: {max_traffic:.2f} MB")
        
        if latency_values:
            avg_latency = statistics.mean(latency_values)
            max_latency = max(latency_values)
            
            metrics.update({
                "average_latency_ms": avg_latency,
                "peak_latency_ms": max_latency
            })
            
            insights.append(f"Average latency: {avg_latency:.2f} ms")
            
            if max_latency > 100:
                insights.append(f"Latency spike detected: {max_latency:.2f} ms")
                recommendations.append("Investigate network congestion during peak hours")

        # ADD KQI ANALYSIS HERE ← TAMBAH DI SINI
        valid_kqi_periods = []
        kqi_values = []

        for record in history_data:
            traffic = float(record.get("TOTALTRAFFIC", 0))
            kqi = int(record.get("TOTALSCORE", 0))
            hour = record.get("TEXT", "").split(" ")[1] if " " in record.get("TEXT", "") else ""
            
            # Only analyze KQI when traffic >= 1 MB (reliable measurement)
            if traffic >= TRAFFIC_THRESHOLD:
                valid_kqi_periods.append({
                    "hour": hour,
                    "traffic": traffic,
                    "kqi": kqi
                })
                if kqi > 0:  # Exclude zero values
                    kqi_values.append(kqi)

        # Generate KQI insights
        if valid_kqi_periods:
            avg_kqi = statistics.mean([p["kqi"] for p in valid_kqi_periods if p["kqi"] > 0])
            poor_kqi_hours = [p for p in valid_kqi_periods if p["kqi"] < KQI_GOOD_THRESHOLD and p["kqi"] > 0]
            
            metrics.update({
                "average_kqi": avg_kqi if kqi_values else 0,
                "valid_kqi_periods": len(valid_kqi_periods),
                "poor_kqi_periods": len(poor_kqi_hours)
            })
            
            insights.append(f"KQI analysis based on {len(valid_kqi_periods)} periods with traffic ≥ {TRAFFIC_THRESHOLD} MB")
            
            if kqi_values:
                insights.append(f"Average KQI: {avg_kqi:.1f} (threshold: {KQI_GOOD_THRESHOLD})")
                
                if poor_kqi_hours:
                    poor_details = []
                    for p in poor_kqi_hours[:3]:
                        poor_details.append(f"{p['hour']} (KQI: {p['kqi']}, traffic: {p['traffic']:.1f} MB)")
                    
                    insights.append(f"Kualitas jaringan buruk pada jam: {', '.join(poor_details)}")
                    recommendations.append("Investigate network quality issues during periods with significant traffic")
                else:
                    insights.append("Kualitas jaringan baik di semua periode dengan traffic signifikan")
            else:
                insights.append("No reliable KQI measurements (insufficient traffic periods)")
        else:
            insights.append("No periods with sufficient traffic for KQI analysis")
        
        if peak_hours:
            insights.append(f"Peak usage hours: {', '.join(peak_hours[:3])}")
        
        return {"insights": insights, "recommendations": recommendations, "metrics": metrics}
    
    def _cross_analyze(self, user_info: List[Dict], quality_data: List[Dict], history_data: List[Dict]) -> Dict[str, Any]:
        insights = []
        recommendations = []
        
        # Correlate device capability with performance
        device_mode = "Unknown"
        for section in user_info:
            if section.get("label") == "Device":
                for value in section.get("values", []):
                    if value["label"] == "DeviceMode":
                        device_mode = value["value"]
        
        # Check if performance issues correlate with device limitations
        avg_rtt = 0
        for service in quality_data:
            for counter in service.get("counter", []):
                if "TotalClientRTTCCH" in counter.get("Counter", ""):
                    avg_rtt = float(counter.get("Value", 0))
        
        if "2G/3G" in device_mode and avg_rtt > 80:
            insights.append("Performance issues likely due to limited device capability")
            recommendations.append("Device upgrade recommended for better network performance")
        
        # Analyze traffic patterns vs quality
        if history_data and quality_data:
            high_traffic_periods = [r for r in history_data if float(r.get("TOTALTRAFFIC", 0)) > 50]
            if high_traffic_periods and avg_rtt > 60:
                insights.append("Performance degradation during high usage periods")
                recommendations.append("Consider network capacity optimization")
        
        return {"insights": insights, "recommendations": recommendations}

