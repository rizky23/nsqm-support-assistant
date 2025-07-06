# knowledge/document_processor.py
import os
import re
from typing import List, Dict, Any
from pathlib import Path

class DocumentProcessor:
    """Process various document formats for knowledge base"""
    
    def __init__(self):
        self.supported_formats = ['.txt', '.md', '.pdf', '.xlsx', '.csv']
        
    def process_directory(self, docs_path: str = "./docs") -> List[Dict[str, Any]]:
        """Process all documents in directory"""
        processed_docs = []
        
        if not os.path.exists(docs_path):
            print(f"📁 Creating docs directory: {docs_path}")
            os.makedirs(docs_path)
            return processed_docs
        
        for file_path in Path(docs_path).rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                try:
                    docs = self.process_file(str(file_path))
                    processed_docs.extend(docs)
                    print(f"✅ Processed: {file_path.name} -> {len(docs)} chunks")
                except Exception as e:
                    print(f"❌ Error processing {file_path.name}: {str(e)}")
        
        return processed_docs
    
    def process_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Process single file into chunks"""
        file_extension = Path(file_path).suffix.lower()
        filename = Path(file_path).name
        
        if file_extension == '.txt' or file_extension == '.md':
            return self._process_text_file(file_path, filename)
        elif file_extension == '.pdf':
            return self._process_pdf_file(file_path, filename)
        elif file_extension in ['.xlsx', '.csv']:  # ← Tambah ini
            return self._process_excel_file(file_path, filename)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
    
    def _process_text_file(self, file_path: str, filename: str) -> List[Dict[str, Any]]:
        """Process text/markdown files"""
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Split into chunks
        chunks = self._split_text_into_chunks(content)
        
        processed_docs = []
        for i, chunk in enumerate(chunks):
            processed_docs.append({
                'content': chunk,
                'metadata': {
                    'title': filename,
                    'chunk_id': i + 1,
                    'total_chunks': len(chunks),
                    'file_type': 'text',
                    'source_path': file_path
                }
            })
        
        return processed_docs
    
    def _process_pdf_file(self, file_path: str, filename: str) -> List[Dict[str, Any]]:
        """Process PDF files (basic text extraction)"""
        try:
            import PyPDF2
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                full_text = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    full_text += f"\n[Page {page_num + 1}]\n"
                    full_text += page.extract_text()
            
            # Split into chunks
            chunks = self._split_text_into_chunks(full_text)
            
            processed_docs = []
            for i, chunk in enumerate(chunks):
                processed_docs.append({
                    'content': chunk,
                    'metadata': {
                        'title': filename,
                        'chunk_id': i + 1,
                        'total_chunks': len(chunks),
                        'file_type': 'pdf',
                        'source_path': file_path,
                        'pages': len(pdf_reader.pages)
                    }
                })
            
            return processed_docs
            
        except ImportError:
            print("❌ PyPDF2 not installed. Install with: pip install PyPDF2")
            return []
        except Exception as e:
            print(f"❌ Error processing PDF: {str(e)}")
            return []
        
    def _process_excel_file(self, file_path: str, filename: str) -> List[Dict[str, Any]]:
        """Process Excel/CSV files"""
        try:
            import pandas as pd
            
            # Read Excel/CSV
            if file_path.endswith('.xlsx'):
                df = pd.read_excel(file_path)
            else:
                df = pd.read_csv(file_path)
            
            processed_docs = []
            
            # Convert each row to structured text
            for index, row in df.iterrows():
                # Format row as readable text
                content_parts = []
                
                # Add parameter info if it's optimization data
                if 'Parameter Name' in df.columns:
                    content_parts.append(f"# {row.get('Parameter Name', 'Unknown Parameter')}")
                    content_parts.append(f"**Category**: {row.get('Category', 'N/A')}")
                    content_parts.append(f"**Function**: {row.get('Function', 'N/A')}")
                    content_parts.append(f"**Default Value**: {row.get('Default Value', 'N/A')}")
                    content_parts.append(f"**Recommended Value**: {row.get('Recommended Value', 'N/A')}")
                    content_parts.append(f"**Range**: {row.get('Range Value', 'N/A')}")
                    content_parts.append(f"**Description**: {row.get('Parameter Description', 'N/A')}")
                    content_parts.append(f"**Scenario**: {row.get('Scenario Implementation', 'N/A')}")
                    content_parts.append(f"**Impact**: {row.get('Impacted Service', 'N/A')}")
                else:
                    # Generic row processing
                    for col, value in row.items():
                        if pd.notna(value):
                            content_parts.append(f"**{col}**: {value}")
                
                content = "\n".join(content_parts)
                
                processed_docs.append({
                    'content': content,
                    'metadata': {
                        'title': filename,
                        'row_id': index + 1,
                        'total_rows': len(df),
                        'file_type': 'excel',
                        'source_path': file_path,
                        'parameter_name': row.get('Parameter Name', f'Row_{index+1}')
                    }
                })
            
            return processed_docs
            
        except ImportError:
            print("❌ pandas/openpyxl not installed. Install with: pip install pandas openpyxl")
            return []
        except Exception as e:
            print(f"❌ Error processing Excel: {str(e)}")
            return []
    
    def _split_text_into_chunks(self, text: str, max_chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """Split text into overlapping chunks"""
        
        # Clean text
        text = re.sub(r'\n+', '\n', text)  # Remove multiple newlines
        text = re.sub(r'\s+', ' ', text)   # Remove multiple spaces
        text = text.strip()
        
        if len(text) <= max_chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Find end position
            end = start + max_chunk_size
            
            if end >= len(text):
                # Last chunk
                chunks.append(text[start:])
                break
            
            # Try to find a good break point (sentence end)
            break_point = text.rfind('.', start, end)
            if break_point == -1:
                break_point = text.rfind(' ', start, end)
            
            if break_point == -1 or break_point <= start:
                break_point = end
            
            chunks.append(text[start:break_point].strip())
            
            # Move start with overlap
            start = max(break_point - overlap, start + 1)
        
        return [chunk for chunk in chunks if len(chunk.strip()) > 50]  # Filter very short chunks
    
    def create_sample_documents(self, docs_path: str = "./docs") -> None:
        """Create sample knowledge documents"""
        
        if not os.path.exists(docs_path):
            os.makedirs(docs_path)
        
        sample_docs = {
            "troubleshooting_internet.txt": """
# Troubleshooting Internet Telkomsel

## Masalah Umum Internet Lambat

### Langkah Troubleshooting:
1. Cek signal strength - minimal 2 bar
2. Restart handphone 
3. Cek kuota data tersisa
4. Ganti ke mode 4G jika di 3G
5. Pindah lokasi jika indoor

### Root Cause Analysis:
- Coverage area lemah
- Congestion network 
- Device compatibility issue
- Carrier aggregation not optimal

### Eskalasi:
Jika langkah diatas gagal, eskalasi ke Level 2 dengan informasi:
- MSISDN customer
- Lokasi detail dengan koordinat
- Hasil speed test
- Device type dan OS version
            """,
            
            "complaint_handling_sop.txt": """
# SOP Penanganan Keluhan Pelanggan

## Prioritas Keluhan

### High Priority:
- Total blackout (no signal)
- Service affecting massive customers
- VIP customer complaints
- Durasi: Max 4 jam resolution

### Medium Priority:  
- Slow internet performance
- Intermittent connection
- Voice quality issues
- Durasi: Max 24 jam resolution

### Low Priority:
- Minor service degradation
- Feature request
- General inquiry
- Durasi: Max 72 jam resolution

## Escalation Matrix:
Level 1 → Level 2: Complex technical issues
Level 2 → Level 3: Infrastructure problems  
Level 3 → Management: Policy decisions
            """,
            
            "technical_parameters.txt": """
# Parameter Teknis Telkomsel

## 4G LTE Parameters:

### RSRP (Reference Signal Received Power):
- Excellent: > -80 dBm
- Good: -80 to -90 dBm  
- Fair: -90 to -100 dBm
- Poor: < -100 dBm

### SINR (Signal to Interference plus Noise Ratio):
- Excellent: > 20 dB
- Good: 13-20 dB
- Fair: 0-13 dB
- Poor: < 0 dB

### Carrier Aggregation:
- Primary Component Carrier (PCC): Band 3 (1800MHz)
- Secondary Component Carrier (SCC): Band 40 (2300MHz)
- Expected throughput improvement: 30-50%

## Troubleshooting Actions:
- RSRP < -100 dBm: Check antenna alignment
- SINR < 0 dB: Identify interference source  
- CA not working: Verify device capability
            """
        }
        
        for filename, content in sample_docs.items():
            file_path = os.path.join(docs_path, filename)
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"📝 Created sample document: {filename}")
            else:
                print(f"📄 Document already exists: {filename}")
        
        print(f"✅ Sample documents ready in {docs_path}")