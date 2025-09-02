import os
import json
import time
import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from openai import OpenAI
from io import BytesIO
import fitz  # PyMuPDF


class DocumentEvaluator:
    """Document evaluation class for DOTS OCR engine"""
    
    def __init__(self, api_url: str, api_key: str, output_dir: str = "sample_outputs", 
                 pdf_dpi: int = 200, max_pages: int = 10):
        """
        Initialize the DocumentEvaluator
        
        Args:
            api_url: The API URL for the model
            api_key: The API key for authentication
            output_dir: Directory to save output files
            pdf_dpi: DPI for PDF to image conversion
            max_pages: Maximum pages to process per PDF
        """
        self.client = OpenAI(
            base_url=api_url,
            api_key=api_key,
        )
        self.results = []
        self.output_dir = output_dir
        self.pdf_dpi = pdf_dpi
        self.max_pages = max_pages
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
    def get_file_metadata(self, file_path: str) -> Dict:
        """Extract file metadata"""
        stat = os.stat(file_path)
        return {
            "filename": os.path.basename(file_path),
            "path": file_path,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "mimetype": "application/pdf",
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
        }
    
    def pdf_to_images(self, pdf_path: str) -> List[str]:
        """
        Convert PDF pages to base64 encoded images using PyMuPDF
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of base64 encoded images
        """
        try:
            pdf_document = fitz.open(pdf_path)
            
            # Limit pages if specified
            num_pages = len(pdf_document)
            if self.max_pages and self.max_pages < num_pages:
                num_pages = self.max_pages
            
            base64_images = []
            for page_num in range(num_pages):
                page = pdf_document[page_num]
                # Convert to image with specific DPI
                mat = fitz.Matrix(self.pdf_dpi / 72.0, self.pdf_dpi / 72.0)
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("jpeg")
                img_b64 = base64.b64encode(img_data).decode('utf-8')
                base64_images.append(img_b64)
            
            pdf_document.close()
            return base64_images
            
        except Exception as e:
            print(f"Error converting PDF: {e}")
            return []
    
    def process_document_page(self, image_b64: str, page_num: int) -> Dict:
        """Process a single document page"""
        try:
            response = self.client.chat.completions.create(
                model="DotsOCR",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract all layout information and text content from this document. Return as JSON with layout elements, text, tables, and formulas."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            }
                        }
                    ]
                }],
                max_tokens=24000,
                temperature=0.1,
                stream=False
            )
            
            content = response.choices[0].message.content
            
            # Try to parse as JSON, fallback to raw text
            try:
                return json.loads(content)
            except:
                return {"raw_text": content}
                
        except Exception as e:
            return {"error": str(e), "page": page_num}
    
    def evaluate_extraction(self, extraction_results: List[Dict]) -> Dict:
        """Evaluate extraction quality metrics"""
        if not extraction_results:
            return {
                "total_pages": 0,
                "successful_pages": 0,
                "success_rate": 0,
                "elements_detected": {
                    "text_blocks": 0,
                    "tables": 0,
                    "formulas": 0,
                    "layout_elements": 0
                }
            }
            
        total_pages = len(extraction_results)
        successful_pages = sum(1 for r in extraction_results if "error" not in r)
        
        # Count detected elements
        total_text_blocks = 0
        total_tables = 0
        total_formulas = 0
        total_layouts = 0
        
        for result in extraction_results:
            if "error" not in result and isinstance(result, dict):
                # Handle different response formats
                if "text" in result:
                    if isinstance(result["text"], list):
                        total_text_blocks += len(result["text"])
                    elif isinstance(result["text"], str):
                        total_text_blocks += 1
                        
                if "tables" in result and isinstance(result["tables"], list):
                    total_tables += len(result["tables"])
                    
                if "formulas" in result and isinstance(result["formulas"], list):
                    total_formulas += len(result["formulas"])
                    
                if "layout" in result and isinstance(result["layout"], list):
                    total_layouts += len(result["layout"])
        
        return {
            "total_pages": total_pages,
            "successful_pages": successful_pages,
            "success_rate": round(successful_pages / total_pages * 100, 2) if total_pages > 0 else 0,
            "elements_detected": {
                "text_blocks": total_text_blocks,
                "tables": total_tables,
                "formulas": total_formulas,
                "layout_elements": total_layouts
            }
        }
    
    def save_document_output(self, pdf_name: str, result: Dict):
        """Save extraction results for a document"""
        base_name = Path(pdf_name).stem
        output_file = os.path.join(self.output_dir, f"{base_name}_extraction.json")
        
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"    Output saved to: {output_file}")
    
    def process_document(self, pdf_path: str) -> Dict:
        """Process a complete PDF document"""
        print(f"\nProcessing: {os.path.basename(pdf_path)}")
        
        # Get metadata
        metadata = self.get_file_metadata(pdf_path)
        
        # Start timing
        start_time = time.time()
        
        # Convert PDF to images
        print(f"  Converting PDF to images (DPI={self.pdf_dpi})...")
        images = self.pdf_to_images(pdf_path)
        
        if not images:
            result = {
                "metadata": metadata,
                "error": "Failed to convert PDF to images",
                "processing": {
                    "total_time_seconds": round(time.time() - start_time, 2),
                    "avg_time_per_page": 0,
                    "pages_processed": 0,
                    "dpi": self.pdf_dpi
                },
                "evaluation": self.evaluate_extraction([])
            }
            return result
        
        # Process each page
        extraction_results = []
        for i, img_b64 in enumerate(images, 1):
            print(f"  Processing page {i}/{len(images)}...")
            page_start = time.time()
            result = self.process_document_page(img_b64, i)
            page_time = time.time() - page_start
            result["processing_time"] = round(page_time, 2)
            extraction_results.append(result)
        
        # Calculate total processing time
        total_time = time.time() - start_time
        
        # Evaluate extraction quality
        evaluation = self.evaluate_extraction(extraction_results)
        
        result = {
            "metadata": metadata,
            "processing": {
                "total_time_seconds": round(total_time, 2),
                "avg_time_per_page": round(total_time / len(images), 2) if images else 0,
                "pages_processed": len(images),
                "dpi": self.pdf_dpi
            },
            "evaluation": evaluation,
            "page_results": extraction_results  # Include for detailed analysis
        }
        
        # Save individual document output
        self.save_document_output(metadata["filename"], result)
        
        return result
    
    def generate_report(self, total_time: float):
        """Generate evaluation report"""
        print("\n" + "=" * 60)
        print("EVALUATION REPORT")
        print("=" * 60)
        
        # Filter successful results
        successful_results = [r for r in self.results if "processing" in r]
        
        if not successful_results:
            print("No documents were successfully processed.")
            return
        
        # Overall statistics
        total_docs = len(self.results)
        successful_docs = len(successful_results)
        total_pages = sum(r['processing']['pages_processed'] for r in successful_results)
        avg_success_rate = sum(r['evaluation']['success_rate'] for r in successful_results) / successful_docs if successful_docs > 0 else 0
        
        print(f"\nOverall Statistics:")
        print(f"  Total documents: {total_docs}")
        print(f"  Successfully processed: {successful_docs}")
        print(f"  Total pages processed: {total_pages}")
        print(f"  Total processing time: {round(total_time, 2)}s")
        print(f"  Average time per document: {round(total_time / successful_docs, 2)}s" if successful_docs > 0 else "N/A")
        print(f"  Average success rate: {round(avg_success_rate, 2)}%")
        
        if successful_results:
            print(f"\nPer-Document Results:")
            print(f"{'Document':<40} {'Size (MB)':<10} {'Pages':<8} {'Time (s)':<10} {'Success %':<10}")
            print("-" * 80)
            
            for result in successful_results:
                doc_name = result['metadata']['filename'][:39]
                size = result['metadata']['size_mb']
                pages = result['processing']['pages_processed']
                time_taken = result['processing']['total_time_seconds']
                success = result['evaluation']['success_rate']
                
                print(f"{doc_name:<40} {size:<10.2f} {pages:<8} {time_taken:<10.2f} {success:<10.2f}")
        
        # Save detailed report to output directory
        report_file = os.path.join(self.output_dir, f"evaluation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(report_file, 'w') as f:
            json.dump({
                "summary": {
                    "total_documents": total_docs,
                    "successful_documents": successful_docs,
                    "total_pages": total_pages,
                    "total_time_seconds": round(total_time, 2),
                    "average_success_rate": round(avg_success_rate, 2),
                    "timestamp": datetime.now().isoformat()
                },
                "documents": self.results
            }, f, indent=2)
        
        print(f"\nDetailed report saved to: {report_file}")
        print(f"Individual document outputs saved to: {self.output_dir}/")