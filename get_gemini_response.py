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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    logging.critical("Error: GEMINI_API_KEY environment variable not set. Exiting.")
    exit(1)
else:
    logging.info("GEMINI_API_KEY loaded successfully.")

# --- Client Initialization ---
try:
    logging.info("Initializing Google Gemini client...")
    client = genai.Client(api_key=GEMINI_API_KEY)
    logging.info("Gemini client initialized successfully.")
except Exception as e:
    logging.critical(f"Fatal Error: Could not initialize the Gemini client: {e}", exc_info=True)
    exit(1)

# --- Configuration for Intelligent Retries ---
MAX_RETRIES = 10
INITIAL_BACKOFF_SECONDS = 60
MAX_BACKOFF_SECONDS = 600

def get_gemini_response(prompt: str, model: str = 'gemini-2.5-flash') -> str:
    """
    Sends a prompt to the Google Gemini API using the Python SDK and returns the response.
    Includes an intelligent retry mechanism by inspecting exception messages for rate limit errors.
    """
    logging.info(f"Preparing to send prompt to Gemini model: '{model}'")
    # For security and cleaner logs, we'll log only a snippet of the prompt at INFO level
    logging.info(f"Prompt (first 70 chars): \"{prompt[:70].replace('\n', ' ')}...\"")
    logging.debug(f"Full prompt being sent:\n---\n{prompt}\n---")

    for attempt in range(MAX_RETRIES):
        try:
            logging.info(f"Attempt {attempt + 1}/{MAX_RETRIES}: Calling Gemini API...")
            
            # --- CORRECTED API CALL ---
            # You call generate_content directly on client.models and pass the model name
            # and contents as arguments, as shown in the official documentation.
            response = client.models.generate_content(
                model=model,
                contents=prompt # The SDK is smart enough to handle a simple string
            )
            
            logging.info(f"Attempt {attempt + 1}/{MAX_RETRIES}: API call successful. Received response.")
            
            if response.text:
                logging.info("Response contains text. Returning content.")
                return response.text.strip()
            else:
                logging.warning("Response received, but it contains no text. It may have been blocked by safety filters.")
                raise RuntimeError("API responded with no text content. Check safety settings or prompt feedback.")

        except Exception as e:
            error_message_upper = str(e).upper()
            
            if "429" in error_message_upper or "RESOURCE_EXHAUSTED" in error_message_upper:
                if attempt < MAX_RETRIES - 1:
                    backoff_time = min(INITIAL_BACKOFF_SECONDS * (2 ** attempt), MAX_BACKOFF_SECONDS)
                    jitter = random.uniform(0, 5)
                    wait_time = backoff_time + jitter
                    
                    logging.warning(
                        f"Attempt {attempt + 1}/{MAX_RETRIES}: Rate limit hit. "
                        f"Waiting for {wait_time:.2f} seconds before next retry."
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    logging.critical(f"Gemini API failed after {MAX_RETRIES} attempts due to persistent rate limiting.")
                    raise RuntimeError(f"Exhausted all retries due to persistent rate limiting.") from e
            else:
                logging.error(f"Attempt {attempt + 1}/{MAX_RETRIES}: A non-recoverable error occurred.", exc_info=True)
                raise RuntimeError(f"Gemini API call failed with a non-recoverable error: {e}") from e

    raise RuntimeError(f"Failed to get response for prompt after {MAX_RETRIES} attempts.")

# --- Example Usage ---
if __name__ == "__main__":
    logging.info("--- Starting Example Usage ---")
    my_prompt = "Tell me a short, inspiring story about a breakthrough in science."
    
    try:
        # NOTE: When running this file directly, you might need to adjust the model name
        # if your other scripts pass a different one.
        response = get_gemini_response(my_prompt, model='gemini-1.5-flash')
        logging.info("--- Gemini Response ---")
        print(response)
        logging.info("--- Example Usage Finished Successfully ---")
    except Exception as e:
        logging.error("--- An error occurred during the example usage ---")
        logging.error(e)