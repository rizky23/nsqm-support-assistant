from typing import Dict, Any, List, Optional
from ..services.mbb_rag_service import MBBRAGService
from shared.utils.logger import log
import pandas as pd
import io
import json
import base64
import io

class MBBSearchTools:
    def __init__(self):
        self.rag_service = MBBRAGService()
    
    async def initialize(self):
        """Initialize MBB search tools"""
        return await self.rag_service.initialize()
    
    async def search_mbb_knowledge(self, query: str, category: str = None, max_results: int = 5) -> Dict[str, Any]:
        """Search MBB knowledge base"""
        try:
            return await self.rag_service.search_mbb_knowledge(query, category, max_results)
        except Exception as e:
            log.error(f"MBB knowledge search failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def search_4g_parameters(self, parameter_name: str = None, category: str = None, scenario: str = None) -> Dict[str, Any]:
        """Search 4G/LTE parameters from Huawei knowledge"""
        try:
            # Build search query based on inputs
            search_terms = []
            
            if parameter_name:
                search_terms.append(parameter_name)
            if category:
                search_terms.append(category)
            if scenario:
                search_terms.append(scenario)
            
            query = " ".join(search_terms) if search_terms else "4G LTE parameters"
            
            # Search with specific filters
            filters = {"domain": "mobile_broadband", "source": "huawei_4g_params"}
            if category:
                filters["category"] = category
            
            results = await self.rag_service.vector_store.search(
                query=query,
                n_results=10,
                filters=filters
            )
            
            return {
                "success": True,
                "query": query,
                "parameter_name": parameter_name,
                "category": category,
                "scenario": scenario,
                "results_found": len(results),
                "parameters": results
            }
            
        except Exception as e:
            log.error(f"4G parameter search failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_parameter_recommendations(self, parameter_name: str, current_value: str = None) -> Dict[str, Any]:
        """Get optimization recommendations for specific parameter"""
        try:
            # Search for parameter-specific information
            query = f"{parameter_name} optimization recommendation"
            
            results = await self.rag_service.search_mbb_knowledge(
                query=query,
                category="parameter_optimization",
                max_results=3
            )
            
            if not results.get("results"):
                return {
                    "success": False,
                    "message": f"No optimization data found for parameter: {parameter_name}",
                    "parameter": parameter_name
                }
            
            # Extract optimization info from results
            recommendations = []
            for result in results["results"]:
                metadata = result.get("metadata", {})
                
                if metadata.get("parameter_name") == parameter_name:
                    recommendations.append({
                        "recommended_value": metadata.get("recommended_value"),
                        "range_value": metadata.get("range_value"), 
                        "optimization_priority": metadata.get("optimization_priority"),
                        "description": metadata.get("parameter_description"),
                        "scenario": metadata.get("scenario"),
                        "impacted_service": metadata.get("impacted_service")
                    })
            
            return {
                "success": True,
                "parameter_name": parameter_name,
                "current_value": current_value,
                "recommendations": recommendations,
                "optimization_available": len(recommendations) > 0
            }
            
        except Exception as e:
            log.error(f"Parameter recommendation failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def search_by_scenario(self, scenario: str, service_type: str = None) -> Dict[str, Any]:
        """Search parameters by optimization scenario"""
        try:
            query = f"scenario {scenario}"
            if service_type:
                query += f" {service_type}"
            
            results = await self.rag_service.search_mbb_knowledge(
                query=query,
                max_results=15
            )
            
            # Group results by parameter category
            grouped_results = {}
            for result in results.get("results", []):
                metadata = result.get("metadata", {})
                category = metadata.get("category", "unknown")
                
                if category not in grouped_results:
                    grouped_results[category] = []
                
                grouped_results[category].append({
                    "parameter_name": metadata.get("parameter_name"),
                    "recommended_value": metadata.get("recommended_value"),
                    "optimization_priority": metadata.get("optimization_priority"),
                    "description": metadata.get("parameter_description")
                })
            
            return {
                "success": True,
                "scenario": scenario,
                "service_type": service_type,
                "categories_found": len(grouped_results),
                "parameters_by_category": grouped_results,
                "total_parameters": sum(len(params) for params in grouped_results.values())
            }
            
        except Exception as e:
            log.error(f"Scenario search failed: {e}")
            return {"success": False, "error": str(e)}

    async def process_excel_knowledge(self, file_path: str = None, file_content: str = None, filename: str = None) -> Dict[str, Any]:
        """Process and embed Excel knowledge file - supports both file path and base64 content"""
        try:
            # Determine input method
            if file_path:
                log.info(f"Processing Excel from file path: {file_path}")
                try:
                    df = pd.read_excel(file_path)
                    filename = filename or file_path.split('/')[-1]
                    log.info(f"Excel file loaded successfully from path, shape: {df.shape}")
                except Exception as excel_error:
                    log.error(f"Excel read error from path: {excel_error}")
                    return {
                        "success": False,
                        "error": f"Failed to read Excel file from path: {str(excel_error)}"
                    }
                    
            elif file_content:
                log.info(f"Processing Excel from base64 content")
                # Decode base64 string to bytes
                try:
                    file_bytes = base64.b64decode(file_content)
                    df = pd.read_excel(io.BytesIO(file_bytes))
                    log.info(f"Excel file loaded successfully from base64, shape: {df.shape}")
                except Exception as decode_error:
                    log.error(f"Base64/Excel decode error: {decode_error}")
                    return {
                        "success": False,
                        "error": f"Invalid base64 content or Excel format: {str(decode_error)}"
                    }
            else:
                return {
                    "success": False,
                    "error": "Either file_path or file_content must be provided"
                }
            
            # Validate expected columns for Huawei 4G params
            expected_columns = [
                'Category', 'Function', 'Sub Function', 'MO-PARA', 'MO Level',
                'Parameter Name', 'Default Value', 'Recommended Value', 'Range Value',
                'Optim Priority', 'Range Optim', 'Parameter Description', 'Scenario',
                'Implementation', 'Optimized parameter', 'Impacted Service', 'Additional'
            ]
            
            # Check which columns exist
            existing_columns = list(df.columns)
            missing_columns = set(expected_columns) - set(existing_columns)
            if missing_columns:
                log.warning(f"Missing columns in Excel: {missing_columns}")
                log.info(f"Available columns: {existing_columns}")
            
            # Process each row as a knowledge document
            documents = []
            metadatas = []
            ids = []
            processed_count = 0
            
            for index, row in df.iterrows():
                try:
                    # Handle missing columns gracefully
                    def safe_get(column_name, default=''):
                        return str(row.get(column_name, default)) if column_name in df.columns else default
                    
                    # Skip rows with empty parameter names
                    param_name = safe_get('Parameter Name', '').strip()
                    if not param_name or param_name.lower() in ['nan', 'none', '']:
                        continue
                    
                    # Create rich document text
                    doc_text = f"""
    Parameter: {param_name}
    Category: {safe_get('Category')} - {safe_get('Function')} - {safe_get('Sub Function')}
    MO Level: {safe_get('MO Level')}

    Description: {safe_get('Parameter Description')}

    Configuration:
    - Default Value: {safe_get('Default Value')}
    - Recommended Value: {safe_get('Recommended Value')}
    - Value Range: {safe_get('Range Value')}
    - Optimization Range: {safe_get('Range Optim')}

    Optimization:
    - Priority: {safe_get('Optim Priority')}
    - Scenario: {safe_get('Scenario')}
    - Implementation: {safe_get('Implementation')}
    - Impacted Service: {safe_get('Impacted Service')}

    Additional Notes: {safe_get('Additional')}
                    """.strip()
                    
                    # Create metadata
                    metadata = {
                        "source": "huawei_4g_params",
                        "filename": filename or "unknown.xlsx",
                        "domain": "mobile_broadband",
                        "category": str(safe_get('Category', '')).lower().replace(' ', '_'),
                        "function": safe_get('Function'),
                        "sub_function": safe_get('Sub Function'),
                        "parameter_name": param_name,
                        "default_value": safe_get('Default Value'),
                        "recommended_value": safe_get('Recommended Value'),
                        "range_value": safe_get('Range Value'),
                        "optimization_priority": safe_get('Optim Priority'),
                        "parameter_description": safe_get('Parameter Description'),
                        "scenario": safe_get('Scenario'),
                        "impacted_service": safe_get('Impacted Service'),
                        "mo_level": safe_get('MO Level'),
                        "mo_para": safe_get('MO-PARA'),
                        "row_index": index
                    }
                    
                    # Create unique ID
                    clean_param_name = param_name.replace(' ', '_').replace('/', '_').replace('-', '_')
                    doc_id = f"huawei_4g_{clean_param_name}_{index}"
                    
                    documents.append(doc_text)
                    metadatas.append(metadata)
                    ids.append(doc_id)
                    processed_count += 1
                    
                except Exception as row_error:
                    log.error(f"Error processing row {index}: {row_error}")
                    continue
            
            if not documents:
                return {
                    "success": False,
                    "error": "No valid documents could be processed from Excel file",
                    "total_rows": len(df),
                    "processed_rows": 0
                }
            
            # Add documents to vector store
            log.info(f"Adding {len(documents)} documents to vector store...")
            success = await self.rag_service.vector_store.add_documents(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            if success:
                log.info(f"Successfully processed {len(documents)} parameters from {filename}")
                
                # Extract summary statistics
                categories = list(set(str(meta.get('category', '')) for meta in metadatas if meta.get('category')))
                functions = list(set(str(meta.get('function', '')) for meta in metadatas if meta.get('function')))
                priorities = list(set(str(meta.get('optimization_priority', '')) for meta in metadatas if meta.get('optimization_priority')))
                
                return {
                    "success": True,
                    "filename": filename or "unknown.xlsx",
                    "input_method": "file_path" if file_path else "base64_content",
                    "total_rows": len(df),
                    "parameters_processed": len(documents),
                    "skipped_rows": len(df) - len(documents),
                    "categories": sorted(categories)[:15],  
                    "functions": sorted(functions)[:15],    
                    "optimization_priorities": sorted(priorities),
                    "sample_parameters": [meta.get('parameter_name') for meta in metadatas[:5]],
                    "message": f"Successfully embedded {len(documents)} 4G parameters from {filename}"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to add documents to vector store",
                    "processed_documents": len(documents)
                }
            
        except Exception as e:
            log.error(f"Excel processing failed: {e}")
            return {
                "success": False,
                "error": f"Excel processing error: {str(e)}",
                "input_method": "file_path" if file_path else "base64_content"
            }