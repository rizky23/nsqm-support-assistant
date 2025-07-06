from typing import Dict, Any, Optional, List
from tools.query_parser import SmartCareQueryParser
from tools.telkomsel_api_client import TelkomselAPIClient
from tools.chart_generator import ChartGenerator

class SmartCareWorkflow:
    """Workflow for handling real-time MSISDN queries with API integration"""
    
    def __init__(self):
        """Initialize SmartCare workflow components"""
        self.query_parser = SmartCareQueryParser()
        self.api_client = TelkomselAPIClient()
        self.chart_generator = ChartGenerator()
        print("🔗 SmartCareWorkflow initialized")

    def _convert_to_api_format(self, normalized_msisdn: str) -> str:
        """Convert 628xxx format to 8xxx format for API"""
        if normalized_msisdn.startswith('628'):
            return normalized_msisdn[3:]  # Remove '628' prefix, keep 8xxxxx
        return normalized_msisdn
    
    def execute(self, user_query: str, enhanced_context: Optional[Dict] = None, session_id: str = "") -> Dict[str, Any]:
        """
        Execute SmartCare workflow for MSISDN-specific queries
        """
        try:
            self._log_workflow_execution(session_id, "SmartCareWorkflow", user_query, True)
            
            # Step 1: Parse query for MSISDN and time
            parsed_query = self.query_parser.parse_query(user_query)
            if not parsed_query["success"]:
                return self._create_error_response(
                    f"Query parsing failed: {'; '.join(parsed_query['errors'])}",
                    "parsing_error"
                )

            # Step 2: Validate MSISDN is Telkomsel number
            msisdn_info = parsed_query["msisdn"]
            if not self.query_parser.msisdn_validator.is_telkomsel_number(msisdn_info["normalized"]):
                return self._create_error_response(
                    f"Nomor {msisdn_info['format']} bukan nomor Telkomsel. Sistem hanya mendukung analisis nomor Telkomsel.",
                    "invalid_operator"
                )

            # Step 3: Call Telkomsel API with enhanced error handling
            api_params = parsed_query["api_params"]
            api_format_msisdn = self._convert_to_api_format(msisdn_info["normalized"])
            
            try:
                api_result = self.api_client.query_user_history(
                    api_format_msisdn,
                    api_params["startTime"],
                    api_params["endTime"]
                )
            except Exception as api_error:
                # Catch ALL exceptions from API calls
                print(f"API Error caught: {api_error}")
                return self._create_maintenance_response(msisdn_info, api_error)
            
            if not api_result["success"]:
                # API returned error response but didn't throw exception
                return self._create_maintenance_response(msisdn_info, Exception(api_result['error']))

            # Step 4: Process API response based on intent
            intent = parsed_query["intent"]
            time_range = parsed_query["time_range"]
            
            if intent in ["chart", "grafik", "visualisasi"]:
                chart_response = self._generate_chart_response(
                    api_result, msisdn_info, time_range, session_id
                )
                return chart_response
            else:
                narrative_response = self._generate_narrative_response(
                    api_result, msisdn_info, time_range, intent, session_id
                )
                return narrative_response

        except Exception as e:
            self._log_workflow_execution(session_id, "SmartCareWorkflow", user_query, False)
            return self._create_error_response(f"SmartCare workflow execution failed: {str(e)}")

    def _create_maintenance_response(self, msisdn_info: dict, error: Exception) -> dict:
        """Create user-friendly response when API is down"""
        return {
            "response": f"""🔧 **Layanan SmartCare Sedang Maintenance**

**Nomor:** {msisdn_info.get('format', 'N/A')} (Telkomsel)
**Status:** API server sedang dalam perbaikan

⏳ **Mohon tunggu beberapa saat dan coba lagi.**
📞 **Atau hubungi customer service untuk bantuan langsung.**

**Error:** Connection timeout""",
            "status": "api_maintenance",
            "metadata": {
                "error_type": "api_unavailable",
                "msisdn": msisdn_info,
                "error_details": str(error)
            }
        }

    def _generate_chart_response(self, api_result: Dict, msisdn_info: Dict, time_range: Dict, session_id: str) -> Dict[str, Any]:
        """Generate chart visualization from API data"""
        try:
            api_data = api_result["data"]
            
            # Generate chart HTML
            chart_html = self.chart_generator.generate_traffic_score_chart(
                api_data,
                msisdn_info["format"],
                f"{time_range['start_time']} to {time_range['end_time']}"
            )
            
            # Create summary statistics
            stats = self._calculate_summary_stats(api_data)
            
            return {
                "response": chart_html,
                "status": "success",
                "metadata": {
                    "msisdn": msisdn_info,
                    "time_range": time_range,
                    "chart_type": "traffic_score",
                    "data_points": len(api_data.get("history", [])),
                    "summary_stats": stats
                }
            }
            
        except Exception as e:
            return self._create_error_response(f"Chart generation failed: {str(e)}")
    
    def _generate_narrative_response(self, api_result: Dict, msisdn_info: Dict, time_range: Dict, intent: str, session_id: str) -> Dict[str, Any]:
        """Generate narrative response from API data"""
        try:
            api_data = api_result["data"]
            history = api_data.get("history", [])
            
            if not history:
                return {
                    "response": f"📱 **Data untuk nomor {msisdn_info['format']}**\n\n❌ Tidak ada data ditemukan untuk periode {time_range.get('duration_text', 'yang diminta')}.",
                    "status": "success",
                    "metadata": {
                        "msisdn": msisdn_info,
                        "time_range": time_range,
                        "data_points": 0
                    }
                }
            
            # Calculate statistics
            stats = self._calculate_summary_stats(api_data)
            
            # Generate narrative based on intent
            if intent == "usage":
                narrative = self._generate_usage_narrative(msisdn_info, time_range, stats)
            elif intent == "history":
                narrative = self._generate_history_narrative(msisdn_info, time_range, stats, history)
            elif intent == "detail":
                narrative = self._generate_detail_narrative(msisdn_info, time_range, stats, history)
            else:  # default check
                narrative = self._generate_check_narrative(msisdn_info, time_range, stats)
            
            return {
                "response": narrative,
                "status": "success", 
                "metadata": {
                    "msisdn": msisdn_info,
                    "time_range": time_range,
                    "intent": intent,
                    "data_points": len(history),
                    "summary_stats": stats
                }
            }
            
        except Exception as e:
            return self._create_error_response(f"Narrative generation failed: {str(e)}")
    
    def _calculate_summary_stats(self, api_data: Dict) -> Dict[str, Any]:
        """Calculate summary statistics from API data"""
        history = api_data.get("history", [])
        
        if not history:
            return {
                "total_traffic": 0,
                "avg_score": 0,
                "avg_latency": 0,
                "peak_traffic": 0,
                "peak_traffic_time": "N/A"
            }
        
        # Extract numeric values
        traffic_values = []
        score_values = []
        latency_values = []
        
        for entry in history:
            try:
                traffic = float(entry.get("TOTALTRAFFIC", 0))
                score = float(entry.get("TOTALSCORE", 0))
                latency = float(entry.get("TOTALINTERNALLATENCYCCH", 0))
                
                traffic_values.append(traffic)
                if score > 0:  # Only include non-zero scores
                    score_values.append(score)
                if latency > 0:  # Only include non-zero latency
                    latency_values.append(latency)
                    
            except (ValueError, TypeError):
                continue
        
        # Find peak traffic
        peak_traffic = max(traffic_values) if traffic_values else 0
        peak_entry = None
        if peak_traffic > 0:
            for entry in history:
                if float(entry.get("TOTALTRAFFIC", 0)) == peak_traffic:
                    peak_entry = entry
                    break
        
        return {
            "total_traffic": sum(traffic_values),
            "avg_score": sum(score_values) / len(score_values) if score_values else 0,
            "avg_latency": sum(latency_values) / len(latency_values) if latency_values else 0,
            "peak_traffic": peak_traffic,
            "peak_traffic_time": peak_entry.get("TEXT", "N/A") if peak_entry else "N/A",
            "data_points": len(history),
            "active_hours": len([t for t in traffic_values if t > 0])
        }
    
    def _generate_usage_narrative(self, msisdn_info: Dict, time_range: Dict, stats: Dict) -> str:
        """Generate usage-focused narrative"""
        total_traffic = stats["total_traffic"]
        avg_score = stats["avg_score"]
        peak_traffic = stats["peak_traffic"]
        peak_time = stats["peak_traffic_time"]
        
        # Convert MB to appropriate unit
        if total_traffic >= 1024:
            traffic_display = f"{total_traffic/1024:.2f} GB"
        else:
            traffic_display = f"{total_traffic:.2f} MB"
        
        narrative = f"""📱 **Analisis Penggunaan Data**

**Nomor:** {msisdn_info['format']} ({msisdn_info['operator']})
**Periode:** {time_range.get('duration_text', 'Yang diminta')}

📊 **Ringkasan Penggunaan:**
• Total Traffic: {traffic_display}
• Score Rata-rata: {avg_score:.1f}/100
• Peak Usage: {peak_traffic:.2f} MB pada {peak_time}
• Jam Aktif: {stats['active_hours']} dari {stats['data_points']} jam

"""
        
        # Add insights
        if total_traffic == 0:
            narrative += "ℹ️ **Insight:** Tidak ada aktivitas data terdeteksi pada periode ini."
        elif total_traffic < 1:
            narrative += "ℹ️ **Insight:** Penggunaan data sangat rendah, mostly idle."
        elif total_traffic > 100:
            narrative += "ℹ️ **Insight:** Penggunaan data tinggi, kemungkinan heavy usage periode."
        
        if avg_score > 0:
            if avg_score >= 80:
                narrative += "\n✅ **Kualitas:** Score tinggi, koneksi sangat baik."
            elif avg_score >= 60:
                narrative += "\n⚠️ **Kualitas:** Score sedang, koneksi cukup stabil."
            else:
                narrative += "\n❌ **Kualitas:** Score rendah, ada gangguan koneksi."
        
        return narrative
    
    def _generate_history_narrative(self, msisdn_info: Dict, time_range: Dict, stats: Dict, history: List) -> str:
        """Generate history-focused narrative with timeline"""
        narrative = f"""📱 **Riwayat Aktivitas Data**

**Nomor:** {msisdn_info['format']} ({msisdn_info['operator']})
**Periode:** {time_range.get('duration_text', 'Yang diminta')}

📈 **Timeline Aktivitas:**
"""
        
        # Show key activity periods
        active_periods = []
        for entry in history:
            traffic = float(entry.get("TOTALTRAFFIC", 0))
            if traffic > 1:  # Only significant traffic
                time_str = entry.get("TEXT", "").split(" ")[1] if " " in entry.get("TEXT", "") else entry.get("TEXT", "")
                active_periods.append(f"• {time_str}: {traffic:.1f} MB")
        
        if active_periods:
            narrative += "\n".join(active_periods[:10])  # Show top 10
            if len(active_periods) > 10:
                narrative += f"\n... dan {len(active_periods) - 10} periode lainnya"
        else:
            narrative += "• Tidak ada aktivitas signifikan terdeteksi"
        
        narrative += f"""

📊 **Statistik:**
• Total: {stats['total_traffic']:.2f} MB
• Peak: {stats['peak_traffic']:.2f} MB
• Jam Aktif: {stats['active_hours']}/{stats['data_points']}
"""
        
        return narrative
    
    def _generate_detail_narrative(self, msisdn_info: Dict, time_range: Dict, stats: Dict, history: List) -> str:
        """Generate detailed technical narrative"""
        narrative = f"""📱 **Detail Teknis Lengkap**

**Informasi Nomor:**
• MSISDN: {msisdn_info['format']}
• Format Internal: {msisdn_info['normalized']}
• Operator: {msisdn_info['operator']}

**Periode Analisis:**
• Waktu: {time_range['start_time']} - {time_range['end_time']}
• Durasi: {time_range.get('duration_text', 'N/A')}

**Metrik Performa:**
• Total Traffic: {stats['total_traffic']:.2f} MB
• Average Score: {stats['avg_score']:.1f}/100
• Average Latency: {stats['avg_latency']:.1f} ms
• Peak Traffic: {stats['peak_traffic']:.2f} MB pada {stats['peak_traffic_time']}

**Data Points:** {stats['data_points']} jam dianalisis
**Active Periods:** {stats['active_hours']} jam dengan aktivitas

"""
        
        # Add technical insights
        if stats['avg_latency'] > 0:
            if stats['avg_latency'] < 30:
                narrative += "🟢 **Latency:** Sangat baik (< 30ms)\n"
            elif stats['avg_latency'] < 50:
                narrative += "🟡 **Latency:** Normal (30-50ms)\n"
            else:
                narrative += "🔴 **Latency:** Tinggi (> 50ms)\n"
        
        return narrative
    
    def _generate_check_narrative(self, msisdn_info: Dict, time_range: Dict, stats: Dict) -> str:
        """Generate general check narrative"""
        return f"""📱 **Status Check - {msisdn_info['format']}**

✅ Data berhasil diambil untuk periode {time_range.get('duration_text', 'yang diminta')}

📊 **Quick Stats:**
• Total Traffic: {stats['total_traffic']:.2f} MB
• Quality Score: {stats['avg_score']:.1f}/100
• Data Points: {stats['data_points']} jam

💡 *Gunakan 'grafik {msisdn_info['normalized']}' untuk visualisasi atau 'detail {msisdn_info['normalized']}' untuk analisis mendalam.*
"""
    
    def _create_error_response(self, error_message: str, error_type: str = "execution_error") -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "response": f"❌ {error_message}",
            "status": "error",
            "error_type": error_type,
            "metadata": {}
        }
    
    def _log_workflow_execution(self, session_id: str, workflow_name: str, user_query: str, success: bool):
        """Log workflow execution for debugging"""
        status_emoji = "✅" if success else "❌"
        print(f"{status_emoji} [{session_id}] {workflow_name} - {user_query[:50]}...")