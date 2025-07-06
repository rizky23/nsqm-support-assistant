# import re
# from datetime import datetime, timedelta
# from typing import Dict, Optional, Tuple

# class TimeParser:
#     """Parse natural language time expressions to API format"""
    
#     def __init__(self):
#         # Time expression patterns
#         self.patterns = {
#             'hours_ago': r'(\d+)\s*(jam|hour)s?\s*(yang\s+)?lalu',
#             'minutes_ago': r'(\d+)\s*(menit|minute)s?\s*(yang\s+)?lalu',
#             'specific_hour': r'jam\s*(\d{1,2})',
#             'specific_time': r'(\d{1,2})[:.:](\d{2})',
#             'today': r'(hari\s+ini|today|sekarang)',
#             'yesterday': r'(kemarin|yesterday)',
#             'days_ago': r'(\d+)\s*(hari|day)s?\s*(yang\s+)?lalu',
#             'this_morning': r'(pagi\s+(ini|tadi)|this\s+morning)',
#             'this_afternoon': r'(siang\s+(ini|tadi)|this\s+afternoon)',
#             'this_evening': r'(sore\s+(ini|tadi)|this\s+evening)',
#             'last_night': r'(malam\s+tadi|last\s+night)',
#             'date_format': r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})'
#         }
        
#         # Default time ranges for different periods
#         self.default_ranges = {
#             'full_day': {'start': '00:00', 'end': '23:59'},
#             'morning': {'start': '06:00', 'end': '11:59'},
#             'afternoon': {'start': '12:00', 'end': '17:59'},
#             'evening': {'start': '18:00', 'end': '22:59'},
#             'night': {'start': '23:00', 'end': '05:59'}
#         }
    
#     def parse_time_expression(self, text: str) -> Dict[str, str]:
#         """Parse time expression and return start/end time for API"""
#         text = text.lower().strip()
#         now = datetime.now()
        
#         # Try to match different patterns
#         result = self._try_parse_patterns(text, now)
        
#         if result:
#             return {
#                 "startTime": result[0],
#                 "endTime": result[1],
#                 "parsed_expression": text,
#                 "success": True
#             }
        
#         # Default to today if no pattern matches
#         return {
#             "startTime": now.strftime("%Y-%m-%d 00:00"),
#             "endTime": now.strftime("%Y-%m-%d 23:59"),
#             "parsed_expression": text,
#             "success": False,
#             "fallback": "today"
#         }
    
#     def _try_parse_patterns(self, text: str, now: datetime) -> Optional[Tuple[str, str]]:
#         """Try to match against all patterns"""
        
#         # Hours ago - "2 jam lalu"
#         match = re.search(self.patterns['hours_ago'], text)
#         if match:
#             hours = int(match.group(1))
#             target_time = now - timedelta(hours=hours)
#             start_time = target_time.replace(minute=0, second=0)
#             end_time = target_time.replace(minute=59, second=59)
#             return (
#                 start_time.strftime("%Y-%m-%d %H:%M"),
#                 end_time.strftime("%Y-%m-%d %H:%M")
#             )
        
#         # Minutes ago - "30 menit lalu"
#         match = re.search(self.patterns['minutes_ago'], text)
#         if match:
#             minutes = int(match.group(1))
#             target_time = now - timedelta(minutes=minutes)
#             start_time = target_time - timedelta(minutes=30)  # 30 min window
#             end_time = target_time + timedelta(minutes=30)
#             return (
#                 start_time.strftime("%Y-%m-%d %H:%M"),
#                 end_time.strftime("%Y-%m-%d %H:%M")
#             )
        
#         # Specific hour - "jam 10"
#         match = re.search(self.patterns['specific_hour'], text)
#         if match:
#             hour = int(match.group(1))
#             if 0 <= hour <= 23:
#                 target_date = now.date()
#                 start_time = datetime.combine(target_date, datetime.min.time().replace(hour=hour))
#                 end_time = start_time.replace(minute=59, second=59)
#                 return (
#                     start_time.strftime("%Y-%m-%d %H:%M"),
#                     end_time.strftime("%Y-%m-%d %H:%M")
#                 )
        
#         # Specific time - "10:30" or "10.30"
#         match = re.search(self.patterns['specific_time'], text)
#         if match:
#             hour, minute = int(match.group(1)), int(match.group(2))
#             if 0 <= hour <= 23 and 0 <= minute <= 59:
#                 target_date = now.date()
#                 target_time = datetime.combine(target_date, datetime.min.time().replace(hour=hour, minute=minute))
#                 start_time = target_time - timedelta(minutes=30)
#                 end_time = target_time + timedelta(minutes=30)
#                 return (
#                     start_time.strftime("%Y-%m-%d %H:%M"),
#                     end_time.strftime("%Y-%m-%d %H:%M")
#                 )
        
#         # Today - "hari ini"
#         if re.search(self.patterns['today'], text):
#             return (
#                 now.strftime("%Y-%m-%d 00:00"),
#                 now.strftime("%Y-%m-%d 23:59")
#             )
        
#         # Yesterday - "kemarin"
#         if re.search(self.patterns['yesterday'], text):
#             yesterday = now - timedelta(days=1)
#             return (
#                 yesterday.strftime("%Y-%m-%d 00:00"),
#                 yesterday.strftime("%Y-%m-%d 23:59")
#             )
        
#         # Days ago - "2 hari lalu"
#         match = re.search(self.patterns['days_ago'], text)
#         if match:
#             days = int(match.group(1))
#             target_date = now - timedelta(days=days)
#             return (
#                 target_date.strftime("%Y-%m-%d 00:00"),
#                 target_date.strftime("%Y-%m-%d 23:59")
#             )
        
#         # Time of day expressions
#         if re.search(self.patterns['this_morning'], text):
#             return self._get_time_of_day_range(now, 'morning')
#         elif re.search(self.patterns['this_afternoon'], text):
#             return self._get_time_of_day_range(now, 'afternoon')
#         elif re.search(self.patterns['this_evening'], text):
#             return self._get_time_of_day_range(now, 'evening')
#         elif re.search(self.patterns['last_night'], text):
#             yesterday = now - timedelta(days=1)
#             return self._get_time_of_day_range(yesterday, 'night')
        
#         # Date format - "01/07/2025"
#         match = re.search(self.patterns['date_format'], text)
#         if match:
#             day, month, year = match.groups()
#             try:
#                 if len(year) == 2:
#                     year = '20' + year
#                 target_date = datetime(int(year), int(month), int(day))
#                 return (
#                     target_date.strftime("%Y-%m-%d 00:00"),
#                     target_date.strftime("%Y-%m-%d 23:59")
#                 )
#             except ValueError:
#                 pass
        
#         return None
    
#     def _get_time_of_day_range(self, date: datetime, time_period: str) -> Tuple[str, str]:
#         """Get start/end time for specific time of day"""
#         range_info = self.default_ranges[time_period]
        
#         start_hour, start_min = map(int, range_info['start'].split(':'))
#         end_hour, end_min = map(int, range_info['end'].split(':'))
        
#         start_time = date.replace(hour=start_hour, minute=start_min, second=0)
        
#         # Handle night period that crosses midnight
#         if time_period == 'night' and end_hour < start_hour:
#             end_time = (date + timedelta(days=1)).replace(hour=end_hour, minute=end_min, second=59)
#         else:
#             end_time = date.replace(hour=end_hour, minute=end_min, second=59)
        
#         return (
#             start_time.strftime("%Y-%m-%d %H:%M"),
#             end_time.strftime("%Y-%m-%d %H:%M")
#         )
    
#     def validate_time_range(self, start_time: str, end_time: str) -> Dict[str, any]:
#         """Validate parsed time range"""
#         try:
#             start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
#             end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M")
            
#             if start_dt >= end_dt:
#                 return {
#                     "valid": False,
#                     "error": "Start time must be before end time"
#                 }
            
#             # Check if range is not too far in the future
#             now = datetime.now()
#             if start_dt > now + timedelta(days=1):
#                 return {
#                     "valid": False,
#                     "error": "Time range cannot be in the future"
#                 }
            
#             # Check if range is not too old (e.g., more than 30 days)
#             if end_dt < now - timedelta(days=30):
#                 return {
#                     "valid": False,
#                     "error": "Time range is too old (max 30 days ago)"
#                 }
            
#             duration = end_dt - start_dt
#             return {
#                 "valid": True,
#                 "start_time": start_time,
#                 "end_time": end_time,
#                 "duration_hours": duration.total_seconds() / 3600,
#                 "duration_text": self._format_duration(duration)
#             }
            
#         except ValueError as e:
#             return {
#                 "valid": False,
#                 "error": f"Invalid time format: {str(e)}"
#             }
    
#     def _format_duration(self, duration: timedelta) -> str:
#         """Format duration for display"""
#         total_seconds = int(duration.total_seconds())
#         hours, remainder = divmod(total_seconds, 3600)
#         minutes, _ = divmod(remainder, 60)
        
#         if hours > 0:
#             return f"{hours} jam {minutes} menit"
#         else:
#             return f"{minutes} menit"


import re
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

class TimeParser:
    """Parse natural language time expressions to API format"""
    
    def __init__(self):
        # Time expression patterns
        self.patterns = {
            'hours_ago': r'(\d+)\s*(jam|hour)s?\s*(yang\s+)?lalu',
            'minutes_ago': r'(\d+)\s*(menit|minute)s?\s*(yang\s+)?lalu',
            'specific_hour': r'jam\s*(\d{1,2})',
            'specific_time': r'(\d{1,2})[:.:](\d{2})',
            'today': r'(hari\s+ini|today|sekarang)',
            'yesterday': r'(kemarin|yesterday)',
            'days_ago': r'(\d+)\s*(hari|day)s?\s*(yang\s+)?lalu',
            'this_morning': r'(pagi\s+(ini|tadi)|this\s+morning)',
            'this_afternoon': r'(siang\s+(ini|tadi)|this\s+afternoon)',
            'this_evening': r'(sore\s+(ini|tadi)|this\s+evening)',
            'last_night': r'(malam\s+tadi|last\s+night)',
            'date_format': r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})'
        }
        
        # Default time ranges for different periods
        self.default_ranges = {
            'full_day': {'start': '00:00', 'end': '23:55'},
            'morning': {'start': '06:00', 'end': '11:59'},
            'afternoon': {'start': '12:00', 'end': '17:59'},
            'evening': {'start': '18:00', 'end': '22:59'},
            'night': {'start': '23:00', 'end': '05:59'}
        }
    
    def parse_time_expression(self, text: str) -> Dict[str, str]:
        """Parse time expression and return start/end time for API"""
        text = text.lower().strip()
        now = datetime.now()
        
        # Try to match different patterns
        result = self._try_parse_patterns(text, now)
        
        if result:
            return {
                "startTime": result[0],
                "endTime": result[1],
                "parsed_expression": text,
                "success": True
            }
        
        # Default to today if no pattern matches
        return {
            "startTime": now.strftime("%Y-%m-%d 00:00"),
            "endTime": now.strftime("%Y-%m-%d 23:55"),
            "parsed_expression": text,
            "success": False,
            "fallback": "today"
        }
    
    def _try_parse_patterns(self, text: str, now: datetime) -> Optional[Tuple[str, str]]:
        """Try to match against all patterns"""
        
        # Hours ago - "2 jam lalu"
        match = re.search(self.patterns['hours_ago'], text)
        if match:
            hours = int(match.group(1))
            target_time = now - timedelta(hours=hours)
            start_time = target_time.replace(minute=0, second=0)
            end_time = target_time.replace(minute=59, second=59)
            return (
                start_time.strftime("%Y-%m-%d %H:%M"),
                end_time.strftime("%Y-%m-%d %H:%M")
            )
        
        # Minutes ago - "30 menit lalu"
        match = re.search(self.patterns['minutes_ago'], text)
        if match:
            minutes = int(match.group(1))
            target_time = now - timedelta(minutes=minutes)
            start_time = target_time - timedelta(minutes=30)  # 30 min window
            end_time = target_time + timedelta(minutes=30)
            return (
                start_time.strftime("%Y-%m-%d %H:%M"),
                end_time.strftime("%Y-%m-%d %H:%M")
            )
        
        # Specific hour - "jam 10"
        match = re.search(self.patterns['specific_hour'], text)
        if match:
            hour = int(match.group(1))
            if 0 <= hour <= 23:
                target_date = now.date()
                start_time = datetime.combine(target_date, datetime.min.time().replace(hour=hour))
                end_time = start_time.replace(minute=59, second=59)
                return (
                    start_time.strftime("%Y-%m-%d %H:%M"),
                    end_time.strftime("%Y-%m-%d %H:%M")
                )
        
        # Specific time - "10:30" or "10.30"
        match = re.search(self.patterns['specific_time'], text)
        if match:
            hour, minute = int(match.group(1)), int(match.group(2))
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                target_date = now.date()
                target_time = datetime.combine(target_date, datetime.min.time().replace(hour=hour, minute=minute))
                start_time = target_time - timedelta(minutes=30)
                end_time = target_time + timedelta(minutes=30)
                return (
                    start_time.strftime("%Y-%m-%d %H:%M"),
                    end_time.strftime("%Y-%m-%d %H:%M")
                )
        
        # Today - "hari ini"
        if re.search(self.patterns['today'], text):
            return (
                now.strftime("%Y-%m-%d 00:00"),
                now.strftime("%Y-%m-%d 23:55")
            )
        
        # Yesterday - "kemarin"
        if re.search(self.patterns['yesterday'], text):
            yesterday = now - timedelta(days=1)
            return (
                yesterday.strftime("%Y-%m-%d 00:00"),
                yesterday.strftime("%Y-%m-%d 23:55")
            )
        
        # Days ago - "2 hari lalu"
        match = re.search(self.patterns['days_ago'], text)
        if match:
            days = int(match.group(1))
            target_date = now - timedelta(days=days)
            return (
                target_date.strftime("%Y-%m-%d 00:00"),
                target_date.strftime("%Y-%m-%d 23:55")
            )
        
        # Time of day expressions
        if re.search(self.patterns['this_morning'], text):
            return self._get_time_of_day_range(now, 'morning')
        elif re.search(self.patterns['this_afternoon'], text):
            return self._get_time_of_day_range(now, 'afternoon')
        elif re.search(self.patterns['this_evening'], text):
            return self._get_time_of_day_range(now, 'evening')
        elif re.search(self.patterns['last_night'], text):
            yesterday = now - timedelta(days=1)
            return self._get_time_of_day_range(yesterday, 'night')
        
        # Date format - "01/07/2025"
        match = re.search(self.patterns['date_format'], text)
        if match:
            day, month, year = match.groups()
            try:
                if len(year) == 2:
                    year = '20' + year
                target_date = datetime(int(year), int(month), int(day))
                return (
                    target_date.strftime("%Y-%m-%d 00:00"),
                    target_date.strftime("%Y-%m-%d 23:55")
                )
            except ValueError:
                pass
        
        # Try LLM extraction as last resort
        llm_result = self._extract_date_with_llm(text)
        if llm_result:
            return llm_result
        
        return None
    
    def _extract_date_with_llm(self, text: str) -> Optional[Tuple[str, str]]:
        """Use LLM to extract date and return API format"""
        
        prompt = f"""Extract date from text: "{text}"

If date found, return ONLY in this exact format:
YYYY-MM-DD 00:00,YYYY-MM-DD 23:55

Examples:
- "1 juli 2025" → "2025-07-01 00:00,2025-07-01 23:55"  
- "01 jul 25" → "2025-07-01 00:00,2025-07-01 23:55"
- "1jul25" → "2025-07-01 00:00,2025-07-01 23:55"
- "tanggal 15 agustus 2025" → "2025-08-15 00:00,2025-08-15 23:55"
- "15/8/25" → "2025-08-15 00:00,2025-08-15 23:55"

If no date found, return: NONE

Text: {text}
Answer:"""

        try:
            response = requests.post("http://host.docker.internal:11434/api/generate", 
                json={
                    "model": "llama3", 
                    "prompt": prompt, 
                    "stream": False,
                    "options": {"temperature": 0.0}
                }, timeout=10)
            
            if response.status_code == 200:
                result = response.json()["response"].strip()

                # Extract the date line (look for YYYY-MM-DD pattern)
                import re
                date_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2},\d{4}-\d{2}-\d{2} \d{2}:\d{2})', result)

                if date_match:
                    date_line = date_match.group(1)
                    parts = date_line.split(",")
                    if len(parts) == 2:
                        start_time = parts[0].strip()
                        end_time = parts[1].strip()
                        
                        # Validate format
                        try:
                            datetime.strptime(start_time, "%Y-%m-%d %H:%M")
                            datetime.strptime(end_time, "%Y-%m-%d %H:%M")
                            return (start_time, end_time)
                        except ValueError:
                            pass
            
        except Exception as e:
            print(f"LLM date extraction failed: {str(e)}")
        
        return None
    
    def _get_time_of_day_range(self, date: datetime, time_period: str) -> Tuple[str, str]:
        """Get start/end time for specific time of day"""
        range_info = self.default_ranges[time_period]
        
        start_hour, start_min = map(int, range_info['start'].split(':'))
        end_hour, end_min = map(int, range_info['end'].split(':'))
        
        start_time = date.replace(hour=start_hour, minute=start_min, second=0)
        
        # Handle night period that crosses midnight
        if time_period == 'night' and end_hour < start_hour:
            end_time = (date + timedelta(days=1)).replace(hour=end_hour, minute=end_min, second=59)
        else:
            end_time = date.replace(hour=end_hour, minute=end_min, second=59)
        
        return (
            start_time.strftime("%Y-%m-%d %H:%M"),
            end_time.strftime("%Y-%m-%d %H:%M")
        )
    
    def validate_time_range(self, start_time: str, end_time: str) -> Dict[str, any]:
        """Validate parsed time range"""
        try:
            start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M")
            
            if start_dt >= end_dt:
                return {
                    "valid": False,
                    "error": "Start time must be before end time"
                }
            
            # Check if range is not too far in the future
            now = datetime.now()
            if start_dt > now + timedelta(days=1):
                return {
                    "valid": False,
                    "error": "Time range cannot be in the future"
                }
            
            # Check if range is not too old (e.g., more than 30 days)
            if end_dt < now - timedelta(days=30):
                return {
                    "valid": False,
                    "error": "Time range is too old (max 30 days ago)"
                }
            
            duration = end_dt - start_dt
            return {
                "valid": True,
                "start_time": start_time,
                "end_time": end_time,
                "duration_hours": duration.total_seconds() / 3600,
                "duration_text": self._format_duration(duration)
            }
            
        except ValueError as e:
            return {
                "valid": False,
                "error": f"Invalid time format: {str(e)}"
            }
    
    def _format_duration(self, duration: timedelta) -> str:
        """Format duration for display"""
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours} jam {minutes} menit"
        else:
            return f"{minutes} menit"