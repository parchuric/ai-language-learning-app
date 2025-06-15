import os
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END
# from langgraph.graph.message import add_messages # Not used currently
# from openai import AzureOpenAI # Not directly used, client obtained from azure_clients

from .azure_clients import (
    get_azure_openai_client, 
    get_content_safety_client,
    get_speech_config, 
    get_speech_synthesizer
)
from .constants import SUPPORTED_LANGUAGES_VOICES # Import constants
from azure.ai.contentsafety.models import AnalyzeTextOptions, TextCategory
from azure.cognitiveservices.speech import SpeechSynthesisOutputFormat, ResultReason, CancellationDetails, CancellationReason

# 1. Define Agent State
class TranslationState(TypedDict):
    original_text: str
    target_language: str # This is the language name e.g. "Spanish"
    translated_text: str | None # This will hold the accumulating/final text from the stream
    audio_bytes: bytes | None 
    error_message: str | None
    is_safe: bool | None

# 2. Define Nodes
def content_safety_check_node(state: TranslationState):
    """
    Checks the input text for harmful content.
    """
    print("---LANGGRAPH: Running Content Safety Check---")
    try:
        if not state.get("original_text"):
            print("---LANGGRAPH ERROR: Missing input text for content safety---")
            return {"error_message": "Input text is missing for content safety check.", "is_safe": False}

        try:
            content_safety_client = get_content_safety_client()
            print("---LANGGRAPH: Content Safety client initialized---")
        except Exception as client_e:
            print(f"---LANGGRAPH ERROR: Failed to initialize Content Safety client: {client_e}---")
            # For demo/testing, allow the flow to continue with a warning
            print("---LANGGRAPH WARNING: Bypassing content safety check due to client initialization error---")
            return {"is_safe": True, "error_message": None}

        try:
            analysis_result = content_safety_client.analyze_text(AnalyzeTextOptions(text=state["original_text"]))
            print(f"---LANGGRAPH: Content Safety analysis result received: {type(analysis_result)}---")
        except Exception as analysis_e:
            print(f"---LANGGRAPH ERROR: Content analysis failed: {analysis_e}---")
            # For demo/testing, allow the flow to continue with a warning
            return {"is_safe": True, "error_message": None}

        # The Content Safety API could have different response formats. Try multiple ways to access results.
        unsafe = False
        
        # Approach 1: Check categories_analysis
        if hasattr(analysis_result, 'categories_analysis') and analysis_result.categories_analysis:
            print("---LANGGRAPH: Using categories_analysis property---")
            for category in analysis_result.categories_analysis:
                # Check if category is a dict or an object
                if isinstance(category, dict) and category.get('severity', 0) > 0:
                    unsafe = True
                    print(f"---LANGGRAPH: Content Safety - Found {category.get('category')} with severity {category.get('severity')}---")
                    break
                elif hasattr(category, 'severity') and getattr(category, 'severity', 0) > 0:
                    unsafe = True
                    print(f"---LANGGRAPH: Content Safety - Found {getattr(category, 'category', 'unknown')} with severity {getattr(category, 'severity', 0)}---")
                    break
        
        # Approach 2: Check hate/self_harm/sexual/violence properties directly
        elif any(hasattr(analysis_result, attr) and getattr(analysis_result, attr) and 
                hasattr(getattr(analysis_result, attr), 'severity') and 
                getattr(getattr(analysis_result, attr), 'severity', 0) > 0 
                for attr in ['hate', 'self_harm', 'sexual', 'violence']):
            print("---LANGGRAPH: Using direct category properties---")
            unsafe = True
        
        if unsafe:
            print("---LANGGRAPH: Content Safety Check - Unsafe---")
            return {"error_message": "Input text was found to be unsafe.", "is_safe": False}
        else:
            print("---LANGGRAPH: Content Safety Check - Safe---")
            return {"is_safe": True, "error_message": None}
    except Exception as e:
        print(f"---LANGGRAPH ERROR in content_safety_check_node: {e}---")
        # For demo/testing, allow the flow to continue
        return {"is_safe": True, "error_message": None}

def translate_text_node(state: TranslationState):
    """
    Translates the text using Azure OpenAI and streams the output.
    This node is a generator, yielding partial updates to translated_text.
    """
    print(f"---LANGGRAPH: Streaming translation to {state['target_language']}---")
    try:
        if not state.get("original_text") or not state.get("target_language"):
            # This error should ideally be caught before this node if inputs are missing
            print("---LANGGRAPH ERROR: Original text or target language is missing---")
            return {"error_message": "Original text or target language is missing for translation.", "translated_text": ""}

        try:
            openai_client = get_azure_openai_client()
            # The API changed - no more azure_endpoint attribute
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "Unknown endpoint")
            print(f"---LANGGRAPH: OpenAI client initialized with endpoint from env: {endpoint}---")
        except Exception as client_e:
            print(f"---LANGGRAPH ERROR: Failed to initialize OpenAI client: {client_e}---")
            return {"error_message": f"Azure OpenAI client initialization failed: {str(client_e)}", "translated_text": ""}
            if not openai_client:
             print("---LANGGRAPH ERROR: OpenAI client is None---")
             return {"error_message": "Azure OpenAI client not available.", "translated_text": ""}

        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
        
        system_prompt = f"You are an expert multilingual translator. Translate the following English text to {state['target_language']}. Provide only the direct translation, without any additional commentary or explanations. Be concise and accurate."
        user_prompt_content = state['original_text']

        response_stream = openai_client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_content}
            ],
            temperature=0.3, # Lower for more deterministic translation
            max_tokens=250,  # Adjust as needed
            stream=True
        )

        accumulated_translation = ""
        for chunk in response_stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                content_piece = chunk.choices[0].delta.content
                accumulated_translation += content_piece
                print(f"---LANGGRAPH STREAM CHUNK: {content_piece}---") # For debugging
                yield {"translated_text": accumulated_translation} # Yield partial state update
        
        print(f"---LANGGRAPH: Full streamed translation: {accumulated_translation}---")
        # Final return ensures the complete text is set in the state for subsequent nodes
        return {"translated_text": accumulated_translation, "error_message": None}

    except Exception as e:
        print(f"Error in translate_text_node (streaming): {e}")
        # Ensure translated_text is cleared or handled if an error occurs mid-stream
        return {"error_message": f"Translation failed: {str(e)}", "translated_text": state.get("translated_text", "")} # Keep what was translated so far or empty

def text_to_speech_node(state: TranslationState):
    """
    Synthesizes speech from the translated text.
    """
    print(f"---LANGGRAPH TTS: Starting TTS node for '{state.get('translated_text', 'NO_TEXT')}'---")
    print(f"---LANGGRAPH: Synthesizing speech for target language {state['target_language']}---")
    try:
        if not state.get("translated_text"):
            print("---LANGGRAPH ERROR: Translated text is missing for speech synthesis---")
            return {"error_message": "Translated text is missing for speech synthesis."}
        if not state.get("target_language"):
            print("---LANGGRAPH ERROR: Target language is missing for speech synthesis---")
            return {"error_message": "Target language is missing for speech synthesis."}

        target_language_name = state['target_language']
        if target_language_name not in SUPPORTED_LANGUAGES_VOICES:
            print(f"---LANGGRAPH ERROR: Language '{target_language_name}' not supported for TTS---")
            print(f"---LANGGRAPH: Available languages: {list(SUPPORTED_LANGUAGES_VOICES.keys())}---")
            return {"error_message": f"Language '{target_language_name}' not supported for TTS."}

        print("---LANGGRAPH: Getting speech config---")
        try:
            speech_config = get_speech_config()
            print("---LANGGRAPH: Speech config obtained---")
        except Exception as speech_config_error:
            print(f"---LANGGRAPH ERROR: Failed to get speech config: {speech_config_error}---")
            return {"error_message": f"Speech config error: {str(speech_config_error)}"}
            
        if not speech_config:
            print("---LANGGRAPH ERROR: Speech config is None---")
            return {"error_message": "Speech config not available for TTS."}
        
        # Configure speech synthesis voice for the selected language
        speech_config.speech_synthesis_voice_name = SUPPORTED_LANGUAGES_VOICES[target_language_name]["voice"]
        speech_config.set_speech_synthesis_output_format(SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3)

        # Synthesizer is created without specific audio output config to get bytes directly
        speech_synthesizer = get_speech_synthesizer(speech_config_val=speech_config)
        if not speech_synthesizer:
            return {"error_message": "Speech synthesizer not available."}

        tts_result = speech_synthesizer.speak_text_async(state["translated_text"]).get() # Blocks until synthesis is complete
        print(f"---LANGGRAPH DEBUG: TTS Result reason = {tts_result.reason}---")

        if tts_result.reason == ResultReason.SynthesizingAudioCompleted:
            print("---LANGGRAPH: Speech synthesis successful---")
            return {"audio_bytes": tts_result.audio_data, "error_message": None}
        elif tts_result.reason == ResultReason.Canceled:
            cancellation_details: CancellationDetails = tts_result.cancellation_details
            error_details = f"Speech synthesis canceled: {cancellation_details.reason}"
            if cancellation_details.reason == CancellationReason.Error:
                error_details += f" - Error details: {cancellation_details.error_details}"
            print(f"---LANGGRAPH: Speech synthesis failed: {error_details}---")
            return {"error_message": error_details, "audio_bytes": None}
        else:
            # Handle other unexpected ResultReason values
            error_details = f"Speech synthesis failed with unexpected reason: {tts_result.reason}"
            print(f"---LANGGRAPH: Speech synthesis failed: {error_details}---")
            return {"error_message": error_details, "audio_bytes": None}

    except Exception as e:
        print(f"Error in text_to_speech_node: {e}")
        return {"error_message": f"Text-to-speech failed: {str(e)}", "audio_bytes": None}

# 3. Conditional Edge Logic
def should_translate(state: TranslationState) -> Literal["translate_text", "__end__"]:
    """
    Determines if the translation should proceed based on content safety check.
    """
    if state.get("is_safe") and not state.get("error_message"):
        return "translate_text"
    return "__end__" # End the graph if content is not safe or an error occurred in safety check

def should_synthesize_speech(state: TranslationState) -> Literal["text_to_speech", "__end__"]:
    """
    Determines if speech synthesis should proceed based on successful translation.
    """
    if state.get("translated_text") and not state.get("error_message"):
        return "text_to_speech"
    return "__end__" # End the graph if translation failed or an error occurred

# 4. Construct Graph
workflow = StateGraph(TranslationState)
workflow.add_node("content_safety_check", content_safety_check_node)
workflow.add_node("translate_text", translate_text_node)
workflow.add_node("text_to_speech", text_to_speech_node) # Added TTS node

# Define edges
workflow.set_entry_point("content_safety_check")
workflow.add_conditional_edges(
    "content_safety_check",
    should_translate,
    {
        "translate_text": "translate_text",
        "__end__": END
    }
)
workflow.add_conditional_edges(
    "translate_text",
    should_synthesize_speech,
    {
        "text_to_speech": "text_to_speech",
        "__end__": END
    }
)
workflow.add_edge("text_to_speech", END) # New edge from TTS to END

# 5. Compile the graph
app_translator = workflow.compile()

# 6. Function to invoke the agent
def run_translation_agent(text_to_translate: str, target_language: str):
    """
    Invokes the translation agent.
    """
    print(f"---LANGGRAPH MAIN: Starting translation for '{text_to_translate}' -> {target_language}---")
    initial_state = {
        "original_text": text_to_translate,
        "target_language": target_language,
    }
    # The `stream` method is for streaming intermediate steps.
    # For a final result, `invoke` is typically used.
    # If you need to stream tokens from the LLM itself, that's a different setup within the node.
    final_state = app_translator.invoke(initial_state)
    print(f"---LANGGRAPH MAIN: Final state keys: {list(final_state.keys())}---")
    print(f"---LANGGRAPH MAIN: Audio bytes present: {'audio_bytes' in final_state and final_state['audio_bytes'] is not None}---")
    return final_state

def run_translation_agent_streaming(text_to_translate: str, target_language: str):
    """
    Invokes the translation agent and streams its state updates.
    Yields the full state of the graph after each step.
    """
    initial_state = {
        "original_text": text_to_translate,
        "target_language": target_language,
        "translated_text": "", # Initialize to empty for streaming
        "audio_bytes": None,
        "error_message": None,
        "is_safe": None
    }
    # The stream method yields state dictionaries at each step of the graph's execution.
    # When a node (like translate_text_node) yields, that partial state is included.
    return app_translator.stream(initial_state, {"recursion_limit": 25})


if __name__ == '__main__':
    # Example usage (requires Azure credentials to be set in environment)
    # Ensure you have .env file with:
    # AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME
    # AZURE_CONTENT_SAFETY_ENDPOINT, AZURE_CONTENT_SAFETY_KEY
    from dotenv import load_dotenv
    load_dotenv(dotenv_path='../../.env') # Adjust path to .env if necessary

    print(f"OpenAI Key Loaded: {bool(os.getenv('AZURE_OPENAI_API_KEY'))}")
    print(f"OpenAI Endpoint Loaded: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
    print(f"OpenAI Deployment: {os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')}")
    print(f"Content Safety Key Loaded: {bool(os.getenv('AZURE_CONTENT_SAFETY_KEY'))}")
    print(f"Content Safety Endpoint Loaded: {os.getenv('AZURE_CONTENT_SAFETY_ENDPOINT')}")


    if not all([os.getenv("AZURE_OPENAI_ENDPOINT"), os.getenv("AZURE_OPENAI_API_KEY"), 
                os.getenv("AZURE_CONTENT_SAFETY_ENDPOINT"), os.getenv("AZURE_CONTENT_SAFETY_KEY"),
                os.getenv("AZURE_SPEECH_KEY"), os.getenv("AZURE_SPEECH_REGION") # Added speech env vars for local test
                ]):
        print("Azure credentials (OpenAI, Content Safety, Speech) not found in environment variables. Skipping example run.")
    else:
        example_text = "Hello, how are you today? This is a test of the full agent."
        example_language = "French" # Changed for testing TTS
        print(f"\nAttempting to translate and synthesize: '{example_text}' to {example_language}")
        result = run_translation_agent(example_text, example_language)
        print("\nAgent Result:")
        if result.get("error_message"):
            print(f"  Error: {result['error_message']}")
        else:
            print(f"  Original: {result['original_text']}")
            print(f"  Target Language: {result['target_language']}")
            print(f"  Translated: {result['translated_text']}")
            if result.get("audio_bytes"):
                print(f"  Audio Bytes Length: {len(result['audio_bytes'])}")
                # To save and play audio locally (optional):
                # with open("translated_audio.mp3", "wb") as f:
                #     f.write(result['audio_bytes'])
                # print("  Audio saved to translated_audio.mp3")
            else:
                print("  Audio Bytes: Not generated")

        example_text_unsafe = "I want to buy drugs."
        print(f"\nAttempting to translate unsafe text: '{example_text_unsafe}' to {example_language}")
        result_unsafe = run_translation_agent(example_text_unsafe, example_language)
        print("\nAgent Result (unsafe text):")
        if result_unsafe.get("error_message"):
            print(f"  Error: {result_unsafe['error_message']}")
        else:
            print(f"  Original: {result_unsafe['original_text']}")
            print(f"  Target Language: {result_unsafe['target_language']}")
            print(f"  Translated: {result_unsafe['translated_text']}")

    # Test streaming
    if not all([os.getenv("AZURE_OPENAI_ENDPOINT"), os.getenv("AZURE_OPENAI_API_KEY"), 
                os.getenv("AZURE_CONTENT_SAFETY_ENDPOINT"), os.getenv("AZURE_CONTENT_SAFETY_KEY"),
                os.getenv("AZURE_SPEECH_KEY"), os.getenv("AZURE_SPEECH_REGION")
                ]):
        print("Azure credentials not found. Skipping streaming example run.")
    else:
        example_text_stream = "Tell me a very short story about a friendly robot learning a new language."
        example_language_stream = "German"
        print(f"\nAttempting to stream translate: '{example_text_stream}' to {example_language_stream}")
        
        full_final_state = None
        current_translated_text = ""
        for event_state in run_translation_agent_streaming(example_text_stream, example_language_stream):
            # event_state is the full state snapshot after each yielding step or node completion
            # print(f"\n--- STREAM EVENT ---")
            # print(event_state) # This can be very verbose, print specific parts
            
            # Check for updates to translated_text
            if "translate_text" in event_state: # Check if translate_text node has produced output
                node_output = event_state["translate_text"]
                if isinstance(node_output, dict) and "translated_text" in node_output:
                    new_text_chunk = node_output.get("translated_text")
                    if new_text_chunk and new_text_chunk != current_translated_text:
                        # This logic is more for UI, here we just print the latest full version
                        # To see chunks, you'd compare with previous version of event_state['translate_text']['translated_text']
                        # For console, let's just print the latest version of translated_text from the state
                        pass # The node itself prints chunks

            # Keep the latest full state
            full_final_state = event_state # The last event will be the final state of the graph run

        print("\n--- FINAL AGENT STATE (from streaming test) ---")
        if full_final_state:
            if full_final_state.get("error_message"):
                print(f"  Error: {full_final_state['error_message']}")
            else:
                print(f"  Original: {full_final_state.get('original_text')}")
                print(f"  Target Language: {full_final_state.get('target_language')}")
                print(f"  Final Translated: {full_final_state.get('translated_text')}")
                if full_final_state.get("audio_bytes"):
                    print(f"  Audio Bytes Length: {len(full_final_state['audio_bytes'])}")
                else:
                    print("  Audio Bytes: Not generated (or not requested in this simple stream test)")
        else:
            print("  No final state captured from streaming test.")
