#!/usr/bin/env python3
"""
Communicates with the Google Gemini API using the official Python SDK.
This version includes detailed logging, handles rate limit retries, and uses 
the correct client initialization and API call patterns.
"""
import os
import time
import random
import logging
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
GEMINI_API_KEY_M=os.getenv("GEMINI_API_KEY_M")
GEMINI_API_KEY_D=os.getenv("GEMINI_API_KEY_D")
GEMINI_API_KEY_N_1=os.getenv("GEMINI_API_KEY_N_1")
GEMINI_API_KEY_N_P1=os.getenv("GEMINI_API_KEY_N_P1")
GEMINI_API_KEY_U1=os.getenv("GEMINI_API_KEY_U1")
GEMINI_API_KEY_U2=os.getenv("GEMINI_API_KEY_U2")
GEMINI_API_KEY_N_2=os.getenv("GEMINI_API_KEY_N_2")
GEMINI_API_KEY_N_P2=os.getenv("GEMINI_API_KEY_N_P2")
GEMINI_API_KEY_N_3=os.getenv("GEMINI_API_KEY_N_3")
GEMINI_API_KEY_N_P3=os.getenv("GEMINI_API_KEY_N_P3")

# --- API Key Configuration ---
# The list of keys provided in the prompt, mapped in sequential order.
API_KEYS = [
    GEMINI_API_KEY_M,
    GEMINI_API_KEY_D,
    GEMINI_API_KEY_N_1,
    GEMINI_API_KEY_N_P1,
    GEMINI_API_KEY_U1,
    GEMINI_API_KEY_U2,
    GEMINI_API_KEY_N_2,
    GEMINI_API_KEY_N_P2,
    GEMINI_API_KEY_N_3,
    GEMINI_API_KEY_N_P3
]

if not GEMINI_API_KEY_M and GEMINI_API_KEY_N_1 and GEMINI_API_KEY_N_P1 and GEMINI_API_KEY_N_2 and GEMINI_API_KEY_N_P2 and GEMINI_API_KEY_N_3 and GEMINI_API_KEY_N_P3=os.getenv("GEMINI_API_KEY_N_P3"):
    logging.critical("Error: API_KEYS list is not full. Exiting.")
    exit(1)
else:
    logging.info(f"Loaded {len(API_KEYS)} API keys for rotation.")

# --- Configuration for Intelligent Retries ---
MAX_CYCLES = 10 
INITIAL_BACKOFF_SECONDS = 60
MAX_BACKOFF_SECONDS = 600

def get_gemini_response(prompt: str, model: str = 'gemini-2.5-flash') -> str:
    """
    Sends a prompt to the Google Gemini API.
    Implements round-robin rotation of API keys on rate limit errors.
    """
    logging.info(f"Preparing to send prompt to Gemini model: '{model}'")
    logging.info(f"Prompt (first 70 chars): \"{prompt[:70].replace('\n', ' ')}...\"")
    logging.debug(f"Full prompt being sent:\n---\n{prompt}\n---")

    cycle_count = 0
    total_keys = len(API_KEYS)

    # Outer loop: Handles waiting (backoff) after exhausting all keys
    while cycle_count < MAX_CYCLES:
        
        # Inner loop: Iterates through available keys
        for key_index, api_key in enumerate(API_KEYS):
            
            try:
                logging.info(f"Cycle {cycle_count + 1}/{MAX_CYCLES} | Key {key_index + 1}/{total_keys}: Calling Gemini API...")
                
                # Initialize a fresh client for this specific key
                client = genai.Client(api_key=api_key)
                
                # API Call
                response = client.models.generate_content(
                    model=model,
                    contents=prompt
                )
                
                logging.info(f"Cycle {cycle_count + 1}/{MAX_CYCLES} | Key {key_index + 1}/{total_keys}: API call successful.")
                
                if response.text:
                    logging.info("Response contains text. Returning content.")
                    return response.text.strip()
                else:
                    logging.warning("Response received, but it contains no text. It may have been blocked by safety filters.")
                    raise RuntimeError("API responded with no text content. Check safety settings or prompt feedback.")

            except Exception as e:
                error_message_upper = str(e).upper()
                
                # Check for Rate Limit (429) or Resource Exhausted
                if "429" in error_message_upper or "RESOURCE_EXHAUSTED" in error_message_upper:
                    logging.warning(
                        f"Cycle {cycle_count + 1} | Key {key_index + 1}: Rate limit hit. "
                        f"Switching to next key immediately."
                    )
                    # Continue to the next iteration of the for-loop (next key)
                    time.sleep(2)
                    continue
                else:
                    # Non-recoverable error (e.g., 400 Bad Request, 401 Invalid Key)
                    logging.error(f"A non-recoverable error occurred with Key {key_index + 1}.", exc_info=True)
                    raise RuntimeError(f"Gemini API call failed with a non-recoverable error: {e}") from e

        # --- If we reach this point, the 'for' loop finished without returning ---
        # This means ALL keys in the list have hit their rate limit in this cycle.
        
        if cycle_count < MAX_CYCLES - 1:
            backoff_time = min(INITIAL_BACKOFF_SECONDS * (2 ** cycle_count), MAX_BACKOFF_SECONDS)
            jitter = random.uniform(0, 5)
            wait_time = backoff_time + jitter
            
            logging.critical(
                f"All {total_keys} API keys exhausted in Cycle {cycle_count + 1}. "
                f"Waiting {wait_time:.2f} seconds before restarting from Key 1."
            )
            time.sleep(wait_time)
        else:
            logging.critical(f"All API keys failed after {MAX_CYCLES} full cycles.")
            raise RuntimeError(f"Exhausted all retries. All {total_keys} keys persistently rate-limited.")

        cycle_count += 1

    raise RuntimeError(f"Failed to get response for prompt after {MAX_CYCLES} cycles.")
