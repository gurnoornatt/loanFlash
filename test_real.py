from document_processor import process_document
import os
import shutil
from dotenv import load_dotenv
import sys
from pathlib import Path

def get_pdf_path():
    """Get the PDF path from user if not found in default location"""
    # First try the current directory
    current_dir_path = Path("09-04-24 Selling-Guide Highlighted (1).pdf")
    if current_dir_path.exists():
        try:
            with open(current_dir_path, 'rb') as f:
                f.read(1)
            return str(current_dir_path)
        except PermissionError:
            pass

    print("\n📋 PDF File Setup:")
    print("=================")
    print("On macOS, we need direct access to the PDF file.")
    print("Please copy your 'Selling-Guide' PDF to this directory:")
    print(f"👉 {os.getcwd()}")
    
    while True:
        print("\nOptions:")
        print("1. I've copied the file, continue")
        print("2. Show me the exact steps")
        print("3. Exit")
        
        choice = input("\nChoose an option (1-3): ")
        
        if choice == "1":
            # Look for PDF files in current directory
            pdfs = list(Path(".").glob("*.pdf"))
            if pdfs:
                if len(pdfs) == 1:
                    return str(pdfs[0])
                else:
                    print("\nMultiple PDFs found. Please choose one:")
                    for i, pdf in enumerate(pdfs, 1):
                        print(f"{i}. {pdf}")
                    while True:
                        try:
                            choice = int(input("\nEnter number: "))
                            if 1 <= choice <= len(pdfs):
                                return str(pdfs[choice - 1])
                        except ValueError:
                            pass
                        print("Invalid choice. Try again.")
            else:
                print("\n❌ No PDF files found in the current directory.")
                print("Please make sure you've copied the file here.")
        
        elif choice == "2":
            print("\n📝 Steps to copy the PDF:")
            print("1. Open Finder")
            print("2. Go to Downloads folder")
            print("3. Find '09-04-24 Selling-Guide Highlighted (1).pdf'")
            print("4. Copy the file (Command+C)")
            print(f"5. Go to this directory: {os.getcwd()}")
            print("6. Paste the file (Command+V)")
            print("7. Come back here and choose option 1")
            input("\nPress Enter to continue...")
        
        elif choice == "3":
            print("Exiting...")
            sys.exit(0)
        
        else:
            print("Invalid choice. Please try again.")

def test_with_real_data(pdf_path: str):
    """Test document processing with a real PDF"""
    # Load environment variables
    load_dotenv()
    
    try:
        print(f"\n📄 Processing: {Path(pdf_path).name}")
        print("⏳ This may take a while for large documents...")
        
        result = process_document(pdf_path)
        
        print("\n📊 Processing Results:")
        print("====================")
        if result['success']:
            print("✅ Successfully processed document!")
            print(f"📚 Processed {result.get('processed_chunks', 1)} chunks")
            print("\n📈 Extracted Data:")
            print("----------------")
            print(f"💰 Income: ${result['data']['income']:,.2f}")
            print(f"📊 Credit Score: {result['data']['credit_score']}")
            print(f"💳 Debt: ${result['data']['debt']:,.2f}")
            print(f"🏠 Property Value: ${result['data']['property_value']:,.2f}")
        else:
            print("❌ Error processing document:")
            print(f"Type: {result['error_type']}")
            print(f"Message: {result['error']}")
        
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

if __name__ == "__main__":
    print("\n🏦 Fannie Mae Document Processor")
    print("==============================")
    
    # Get PDF path with proper permissions
    pdf_path = get_pdf_path()
    
    if pdf_path:
        test_with_real_data(pdf_path) 