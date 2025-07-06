import json
import uuid
from typing import Dict, Any, List
from datetime import datetime

class ChartGenerator:
    """Generate Chart.js visualizations for API data"""
    
    def __init__(self):
        self.chart_js_cdn = "https://cdn.jsdelivr.net/npm/chart.js"
        
        # Color schemes
        self.colors = {
            "traffic": {"border": "rgb(54, 162, 235)", "background": "rgba(54, 162, 235, 0.2)"},
            "score": {"border": "rgb(255, 99, 132)", "background": "rgba(255, 99, 132, 0.2)"},
            "latency": {"border": "rgb(75, 192, 192)", "background": "rgba(75, 192, 192, 0.2)"}
        }
        
        print("📊 ChartGenerator initialized")
    
    def generate_traffic_score_chart(self, api_data: Dict, msisdn: str, period: str) -> str:
        """Generate dual-axis chart for Traffic and Score like the original"""
        try:
            history = api_data.get("history", [])
            
            if not history:
                return self._generate_no_data_message(msisdn, period)
            
            # Extract data for chart
            chart_data = self._extract_chart_data(history)
            
            # Generate unique chart ID
            chart_id = f"chart_{uuid.uuid4().hex[:8]}"
            
            # Build Chart.js configuration
            chart_config = {
                "type": "line",
                "data": {
                    "labels": chart_data["labels"],
                    "datasets": [
                        {
                            "label": "Total Traffic (MB)",
                            "data": chart_data["traffic"],
                            "borderColor": self.colors["traffic"]["border"],
                            "backgroundColor": self.colors["traffic"]["background"],
                            "yAxisID": "y",
                            "tension": 0.1,
                            "fill": False
                        },
                        {
                            "label": "Total Score", 
                            "data": chart_data["score"],
                            "borderColor": self.colors["score"]["border"],
                            "backgroundColor": self.colors["score"]["background"],
                            "yAxisID": "y1",
                            "tension": 0.1,
                            "fill": False
                        }
                    ]
                },
                "options": {
                    "responsive": True,
                    "interaction": {"intersect": False},
                    "scales": {
                        "x": {
                            "display": True,
                            "title": {"display": True, "text": "Time"}
                        },
                        "y": {
                            "type": "linear",
                            "display": True,
                            "position": "left",
                            "title": {"display": True, "text": "Traffic (MB)"},
                            "beginAtZero": True
                        },
                        "y1": {
                            "type": "linear",
                            "display": True,
                            "position": "right",
                            "title": {"display": True, "text": "Score"},
                            "grid": {"drawOnChartArea": False},
                            "beginAtZero": True,
                            "max": 100
                        }
                    },
                    "plugins": {
                        "title": {
                            "display": True,
                            "text": f"Traffic & Score Analysis - {msisdn}"
                        },
                        "legend": {"display": True, "position": "top"},
                        "tooltip": {
                            "mode": "index",
                            "intersect": False
                        }
                    }
                }
            }
            
            # Calculate summary stats
            stats = self._calculate_chart_stats(chart_data)
            
            # Generate HTML
            html = self._generate_chart_html(
                chart_id=chart_id,
                chart_config=chart_config,
                title="Traffic & Score Analysis",
                msisdn=msisdn,
                period=period,
                stats=stats
            )
            
            return html
            
        except Exception as e:
            return self._generate_error_chart(f"Chart generation failed: {str(e)}")
    
    def generate_latency_chart(self, api_data: Dict, msisdn: str, period: str) -> str:
        """Generate latency-focused chart"""
        try:
            history = api_data.get("history", [])
            
            if not history:
                return self._generate_no_data_message(msisdn, period)
            
            chart_data = self._extract_chart_data(history)
            chart_id = f"chart_{uuid.uuid4().hex[:8]}"
            
            chart_config = {
                "type": "line",
                "data": {
                    "labels": chart_data["labels"],
                    "datasets": [
                        {
                            "label": "Latency (ms)",
                            "data": chart_data["latency"],
                            "borderColor": self.colors["latency"]["border"],
                            "backgroundColor": self.colors["latency"]["background"],
                            "tension": 0.1,
                            "fill": True
                        }
                    ]
                },
                "options": {
                    "responsive": True,
                    "scales": {
                        "x": {"display": True, "title": {"display": True, "text": "Time"}},
                        "y": {"display": True, "title": {"display": True, "text": "Latency (ms)"}, "beginAtZero": True}
                    },
                    "plugins": {
                        "title": {"display": True, "text": f"Latency Analysis - {msisdn}"},
                        "legend": {"display": True}
                    }
                }
            }
            
            stats = {
                "avg_latency": sum(chart_data["latency"]) / len(chart_data["latency"]) if chart_data["latency"] else 0,
                "max_latency": max(chart_data["latency"]) if chart_data["latency"] else 0,
                "min_latency": min([l for l in chart_data["latency"] if l > 0]) if chart_data["latency"] else 0
            }
            
            html = self._generate_chart_html(
                chart_id=chart_id,
                chart_config=chart_config,
                title="Latency Analysis",
                msisdn=msisdn,
                period=period,
                stats=stats
            )
            
            return html
            
        except Exception as e:
            return self._generate_error_chart(f"Latency chart generation failed: {str(e)}")
    
    def _extract_chart_data(self, history: List) -> Dict[str, List]:
        """Extract and format data for charts"""
        labels = []
        traffic = []
        score = []
        latency = []
        
        for entry in history:
            # Format time label
            time_text = entry.get("TEXT", "")
            if " " in time_text:
                time_label = time_text.split(" ")[1]  # Extract time part
            else:
                time_label = time_text
            labels.append(time_label)
            
            # Extract numeric values
            try:
                traffic_val = float(entry.get("TOTALTRAFFIC", 0))
                score_val = float(entry.get("TOTALSCORE", 0)) 
                latency_val = float(entry.get("TOTALINTERNALLATENCYCCH", 0))
                
                traffic.append(traffic_val)
                score.append(score_val)
                latency.append(latency_val)
                
            except (ValueError, TypeError):
                traffic.append(0)
                score.append(0)
                latency.append(0)
        
        return {
            "labels": labels,
            "traffic": traffic,
            "score": score,
            "latency": latency
        }
    
    def _calculate_chart_stats(self, chart_data: Dict) -> Dict[str, Any]:
        """Calculate summary statistics for chart"""
        traffic = chart_data["traffic"]
        score = chart_data["score"]
        
        # Filter out zero values for meaningful averages
        non_zero_traffic = [t for t in traffic if t > 0]
        non_zero_scores = [s for s in score if s > 0]
        
        total_traffic = sum(traffic)
        avg_score = sum(non_zero_scores) / len(non_zero_scores) if non_zero_scores else 0
        peak_traffic = max(traffic) if traffic else 0
        
        # Find peak time
        peak_time = "N/A"
        if peak_traffic > 0:
            peak_index = traffic.index(peak_traffic)
            peak_time = chart_data["labels"][peak_index] if peak_index < len(chart_data["labels"]) else "N/A"
        
        return {
            "total_traffic": total_traffic,
            "avg_score": avg_score,
            "peak_traffic": peak_traffic,
            "peak_time": peak_time,
            "active_periods": len(non_zero_traffic),
            "total_periods": len(traffic)
        }
    
    def _generate_chart_html(self, chart_id: str, chart_config: Dict, title: str, msisdn: str, period: str, stats: Dict) -> str:
        """Generate complete HTML for chart"""
        
        # Format traffic display
        total_traffic = stats.get("total_traffic", 0)
        if total_traffic >= 1024:
            traffic_display = f"{total_traffic/1024:.2f} GB"
        else:
            traffic_display = f"{total_traffic:.2f} MB"
        
        # Summary statistics HTML
        summary_stats = f"""
        <div style="background: white; padding: 15px; border-radius: 4px; border-left: 4px solid #3498db;">
            <div style="font-weight: bold; color: #333;">Total Traffic</div>
            <div style="font-size: 18px; color: #3498db; margin-top: 5px;">{traffic_display}</div>
        </div>
        <div style="background: white; padding: 15px; border-radius: 4px; border-left: 4px solid #e74c3c;">
            <div style="font-weight: bold; color: #333;">Avg Score</div>
            <div style="font-size: 18px; color: #e74c3c; margin-top: 5px;">{stats.get('avg_score', 0):.1f}/100</div>
        </div>
        <div style="background: white; padding: 15px; border-radius: 4px; border-left: 4px solid #2ecc71;">
            <div style="font-weight: bold; color: #333;">Peak Usage</div>
            <div style="font-size: 18px; color: #2ecc71; margin-top: 5px;">{stats.get('peak_traffic', 0):.1f} MB</div>
        </div>
        <div style="background: white; padding: 15px; border-radius: 4px; border-left: 4px solid #f39c12;">
            <div style="font-weight: bold; color: #333;">Active Periods</div>
            <div style="font-size: 18px; color: #f39c12; margin-top: 5px;">{stats.get('active_periods', 0)}/{stats.get('total_periods', 0)}</div>
        </div>
        """
        
        # Complete HTML template
        html = f"""
<div style="width: 100%; max-width: 900px; margin: 20px auto; font-family: Arial, sans-serif;">
    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
        <h3 style="margin: 0 0 10px 0; color: #333;">📊 {title}</h3>
        <p style="margin: 0; color: #666; font-size: 14px;">📱 MSISDN: {msisdn} | 📅 Period: {period}</p>
    </div>
    
    <div style="position: relative; width: 100%; height: 450px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <canvas id="{chart_id}" style="max-height: 400px;"></canvas>
    </div>
    
    <script src="{self.chart_js_cdn}"></script>
    <script>
        const ctx_{chart_id} = document.getElementById('{chart_id}').getContext('2d');
        const chart_{chart_id} = new Chart(ctx_{chart_id}, {json.dumps(chart_config, indent=2)});
    </script>
    
    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-top: 20px;">
        <h4 style="margin: 0 0 15px 0; color: #333;">📈 Summary Statistics</h4>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
            {summary_stats}
        </div>
    </div>
    
    <div style="background: #e8f4fd; padding: 15px; border-radius: 8px; margin-top: 15px; border-left: 4px solid #3498db;">
        <p style="margin: 0; color: #2c3e50; font-size: 14px;">
            💡 <strong>Tip:</strong> Hover pada chart untuk melihat detail nilai. Traffic tinggi dengan score rendah menandakan kemungkinan adanya gangguan jaringan.
        </p>
    </div>
</div>
"""
        return html
    
    def _generate_no_data_message(self, msisdn: str, period: str) -> str:
        """Generate message when no data available"""
        return f"""
<div style="width: 100%; max-width: 600px; margin: 20px auto; text-align: center; font-family: Arial, sans-serif;">
    <div style="background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; padding: 30px;">
        <h3 style="color: #856404; margin: 0 0 15px 0;">📊 No Data Available</h3>
        <p style="color: #856404; margin: 0 0 15px 0;">
            Tidak ada data ditemukan untuk nomor <strong>{msisdn}</strong> pada periode <strong>{period}</strong>.
        </p>
        <div style="background: #fcf8e3; padding: 15px; border-radius: 4px; margin-top: 20px;">
            <p style="margin: 0; color: #856404; font-size: 14px;">
                💡 Kemungkinan penyebab: nomor tidak aktif, periode terlalu lama, atau tidak ada aktivitas data.
            </p>
        </div>
    </div>
</div>
"""
    
    def _generate_error_chart(self, error_message: str) -> str:
        """Generate error message for chart failures"""
        return f"""
<div style="width: 100%; max-width: 600px; margin: 20px auto; text-align: center; font-family: Arial, sans-serif;">
    <div style="background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 8px; padding: 30px;">
        <h3 style="color: #721c24; margin: 0 0 15px 0;">❌ Chart Generation Error</h3>
        <p style="color: #721c24; margin: 0;">
            {error_message}
        </p>
        <div style="background: #f1b0b7; padding: 15px; border-radius: 4px; margin-top: 20px;">
            <p style="margin: 0; color: #721c24; font-size: 14px;">
                🔧 Silakan coba lagi atau hubungi administrator jika masalah berlanjut.
            </p>
        </div>
    </div>
</div>
"""

    def test_chart_generation(self) -> str:
        """Generate test chart with sample data"""
        sample_data = {
            "history": [
                {"TOTALTRAFFIC": "10.5", "TOTALSCORE": "85", "TEXT": "2025-07-04 08:00"},
                {"TOTALTRAFFIC": "25.3", "TOTALSCORE": "92", "TEXT": "2025-07-04 09:00"},
                {"TOTALTRAFFIC": "15.7", "TOTALSCORE": "78", "TEXT": "2025-07-04 10:00"},
                {"TOTALTRAFFIC": "8.2", "TOTALSCORE": "95", "TEXT": "2025-07-04 11:00"}
            ]
        }
        
        return self.generate_traffic_score_chart(
            sample_data, 
            "628-111-992-172", 
            "Test Period"
        )