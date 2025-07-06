# agents/story_agent.py (SIMPLIFIED VERSION - 60% reduction)
from typing import Dict, Any, List
from datetime import datetime
import re
import requests

class StoryAgentSummary:
    """Simplified Story Agent for narrative generation"""
    
    def __init__(self):
        # Simple status/customer mappings
        self.status_mapping = {
            'BusinessStatusInProgress': 'Dalam Proses',
            'BusinessStatusResovled': 'Selesai', 
            'BusinessStatusClosed': 'Ditutup',
            'BusinessStatusOpen': 'Terbuka',
            'Open': 'Terbuka',
            'Closed': 'Ditutup'
        }
        
        self.customer_type_mapping = {
            'Consumer': 'Konsumen',
            'Corporate': 'Korporat', 
            'B2C': 'Business to Consumer',
            'B2B': 'Business to Business'
        }
    
    def generate_summary_narrative(self, data: List[Dict], location: str, time_period: str) -> str:
        """Generate comprehensive narrative for summary data"""
        
        if not data or len(data) == 0:
            return f"📊 **Tidak ditemukan keluhan di {location} {time_period}**"
        
        # Simple analysis
        total_complaints = sum(row.get('total_keluhan', 0) for row in data)
        
        # Group by customer and status
        customer_breakdown = {}
        status_breakdown = {}
        
        for row in data:
            count = row.get('total_keluhan', 0)
            
            # Customer analysis
            cust_type = row.get('customer_type_create_ticket', 'Unknown')
            customer_breakdown[cust_type] = customer_breakdown.get(cust_type, 0) + count
            
            # Status analysis
            status = row.get('business_status', 'Unknown')
            status_breakdown[status] = status_breakdown.get(status, 0) + count
        
        # Sort by count
        customer_sorted = sorted(customer_breakdown.items(), key=lambda x: x[1], reverse=True)
        status_sorted = sorted(status_breakdown.items(), key=lambda x: x[1], reverse=True)
        
        # Build narrative
        narrative_parts = []
        
        # Header
        narrative_parts.append(f"📊 **Ringkasan Keluhan di {location} {time_period}**\n")
        narrative_parts.append(f"Total **{total_complaints} keluhan** ditemukan dari **{len(data)} record** data.")
        
        # Overview
        if total_complaints == 0:
            narrative_parts.append("📈 **Overview:** Periode ini menunjukkan tidak ada keluhan yang tercatat.")
        elif total_complaints < 10:
            narrative_parts.append(f"📈 **Overview:** Volume keluhan rendah dengan {total_complaints} keluhan total.")
        elif total_complaints < 50:
            narrative_parts.append(f"📈 **Overview:** Volume keluhan sedang dengan {total_complaints} keluhan total.")
        else:
            narrative_parts.append(f"📈 **Overview:** Volume keluhan tinggi dengan {total_complaints} keluhan total, memerlukan perhatian khusus.")
        
        # Customer breakdown
        if customer_breakdown:
            narrative_parts.append("👥 **Breakdown per Tipe Customer:**")
            for i, (cust_type, count) in enumerate(customer_sorted[:3]):
                percentage = (count / total_complaints) * 100
                display_name = self.customer_type_mapping.get(cust_type, cust_type)
                
                if i == 0:
                    narrative_parts.append(f"• **{display_name}**: {count} keluhan ({percentage:.1f}%) - *Dominan*")
                else:
                    narrative_parts.append(f"• **{display_name}**: {count} keluhan ({percentage:.1f}%)")
        
        # Status breakdown
        if status_breakdown:
            narrative_parts.append("📋 **Status Keluhan:**")
            for status, count in status_sorted[:3]:
                percentage = (count / total_complaints) * 100
                display_name = self.status_mapping.get(status, status)
                
                # Add status indicator
                if 'Progress' in status or 'Open' in status:
                    indicator = "🔄"
                elif 'Resolved' in status or 'Closed' in status:
                    indicator = "✅"
                else:
                    indicator = "📌"
                
                narrative_parts.append(f"• {indicator} **{display_name}**: {count} keluhan ({percentage:.1f}%)")
        
        # Simple insights
        insights = []
        if customer_breakdown:
            dominant_customer = customer_sorted[0]
            customer_name = self.customer_type_mapping.get(dominant_customer[0], dominant_customer[0])
            percentage = (dominant_customer[1] / total_complaints) * 100
            
            if percentage > 70:
                insights.append(f"🎯 Customer **{customer_name}** mendominasi dengan {percentage:.1f}% keluhan")
        
        if status_breakdown:
            dominant_status = status_sorted[0]
            status_name = self.status_mapping.get(dominant_status[0], dominant_status[0])
            percentage = (dominant_status[1] / total_complaints) * 100
            
            if 'Progress' in dominant_status[0] and percentage > 60:
                insights.append(f"⚠️ {percentage:.1f}% keluhan masih **{status_name}** - perlu follow up")
            elif 'Resolved' in dominant_status[0] and percentage > 70:
                insights.append(f"✅ {percentage:.1f}% keluhan sudah **{status_name}** - indikator positif")
        
        if total_complaints > 100:
            insights.append("📈 Volume tinggi memerlukan prioritas penanganan")
        elif total_complaints < 5:
            insights.append("📉 Volume rendah menunjukkan kondisi stabil")
        
        if not insights:
            insights.append("📋 Data menunjukkan pola distribusi normal")
        
        narrative_parts.append("🔍 **Key Insights:**")
        for insight in insights:
            narrative_parts.append(f"• {insight}")
        
        return "\n\n".join(narrative_parts)
    
    def extract_location_from_entities(self, entities: Dict[str, Any]) -> str:
        """Extract location name from entities"""
        geo_entities = entities.get('geographic', [])
        if geo_entities:
            location = geo_entities[0].get('value', 'lokasi yang diminta')
            return location
        return "lokasi yang diminta"
    
    def extract_time_period_from_entities(self, entities: Dict[str, Any]) -> str:
        """Extract time period description from entities"""
        temporal_entities = entities.get('temporal', [])
        if temporal_entities:
            value = temporal_entities[0].get('value', '').lower()
            
            # Extract interval pattern: INTERVAL '2 day', INTERVAL '1 week', etc
            interval_match = re.search(r"interval\s+'(\d+)\s+(\w+)'", value)
            
            if interval_match and '- interval' in value:
                number = interval_match.group(1)
                unit = interval_match.group(2)
                
                # Map units
                if unit in ['day', 'days']:
                    if number == '1':
                        return "kemarin"
                    else:
                        return f"{number} hari lalu"
                elif unit in ['week', 'weeks']:
                    if number == '1':
                        return "minggu lalu"
                    else:
                        return f"{number} minggu lalu"
                elif unit in ['month', 'months']:
                    if number == '1':
                        return "bulan lalu"
                    else:
                        return f"{number} bulan lalu"
            
            # Current periods (tanpa interval negatif)
            elif 'current_date' in value and '- interval' not in value:
                if 'week' in value:
                    return "minggu ini"
                elif 'month' in value:
                    return "bulan ini" 
                elif 'day' in value:
                    return "hari ini"
                    
        return "periode yang diminta"
    
    def generate_detail_narrative(self, ticket_data: Dict) -> str:
        """Generate detailed narrative for individual ticket"""
        
        if not ticket_data:
            return "❌ Data tidak ditemukan."
        
        # Extract key fields
        order_id = ticket_data.get('order_id', 'N/A')
        description = ticket_data.get('description_fault_sumptomps_create_ticket', '')
        cch_suggestion = ticket_data.get('cch_suggestion_l1_assign', '')
        
        # Parse basic info
        keluhan = self._extract_and_improve_keluhan(description)
        nama = self._extract_field(description, r'Nama\s*(?:Customer)?\s*:\s*([^\n]+)')
        msisdn = self._extract_field(description, r'MSISDN(?:-[AB])?\s*(?:Yang [Bermasalah]+)?\s*:\s*:?(\d+)')
        tanggal = self._extract_field(description, r'Tanggal(?:/Jam)?\s*Kejadian\s*:\s*([^\n]+)')
        lokasi = self._extract_field(description, r'Lokasi\s*(?:Pelanggan)?\s*(?:\(alamat\))?\s*:\s*([^→\n]+)')
        
        # Parse device info
        mode_jaringan = ticket_data.get('type_jaringan', 'N/A')
        kategori_keluhan = self._extract_field(description, r'Kategori Keluhan\s*:\s*([^\n]+)')
        tipe_pelanggan = self._extract_field(description, r'Customer Tier pelanggan\s*:\s*([^\n]+)')
        sim_capability = self._extract_field(description, r'SIM Capability\s*:\s*([^\n]+)')
        device = ticket_data.get('type_handset', 'N/A')
        
        # Parse coordinates
        lat = ticket_data.get('latitude_l2_assign', 'N/A')
        lng = ticket_data.get('longitude_l2_assign', 'N/A')
        coord_text = f"{lat}, {lng}" if lat != 'N/A' and lng != 'N/A' else "Tidak tersedia"
        
        # Parse technical analysis
        tech_analysis = self._parse_simple_technical_analysis(cch_suggestion)
        
        # Build response
        response_parts = []
        
        # Header Info
        response_parts.append(f"**No. Ticket** : {order_id}")
        response_parts.append(f"**Detail Keluhan** : {keluhan}")
        response_parts.append(f"**Nama** : {nama}")
        response_parts.append(f"**MSISDN** : {msisdn}")
        response_parts.append(f"**Tanggal Kejadian** : {tanggal}")
        response_parts.append("\n------------------")
        
        # Lokasi & Koordinat
        response_parts.append(f"**Lokasi** : {lokasi}")
        response_parts.append(f"**Long Lat** : {coord_text}")
        response_parts.append("\n-------------------")
        
        # Device & Network Info
        response_parts.append(f"**Mode Jaringan** : {mode_jaringan}")
        response_parts.append(f"**Kategori Keluhan** : {kategori_keluhan}")
        response_parts.append(f"**Tipe Pelanggan** : {tipe_pelanggan}")
        response_parts.append(f"**SIM Capability** : {sim_capability}")
        response_parts.append(f"**Device** : {device}")
        response_parts.append("\n-------------------")
        
        # Technical Analysis
        if tech_analysis:
            response_parts.append("\n**Technical Analysis (CCH):**")
            for key, value in tech_analysis.items():
                if value != "N/A":
                    response_parts.append(f"• **{key.title()}:** {value}")
        
        return "\n".join(response_parts)
    
    def _extract_field(self, text: str, pattern: str) -> str:
        """Extract field using regex pattern"""
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else "N/A"
    
    def _extract_and_improve_keluhan(self, description: str) -> str:
        """Extract and improve keluhan text"""
        raw_keluhan = self._extract_field(description, r'Detail Keluhan\s*:\s*([^\n]+)')
        if raw_keluhan == "N/A":
            raw_keluhan = self._extract_field(description, r'Detail Complain\s*:\s*([^\n]+)')
        
        if raw_keluhan != "N/A":
            return self._improve_keluhan_with_llm(raw_keluhan)
        return "N/A"
    
    def _improve_keluhan_with_llm(self, raw_keluhan: str) -> str:
        """Improve keluhan text using LLM"""
        prompt = f"""
Perbaiki keluhan pelanggan ini menjadi 1 kalimat yang jelas:
"{raw_keluhan}"

Aturan:
- "ket" -> "keterangan"
- Perbaiki kata singkatan
- Hanya berikan hasil akhir, tidak perlu penjelasan

Contoh:
Input: "Tidak bisa terima call ket dialihkan"
Output: "Tidak dapat menerima panggilan ketika dialihkan"
"""
        
        try:
            response = requests.post("http://localhost:11434/api/generate", 
                json={"model": "llama3", "prompt": prompt, "stream": False, "options": {"temperature": 0.3}})
            
            if response.status_code == 200:
                result = response.json()["response"].strip()
                
                # Extract clean result
                lines = [line.strip() for line in result.split('\n') if line.strip()]
                
                for line in reversed(lines):
                    if not any(skip in line.lower() for skip in ['perbaikan:', 'contoh:', 'aturan:', 'input:', 'output:', 'berikut']):
                        if len(line) > 10 and not line.startswith('*'):
                            return line.strip('"')
                
                return lines[0] if lines else raw_keluhan
        except:
            pass
        
        # Manual fallback
        return raw_keluhan.replace("ket ", "keterangan ").replace(" ga ", " tidak ")
    
    def _parse_simple_technical_analysis(self, cch_suggestion: str) -> Dict[str, str]:
        """Simple technical analysis parsing"""
        if not cch_suggestion:
            return {}
        
        analysis = {}
        
        # Extract basic fields
        analysis["cause"] = self._extract_field(cch_suggestion, r'cause:\s*([^,]+)')
        analysis["category"] = self._extract_field(cch_suggestion, r'Category:\s*([^;]+)')
        analysis["dominant_cell"] = self._extract_field(cch_suggestion, r'Dominant\s+Cell:\s*([^;]+)')
        
        # Extract suggestion with simple translation
        suggestion_raw = self._extract_field(cch_suggestion, r'suggestion:\s*(.*?)(?=,\s*other:|$)')
        if suggestion_raw != "N/A":
            analysis["suggestion"] = self._simple_translate_suggestion(suggestion_raw)
        
        return {k: v for k, v in analysis.items() if v != "N/A"}
    
    def _simple_translate_suggestion(self, text: str) -> str:
        """Simple suggestion translation"""
        translations = {
            "If nearest sites no serving, need crosscheck Availability": "🔧 Jika site terdekat tidak serving, perlu crosscheck Availability",
            "Make RSRP serving cells more dominant, by increase RS Power, Uptilt or reazimuth": "📡 Buat RSRP serving cells lebih dominan dengan meningkatkan RS Power, Uptilt atau reazimuth", 
            "Check whether area serving are blocking by building or countour": "🔍 Periksa apakah area serving terhalang oleh building atau countour"
        }
        
        if ';;' in text:
            suggestions = text.split(';;')
            formatted = []
            for suggestion in suggestions:
                suggestion = suggestion.strip()
                if suggestion:
                    suggestion = re.sub(r'^\d+\.\s*', '', suggestion)
                    formatted.append(translations.get(suggestion, f"🔧 {suggestion}"))
            return '\n'.join(formatted)
        
        return translations.get(text.strip(), f"🔧 {text}")

# Factory function for compatibility
def create_story_agent():
    """Factory function untuk MainCrew compatibility"""
    return StoryAgentSummary()