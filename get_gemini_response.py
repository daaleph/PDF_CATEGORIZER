#!/usr/bin/env python3
"""
Communicates with the Google Gemini API using the official Python SDK.
Enhanced with TASK-AWARE STRATEGIC MODEL ROTATION.
Maximizes Free Tier usage by exhausting model-specific quotas on the same Key before rotating Keys.
"""
import os
import time
import random
import logging
import requests
from dotenv import load_dotenv
import google.genai as genai

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables
logging.info("Loading environment variables from .env file...")
load_dotenv()

# --- SDK Configuration ---
GEMINI_API_KEY_N=os.getenv("GEMINI_API_KEY_N")
GEMINI_API_KEY_D=os.getenv("GEMINI_API_KEY_D")
GEMINI_API_KEY_DI=os.getenv("GEMINI_API_KEY_Di")
GEMINI_API_KEY_A=os.getenv("GEMINI_API_KEY_A")

# --- API Key Configuration ---
API_KEYS = [
    GEMINI_API_KEY_N,
    GEMINI_API_KEY_D,
    GEMINI_API_KEY_DI,
    GEMINI_API_KEY_A
]

if not all(API_KEYS):
    logging.warning("Warning: One or more API keys are missing.")

# --- LOCAL LLM FALLBACK CONFIGURATION ---
# This activates ONLY when all Gemini keys are exhausted.
LOCAL_LLM_CONFIG = {
    "enabled": True,  # Set to False to disable local fallback
    "provider": "ollama",
    "url": "http://localhost:11434/api/generate",
    # 'qwen3:1.7b' or 'qwen2.5:1.5b' fits easily in 16GB RAM on CPU
    "model": "qwen3:1.7b", 
    "timeout": 300  # 5 minutes timeout for slow CPU inference
}

# --- STRATEGIC MODEL SELECTION CONFIGURATION ---
# Define lists based on task complexity and cost (Free Tier logic).
# Order = Priority (Try first -> Try fallback -> Try last resort)

MODEL_STRATEGIES = {
    
    # Estrategia para pipe.py (Clasificación): 
    # Prioriza velocidad y modelos con alta cuota gratuita.
    "classification": [
        'gemini-2.5-flash',     # Rápido, inteligente, balanceado (Primary)
        'gemini-2.5-flash-lite', # Modelo liviano para evitar parada total (Emergency)
        'gemini-2.5-pro'        # Solo si todo lo demás falla (Last Resort)
    ],

    # Estrategia para segmentation_pipe.py (Segmentación): 
    # Prioriza precisión de sintaxis (JSON) y lógica.
    # NUNCA usa modelos 'lite' ya que suelen fallar en sintaxis estricta.
    "segmentation": [
        'gemini-2.5-flash',     # Primer intento (Rápido)
        'gemini-2.5-pro',       # Fallback para JSON crítico y lógica compleja (High Precision)
        'gemini-3-pro-preview'         # Fallback estable alternativo (Robust)
    ],
    
    # Estrategia por defecto (Balanceada)
    "default": [
        'gemini-2.5-flash',
        'gemini-2.5-pro'
    ]
}

# --- Retry Configuration ---
MAX_CYCLES = 10 
INITIAL_BACKOFF_SECONDS = 60
MAX_BACKOFF_SECONDS = 600

def get_local_response(prompt: str, system_instruction: str = None) -> str:
    """
    Queries the local Ollama instance. 
    This is the 'Final Resilience Layer'.
    """
    if not LOCAL_LLM_CONFIG["enabled"]:
        return None

    logging.info(f"Activating Local Fallback: Querying {LOCAL_LLM_CONFIG['model']} on CPU...")

    # Combine system and prompt for the local model context
    full_prompt = prompt
    if system_instruction:
        full_prompt = f"SYSTEM INSTRUCTION:\n{system_instruction}\n\nUSER PROMPT:\n{prompt}"

    try:
        payload = {
            "model": LOCAL_LLM_CONFIG["model"],
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "num_ctx": 8192  # Ensure context window is sufficient
            }
        }
        
        response = requests.post(
            LOCAL_LLM_CONFIG["url"], 
            json=payload, 
            timeout=LOCAL_LLM_CONFIG["timeout"]
        )
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result.get("response", "").strip()
            logging.info("SUCCESS: Local CPU Fallback returned a response.")
            return generated_text
        else:
            logging.error(f"Local LLM error: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to connect to Local LLM (Ollama): {e}")
        return None

def get_gemini_response(prompt: str, model: str = None, task_type: str = "default", system_instruction: str = None) -> str:
    """
    Sends a prompt to the Google Gemini API with Strategic Model Rotation.
    
    Args:
        prompt (str): The prompt text.
        model (str): Preferred starting model (optional, overrides strategy if needed).
        task_type (str): 'classification' or 'segmentation'. Defines the fallback chain.
    """
    
    # 1. Select Strategy
    strategy_list = MODEL_STRATEGIES.get(task_type, MODEL_STRATEGIES["default"])
    
    # 2. Ensure the requested model is tried first if provided and valid
    if model and model in strategy_list:
        strategy_list.remove(model)
        strategy_list.insert(0, model)
    elif model and model not in strategy_list:
        strategy_list.insert(0, model)

    logging.info(f"Task Type: '{task_type}'. Strategy Chain: {strategy_list}")

    cycle_count = 0
    total_keys = len(API_KEYS)

    while cycle_count < MAX_CYCLES:
        
        # --- Middle Loop: Iterate through API Keys ---
        for key_index, api_key in enumerate(API_KEYS):
            if not api_key:
                continue

            # --- Inner Loop: Iterate through Models (Strategic Fallback) ---
            for model_index, current_model in enumerate(strategy_list):
                
                try:
                    logging.info(
                        f"Cycle {cycle_count + 1} | Key {key_index + 1}/{total_keys} | "
                        f"Model [{model_index + 1}/{len(strategy_list)}]: '{current_model}'"
                    )
                    
                    client = genai.Client(api_key=api_key)
                    # Combine system instruction and prompt if instruction is present
                    final_contents = prompt
                    if system_instruction:
                        final_contents = f"SYSTEM INSTRUCTION:\n{system_instruction}\n\nUSER PROMPT:\n{prompt}"
                    
                    response = client.models.generate_content(
                        model=current_model,
                        contents=final_contents
                    )
                    
                    if response.text:
                        logging.info(f"SUCCESS with '{current_model}'.")
                        return response.text.strip()
                    else:
                        # Empty response (Safety), try next model in chain
                        logging.warning(f"Empty response from '{current_model}'. Rotating model...")
                        continue

                except Exception as e:
                    error_message_upper = str(e).upper()
                    
                    # Check for Rate Limit (429) or Resource Exhausted
                    if "429" in error_message_upper or "RESOURCE_EXHAUSTED" in error_message_upper:
                        logging.warning(
                            f"Quota Exhausted/429 for '{current_model}'. "
                            f"**Applying Strategic Rotation: Trying Next Model on SAME Key.**"
                        )
                        # This is the key logic: Rotate Model, NOT Key (yet)
                        time.sleep(1)
                        continue
                    else:
                        # Fatal errors (400, 401)
                        logging.error(f"Fatal error with '{current_model}'.", exc_info=True)
                        raise RuntimeError(f"API Call Failed: {e}") from e

        # --- Exhaustion Point ---
        # All models in strategy failed for all keys in this cycle.
        if cycle_count < MAX_CYCLES - 1:
            backoff_time = min(INITIAL_BACKOFF_SECONDS * (2 ** cycle_count), MAX_BACKOFF_SECONDS)
            jitter = random.uniform(0, 5)
            wait_time = backoff_time + jitter
            
            logging.critical(
                f"All strategies exhausted for all keys. "
                f"Waiting {wait_time:.2f} seconds before global retry."
            )
            time.sleep(wait_time)
        else:
            # RETRIES EXHAUSTED: ACTIVATE LOCAL FALLBACK
            logging.critical("All Cloud retries exhausted. Activating Local CPU Resilience Layer...")
            local_response = get_local_response(prompt, system_instruction)
            
            if local_response:
                return local_response
            else:
                raise RuntimeError("Exhausted all cloud retries and Local LLM failed or is disabled.")

        cycle_count += 1

    raise RuntimeError("Failed to get response.")