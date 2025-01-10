from dotenv import load_dotenv
from openai import OpenAI
import os

# Load environment variables from .env file
load_dotenv()

def process_with_chatgpt(thread_data):
    """Send the thread data to ChatGPT and return the response."""
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an award winning Quality Assurance engineer."},
            {
                "role": "user",
                "content": f"Write a draft bug ticket based on the data in this Slack thread: {thread_data}. "
                           f"Include the following sections: current state, ideal state, steps to reproduce, references, and notes."
                           f"Do not use any bold formatting."
                           f"Only use Markdown formatting for hyperlinks (e.g., [link text](url)) so that text like 'Loom Video' or 'Dashboard Link' becomes clickable."
                           f"The first sentence will be the title, and should be less than 45 characters long. Do not mention that it's the title."
                           f"Ensure clarity, avoid complex or industry-specific jargon, and use concise, pithy language."
            }
        ]
    )
    print(completion)
    return completion.choices[0].message.content