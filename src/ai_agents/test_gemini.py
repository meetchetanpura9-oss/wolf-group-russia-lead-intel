import os

from dotenv import load_dotenv
from google import genai

load_dotenv()


def main():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing from .env")

    print("Gemini API key detected.")
    print(f"Key prefix: {api_key[:3]}")
    print(f"Key length: {len(api_key)}")
    print("Calling Gemini...")

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents="Reply with exactly: Gemini connection successful"
    )

    print("Gemini response:")
    print(response.text)


if __name__ == "__main__":
    main()
