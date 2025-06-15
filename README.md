# AI Language Learning Companion 🚀🌍

Welcome to the AI Language Learning Companion! This application translates English text into a variety of target languages and provides audio playback of the translation, serving as an interactive tool for language learners.

The project leverages Azure AI services for its core functionalities and is designed to be deployed as a containerized application.

**🌐 LIVE APPLICATION URL (if deployed via `deploy-fixed-complete.ps1` or similar):**
`http://[YOUR_ACI_NAME].[YOUR_REGION].azurecontainer.io:8000` (Replace placeholders with your ACI details)

**(Note: The initial section of your README regarding deployment status and options is very useful; I'll retain its essence but integrate it into a more standard README flow below.)**

## Table of Contents
- [Key Features](#key-features-)
- [Technology Stack](#technology-stack-)
- [Architecture Diagram](#architecture-diagram-)
- [Project Structure](#project-structure-)
- [Application Architecture](#application-architecture-)
- [Application Flow](#application-flow-)
- [Azure Infrastructure Setup (Terraform)](#azure-infrastructure-setup-terraform-)
- [Local Development & Deployment](#local-development--deployment-)
- [Contributing](#contributing-)

## Key Features ✨

*   **Text Translation:** Utilizes Azure OpenAI Service to translate English input text into multiple supported languages.
*   **Speech Synthesis:** Employs Azure AI Speech Service to generate natural-sounding audio for the translated text.
*   **Content Moderation:** Integrates Azure Content Safety to analyze input text and prevent the processing of harmful content.
*   **Interactive UI:** Built with Streamlit for a user-friendly web interface.
*   **Stateful AI Orchestration:** Uses LangGraph to manage the sequence of AI operations (moderation, translation, speech synthesis) in a structured manner.

## Technology Stack 🛠️

This project is built using a combination of modern technologies and cloud services:

*   **Python:** The core programming language for the backend logic and AI integrations.
*   **Streamlit:** A Python framework for building and sharing web apps for data science and machine learning projects. Used here for the frontend UI.
*   **LangGraph:** A library for building stateful, multi-actor applications with Large Language Models (LLMs). It helps define and execute the AI pipeline as a graph.
*   **Azure AI Services:**
    *   **Azure OpenAI Service:** Provides access to powerful language models (e.g., GPT-4o) for translation capabilities.
    *   **Azure AI Speech Service:** Offers text-to-speech (TTS) capabilities to convert translated text into audio.
    *   **Azure Content Safety:** A service to detect and moderate potentially harmful user-generated content.
*   **Docker:** A containerization platform used to package the application and its dependencies, ensuring consistency across different environments.
*   **Azure Container Instances (ACI):** A serverless Azure service to run Docker containers without managing underlying infrastructure. Used for hosting the application.
*   **Azure Container Registry (ACR):** A private Docker registry service in Azure to store and manage container images.
*   **Terraform:** An Infrastructure as Code (IaC) tool to define, provision, and manage the Azure resources (ACI, ACR, AI services, Key Vault, etc.) declaratively.
*   **GitHub & Git:** For version control, collaboration, and potentially CI/CD (via GitHub Actions).

## Architecture Diagram 🖼️

Below is a visual representation of the application's architecture:

![AI Language Learning App Architecture](./docs/images/MultiAgentArchitecture-AI%20Based%20Language%20Learn%20App.png)

## Project Structure 📁

The project is organized as follows:

```
ai-language-learning-app/
│
├── app/  # Contains the core application code
│   ├── main.py
│   └── core/
│       ├── __init__.py
│       ├── azure_clients.py
│       ├── constants.py
│       └── langgraph_agent.py
│
├── docs/ # Documentation and related assets
│   └── images/
│       └── MultiAgentArchitecture-AI Based Language Learn App.png
│
├── scripts/ # Contains ALL operational scripts (PowerShell, Python, Shell)
│   ├── deploy-aci-acr-build.template.ps1
│   ├── deploy-fixed-complete.template.ps1
│   ├── deploy-with-credentials.template.ps1
│   ├── ... (all other .ps1 deployment and utility scripts)
│   │
│   ├── check-deployment-status.py  # Utility: Checks status of deployed Azure resources
│   ├── deploy.py                   # Utility: Python-based deployment helper script
│   ├── diagnostic_page.py          # Utility: Streamlit page for app diagnostics
│   ├── run_diagnostics.py          # Utility: Script to run various diagnostic checks
│   ├── startup.sh                  # Utility: Startup script (e.g., for Docker container)
│   └── ... (any other .py utility scripts)
│
├── terraform/  # Infrastructure as Code (IaC) using Terraform
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
│
├── tests/ # Contains test scripts and related files
│   ├── test_fixes.py
│   ├── test_langgraph.py
│   ├── test_speech_synthesis.py
│   ├── test_translation.py
│   └── ... (other test_*.py files)
│
├── .env.example                # Example environment file
├── .gitignore                  # Specifies intentionally untracked files
├── docker-compose.yml          # Docker Compose configuration
├── Dockerfile                  # Instructions to build the Docker container image
├── README.md                   # This documentation file
├── requirements.txt            # Python package dependencies
└── ... (other configuration files like .gitattributes, etc.)
```

**Note on PowerShell Deployment Scripts:**
Deployment scripts are located in the `/scripts` folder. The versions that might contain sensitive information (like API keys or specific endpoints) are provided as `.template.ps1` files.
To use them:
1.  Copy the desired `.template.ps1` file from the `scripts/` folder (e.g., `scripts/deploy-fixed-complete.template.ps1` to `scripts/deploy-fixed-complete.ps1`).
2.  Edit the new file (e.g., `scripts/deploy-fixed-complete.ps1`) and fill in your actual secrets and configuration values in the designated placeholder sections.
3.  The original filenames (e.g., `scripts/deploy-fixed-complete.ps1`) are included in `.gitignore` to prevent accidental check-in of your local versions containing secrets.

**Note on Docker Compose Override:**
The `docker-compose.override.yml` file is intentionally gitignored. You should create this file locally to provide your actual secrets and environment-specific configurations for Docker Compose, overriding or extending the base `docker-compose.yml`.

## Application Architecture 🏗️

The application follows a client-server architecture:

1.  **Frontend (Client-Side):**
    *   A web interface built with **Streamlit**, running in the user's browser.
    *   Collects user input (text to translate, target language).
    *   Displays translated text and provides an audio player.

2.  **Backend (Server-Side):**
    *   A **Python application** (orchestrated by `app/main.py` and `app/core/langgraph_agent.py`).
    *   Hosted as a Docker container in **Azure Container Instances (ACI)**.
    *   **LangGraph** manages the flow of operations:
        1.  Receives input text from the frontend.
        2.  Calls **Azure Content Safety** to moderate the input.
        3.  If safe, calls **Azure OpenAI Service** for translation.
        4.  Calls **Azure AI Speech Service** to synthesize audio from the translated text.
        5.  Returns the translated text and audio data to the frontend.

3.  **Azure Services:**
    *   **ACR** stores the Docker image.
    *   **Azure Key Vault** (recommended, managed by Terraform) securely stores API keys and other secrets needed by the backend.
    *   Other **Azure AI services** (OpenAI, Speech, Content Safety) provide the core AI functionalities.

## Application Flow 🔄

1.  **User Interaction:** The user selects a target language and enters English text into the Streamlit frontend.
2.  **API Request:** Upon submission, the frontend sends an HTTP request to the backend API (hosted on ACI).
3.  **Content Moderation:** The backend, via the LangGraph agent, first sends the input text to Azure Content Safety.
    *   If flagged as harmful, an error is returned to the user.
4.  **Translation:** If the content is safe, the text is sent to Azure OpenAI Service for translation into the selected language.
5.  **Speech Synthesis:** The translated text is then sent to Azure AI Speech Service to generate audio data.
6.  **API Response:** The backend returns the translated text and the audio data (e.g., as base64 encoded bytes or a playable format) to the frontend.
7.  **Display Results:** The Streamlit frontend displays the translated text and provides an audio player for the synthesized speech.

## Azure Infrastructure Setup (Terraform) ⚙️

The Azure infrastructure is provisioned using Terraform. The configuration files are located in the `/terraform` directory.

**Key Resources Managed by Terraform:**
*   Azure Resource Group
*   Azure Container Registry (ACR)
*   Azure Container Instances (ACI) - for deploying the application container
*   Azure OpenAI Service instance & deployment (e.g., for GPT-4o)
*   Azure AI Speech Service instance
*   Azure Content Safety instance
*   Azure Key Vault (for storing secrets like API keys)
*   Associated roles and permissions for services to interact securely.

### Steps to Provision Infrastructure:

1.  **Prerequisites:**
    *   Azure Subscription
    *   Azure CLI installed and configured (`az login`)
    *   Terraform CLI installed
2.  **Navigate to Terraform Directory:**
    ```bash
    cd terraform
    ```
3.  **Initialize Terraform:**
    Downloads necessary providers.
    ```bash
    terraform init
    ```
4.  **Create `terraform.tfvars` (Optional but Recommended):**
    To customize variables (e.g., resource names, location), create a `terraform.tfvars` file in the `/terraform` directory. Refer to `variables.tf` for available variables.
    Example `terraform.tfvars`:
    ```hcl
    resource_group_name = "ai-lang-app-rg-dev"
    location            = "East US"
    app_name            = "ailangappdev" // Prefix for many resources
    # Add other variable overrides as needed
    ```
5.  **Plan Infrastructure Changes:**
    Preview the resources Terraform will create/modify.
    ```bash
    terraform plan -out=tfplan
    ```
6.  **Apply Infrastructure Changes:**
    Provision the resources in Azure.
    ```bash
    terraform apply "tfplan"
    ```
    Confirm by typing `yes` when prompted. Note the outputs from Terraform, as they may contain important information like Key Vault URIs or service endpoints.

## Local Development & Deployment 🚀

### Prerequisites:
*   Python (3.9+ recommended)
*   Docker Desktop (for containerized development/deployment)
*   Git
*   Azure CLI
*   PowerShell (if using `.ps1` deployment scripts on Windows)
*   An `.env` file in the project root with necessary API keys and endpoints (see `.env.example`).

### Option 1: Local Streamlit Development (Without Docker)
1.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/macOS
    # venv\\Scripts\\activate    # Windows
    ```
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Set up your `.env` file:**
    Copy `.env.example` to `.env` and fill in your Azure service credentials and endpoints.
4.  **Run the Streamlit app:**
    ```bash
    streamlit run app/main.py
    ```
    The application should be accessible at `http://localhost:8501` (or the port Streamlit indicates).

### Option 2: Local Docker Development
1.  Ensure Docker Desktop is running.
2.  Set up your `.env` file (as above). 
3.  For Docker Compose, the main `docker-compose.yml` now uses placeholders (e.g., `${AZURE_OPENAI_ENDPOINT:-<YOUR_AZURE_OPENAI_ENDPOINT>}`). You have two main ways to provide these values for local development:
    *   **Using an `.env` file (Recommended for many variables):** Docker Compose automatically picks up variables from an `.env` file in the project root. Your application inside the container can also load this `.env` file if `python-dotenv` is used.
    *   **Using `docker-compose.override.yml` (Good for overriding or adding services/configs locally):** Create a `docker-compose.override.yml` file (this file is in `.gitignore`). In this file, you can specify the actual values for environment variables or override other settings. For example:
        ```yaml
        # docker-compose.override.yml (This file is gitignored)
        version: '3.8'
        services:
          ai-language-app:
            environment:
              - AZURE_OPENAI_ENDPOINT=https://your-actual-openai-resource.openai.azure.com/
              - AZURE_OPENAI_API_KEY=your_actual_openai_api_key
              - AZURE_SPEECH_REGION=your_speech_region
              - AZURE_SPEECH_KEY=your_actual_speech_key
              - KEY_VAULT_URI=https://your-actual-kv.vault.azure.net/
              - AZURE_CONTENT_SAFETY_ENDPOINT=https://your-actual-cs-endpoint.cognitiveservices.azure.com/
              - AZURE_CONTENT_SAFETY_KEY=your_actual_cs_key
              - APPLICATIONINSIGHTS_CONNECTION_STRING=your_actual_appinsights_connection_string
            # You can also override other settings like ports or volumes here for local dev
        ```
4.  Build and run with Docker Compose:
    ```bash
    docker-compose up --build
    ```
    The application should be accessible at `http://localhost:8000` (or the port specified in your `docker-compose.yml`).

### Option 3: Deploy to Azure Container Instances (ACI)
This is the primary cloud deployment method for this project.
1.  **Ensure Azure infrastructure is provisioned via Terraform.** This includes ACR.
2.  **Authenticate Docker with ACR:**
    ```bash
    az acr login --name <your_acr_name>
    ```
3.  **Build the Docker Image:**
    ```bash
    docker build -t <your_acr_name>.azurecr.io/ai-language-app:latest .
    ```
4.  **Push the Image to ACR:**
    ```bash
    docker push <your_acr_name>.azurecr.io/ai-language-app:latest
    ```
5.  **Deploy to ACI:**
    You can use Azure CLI commands or the provided PowerShell scripts (e.g., `deploy-fixed-complete.ps1` or `deploy-aci-acr-build.ps1`). These scripts typically handle:
    *   Building the image (optionally via `az acr build`).
    *   Pushing to ACR.
    *   Creating or updating the ACI container group, ensuring environment variables (API keys, endpoints from your `.env` or Key Vault) are correctly configured for the container.
    Example using a script:
    ```powershell
    # Ensure script variables (resource group, ACR name, ACI name, image tag, env vars) are correct
    .\deploy-fixed-complete.ps1
    ```
    The script should output the public IP address or FQDN of your ACI.

## Contributing 🤝

Contributions are welcome! If you have improvements, bug fixes, or new features:

1.  **Fork the repository** on GitHub.
2.  **Create a new branch** for your feature or fix (`git checkout -b feature/your-feature-name`).
3.  **Make your changes** and commit them with clear, descriptive messages.
4.  **Test your changes** thoroughly.
5.  **Push your branch** to your forked repository (`git push origin feature/your-feature-name`).
6.  **Open a Pull Request** against the `main` branch of the original repository. Provide a detailed description of your changes.

---

This AI Language Learning Companion aims to be a helpful tool. We hope you find it useful and enjoy exploring its capabilities!
