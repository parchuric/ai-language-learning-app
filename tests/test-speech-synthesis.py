#!/usr/bin/env python3
"""
Test Azure Speech Synthesis functionality
This script tests if the speech synthesis is working correctly with the current configuration.
"""

import os
from dotenv import load_dotenv
load_dotenv()

from app.core.azure_clients import get_speech_config, get_speech_synthesizer
from app.core.constants import SUPPORTED_LANGUAGES_VOICES
from azure.cognitiveservices.speech import SpeechSynthesisOutputFormat, ResultReason, CancellationDetails, CancellationReason

def test_speech_synthesis():
    """Test speech synthesis functionality"""
    print("🔊 Testing Azure Speech Synthesis...")
    print(f"AZURE_SPEECH_KEY: {'Set' if os.getenv('AZURE_SPEECH_KEY') else 'NOT SET'}")
    print(f"AZURE_SPEECH_REGION: {os.getenv('AZURE_SPEECH_REGION')}")
    
    try:
        # Test speech config
        speech_config = get_speech_config()
        if not speech_config:
            print("❌ Failed to get speech config")
            return False
        
        print("✅ Speech config initialized successfully")
        
        # Test Spanish synthesis
        target_language = "Spanish"
        test_text = "¿Cómo estás?"
        
        print(f"🎯 Testing synthesis for '{test_text}' in {target_language}")
        
        if target_language not in SUPPORTED_LANGUAGES_VOICES:
            print(f"❌ Language '{target_language}' not supported")
            return False
            
        # Configure voice for Spanish
        speech_config.speech_synthesis_voice_name = SUPPORTED_LANGUAGES_VOICES[target_language]["voice"]
        speech_config.set_speech_synthesis_output_format(SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3)
        
        print(f"🎤 Using voice: {speech_config.speech_synthesis_voice_name}")
        
        # Create synthesizer
        speech_synthesizer = get_speech_synthesizer(speech_config_val=speech_config)
        if not speech_synthesizer:
            print("❌ Failed to create speech synthesizer")
            return False
            
        print("✅ Speech synthesizer created successfully")
        
        # Perform synthesis
        print("🔄 Performing speech synthesis...")
        tts_result = speech_synthesizer.speak_text_async(test_text).get()
        
        if tts_result.reason == ResultReason.SynthesizingAudioCompleted:
            print("✅ Speech synthesis SUCCESSFUL!")
            print(f"📊 Audio data length: {len(tts_result.audio_data)} bytes")
            
            # Save audio file for testing
            with open("test_audio.mp3", "wb") as f:
                f.write(tts_result.audio_data)
            print("💾 Audio saved to test_audio.mp3")
            return True
            
        elif tts_result.reason == ResultReason.Canceled:
            cancellation_details: CancellationDetails = tts_result.cancellation_details
            error_details = f"Speech synthesis canceled: {cancellation_details.reason}"
            if cancellation_details.reason == CancellationReason.Error:
                error_details += f" - Error details: {cancellation_details.error_details}"
            print(f"❌ Speech synthesis failed: {error_details}")
            return False
        else:
            print(f"❌ Speech synthesis failed with unexpected reason: {tts_result.reason}")
            return False
            
    except Exception as e:
        print(f"❌ Exception during speech synthesis test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Azure Speech Synthesis Test")
    print("=" * 50)
    
    success = test_speech_synthesis()
    
    print("=" * 50)
    if success:
        print("🎉 Speech synthesis test PASSED!")
    else:
        print("💥 Speech synthesis test FAILED!")
        print("\n🔧 Troubleshooting tips:")
        print("1. Check AZURE_SPEECH_KEY environment variable")
        print("2. Check AZURE_SPEECH_REGION environment variable")
        print("3. Verify Azure Speech Service is running")
        print("4. Check network connectivity to Azure")
        print("5. Verify speech service key permissions")
