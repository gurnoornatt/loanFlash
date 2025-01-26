import os
import json
import requests
from typing import Dict, Any

def download_json_guidelines(url: str, output_file: str) -> bool:
    """Download JSON guidelines from Google Drive"""
    try:
        # Extract file ID from Google Drive URL
        file_id = url.split('/d/')[1].split('/')[0]
        download_url = f"https://drive.google.com/uc?id={file_id}"
        
        response = requests.get(download_url)
        response.raise_for_status()
        
        with open(output_file, 'w') as f:
            json.dump(response.json(), f, indent=2)
        
        print(f"Successfully downloaded guidelines to {output_file}")
        return True
        
    except Exception as e:
        print(f"Error downloading guidelines: {str(e)}")
        return False

def process_guidelines():
    """Download and process all guideline files"""
    # URLs for guidelines
    guidelines_urls = {
        'fannie_mae': 'https://drive.google.com/file/d/1ulTYhtQb3X0Jey4PD8tJ4rj3x1uipBxd/view',
        'freddie_mac': 'https://drive.google.com/file/d/11aZmYoA4zjMVoBpFSauvNiqjOhtBO2-V/view'
    }
    
    # Create guidelines directory if it doesn't exist
    os.makedirs('guidelines', exist_ok=True)
    
    # Download each guideline file
    for name, url in guidelines_urls.items():
        output_file = f"guidelines/{name}_guidelines.json"
        if download_json_guidelines(url, output_file):
            print(f"Successfully processed {name} guidelines")
        else:
            print(f"Failed to process {name} guidelines")

if __name__ == '__main__':
    process_guidelines() 