#!/usr/bin/env python3
"""
DOTS OCR Document Evaluation Script
Simple script to evaluate document extraction performance
"""

import os
import time
import glob
from dotenv import load_dotenv
from utils.document_evaluator import DocumentEvaluator

# Load environment variables
load_dotenv()

# Configuration
MODEL_API_URL = os.environ.get("MODEL_API_URL")
BASETEN_API_KEY = os.environ.get("BASETEN_API_KEY")
PDF_DPI = 200
MAX_PAGES_PER_PDF = 10
OUTPUT_DIR = "large_sample_outputs"


def main():
    """Main evaluation function"""
    print("DOTS OCR Document Evaluation")
    print("=" * 60)
    
    # Check for API key
    if not BASETEN_API_KEY:
        print("ERROR: BASETEN_API_KEY environment variable not set")
        print("Please set it in your .env file or environment")
        return
    
    # Initialize evaluator
    evaluator = DocumentEvaluator(
        api_url=MODEL_API_URL,
        api_key=BASETEN_API_KEY,
        output_dir=OUTPUT_DIR,
        pdf_dpi=PDF_DPI,
        max_pages=MAX_PAGES_PER_PDF
    )
    
    # Find PDF files
    pdf_pattern = "large_samples/*.pdf"
    pdf_files = glob.glob(pdf_pattern)
    
    if not pdf_files:
        print(f"No PDF files found matching pattern: {pdf_pattern}")
        return
    
    print(f"Found {len(pdf_files)} PDF files to process")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Settings: DPI={PDF_DPI}, Max pages={MAX_PAGES_PER_PDF}")
    print("=" * 60)
    
    # Process all PDFs
    total_start = time.time()
    
    for pdf_path in pdf_files:
        try:
            result = evaluator.process_document(pdf_path)
            evaluator.results.append(result)
            
            # Print summary for this document
            if "processing" in result:
                print(f"  ✓ Completed in {result['processing']['total_time_seconds']}s")
                print(f"    Success rate: {result['evaluation']['success_rate']}%")
                print(f"    Elements detected: {result['evaluation']['elements_detected']}")
            else:
                print(f"  ✗ Failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"  ✗ Error processing {pdf_path}: {e}")
            evaluator.results.append({
                "metadata": {"filename": os.path.basename(pdf_path)},
                "error": str(e)
            })
    
    total_time = time.time() - total_start
    
    # Generate final report
    evaluator.generate_report(total_time)
    
    print("\n" + "=" * 60)
    print("Evaluation complete!")


if __name__ == "__main__":
    main()