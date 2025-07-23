from typing import Dict, Any
from ..services.api_client import TelcoAPIClient
from ..services.analyzer import TelcoDataAnalyzer
from shared.utils.logger import log

class TelcoAPITools:
    def __init__(self):
        self.api_client = TelcoAPIClient()
        self.analyzer = TelcoDataAnalyzer()

    async def handle_follow_up_command(self, command: str, msisdn: str, start_time: str, end_time: str) -> Dict[str, Any]:
        """Handle follow-up commands from user"""
        command = command.lower().strip()
        
        try:
            if "rca" in command:
                log.info(f"Executing RCA for {msisdn}")
                return await self.perform_root_cause_analysis(msisdn, start_time, end_time)
            
            elif "chart" in command:
                log.info(f"Generating chart for {msisdn}")
                return await self.generate_traffic_chart(msisdn, start_time, end_time)
            
            elif "network" in command:
                log.info(f"Analyzing network issues for {msisdn}")
                return await self.analyze_network_issues(msisdn, start_time, end_time)
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown follow-up command: {command}",
                    "available_commands": ["ya rca", "ya chart", "ya network"]
                }
        
        except Exception as e:
            log.error(f"Follow-up command failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "command": command
            }

    
    async def get_user_info_only(self, msisdn: str, start_time: str, end_time: str) -> Dict[str, Any]:
        """Get only user and device information"""
        try:
            data = await self.api_client.get_user_info(msisdn, start_time, end_time)
            return {"success": True, "data": data}
        except Exception as e:
            log.error(f"User info query failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_quality_metrics_only(self, msisdn: str, start_time: str, end_time: str) -> Dict[str, Any]:
        """Get only quality metrics"""
        try:
            data = await self.api_client.get_overall_quality(msisdn, start_time, end_time)
            return {"success": True, "data": data}
        except Exception as e:
            log.error(f"Quality metrics query failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_history_data_only(self, msisdn: str, start_time: str, end_time: str) -> Dict[str, Any]:
        """Get only historical data"""
        try:
            data = await self.api_client.get_history_info(msisdn, start_time, end_time)
            return {"success": True, "data": data}
        except Exception as e:
            log.error(f"History data query failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def analyze_network_issues(self, msisdn: str, start_time: str, end_time: str) -> Dict[str, Any]:
        """Focused analysis for network performance issues"""
        try:
            combined_data = await self.api_client.get_all_data(msisdn, start_time, end_time)
            
            # Extract quality and history data for focused analysis
            quality_data = combined_data.get("quality_data", {}).get("data", [])
            history_data = combined_data.get("history_data", {}).get("history", [])
            
            issues = []
            solutions = []
            
            # Analyze quality issues
            for service in quality_data:
                for counter in service.get("counter", []):
                    if "Response Delay Experience" in counter.get("Counter", ""):
                        delay_pct = float(counter.get("Value", 100))
                        if delay_pct < 95:
                            issues.append(f"Poor response delay: {delay_pct}%")
                            solutions.append("Network optimization required")
                    
                    elif "TotalClientRTTCCH" in counter.get("Counter", ""):
                        rtt = float(counter.get("Value", 0))
                        if rtt > 100:
                            issues.append(f"High latency: {rtt}ms")
                            solutions.append("Check network congestion and routing")
            
            # Analyze historical patterns
            high_latency_hours = []
            for record in history_data:
                latency = float(record.get("TOTALINTERNALLATENCYCCH", 0))
                if latency > 80:
                    hour = record.get("TEXT", "").split(" ")[1] if " " in record.get("TEXT", "") else ""
                    high_latency_hours.append(hour)
            
            if high_latency_hours:
                issues.append(f"Consistent high latency during: {', '.join(high_latency_hours[:3])}")
                solutions.append("Investigate capacity issues during peak hours")
            
            return {
                "success": True,
                "msisdn": msisdn,
                "issues_found": len(issues),
                "issues": issues,
                "recommendations": solutions,
                "severity": "high" if len(issues) > 3 else "medium" if len(issues) > 1 else "low"
            }
            
        except Exception as e:
            log.error(f"Network issue analysis failed: {e}")
            return {"success": False, "error": str(e)}
        

    async def generate_traffic_chart(self, msisdn: str, start_time: str, end_time: str) -> Dict[str, Any]:
        """Generate chart for traffic and score analysis"""
        try:
            # Get history data
            history_data = await self.api_client.get_history_info(msisdn, start_time, end_time)
            
            if history_data and history_data.get("history"):
                # Generate base64 image instead of HTML
                chart_base64 = self._create_matplotlib_chart(history_data, msisdn)
                
                return {
                    "success": True,
                    "category": "data_visualization",
                    "msisdn": msisdn,
                    "chart_image": chart_base64,  # Base64 image untuk OpenWebUI
                    "chart_type": "traffic_score_analysis",
                    "period": f"{start_time} to {end_time}"
                }
            else:
                return {
                    "success": False,
                    "error": "No historical data available for chart generation",
                    "msisdn": msisdn
                }
                
        except Exception as e:
            log.error(f"Chart generation failed for {msisdn}: {e}")
            return {"success": False, "error": str(e)}

    def _create_matplotlib_chart(self, history_data: Dict, msisdn: str) -> str:
        """Create matplotlib chart as base64"""
        import matplotlib.pyplot as plt
        import base64
        from io import BytesIO
        
        # Extract data
        history = history_data.get("history", [])
        hours = [record.get("TEXT", "").split(" ")[1] if " " in record.get("TEXT", "") else "" for record in history]
        traffic = [float(record.get("TOTALTRAFFIC", 0)) for record in history]
        scores = [int(record.get("TOTALSCORE", 0)) for record in history]
        
        # Create chart
        fig, ax1 = plt.subplots(figsize=(14, 8))
        
        # Traffic line
        ax1.plot(hours, traffic, color='#3b82f6', marker='o', linewidth=3, markersize=6, label='Traffic (MB)')
        ax1.set_xlabel('Time (Hours)', fontsize=12)
        ax1.set_ylabel('Traffic (MB)', color='#3b82f6', fontsize=12)
        ax1.tick_params(axis='y', labelcolor='#3b82f6')
        
        # Score line (secondary axis)
        ax2 = ax1.twinx()
        ax2.plot(hours, scores, color='#10b981', marker='s', linewidth=3, markersize=6, label='Score')
        ax2.set_ylabel('Score', color='#10b981', fontsize=12)
        ax2.tick_params(axis='y', labelcolor='#10b981')
        
        # Styling
        plt.title(f'Network Performance Analysis - MSISDN {msisdn}', fontsize=16, pad=20)
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        plt.close()
        
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{img_base64}"
    
    async def perform_root_cause_analysis(self, msisdn: str, start_time: str, end_time: str) -> Dict[str, Any]:
        """Perform detailed root cause analysis"""
        try:
            # Get demarcation data
            demarcation_data = await self.api_client.get_user_demarcation(msisdn, start_time, end_time)
            
            if "error" in demarcation_data:
                return {
                    "success": False,
                    "error": f"Failed to get demarcation data: {demarcation_data['error']}"
                }
            
            # Analyze demarcation data for root causes
            analysis_results = self._analyze_demarcation_data(demarcation_data, msisdn)
            
            return {
                "success": True,
                "msisdn": msisdn,
                "period": f"{start_time} to {end_time}",
                "demarcation_data": demarcation_data,
                "root_cause_analysis": analysis_results,
                "analysis_type": "Root Cause Analysis"
            }
            
        except Exception as e:
            log.error(f"Root cause analysis failed for {msisdn}: {e}")
            return {
                "success": False,
                "error": str(e),
                "msisdn": msisdn
            }
        
    def _analyze_demarcation_data(self, demarcation_data: Dict[str, Any], msisdn: str) -> Dict[str, Any]:
        """Analyze demarcation data - focus on root cause only"""
        
        root_causes = []
        severity_level = "low"
        recommendations = []
        
        try:
            # Check if this is the real RCA API response format
            if "data" in demarcation_data and "rootcause" in demarcation_data["data"]:
                # FOCUS: Handle hanya rootcause, skip abnormallist
                rootcause = demarcation_data["data"]["rootcause"]
                
                # Extract root cause information
                fault_attribution = rootcause.get("FaultAttribution", "Unknown")
                scene_description = rootcause.get("Scene Description", "Unknown")
                diagnosis_item = rootcause.get("DiagnosisItem", "Unknown")
                suggestion = rootcause.get("Suggestion", "No suggestion available")
                future_analysis = rootcause.get("Future Analysis", "")
                
                # Main root cause
                root_causes.append(f"Root Cause: {diagnosis_item}")
                root_causes.append(f"Fault Attribution: {fault_attribution}")
                root_causes.append(f"Scene: {scene_description}")
                
                # Parse Future Analysis for more details
                if future_analysis:
                    if "Alarm_Name:" in future_analysis:
                        alarms = future_analysis.split("Alarm_Name:")[1].split(";;")[0].strip()
                        root_causes.append(f"Related Alarms: {alarms}")
                    
                    if "Fault_cell_or_site:" in future_analysis:
                        fault_sites = future_analysis.split("Fault_cell_or_site:")[1].split(";;")[0].strip()
                        if fault_sites:
                            root_causes.append(f"Affected Sites: {fault_sites}")
                    
                    if "Category:" in future_analysis:
                        category = future_analysis.split("Category:")[1].split(";;")[0].strip()
                        root_causes.append(f"Issue Category: {category}")
                
                # Main recommendation dari suggestion
                recommendations.append(suggestion)
                
                # Determine severity berdasarkan rootcause saja
                if "Down" in scene_description or "Down" in future_analysis:
                    severity_level = "critical"
                elif "Issue" in diagnosis_item:
                    severity_level = "high"
                else:
                    severity_level = "medium"
                
                summary = f"Root cause analysis completed for MSISDN {msisdn}"
                
            else:
                return {
                    "root_causes": ["No RCA data available for analysis"],
                    "severity": "unknown", 
                    "recommendations": ["Request RCA data from network team"],
                    "summary": "Insufficient data for RCA"
                }
            
            return {
                "root_causes": root_causes,
                "severity": severity_level,
                "recommendations": recommendations,
                "summary": summary,
                "analysis_type": "Root Cause Analysis - Primary Issues Only"
            }
            
        except Exception as e:
            log.error(f"Error analyzing RCA data: {e}")
            return {
                "root_causes": [f"RCA analysis error: {str(e)}"],
                "severity": "error",
                "recommendations": ["Retry RCA analysis with valid data"],
                "summary": "RCA analysis failed"
            }
        
    async def format_analysis_response(self, analysis_result) -> str:
        """Format analysis result - Single Analysis section to avoid duplication"""
        
        # Extract ALL available metrics
        device_model = analysis_result.metrics.get("device_model", "Unknown")
        device_capability = analysis_result.metrics.get("device_capability", "Unknown")
        roam_status = analysis_result.metrics.get("roam_status", "Unknown")
        total_traffic = analysis_result.metrics.get("total_traffic_mb", 0)
        response_delay = analysis_result.metrics.get("response_delay_percent", 0)
        
        # ADD: Missing metrics dari history dan quality analysis
        avg_kqi = analysis_result.metrics.get("average_kqi", 0)
        avg_latency = analysis_result.metrics.get("average_latency_ms", 0)
        avg_rtt = analysis_result.metrics.get("average_rtt_ms", 0)
        peak_traffic = analysis_result.metrics.get("peak_traffic_mb", 0)
        daily_traffic = analysis_result.metrics.get("total_daily_traffic_mb", 0)
        valid_kqi_periods = analysis_result.metrics.get("valid_kqi_periods", 0)
        poor_kqi_periods = analysis_result.metrics.get("poor_kqi_periods", 0)
        
        # Build standardized response
        response = f"""**Ringkasan**
    Pengguna dengan MSISDN {analysis_result.msisdn} menggunakan perangkat {device_model} dengan kemampuan jaringan {device_capability} dan status roaming {roam_status.lower()}. Berdasarkan data, pengguna memiliki daily traffic {daily_traffic:.1f} MB, response delay {response_delay}%, dan KQI rata-rata {avg_kqi:.1f}.

    **Analysis**"""
        
        # GABUNG: Insights + Key Metrics jadi satu Analysis section
        # Kategorisasi insights untuk lebih terstruktur
        device_insights = []
        performance_insights = []
        quality_insights = []
        
        # Kategorisasi berdasarkan content
        for insight in analysis_result.insights:
            insight_lower = insight.lower()
            if any(keyword in insight_lower for keyword in ['perangkat', 'device', 'kemampuan', 'roaming']):
                device_insights.append(insight)
            elif any(keyword in insight_lower for keyword in ['traffic', 'daily', 'peak', 'hourly']):
                performance_insights.append(insight)
            else:
                quality_insights.append(insight)
        
        # Device & Network Info (singkat saja)
        if device_insights:
            response += "\n**📱 Device & Network:**"
            for insight in device_insights[:3]:  # Limit 3 untuk avoid redundancy
                response += f"\n• {insight}"
        
        # Performance Metrics (gabung traffic + metrics)
        if performance_insights:
            response += "\n\n**📊 Performance:**"
            for insight in performance_insights:
                if "total traffic sebesar" not in insight.lower():  # ← ADD THIS
                    response += f"\n• {insight}"
            
            # Tambah key metrics yang tidak ada di insights - USE EXTRACTED VARIABLES
            if avg_rtt > 0 and not any("rtt" in insight.lower() for insight in performance_insights):
                response += f"\n• Average RTT: {avg_rtt:.1f} ms"
            if avg_latency > 0 and not any("latency" in insight.lower() for insight in performance_insights):
                response += f"\n• Average Latency: {avg_latency:.1f} ms"
            if peak_traffic > 0 and not any("peak" in insight.lower() for insight in performance_insights):
                response += f"\n• Peak Traffic: {peak_traffic:.1f} MB"
        
        # Quality Assessment (KQI + assessment) - ADD KQI SUMMARY
        if quality_insights:
            response += "\n\n**🎯 Quality Assessment:**"
            for insight in quality_insights:
                response += f"\n• {insight}"
            
            # ADD: KQI summary jika tidak ada di insights
            if avg_kqi > 0 and not any("kqi" in insight.lower() for insight in quality_insights):
                if poor_kqi_periods > 0:
                    response += f"\n• KQI Issues: {poor_kqi_periods}/{valid_kqi_periods} periods below threshold"
                else:
                    response += f"\n• KQI Status: All {valid_kqi_periods} periods above threshold (avg: {avg_kqi:.1f})"
        
        # LLM Interactive Summary (tetap ada untuk actionable insights)
        response += "\n\n**Summary**"
        try:
            llm_summary = await self._generate_llm_summary(analysis_result)
            response += f"\n{llm_summary}"
        except Exception as e:
            response += f"\n• Error generating summary: {str(e)}"
        
        # Add follow-up prompt
        if hasattr(analysis_result, 'follow_up_suggestions') and analysis_result.follow_up_suggestions:
            response += "\n\n**Apakah anda ingin melanjutkan ke RCA? membutuhkan waktu 1-2 menit**"
        
        return response
    


    async def _generate_llm_summary(self, analysis_result) -> str:
        import traceback
        import asyncio
        print(f"🔍 DEBUG: _generate_llm_summary called")
        print(f"🔍 STACK: {traceback.format_stack()}")
        print(f"🔍 ASYNCIO: {asyncio.current_task()}")
        """Generate LLM summary"""
        try:
            from shared.utils.context_manager import OllamaContextManager
            context_manager = OllamaContextManager()
            
            metrics = analysis_result.metrics
            avg_kqi = metrics.get("average_kqi", 0)
            poor_kqi_periods = metrics.get("poor_kqi_periods", 0)
            valid_kqi_periods = metrics.get("valid_kqi_periods", 0)
            daily_traffic = metrics.get("total_daily_traffic_mb", 0)
            avg_latency = metrics.get("average_latency_ms", 0)
            avg_rtt = metrics.get("average_rtt_ms", 0)
            
            # Build LLM prompt
            prompt = f"""
    Analisis MSISDN {analysis_result.msisdn}:
    - KQI rata-rata: {avg_kqi:.1f} (threshold: 60)
    - Periode KQI buruk: {poor_kqi_periods}/{valid_kqi_periods}
    - Daily traffic: {daily_traffic:.1f} MB
    - Average latency: {avg_latency:.1f} ms
    - Average RTT: {avg_rtt:.1f} ms

    Buat 3-4 bullet summary dalam bahasa Indonesia:
    1. Status KQI (baik/buruk dengan detail jam jika ada masalah)
    2. Traffic pattern assessment 
    3. Latency/performance assessment
    4. Rekomendasi singkat

    Format: • **Kategori** - penjelasan singkat
    """
            
            response = await context_manager.call_ollama_with_context(
                prompt, [],
                """Anda adalah network analyst yang membuat summary ringkas dan actionable.
    WAJIB gunakan format:
    • **Status KQI** - assessment
    • **Traffic Pattern** - assessment  
    • **Performance** - assessment
    • **Rekomendasi** - action item
                
    Maksimal 4 bullet points, fokus pada insights actionable."""
            )
            
            return response.strip()
            
        except Exception as e:
            log.error(f"LLM summary generation failed: {e}")
            # Fallback manual summary - SYNC CALL OK
            manual_summary = self._generate_manual_summary(analysis_result)
            return manual_summary  # ← EXPLICIT RETURN

    def _generate_manual_summary(self, analysis_result) -> str:
        """Fallback manual summary jika LLM gagal"""
        
        metrics = analysis_result.metrics
        summary_lines = []
        
        # KQI Assessment
        avg_kqi = metrics.get("average_kqi", 0)
        poor_kqi_periods = metrics.get("poor_kqi_periods", 0)
        valid_kqi_periods = metrics.get("valid_kqi_periods", 0)
        
        if avg_kqi > 0:
            if poor_kqi_periods == 0:
                summary_lines.append(f"• **Status KQI** - Excellent dengan rata-rata {avg_kqi:.1f} (semua {valid_kqi_periods} periode > 60)")
            else:
                summary_lines.append(f"• **Masalah KQI** - {poor_kqi_periods}/{valid_kqi_periods} periode di bawah threshold 60")
        
        # Traffic Assessment  
        daily_traffic = metrics.get("total_daily_traffic_mb", 0)
        peak_traffic = metrics.get("peak_traffic_mb", 0)
        
        if daily_traffic > 100:
            summary_lines.append(f"• **Heavy User** - {daily_traffic:.1f}MB daily usage dengan peak {peak_traffic:.1f}MB")
        elif daily_traffic > 50:
            summary_lines.append(f"• **Normal Usage** - {daily_traffic:.1f}MB daily traffic")
        else:
            summary_lines.append(f"• **Light User** - {daily_traffic:.1f}MB daily usage")
        
        # Performance Assessment
        avg_latency = metrics.get("average_latency_ms", 0)
        avg_rtt = metrics.get("average_rtt_ms", 0)
        
        if avg_latency > 0 and avg_rtt > 0:
            if avg_latency < 50 and avg_rtt < 50:
                summary_lines.append(f"• **Performance Excellent** - Latency {avg_latency:.1f}ms, RTT {avg_rtt:.1f}ms")
            elif avg_latency < 100 and avg_rtt < 100:
                summary_lines.append(f"• **Performance Good** - Latency {avg_latency:.1f}ms, RTT {avg_rtt:.1f}ms")
            else:
                summary_lines.append(f"• **Performance Issues** - High latency {avg_latency:.1f}ms atau RTT {avg_rtt:.1f}ms")
        
        # Recommendation
        if poor_kqi_periods > 0 or avg_latency > 100:
            summary_lines.append("• **Rekomendasi** - Lakukan RCA untuk investigasi detail masalah kualitas")
        else:
            summary_lines.append("• **Status** - Network performance dalam kondisi optimal")
        
        return "\n".join(summary_lines)




    # Update get_comprehensive_analysis untuk menggunakan formatter ini
    async def get_comprehensive_analysis(self, msisdn: str, start_time: str, end_time: str) -> Dict[str, Any]:
        """Get comprehensive analysis from all telco APIs"""
        try:
            # Get data from all APIs
            combined_data = await self.api_client.get_all_data(msisdn, start_time, end_time)
            
            # Analyze the data
            analysis = self.analyzer.analyze_all_data(combined_data)
            
            # Format response consistently
            formatted_response = await self.format_analysis_response(analysis)
            
            response = {
                "success": True,
                "msisdn": msisdn,
                "period": f"{start_time} to {end_time}",
                "formatted_response": formatted_response,  # ADD THIS
                "raw_data": combined_data,
                "analysis": analysis.dict(),
                "summary": {
                    "total_insights": len(analysis.insights),
                    "recommendations_count": len(analysis.recommendations),
                    "key_metrics": analysis.metrics
                }
            }
            
            # Add follow-up prompt if suggestions exist
            if hasattr(analysis, 'follow_up_suggestions') and analysis.follow_up_suggestions:
                response["follow_up"] = {
                    "suggestions": analysis.follow_up_suggestions,
                    "available_commands": ["ya rca", "ya chart", "ya network"]
                }
            
            return response
            
        except Exception as e:
            log.error(f"Comprehensive analysis failed for {msisdn}: {e}")
            return {
                "success": False,
                "error": str(e),
                "msisdn": msisdn
            }