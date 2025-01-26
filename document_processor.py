import requests
import uuid
import os
import logging
import PyPDF2
import tempfile
from tqdm import tqdm
from dotenv import load_dotenv
from supabase import create_client
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def split_pdf(pdf_path: str, chunk_size: int = 50) -> List[str]:
    """
    Split a large PDF into smaller chunks for processing
    
    Args:
        pdf_path: Path to the PDF file
        chunk_size: Number of pages per chunk
        
    Returns:
        List of temporary PDF file paths
    """
    temp_files = []
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            
            for start in range(0, total_pages, chunk_size):
                end = min(start + chunk_size, total_pages)
                
                # Create a temporary file for this chunk
                temp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
                pdf_writer = PyPDF2.PdfWriter()
                
                # Add pages to this chunk
                for page_num in range(start, end):
                    pdf_writer.add_page(pdf_reader.pages[page_num])
                
                # Save the chunk
                with open(temp_pdf.name, 'wb') as chunk_file:
                    pdf_writer.write(chunk_file)
                
                temp_files.append(temp_pdf.name)
                
        return temp_files
    except Exception as e:
        # Clean up temp files if something goes wrong
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
            except:
                pass
        raise e

def classify_document(file_data: str, addy_api_key: str) -> str:
    """Classify the document using Addy AI's classification API"""
    headers = {
        'api-key': addy_api_key,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    payload = {
        "fileData": [file_data],
        "contentType": "application/pdf",
        "modelDetail": "high"
    }
    
    response = requests.post(
        'https://addy-ai-external-api-dev.firebaseapp.com/document/classify',
        headers=headers,
        json=payload,
        timeout=300
    )
    
    response.raise_for_status()
    result = response.json()
    
    if not result.get('success'):
        raise ValueError(f"Classification failed: {result.get('reason', 'Unknown error')}")
    
    classifications = result.get('classifications', [])
    if not classifications:
        raise ValueError("No document classification found")
    
    return classifications[0].get('documentType', 'w2')  # Default to w2 if type not found

def process_chunk(chunk_path: str, addy_api_key: str) -> Dict:
    """Process a single PDF chunk"""
    with open(chunk_path, 'rb') as file:
        # Read file as base64
        file_content = file.read()
        file_data = base64.b64encode(file_content).decode('utf-8')
        
        # First classify the document
        try:
            doc_type = classify_document(file_data, addy_api_key)
            logger.info(f"Document classified as: {doc_type}")
        except Exception as e:
            logger.warning(f"Classification failed, using default type: {str(e)}")
            doc_type = "w2"  # Default to W2 as it's a supported type
        
        # Prepare request payload
        payload = {
            "documentType": doc_type,
            "contentType": "application/pdf",
            "fileData": file_data,
            "classification": {
                "documentType": doc_type,
                "levelOfConfidence": 1.0
            }
        }
        
        headers = {
            'api-key': addy_api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Make API request
        response = requests.post(
            'https://addy-ai-external-api-dev.firebaseapp.com/document/extract',
            headers=headers,
            json=payload,
            timeout=300
        )
        
        try:
            response.raise_for_status()
            result = response.json()
            
            # Check if extraction was successful
            if not result.get('success'):
                raise ValueError(f"API returned error: {result.get('errorMessage', 'Unknown error')}")
                
            # Extract document data
            document_data = result.get('document', {})
            
            # Map different document types to our required fields
            extracted = {
                'income': 0.0,
                'credit_score': 0,
                'debt': 0.0,
                'property_value': 0.0
            }
            
            if doc_type.lower() in ['w2', 'w-2']:
                extracted['income'] = float(document_data.get('wages', 0))
            elif doc_type.lower() in ['paystub', 'paystubs']:
                extracted['income'] = float(document_data.get('grossPay', 0)) * 12  # Annualize monthly income
            
            return extracted
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"API Response: {response.text}")
            if response.status_code == 404:
                raise ConnectionError("Invalid API endpoint. Please check the API documentation.")
            elif response.status_code == 400:
                raise ValueError(f"Bad request: {response.text}")
            elif response.status_code == 401:
                raise ConnectionError("Invalid API key. Please check your credentials.")
            else:
                raise ConnectionError(f"API Error ({response.status_code}): {response.text}")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Request failed: {str(e)}")
        except ValueError as e:
            raise ValueError(f"Failed to parse API response: {str(e)}")

def merge_results(results: List[Dict]) -> Dict:
    """Merge results from multiple chunks"""
    merged = {
        'income': 0.0,
        'credit_score': 0,
        'debt': 0.0,
        'property_value': 0.0
    }
    
    for result in results:
        merged['income'] = max(merged['income'], float(result.get('income', 0)))
        merged['credit_score'] = max(merged['credit_score'], int(result.get('credit_score', 0)))
        merged['debt'] = max(merged['debt'], float(result.get('debt', 0)))
        merged['property_value'] = max(merged['property_value'], float(result.get('property_value', 0)))
    
    return merged

def process_document(pdf_file_path: str) -> Dict[str, Any]:
    """
    Process a large PDF document through Addy AI's Document Extraction API and store results in Supabase.
    Handles large documents by splitting them into chunks and processing in parallel.
    
    Args:
        pdf_file_path: Path to the PDF file
    
    Returns:
        Dict containing the extracted and stored data or error information
    """
    temp_files = []
    try:
        # Get environment variables
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        addy_api_key = os.getenv('ADDY_API_KEY')
        
        # Validate environment variables
        if not all([supabase_url, supabase_key, addy_api_key]):
            missing_vars = [var for var, val in {
                'SUPABASE_URL': supabase_url,
                'SUPABASE_KEY': supabase_key,
                'ADDY_API_KEY': addy_api_key
            }.items() if not val]
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        # Verify PDF file exists
        if not os.path.exists(pdf_file_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_file_path}")
        
        # Get file size
        file_size = os.path.getsize(pdf_file_path) / (1024 * 1024)  # Size in MB
        logger.info(f"Processing PDF file of size: {file_size:.2f} MB")
        
        # Split PDF into chunks if it's large
        if file_size > 10:  # If file is larger than 10MB
            logger.info("Large PDF detected, splitting into chunks...")
            temp_files = split_pdf(pdf_file_path)
            logger.info(f"Split into {len(temp_files)} chunks")
        else:
            temp_files = [pdf_file_path]
        
        # Process chunks in parallel
        chunk_results = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(process_chunk, chunk_path, addy_api_key)
                for chunk_path in temp_files
            ]
            
            # Show progress bar
            with tqdm(total=len(futures), desc="Processing chunks") as pbar:
                for future in as_completed(futures):
                    chunk_results.append(future.result())
                    pbar.update(1)
        
        # Merge results from all chunks
        extracted_data = merge_results(chunk_results)
        logger.info("Successfully merged results from all chunks")
        
        # Initialize Supabase client
        try:
            logger.info("Connecting to Supabase")
            supabase = create_client(supabase_url, supabase_key)
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Supabase: {str(e)}")
        
        # Prepare data for insertion
        insert_data = {
            'id': str(uuid.uuid4()),
            **extracted_data
        }
        
        # Insert data into Supabase
        try:
            logger.info("Inserting data into Supabase")
            result = supabase.table('borrowers').insert(insert_data).execute()
            logger.info("Successfully inserted data")
        except Exception as e:
            raise ConnectionError(f"Failed to insert data into Supabase: {str(e)}")
        
        return {
            'success': True,
            'data': insert_data,
            'supabase_result': result,
            'processed_chunks': len(temp_files)
        }
            
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }
    
    finally:
        # Clean up temporary files
        if temp_files and temp_files[0] != pdf_file_path:  # Only clean up if we created temp files
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                    logger.debug(f"Cleaned up temporary file: {temp_file}")
                except:
                    pass 