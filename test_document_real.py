from nlp_engine import MortgageNLPEngine
from dotenv import load_dotenv
import os
import json
from typing import Dict, Any, List

# Document type to URL mapping
SAMPLE_DOCS = {
    'W2': 'https://www.irs.gov/pub/irs-pdf/fw2.pdf',
    'Form_1099': 'https://www.irs.gov/pub/irs-pdf/f1099msc.pdf',
    'Bank_Statement': 'https://www.scribd.com/document/448392605/Bank-Statement-1',
    'PayStub': 'https://www.pdfrun.com/form/pay-stub',
    'Tax_Return': 'https://www.irs.gov/pub/irs-pdf/f1040.pdf'
}

def download_sample_doc(doc_type: str, output_dir: str = 'sample_docs') -> str:
    """Download a sample document for testing"""
    import requests
    
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Get document URL
        url = SAMPLE_DOCS.get(doc_type)
        if not url:
            raise ValueError(f"No sample URL found for document type: {doc_type}")
        
        # Download document
        response = requests.get(url)
        response.raise_for_status()
        
        # Save document
        output_path = os.path.join(output_dir, f"{doc_type.lower()}_sample.pdf")
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ Downloaded {doc_type} sample to {output_path}")
        return output_path
        
    except Exception as e:
        print(f"❌ Error downloading {doc_type} sample: {str(e)}")
        return None

def test_with_sample_docs():
    """Test document processing with sample documents"""
    # Load environment variables
    load_dotenv()
    
    # Initialize engine
    try:
        engine = MortgageNLPEngine()
        print("✅ Successfully initialized NLP engine")
    except Exception as e:
        print(f"❌ Failed to initialize NLP engine: {str(e)}")
        return
    
    # Sample applicant data
    applicants = [
        {
            'applicantId': 1,
            'fullName': 'John Doe'
        }
    ]
    
    print("\n🔍 Testing Document Processing")
    print("===========================")
    
    # Process each document type
    for doc_type in SAMPLE_DOCS:
        print(f"\n📄 Testing {doc_type}:")
        
        # Download sample document
        file_path = download_sample_doc(doc_type)
        if not file_path:
            continue
        
        try:
            # Process document
            result = engine.process_document(
                file_path,
                borrower_stated_type=doc_type,
                applicants=applicants
            )
            
            if result['success']:
                print("✅ Document processed successfully")
                print("\n📊 Results:")
                print("=========")
                print(f"🎯 Document Type: {result['classification']['documentType']}")
                print(f"📈 Confidence: {result['extraction']['confidence']}")
                print("\n💡 Extracted Data:")
                print(json.dumps(result['extraction']['data'], indent=2))
            else:
                print(f"❌ Error: {result['error']}")
            
        except Exception as e:
            print(f"❌ Error processing document: {str(e)}")
        
        print("-" * 80)

def test_with_custom_doc():
    """Test document processing with a custom document"""
    # Load environment variables
    load_dotenv()
    
    # Initialize engine
    try:
        engine = MortgageNLPEngine()
        print("✅ Successfully initialized NLP engine")
    except Exception as e:
        print(f"❌ Failed to initialize NLP engine: {str(e)}")
        return
    
    while True:
        print("\n🤔 Enter the path to your document (or 'quit' to exit):")
        file_path = input("> ").strip()
        
        if file_path.lower() in ['quit', 'exit', 'q']:
            break
        
        if not os.path.exists(file_path):
            print("❌ File not found")
            continue
        
        print("\n📄 Document Type (optional, press Enter to skip):")
        doc_type = input("> ").strip() or None
        
        print("\n👤 Applicant Name (optional, press Enter to skip):")
        applicant_name = input("> ").strip()
        
        applicants = None
        if applicant_name:
            applicants = [{'applicantId': 1, 'fullName': applicant_name}]
        
        try:
            # Process document
            result = engine.process_document(
                file_path,
                borrower_stated_type=doc_type,
                applicants=applicants
            )
            
            print("\n📊 Results:")
            print("=========")
            
            if result['success']:
                print(f"🎯 Document Type: {result['classification']['documentType']}")
                print(f"📈 Confidence: {result['extraction']['confidence']}")
                print("\n💡 Extracted Data:")
                print(json.dumps(result['extraction']['data'], indent=2))
            else:
                print(f"❌ Error: {result['error']}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        print("-" * 80)

if __name__ == '__main__':
    print("\n📄 Document Processing Test")
    print("=========================")
    
    while True:
        print("\nOptions:")
        print("1. Test with sample documents")
        print("2. Test with custom document")
        print("3. Exit")
        
        choice = input("\nChoose an option (1-3): ")
        
        if choice == '1':
            test_with_sample_docs()
        elif choice == '2':
            test_with_custom_doc()
        elif choice == '3':
            break
        else:
            print("Invalid choice. Please try again.") 