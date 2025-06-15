from dotenv import load_dotenv
load_dotenv() # Load environment variables from .env file at the very beginning

import streamlit as st
import os
from core.azure_clients import (
    get_speech_config, # Still needed for STT if STT client init is here
    get_speech_recognizer, # Import for STT
    get_speech_synthesizer,
    get_azure_openai_client,
    get_content_safety_client
)
from core.langgraph_agent import run_translation_agent, run_translation_agent_streaming # Import the LangGraph agent runner
from core.constants import SUPPORTED_LANGUAGES_VOICES # Import for UI display
from azure.cognitiveservices.speech import AudioConfig, ResultReason, CancellationReason, SpeechSynthesisOutputFormat # For STT
import tempfile # For handling uploaded audio file
import base64 # For encoding diagnostic audio in HTML

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Language Learning Companion",
    page_icon="🧠",
    layout="wide"
)

# --- Environment Variable Check & Client Initialization ---
# These are expected to be set in the App Service configuration or a local .env file
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")
AZURE_CONTENT_SAFETY_ENDPOINT = os.getenv("AZURE_CONTENT_SAFETY_ENDPOINT")
KEY_VAULT_URI = os.getenv("KEY_VAULT_URI")
AZURE_SPEECH_KEY_SECRET_NAME = os.getenv("AZURE_SPEECH_KEY_SECRET_NAME")

# Check for missing environment variables
missing_vars = []
if not AZURE_OPENAI_ENDPOINT: missing_vars.append("AZURE_OPENAI_ENDPOINT")
# AZURE_OPENAI_DEPLOYMENT_NAME is used by both main.py (legacy) and langgraph_agent.py
if not AZURE_OPENAI_DEPLOYMENT_NAME: missing_vars.append("AZURE_OPENAI_DEPLOYMENT_NAME (defaulted to gpt-4o if not set, but ensure it exists)")

# For Speech Service, check if either direct key OR Key Vault config is available
if not AZURE_SPEECH_KEY and not (KEY_VAULT_URI and AZURE_SPEECH_KEY_SECRET_NAME):
    missing_vars.append("AZURE_SPEECH_KEY (or KEY_VAULT_URI + AZURE_SPEECH_KEY_SECRET_NAME for Key Vault retrieval)")

if not AZURE_SPEECH_REGION: missing_vars.append("AZURE_SPEECH_REGION")
if not AZURE_CONTENT_SAFETY_ENDPOINT: missing_vars.append("AZURE_CONTENT_SAFETY_ENDPOINT")

if missing_vars:
    st.error(f"Missing critical environment variables: {', '.join(missing_vars)}. Please configure them. For App Service, use Configuration > Application settings. For local dev, use a .env file and `python-dotenv`.")
    st.stop()

# Initialize Azure clients - only speech_config might be needed if STT is initialized here
try:
    pass # Clients are initialized within the agent or for STT separately
except Exception as e:
    st.error(f"Error during initial Azure client setup (if any outside agent): {e}.")
    st.exception(e)

# --- Application State (using Streamlit session state) ---
if 'translation' not in st.session_state:
    st.session_state.translation = ""
if 'audio_bytes' not in st.session_state:
    st.session_state.audio_bytes = None
if 'error_message' not in st.session_state:
    st.session_state.error_message = ""
if 'info_message' not in st.session_state:
    st.session_state.info_message = ""
if 'recognized_text' not in st.session_state:
    st.session_state.recognized_text = ""
if 'stt_error_message' not in st.session_state:
    st.session_state.stt_error_message = ""
if 'stt_info_message' not in st.session_state:
    st.session_state.stt_info_message = ""

# --- UI Elements ---
st.title("🧠 AI Language Learning Companion")
st.markdown("Translate English text and hear it spoken in your target language. Powered by Azure AI and LangGraph.")

# Language selection details - moved to constants.py, imported for UI
target_language_name_main = st.selectbox(
    "Choose target language:",
    options=list(SUPPORTED_LANGUAGES_VOICES.keys()),
    key="language_selector_main_app"  # Changed key
)

user_prompt_main = st.text_area("Enter English text to translate:", height=100, key="user_prompt_input_main_app") # Changed key

if st.button("Translate and Speak", key="translate_button_main_app"): # Changed key
    st.session_state.translation = ""
    st.session_state.audio_bytes = None
    st.session_state.error_message = ""
    st.session_state.info_message = ""

    if not user_prompt_main: # Use the correct variable
        st.session_state.error_message = "Please enter some text to translate."
    else:
        with st.spinner("AI is thinking... (LangGraph agent processing)"):
            try:
                # Use the streaming function
                # final_agent_state = None # Will be built from accumulated_graph_state
                accumulated_translation_for_display = "" # Used for streaming display
                
                # Initialize placeholders
                translated_text_placeholder = st.empty()
                audio_player_placeholder = st.empty()
                translated_text_placeholder.markdown("*(Translating...)*")
                audio_player_placeholder.empty()

                # This will hold the merged state from all graph steps
                # It should reflect the TranslationState structure
                accumulated_graph_state = {}

                stream = run_translation_agent_streaming(user_prompt_main, target_language_name_main)
                for event_output_for_node in stream: 
                    # event_output_for_node is like {"node_name": output_dict_from_node}
                    # Each event_output_for_node should contain one key: the name of the node that just ran or yielded.
                    # The value associated with that key is the actual output from that node.
                    
                    if not event_output_for_node: continue # Should not happen, but good practice

                    # Ensure event_output_for_node is a dictionary and not empty
                    if not isinstance(event_output_for_node, dict) or not event_output_for_node:
                        # print(f"Skipping non-dict or empty event: {event_output_for_node}")
                        continue

                    node_name = list(event_output_for_node.keys())[0] 
                    node_actual_output = event_output_for_node[node_name] 

                    if isinstance(node_actual_output, dict):
                        # Merge the actual output of the node into our accumulated_graph_state
                        accumulated_graph_state.update(node_actual_output)

                        # Handle streaming display for translation
                        if node_name == "translate_text" and "translated_text" in node_actual_output:
                            accumulated_translation_for_display = node_actual_output["translated_text"]
                            if accumulated_translation_for_display:
                                translated_text_placeholder.markdown(f"### {accumulated_translation_for_display}")
                    # else:
                        # print(f"Warning: Node {node_name} output was not a dict: {node_actual_output}")

                # After the stream is exhausted, accumulated_graph_state holds the final merged state
                final_agent_state = accumulated_graph_state
                
                # Debug block (can be kept or modified)
                st.sidebar.subheader("Stream Debug Info (Main App)")
                st.sidebar.write("Final Accumulated Graph State Keys:")
                st.sidebar.json(list(final_agent_state.keys()) if final_agent_state else "None")
                
                if "audio_bytes" in final_agent_state:
                    audio_present = final_agent_state["audio_bytes"] is not None
                    audio_len = len(final_agent_state["audio_bytes"]) if audio_present else "N/A"
                    st.sidebar.write(f"audio_bytes key present in final_agent_state: True, Has data: {audio_present}, Length: {audio_len}")
                else:
                    st.sidebar.write("audio_bytes key present in final_agent_state: False")
                
                if "error_message" in final_agent_state and final_agent_state["error_message"]:
                    st.sidebar.write(f"Error in final_agent_state: {final_agent_state['error_message']}")
                elif not ("audio_bytes" in final_agent_state and final_agent_state["audio_bytes"]):
                    st.sidebar.write("Audio bytes not found or empty in final_agent_state, and no explicit error message for audio generation reported by agent.")
                # ---- END DEBUG BLOCK ----

                if final_agent_state: # Check if final_agent_state has content
                    if final_agent_state.get("error_message"):
                        st.session_state.error_message = final_agent_state["error_message"]
                        # Clear previous success to avoid showing stale translation/audio
                        translated_text_placeholder.error(st.session_state.error_message)
                        st.session_state.translation = "" 
                        st.session_state.audio_bytes = None
                    else:
                        final_translation_from_state = final_agent_state.get("translated_text", "")
                        
                        if final_translation_from_state:
                            st.session_state.translation = final_translation_from_state
                            # Update placeholder with final translation
                            translated_text_placeholder.markdown(f"### {st.session_state.translation}")
                        else: 
                            st.session_state.translation = "" 
                            translated_text_placeholder.markdown("*(No translation received from agent)*")
                        
                        # Handle audio only if translation was successful
                        if st.session_state.translation: 
                            if final_agent_state.get("audio_bytes"):
                                st.session_state.audio_bytes = final_agent_state["audio_bytes"]
                                audio_player_placeholder.audio(st.session_state.audio_bytes, format="audio/mp3")
                            else:
                                audio_player_placeholder.info("Audio could not be generated for the translation (final_agent_state).")
                                st.session_state.audio_bytes = None
                        else: # No translation, so no audio
                            audio_player_placeholder.empty()
                            st.session_state.audio_bytes = None
                else: # No final_agent_state at all (e.g., stream was empty or all events were invalid)
                    st.session_state.error_message = "Translation agent did not return a final state (stream processing issue)."
                    translated_text_placeholder.error(st.session_state.error_message)
                    st.session_state.translation = ""
                    st.session_state.audio_bytes = None

            except Exception as e:
                st.session_state.error_message = f"An unexpected error occurred: {str(e)}"
                translated_text_placeholder.error(st.session_state.error_message) # Show error in placeholder
                st.session_state.translation = "" # Clear translation on error
                st.session_state.audio_bytes = None # Clear audio on error
                st.exception(e)

# --- Display Results and Messages (Persistent section) ---
if st.session_state.error_message:
    st.error(st.session_state.error_message)
    # Consider clearing st.session_state.error_message here if it's meant to be transient for each operation
    # For now, it persists until the next operation.

if st.session_state.translation:
    st.subheader(f"Last Successful Translation in {target_language_name_main}:")
    st.markdown(f"### {st.session_state.translation}")

if st.session_state.audio_bytes:
    st.subheader("Listen to Pronunciation:")
    st.audio(st.session_state.audio_bytes, format="audio/mp3")

# --- Speech-to-Text (Practice Speaking) ---
st.sidebar.title("🎤 Practice Speaking")
st.sidebar.markdown("Upload an audio file of yourself speaking the translated phrase to get feedback.")

# Get the language code for the selected target language for STT
# This assumes the `code` in SUPPORTED_LANGUAGES_VOICES is suitable for STT
# e.g., "es-ES", "fr-FR", etc.
stt_language_code = SUPPORTED_LANGUAGES_VOICES[target_language_name_main]["code"] # Use correct variable

uploaded_audio_file = st.sidebar.file_uploader(
    f"Upload your audio recording (e.g., WAV, MP3) in {target_language_name_main}:", # Use correct variable
    type=["wav", "mp3"], # Add other supported types if needed
    key="stt_audio_uploader"
)

if uploaded_audio_file is not None:
    st.session_state.recognized_text = ""
    st.session_state.stt_error_message = ""
    st.session_state.stt_info_message = ""

    with st.spinner(f"Recognizing speech from uploaded audio in {target_language_name_main}..."):
        try:
            # Save the uploaded BytesIO to a temporary file because Speech SDK's AudioConfig(filename=...) expects a path
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_audio_file.name)[1]) as tmp_audio_file:
                tmp_audio_file.write(uploaded_audio_file.getvalue())
                tmp_audio_file_path = tmp_audio_file.name
            
            st.sidebar.audio(tmp_audio_file_path) # Display the uploaded audio

            speech_config_stt = get_speech_config()
            speech_config_stt.speech_recognition_language = stt_language_code
            
            # Using a file as input for STT
            audio_input_config = AudioConfig(filename=tmp_audio_file_path)
            speech_recognizer = get_speech_recognizer(speech_config_val=speech_config_stt, audio_input_config=audio_input_config)

            st.session_state.stt_info_message = f"Attempting speech recognition in {stt_language_code}..."
            
            recognition_result = speech_recognizer.recognize_once_async().get() # Blocking call

            if recognition_result.reason == ResultReason.RecognizedSpeech:
                st.session_state.recognized_text = recognition_result.text
                st.session_state.stt_info_message = "Speech recognized successfully."
            elif recognition_result.reason == ResultReason.NoMatch:
                st.session_state.stt_error_message = "No speech could be recognized from the audio."
            elif recognition_result.reason == ResultReason.Canceled:
                cancellation_details = recognition_result.cancellation_details
                st.session_state.stt_error_message = f"Speech recognition canceled: {cancellation_details.reason}"
                if cancellation_details.reason == CancellationReason.Error:
                    st.session_state.stt_error_message += f" - Error details: {cancellation_details.error_details}"
            else:
                st.session_state.stt_error_message = f"Speech recognition failed with reason: {recognition_result.reason}"

        except Exception as e:
            st.session_state.stt_error_message = f"An error occurred during speech recognition: {str(e)}"
            st.exception(e)
        finally:
            # Clean up the temporary file
            if 'tmp_audio_file_path' in locals() and os.path.exists(tmp_audio_file_path):
                os.remove(tmp_audio_file_path)

# Display STT Results
if st.session_state.stt_info_message and not st.session_state.stt_error_message:
    st.sidebar.info(st.session_state.stt_info_message)
if st.session_state.stt_error_message:
    st.sidebar.error(st.session_state.stt_error_message)

if st.session_state.recognized_text:
    st.sidebar.subheader("You said:")
    st.sidebar.markdown(f"**{st.session_state.recognized_text}**")
    # Simple comparison (exact match)
    if st.session_state.translation:
        if st.session_state.recognized_text.strip().lower() == st.session_state.translation.strip().lower():
            st.sidebar.success("👍 Perfect match with the translated text!")
        else:
            st.sidebar.warning("Hmm, that's not an exact match. Keep practicing!")
            st.sidebar.markdown(f"**Original translation:** {st.session_state.translation}")

# --- Diagnostic Endpoint (Azure Speech Service Connectivity) ---
st.sidebar.markdown("---")
st.sidebar.title("🔧 Diagnostics")
st.sidebar.markdown("Test Azure Speech Service connectivity and settings.")

# Button to trigger diagnostic speech synthesis
if st.sidebar.button("Test Speech Service", key="sidebar_test_speech_button"): # Added key
    st.sidebar.info("Testing Azure Speech Service connectivity...")
    temp_audio_path = None # Initialize variable
    try:
        # Simple text-to-speech test
        test_text = "Azure Speech Service is working."
        speech_config_test = get_speech_config() # This sets MP3 format by default
        
        # Create a temporary file for audio output with .mp3 suffix
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_audio_path = temp_file.name
        
        audio_config_test = AudioConfig(filename=temp_audio_path)
        synthesizer = get_speech_synthesizer(speech_config_val=speech_config_test, audio_config_val=audio_config_test)

        result = synthesizer.speak_text_async(test_text).get()

        if result.reason == ResultReason.SynthesizingAudioCompleted:
            st.sidebar.success("Speech Service test: SynthesizingAudioCompleted.")
            # Read the audio from the temporary file and play it
            if os.path.exists(temp_audio_path):
                with open(temp_audio_path, "rb") as f:
                    audio_bytes = f.read()
                if audio_bytes:
                    st.sidebar.audio(audio_bytes, format="audio/mp3")
                    st.sidebar.info(f"Generated {len(audio_bytes)} bytes of audio.")
                else:
                    st.sidebar.warning("Audio file was empty after synthesis.")
            else:
                st.sidebar.error("Temporary audio file not found after synthesis.")
        else:
            st.sidebar.error(f"Speech synthesis failed: {result.reason}")
            if result.reason == ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                st.sidebar.error(f"Cancellation reason: {cancellation_details.reason}")
                if cancellation_details.reason == CancellationReason.Error:
                    st.sidebar.error(f"Error details: {cancellation_details.error_details}")

    except Exception as e:
        st.sidebar.error(f"An error occurred while testing Speech Service: {str(e)}")
        st.exception(e)
    finally:
        # Clean up the temporary file
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

# --- Footer Information ---
st.sidebar.markdown("---")
st.sidebar.markdown("**Azure Services Powering this App:**")
st.sidebar.markdown("- Azure OpenAI Service (Translation)")
st.sidebar.markdown("- Azure AI Speech Service (Text-to-Speech)")
st.sidebar.markdown("- Azure AI Content Safety (Input Moderation)")
st.sidebar.markdown("**Application Frameworks:**")
st.sidebar.markdown("- Streamlit (UI)")
st.sidebar.markdown("- LangGraph (Conceptual for future agentic workflow)")

# --- Main Navigation ---
# Add simple navigation between main app and diagnostics
page = st.sidebar.radio("Navigation", ["Main Application", "Diagnostics"], key="page_navigation_selector") # Added key

if page == "Diagnostics":
    st.title("🔍 Service Diagnostics")
    st.write("Use this page to test connectivity to Azure services directly from the container.")
    
    with st.expander("Environment Variables", expanded=True):
        st.write("Checking environment variables required for the application:")
        
        env_vars = {
            "AZURE_OPENAI_ENDPOINT": os.getenv("AZURE_OPENAI_ENDPOINT", "Not set"),
            "AZURE_OPENAI_API_KEY": "✓ Set" if os.getenv("AZURE_OPENAI_API_KEY") else "Not set",
            "AZURE_OPENAI_API_VERSION": os.getenv("AZURE_OPENAI_API_VERSION", "2023-12-01-preview"),
            "AZURE_OPENAI_DEPLOYMENT_NAME": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
            "AZURE_SPEECH_KEY": "✓ Set" if os.getenv("AZURE_SPEECH_KEY") else "Not set",
            "AZURE_SPEECH_REGION": os.getenv("AZURE_SPEECH_REGION", "Not set"),
            "AZURE_CONTENT_SAFETY_ENDPOINT": "✓ Set" if os.getenv("AZURE_CONTENT_SAFETY_ENDPOINT") else "Not set",
            "AZURE_CONTENT_SAFETY_KEY": "✓ Set" if os.getenv("AZURE_CONTENT_SAFETY_KEY") else "Not set",
            "KEY_VAULT_URI": os.getenv("KEY_VAULT_URI", "Not set"),
            "AZURE_SPEECH_KEY_SECRET_NAME": os.getenv("AZURE_SPEECH_KEY_SECRET_NAME", "Not set")
        }
        
        for var, value in env_vars.items():
            if var.endswith("_KEY") and value != "Not set" and value != "✓ Set":
                # Don't display actual key values
                st.write(f"- {var}: ✓ Set")
            else:
                st.write(f"- {var}: {value}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Test OpenAI API")
        if st.button("Test OpenAI Connection"):
            try:
                with st.spinner("Testing Azure OpenAI..."):
                    client = get_azure_openai_client()
                    test_prompt = "Translate 'Hello' to Spanish."
                    response = client.chat.completions.create(
                        model=os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4o'),
                        messages=[{"role": "user", "content": test_prompt}],
                        max_tokens=20
                    )
                    result = response.choices[0].message.content.strip()
                    st.success(f"✅ OpenAI connection successful! Response: '{result}'")
            except Exception as e:
                st.error(f"❌ OpenAI test failed: {str(e)}")
                st.exception(e)
    
    with col2:
        st.subheader("Test Speech Service")
        if st.button("Test Speech Synthesis"):
            try:
                with st.spinner("Testing Azure Speech Service..."):
                    speech_config = get_speech_config()
                    
                    if speech_config:
                        # Set Spanish voice for testing
                        speech_config.speech_synthesis_voice_name = "es-ES-AlvaroNeural"
                        speech_config.set_speech_synthesis_output_format(SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3)
                        
                        synthesizer = get_speech_synthesizer(speech_config_val=speech_config)
                        test_text = "Hola mundo. Esta es una prueba del servicio de voz."
                        result = synthesizer.speak_text_async(test_text).get()
                        
                        if result.reason == ResultReason.SynthesizingAudioCompleted:
                            audio_bytes = result.audio_data
                            st.success(f"✅ Speech synthesis successful! Generated {len(audio_bytes)} bytes of audio.")
                            st.audio(audio_bytes, format="audio/mp3")
                        else:
                            st.error(f"❌ Speech synthesis failed: {result.reason}")
                            if result.reason == ResultReason.Canceled:
                                cancellation = result.cancellation_details
                                st.error(f"Speech synthesis canceled: {cancellation.reason}")
                                st.error(f"Error details: {cancellation.error_details}")
                    else:
                        st.error("❌ Could not create Speech config. Check the AZURE_SPEECH_KEY and AZURE_SPEECH_REGION.")
            except Exception as e:
                st.error(f"❌ Speech test failed: {str(e)}")
                st.exception(e)
    
    st.subheader("Test Full Translation Agent")
    test_text = st.text_input("Enter text to translate", value="Hello, this is a test of the translation agent.", key="test_text_input_diagnostics") # Changed key
    test_language = st.selectbox("Target language", list(SUPPORTED_LANGUAGES_VOICES.keys()), index=list(SUPPORTED_LANGUAGES_VOICES.keys()).index("Spanish") if "Spanish" in SUPPORTED_LANGUAGES_VOICES else 0, key="diagnostic_language_selector_diagnostics") # Changed key
    
    if st.button("Test Full Agent", key="test_full_agent_button_diagnostics"): # Changed key
        with st.spinner("Running full LangGraph translation agent..."):
            try:
                result = run_translation_agent(test_text, test_language)
                
                has_translation = "translated_text" in result and result["translated_text"]
                has_audio = "audio_bytes" in result and result["audio_bytes"]
                has_error = "error_message" in result and result["error_message"]
                
                if has_translation:
                    st.success(f"✅ Translation successful: {result['translated_text']}")
                else:
                    st.error("❌ Translation failed or returned empty.")
                
                if has_audio:
                    st.success(f"✅ Audio generation successful ({len(result['audio_bytes'])} bytes).")
                    st.audio(result["audio_bytes"], format="audio/mp3")
                else:
                    st.error("❌ Audio generation failed or returned empty.")
                
                if has_error:
                    st.error(f"❌ Agent error: {result['error_message']}")
                
            except Exception as e:
                st.error(f"❌ Agent test failed: {str(e)}")
                st.exception(e)

else:  # Main Application
    # The main application UI is now defined above, before the STT and sidebar diagnostics.
    # This section can be removed or refactored if the UI is meant to be conditional based on `page`.
    # For now, assuming the main UI elements (title, language selector, text area, button)
    # should always be visible when page == "Main Application".
    # The current structure has main UI elements outside this if/else, then STT, then sidebar diagnostics,
    # then this if/else for page navigation.

    # To avoid re-declaring elements and causing new key issues,
    # we ensure the main application's interactive elements are defined once.
    # The existing structure seems to define them once at the top.
    # This 'else' block might be redundant if the main app content is already displayed.
    # However, to strictly follow the if/else for page navigation, we might duplicate or move them.
    # Let's ensure the main app UI is correctly scoped.
    # The main application content defined at the top level will serve as the
    # "Main Application" page. The `if page == "Diagnostics":` block will overlay or replace
    # the view with diagnostic tools. We don't need to redefine main app elements here.
    pass # Main application content is already rendered above the page == "Diagnostics" block.

# The following UI elements were duplicated from the top of the file.
# They are part of the main application and should only be defined once.
# I am removing this duplicated block.
# st.title(\"🧠 AI Language Learning Companion\")
# st.markdown(\"Translate English text and hear it spoken in your target language. Powered by Azure AI and LangGraph.\")

# # Language selection details - moved to constants.py, imported for UI
# target_language_name = st.selectbox(
# \"Choose target language:\",
# options=list(SUPPORTED_LANGUAGES_VOICES.keys()),
# key=\"main_language_selector\" # This was a duplicate key source
# )

# user_prompt = st.text_area(\"Enter English text to translate:\", height=100, key=\"user_prompt_input_diagnostic\") # This was a duplicate key source

# if st.button(\"Translate and Speak\", key=\"translate_button\"): # This was the original duplicate key
# st.session_state.translation = \"\"
# st.session_state.audio_bytes = None
# st.session_state.error_message = \"\"
# st.session_state.info_message = \"\"

# if not user_prompt:
# st.session_state.error_message = \"Please enter some text to translate.\"
# else:
# with st.spinner(\"AI is thinking... (LangGraph agent processing)\"):\n# try:
# # Use the streaming function
# final_agent_state = None # Will be built from accumulated_graph_state
# accumulated_translation = \"\"\n                
# # Initialize placeholders
# translated_text_placeholder = st.empty()
# audio_player_placeholder = st.empty()
# translated_text_placeholder.markdown(\"*(Translating...)*\")
# audio_player_placeholder.empty()

# stream = run_translation_agent_streaming(user_prompt, target_language_name)
# for event in stream:
# # The event dictionary contains the full state after each step.
# # We are interested in the \'translate_text\' node\'s output for streaming text,
# # and the final state for audio and errors.
# # Check for updates from the translate_text node
# print(f\"LangGraph event received: {event.keys()}\")\n                    
# # Handle translated_text directly in the state
# if \"translated_text\" in event:
# accumulated_translation = event[\"translated_text\"]
# if accumulated_translation:
# translated_text_placeholder.markdown(accumulated_translation)\n                    
# # Also try to handle node-specific outputs for backward compatibility
# elif \"translate_text\" in event: # This key corresponds to the node name
# node_output = event[\"translate_text\"]
# print(f\"translate_text node output: {type(node_output)}\")
# if isinstance(node_output, dict) and \"translated_text\" in node_output:
# current_chunk = node_output.get(\"translated_text\")
# if current_chunk: # LangGraph yields the full accumulated text
# accumulated_translation = current_chunk
# translated_text_placeholder.markdown(accumulated_translation)

# # Store the latest full state
# final_agent_state = event # The last event is the final state of the graph

# # After the stream is exhausted, process the final state
# if final_agent_state:
# if final_agent_state.get(\"error_message\"):
# st.session_state.error_message = final_agent_state[\"error_message\"]
# translated_text_placeholder.markdown(\"*(Translation failed)*\")
# else:
# # Final translation text (already displayed by streaming)
# if not accumulated_translation and final_agent_state.get(\"translated_text\"):
# # If for some reason streaming didn\'t update, set final text
# translated_text_placeholder.markdown(final_agent_state[\"translated_text\"])\n                        elif not accumulated_translation and not final_agent_state.get(\"translated_text\"):\n                            translated_text_placeholder.markdown(\"*(No translation received)*\")

# # Handle audio
# if final_agent_state.get(\"audio_bytes\"):
# st.session_state.audio_bytes = final_agent_state[\"audio_bytes\"]
# audio_player_placeholder.audio(st.session_state.audio_bytes, format=\"audio/mp3\")
# else:
# audio_player_placeholder.info(\"Audio could not be generated.\")
# else:
# st.session_state.error_message = \"Failed to get a response from the translation agent.\"
# translated_text_placeholder.markdown(\"*(Translation failed)*\")

# --- Final display of messages (already present, ensure it's correctly placed after all logic) ---
# This block was fine, just ensuring it's not duplicated or misplaced.
# if st.session_state.info_message and not st.session_state.error_message:
# st.info(st.session_state.info_message)
# if st.session_state.error_message:
# st.error(st.session_state.error_message)

# if st.session_state.translation: # This was the part that might not show if placeholder handles it
# st.subheader(f\"Translation in {target_language_name}:\")
# st.markdown(f\"### {st.session_state.translation}\")

# if st.session_state.audio_bytes:
# st.subheader(\"Listen to Pronunciation:\")
# st.audio(st.session_state.audio_bytes, format=\"audio/mp3\")



