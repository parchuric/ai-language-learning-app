import os
from azure.identity import DefaultAzureCredential
from openai import AzureOpenAI
from azure.ai.contentsafety import ContentSafetyClient
from azure.cognitiveservices.speech import SpeechConfig, SpeechSynthesizer, AudioConfig, ResultReason, CancellationReason, SpeechRecognizer
from azure.keyvault.secrets import SecretClient

def get_default_azure_credential():
    """Gets the default Azure credential."""
    return DefaultAzureCredential()

def get_azure_openai_client():
    """Initializes and returns the Azure OpenAI client."""
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2023-12-01-preview")  # This is a stable version that works well
    if not endpoint:
        raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is not set.")
    
    # Use API key if provided, otherwise use managed identity
    if api_key:
        openai_client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version
        )
    else:
        # Fallback to managed identity
        # The AzureOpenAI SDK (>=1.0.0) uses DefaultAzureCredential by default if api_key is not provided.
        # To be explicit, one can pass azure_ad_token_provider.
        openai_client = AzureOpenAI(
            azure_endpoint=endpoint,
            azure_ad_token_provider=get_default_azure_credential(), # Correct way for SDK v1.x
            api_version=api_version
        )
    
    return openai_client

# Function to get Azure Speech SDK SpeechConfig object
# This version prioritizes Managed Identity (via DefaultAzureCredential)
# and falls back to Key Vault for the key if direct MI auth to Speech Service is not preferred/fully set up for keyless.
# For App Service with MI, direct keyless is best. For local dev, .env key is used.
def get_speech_config():
    """
    Initializes and returns an Azure SpeechConfig object.
    Prioritizes keyless authentication if deployed to Azure with Managed Identity.
    Otherwise, attempts to use environment variables for key/region,
    or fetches the key from Key Vault if configured for it.
    """
    try:
        # Scenario 1: Running in Azure with Managed Identity (preferred for App Service)
        # DefaultAzureCredential will attempt to use the MI.
        # SpeechSDK supports token-based auth which DefaultAzureCredential can provide.
        # However, direct keyless with SpeechConfig is simpler if MI has "Cognitive Services User" role.
        
        # Let's assume MI is configured and DefaultAzureCredential will be used by the SDK implicitly
        # if key and region are provided and the MI has permissions.
        # A more explicit way for keyless with MI (if SDK supports it directly without key/region):
        # speech_config = SpeechConfig(auth_token_provider=lambda: default_azure_credential.get_token("https://cognitiveservices.azure.com/.default").token)
        # For now, we rely on the SDK's behavior with DefaultAzureCredential when key/region are set.

        speech_key = os.getenv("AZURE_SPEECH_KEY")
        speech_region = os.getenv("AZURE_SPEECH_REGION")
        key_vault_uri = os.getenv("KEY_VAULT_URI")
        speech_key_secret_name = os.getenv("AZURE_SPEECH_KEY_SECRET_NAME")

        if not speech_key and key_vault_uri and speech_key_secret_name:
            print(f"Attempting to fetch Speech Key from Key Vault: {key_vault_uri}, Secret: {speech_key_secret_name}")
            try:
                credential = DefaultAzureCredential()
                secret_client = SecretClient(vault_url=key_vault_uri, credential=credential)
                retrieved_secret = secret_client.get_secret(speech_key_secret_name)
                speech_key = retrieved_secret.value
                print("Successfully fetched Speech Key from Key Vault.")
            except Exception as kv_e:
                print(f"Failed to fetch Speech Key from Key Vault: {kv_e}")
                # Fallback or error, depending on policy. For now, continue to see if region is set.
        
        if speech_key and speech_region:
            print(f"Using Speech Key (from .env or Key Vault) and Region for SpeechConfig. Region: {speech_region}")
            speech_config = SpeechConfig(subscription=speech_key, region=speech_region)
            return speech_config
        elif speech_region: # Case for Managed Identity where key is not needed but region is
            print(f"Using Managed Identity and Region ({speech_region}) for SpeechConfig (keyless).")            # For keyless with MI, ensure the MI has "Cognitive Services User" role on the Speech resource.
            # The SDK should pick up the MI automatically if key is not provided.
            speech_config = SpeechConfig(region=speech_region)
            # To be certain DefaultAzureCredential is used if the SDK doesn't do it implicitly without a key:
            # You might need to pass an auth_token_provider as shown in commented section above,
            # or ensure the SDK version directly supports DefaultAzureCredential for keyless.
            # For simplicity, we assume providing only region works if MI is correctly permissioned.
            return speech_config
        else:
            print("Speech Key or Region not found in environment variables or Key Vault. Speech services may fail.")
            return None
    except Exception as e:
        print(f"Error initializing SpeechConfig: {e}")
        return None

def get_speech_synthesizer(audio_output_path=None, speech_config_val=None, audio_config_val=None):
    """Initializes and returns the Azure Speech Synthesizer."""
    current_speech_config = speech_config_val if speech_config_val else get_speech_config()
    
    # Allow passing custom audio_config or create one from path if specified
    if audio_config_val is not None:
        # Handle the case where audio_config_val has use_default_speaker which isn't supported in the container
        if hasattr(audio_config_val, "use_default_speaker"):
            # Create a temporary file instead
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_audio_path = temp_file.name
            current_audio_config = AudioConfig(filename=temp_audio_path)
            print(f"Replaced use_default_speaker with file output: {temp_audio_path}")
        else:
            current_audio_config = audio_config_val
    elif audio_output_path:
        current_audio_config = AudioConfig(filename=audio_output_path)
    else:
        # For Streamlit, we want to get the audio data as bytes to play it with st.audio
        # Setting audio_config to None allows us to get the result as an in-memory stream (result.audio_data)
        current_audio_config = None

    speech_synthesizer = SpeechSynthesizer(speech_config=current_speech_config, audio_config=current_audio_config)
    return speech_synthesizer

def get_speech_recognizer(speech_config_val: SpeechConfig | None = None, audio_input_config: AudioConfig | None = None):
    """Initializes and returns the Azure Speech Recognizer.

    Args:
        speech_config_val: Optional pre-configured SpeechConfig.
        audio_input_config: Optional pre-configured AudioConfig for the input audio source.
                          If None, it implies the caller will handle audio input differently or it's not needed at init.
    """
    current_speech_config = speech_config_val if speech_config_val else get_speech_config()
    
    # If no audio_input_config is provided, the recognizer can be created
    # and then methods like recognize_once_async(audio_stream) can be used with PushAudioInputStream or PullAudioInputStream
    # or from a file with AudioConfig(filename="path_to_file.wav")
    # For flexibility, we allow audio_input_config to be None here.
    # The caller will be responsible for providing the correct AudioConfig based on the input source (file, stream, microphone).
    speech_recognizer = SpeechRecognizer(speech_config=current_speech_config, audio_config=audio_input_config)
    return speech_recognizer

def get_content_safety_client():
    """Initializes and returns the Azure Content Safety client."""
    from azure.core.credentials import AzureKeyCredential
    
    endpoint = os.getenv("AZURE_CONTENT_SAFETY_ENDPOINT")
    api_key = os.getenv("AZURE_CONTENT_SAFETY_KEY")
    
    if not endpoint:
        raise ValueError("AZURE_CONTENT_SAFETY_ENDPOINT environment variable is not set.")
    
    # Use API key if provided, otherwise use managed identity
    if api_key:
        credential = AzureKeyCredential(api_key)
        content_safety_client = ContentSafetyClient(endpoint=endpoint, credential=credential)
    else:
        # Fallback to managed identity
        credential = get_default_azure_credential()
        content_safety_client = ContentSafetyClient(endpoint=endpoint, credential=credential)
    
    return content_safety_client

# Example usage for local testing (ensure relevant environment variables are set)
if __name__ == '__main__':
    # Mock environment variables for local testing if not running in Azure
    # Replace with your actual service endpoints and keys for testing.
    os.environ.setdefault('AZURE_OPENAI_ENDPOINT', 'https://your-openai-service.openai.azure.com/')
    os.environ.setdefault('AZURE_SPEECH_KEY', 'your_speech_service_key')
    os.environ.setdefault('AZURE_SPEECH_REGION', 'eastus') # Or your speech service region
    os.environ.setdefault("AZURE_CONTENT_SAFETY_ENDPOINT", "https://your-contentsafety-service.cognitiveservices.azure.com/")
    print("Attempting to initialize Azure clients for local testing...")
    try:
        openai_client = get_azure_openai_client()
        print(f"OpenAI client initialized for endpoint: {openai_client.endpoint}")
        
        content_safety_client = get_content_safety_client()
        print(f"Content Safety client initialized for endpoint: {content_safety_client.endpoint}")

        # Test Speech Synthesizer
        # Note: Speech SDK operations (synthesis/recognition) are not performed in this block,
        # only client initialization is tested.
        speech_synthesizer = get_speech_synthesizer()
        print(f"Speech synthesizer initialized. Configured for region: {os.getenv('AZURE_SPEECH_REGION')}")
        
        # Test Speech Recognizer
        # speech_recognizer = get_speech_recognizer()
        # print(f"Speech recognizer initialized. Configured for region: {os.getenv('AZURE_SPEECH_REGION')}")
        print("\nTo fully test speech recognizer, you would call its methods with audio input.")

        print("\nAzure client initializations appear successful.")

    except ValueError as e:
        print(f"ERROR - Value Error during client initialization: {e}")
    except Exception as e:
        print(f"ERROR - An unexpected error occurred during client initialization: {e}")
