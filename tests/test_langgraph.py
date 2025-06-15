#!/usr/bin/env python3
"""
Test the LangGraph translation agent
"""
import os
from dotenv import load_dotenv
load_dotenv()

from app.core.langgraph_agent import run_translation_agent

def test_langgraph_agent():
    """Test the complete LangGraph translation workflow."""
    print("🧪 Testing LangGraph Translation Agent")
    print("=" * 50)
    
    test_text = "Hello, how are you today?"
    target_language = "Spanish"
    
    print(f"Input: '{test_text}'")
    print(f"Target Language: {target_language}")
    print("\nRunning LangGraph agent...")
    
    try:
        result = run_translation_agent(test_text, target_language)
        
        print("\n📊 Results:")
        print(f"Original Text: {result.get('original_text', 'N/A')}")
        print(f"Target Language: {result.get('target_language', 'N/A')}")
        print(f"Translated Text: {result.get('translated_text', 'N/A')}")
        print(f"Error Message: {result.get('error_message', 'None')}")
        print(f"Audio Generated: {'Yes' if result.get('audio_bytes') else 'No'}")
        
        if result.get('error_message'):
            print(f"\n❌ Translation failed: {result['error_message']}")
            return False
        elif result.get('translated_text'):
            print(f"\n✅ Translation successful!")
            return True
        else:
            print(f"\n⚠️ No translation received")
            return False
            
    except Exception as e:
        print(f"\n❌ LangGraph agent error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_langgraph_agent()
