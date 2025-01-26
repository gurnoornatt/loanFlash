from nlp_engine import MortgageNLPEngine
from dotenv import load_dotenv
import json

def test_with_sample_queries():
    """Test the NLP engine with real queries"""
    # Load environment variables
    load_dotenv()
    
    # Initialize engine
    try:
        engine = MortgageNLPEngine()
        print("✅ Successfully initialized NLP engine")
    except Exception as e:
        print(f"❌ Failed to initialize NLP engine: {str(e)}")
        return
    
    # Sample queries to test
    test_queries = [
        "What is the maximum LTV for a single-family home in California?",
        "What's the minimum credit score required for a conventional loan?",
        "What is the maximum DTI ratio allowed for FHA loans?",
        "Can you explain the LTV requirements for investment properties?",
        "What are the income requirements for a jumbo loan?"
    ]
    
    print("\n🔍 Testing Sample Queries")
    print("=======================")
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        try:
            result = engine.process_query(query)
            
            if result['success']:
                print("✅ Response:")
                print(f"Intent: {result['intent']}")
                print(f"Entities: {json.dumps(result['entities'], indent=2)}")
                print(f"Answer: {result['answer']}")
                print(f"Confidence: {result['metadata'].get('confidence_score', 'N/A')}")
            else:
                print(f"❌ Error: {result['error']}")
        
        except Exception as e:
            print(f"❌ Error processing query: {str(e)}")

def test_with_custom_query():
    """Test the NLP engine with a custom query from user input"""
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
        print("\n🤔 Enter your mortgage-related question (or 'quit' to exit):")
        query = input("> ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            break
        
        if not query:
            continue
        
        try:
            result = engine.process_query(query)
            
            print("\n📊 Results:")
            print("=========")
            
            if result['success']:
                print(f"🎯 Intent: {result['intent']}")
                print(f"🔍 Entities: {json.dumps(result['entities'], indent=2)}")
                print(f"\n💡 Answer: {result['answer']}")
                print(f"\n📈 Confidence: {result['metadata'].get('confidence_score', 'N/A')}")
            else:
                print(f"❌ Error: {result['error']}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    print("\n🏦 Mortgage Guidelines NLP Test")
    print("============================")
    
    while True:
        print("\nOptions:")
        print("1. Run sample queries")
        print("2. Enter custom queries")
        print("3. Exit")
        
        choice = input("\nChoose an option (1-3): ")
        
        if choice == "1":
            test_with_sample_queries()
        elif choice == "2":
            test_with_custom_query()
        elif choice == "3":
            break
        else:
            print("Invalid choice. Please try again.") 