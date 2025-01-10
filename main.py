import slack
import os
import time
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from slackeventsapi import SlackEventAdapter
from ChatGPT_stuff import process_with_chatgpt
from notioncode import create_notion_page
from fetchname import fetch_users_list, get_real_name  # Import functions from fetchname.py
import re

# Load environment variables
load_dotenv()

# Initialize Flask app and Slack Event Adapter
app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(
    os.environ['SIGNING_SECRET'], '/slack/events', app
)

# Slack client setup
client = slack.WebClient(token=os.environ['SLACK_TOKEN'])
BOT_ID = client.api_call("auth.test")['user_id']

# Notion constants
NOT_STARTED_STATUS_ID = "304e7960-6892-4246-ba10-e6872008dc49"

# Cache processed event IDs to avoid duplicate handling
processed_event_ids = set()


def fetch_thread_messages(channel_id, thread_ts):
    """Fetch all messages in a thread."""
    try:
        response = client.conversations_replies(channel=channel_id, ts=thread_ts)
        messages = response.get("messages", [])
        return messages
    except Exception as e:
        print(f"Error fetching thread messages: {e}")
        return []

'''
def extract_links_and_clean(messages):
    """Clean and extract links from Slack messages."""
    links = []
    cleaned_messages = []

    for message in messages:
        text = message.get("text", "")
        # Extract dashboard links
        dashboard_link_pattern = r"(https?://app\.podscribe\.ai[^\s]*)"
        links.extend(re.findall(dashboard_link_pattern, text))

        # Format Slack rich text links into plain text
        link_pattern = r"<(https?://[^|]+)\|([^>]+)>"
        text = re.sub(link_pattern, r"\2: \1", text)

        cleaned_messages.append({"text": text})

    return cleaned_messages, links
'''

def extract_links_and_clean(messages):
    """Clean and extract links from Slack messages."""
    links = []
    cleaned_messages = []

    for message in messages:
        text = message.get("text", "")
        # Extract dashboard links
        dashboard_link_pattern = r"(https?://app\.podscribe\.ai[^ \n]*)"
        links.extend(re.findall(dashboard_link_pattern, text))

        # Format Slack rich text links into plain text
        link_pattern = r"<(https?://[^|]+)\|([^>]+)>"
        text = re.sub(link_pattern, r"\1", text)  # Replace rich text links with raw links

        cleaned_messages.append({"text": text})

    # Remove duplicates and sanitize links
    links = list(set(link.strip() for link in links))
    return cleaned_messages, links


def format_data_for_processing(messages, links, user_name):
    """Format Slack thread data for processing."""
    formatted_messages = "\n".join(
        f"- {msg['text']}" for msg in messages if msg.get("text")
    )
    formatted_links = "\n".join(f"- Dashboard Link: {link}" for link in links)
    user_info = f"Reported by: {user_name}\n"
    return f"{user_info}{formatted_messages}\n\n{formatted_links}" if links else f"{user_info}{formatted_messages}"

def create_notion_ticket(chatgpt_response, user_name):
    """Extract title and create a Notion ticket."""
    lines = chatgpt_response.split("\n")
    title = lines[0][:50] if lines else "Untitled"  # Extracts the first line as the title.
    description = chatgpt_response  # Passes the full ChatGPT response as the description.
    notion_link = create_notion_page(title, description, NOT_STARTED_STATUS_ID, user_name)
    return notion_link

import time

def post_to_slack_with_retry(channel, text, thread_ts, max_retries=5, delay=5):
    """
    Posts a message to Slack with a retry mechanism for rate-limited responses.

    Args:
        channel (str): Slack channel ID.
        text (str): Message text to post.
        thread_ts (str): Thread timestamp to post the message in a thread.
        max_retries (int): Maximum number of retry attempts.
        delay (int): Delay in seconds between retries.

    Returns:
        None
    """
    for attempt in range(max_retries):
        try:
            response = client.chat_postMessage(channel=channel, text=text, thread_ts=thread_ts)
            if response["ok"]:
                return  # Successfully posted message
        except Exception as e:
            error_message = str(e)
            if 'ratelimited' in error_message.lower():
                print(f"Rate limit hit. Retrying in {delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                print(f"Failed to post to Slack: {e}")
                return
    print(f"Exceeded maximum retries. Could not post message: {text}")


@slack_event_adapter.on("message")
def handle_message(payload):
    """Handle incoming Slack messages."""
    event = payload.get("event", {})
    event_id = payload.get("event_id")
    channel_id = event.get("channel")
    user_id = event.get("user")  # Slack user ID of the sender
    text = event.get("text", "").lower()
    ts = event.get("ts")
    thread_ts = event.get("thread_ts", ts)

    # Skip if event already processed
    if event_id in processed_event_ids:
        return
    processed_event_ids.add(event_id)

    # Fetch user list and get real name
    users_dict = fetch_users_list()  # Fetch Slack user details
    user_name = get_real_name(user_id, users_dict)  # Get real name of the sender

    # Process only messages directed to the bot with specific keywords
    if BOT_ID != user_id and all(keyword in text for keyword in ["jarvis", "ticket", "please"]):
        print(f"Processing Slack thread reported by {user_name}...")

        # Fetch thread messages
        messages = fetch_thread_messages(channel_id, thread_ts)

        # Clean and extract links
        cleaned_messages, dashboard_links = extract_links_and_clean(messages)

        # Format data for ChatGPT
        formatted_data = format_data_for_processing(cleaned_messages, dashboard_links, user_name)
        print(f"Formatted Slack Thread Data:\n{formatted_data}")

        # Get ChatGPT response
        chatgpt_response = process_with_chatgpt(formatted_data)
        print(f"ChatGPT Response:\n{chatgpt_response}")

        # Create Notion ticket and pass user_name
        notion_link = create_notion_ticket(chatgpt_response, user_name)  # Fixed call

        # Notify Slack
        if notion_link:
            post_to_slack_with_retry(
                channel=channel_id,
                text=f"🎉 Notion ticket created: {notion_link}",
                thread_ts=thread_ts
            )
        else:
            post_to_slack_with_retry(
                channel=channel_id,
                text="🚨 Failed to create Notion ticket. Check logs.",
                thread_ts=thread_ts
            )


'''
@slack_event_adapter.on("message")
def handle_message(payload):
    """Handle incoming Slack messages."""
    event = payload.get("event", {})
    event_id = payload.get("event_id")
    channel_id = event.get("channel")
    user_id = event.get("user")  # Slack user ID of the sender
    text = event.get("text", "").lower()
    ts = event.get("ts")
    thread_ts = event.get("thread_ts", ts)

    # Skip if event already processed
    if event_id in processed_event_ids:
        return
    processed_event_ids.add(event_id)

    # Fetch user list and get real name
    users_dict = fetch_users_list()  # Fetch Slack user details
    user_name = get_real_name(user_id, users_dict)  # Get real name of the sender

    # Process only messages directed to the bot with specific keywords
    if BOT_ID != user_id and all(keyword in text for keyword in ["jarvis", "ticket", "please"]):
        print(f"Processing Slack thread reported by {user_name}...")

        # Fetch thread messages
        messages = fetch_thread_messages(channel_id, thread_ts)

        # Clean and extract links
        cleaned_messages, dashboard_links = extract_links_and_clean(messages)

        # Format data for ChatGPT
        formatted_data = format_data_for_processing(cleaned_messages, dashboard_links, user_name)
        print(f"Formatted Slack Thread Data:\n{formatted_data}")

        # Get ChatGPT response
        chatgpt_response = process_with_chatgpt(formatted_data)
        print(f"ChatGPT Response:\n{chatgpt_response}")

        # Create Notion ticket and pass user_name
        notion_link = create_notion_ticket(chatgpt_response, user_name)  # Fixed call

        # Notify Slack
        if notion_link:
            client.chat_postMessage(
                channel=channel_id,
                text=f"🎉 Notion ticket created: {notion_link}",
                thread_ts=thread_ts
            )
        else:
            client.chat_postMessage(
                channel=channel_id,
                text="🚨 Failed to create Notion ticket. Check logs.",
                thread_ts=thread_ts
            )
'''


@app.route("/slack/events", methods=["POST"])
def handle_slack_event():
    """Endpoint for Slack events."""
    data = request.get_json()
    if "challenge" in data:  # Respond to Slack verification
        return jsonify({"challenge": data["challenge"]})
    return jsonify({"status": "OK"}), 200


if __name__ == "__main__":
    app.run(port=5000)
