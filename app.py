from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    cred = credentials.Certificate("test-c071e-firebase-adminsdk-c1saq-600bcb5bfd.json")  # Replace with your Firebase credentials file
    firebase_admin.initialize_app(cred)

db = firestore.client()

def filter_valid_articles(articles):
    """
    Filter out articles with 'Removed' content or null fields.
    """
    filtered_articles = []
    for article in articles:
        if any(
            article.get(key) in [None, "[Removed]"]
            for key in ["author", "title", "description", "url", "content"]
        ):
            continue
        if article.get("source", {}).get("name") in [None, "[Removed]"]:
            continue
        filtered_articles.append(article)
    return filtered_articles

def format_date_to_midnight():
    """
    Return the current date with time set to 00:00:00.000 in the format YYYY-MM-DD HH:MM:SS.sss
    """
    return datetime.now().strftime("%Y-%m-%d") + " 00:00:00.000"

@app.route('/')
def hello_world():
    return 'Hello from Flask!'

@app.route('/api/update-news', methods=['POST'])
def update_news():
    try:
        # Check if the user input is 'set'
        user_input = request.json
        action = user_input.get("action")

        if action != "set":
            return jsonify({"error": "Invalid action. Use 'set' to update news."}), 400

        # Get yesterday's date
        yesterday = (datetime.now() - timedelta(1)).strftime("%Y-%m-%d")

        # Fetch data from the News API
        api_url = "https://newsapi.org/v2/everything"
        params = {
            "q": "Construction industry news india",  # Search query
            "from": yesterday,  # Start date (yesterday)
            "to": yesterday,  # End date (yesterday)
            "sortBy": "popularity",  # Sorting criteria
            "apiKey": "7670eff5bc174feda058ca8306bf7abe",  # Your News API key
        }
        response = requests.get(api_url, params=params)

        if response.status_code != 200:
            return jsonify({"error": f"News API error: {response.status_code}"}), 500

        news_data = response.json()
        articles = news_data.get("articles", [])

        # Filter the articles to remove invalid ones
        filtered_articles = filter_valid_articles(articles)

        if not filtered_articles:
            return jsonify({"error": "No valid articles to upload"}), 400

        # Upload filtered articles to Firebase Firestore
        news_collection = db.collection("news")
        for article in filtered_articles:
            # Add a custom date-time field with time set to midnight
            article['upload_date'] = format_date_to_midnight()

            # Upload article to Firestore
            doc_ref = news_collection.document()  # Generate a unique document ID
            doc_ref.set(article)

        return jsonify({"message": "News articles fetched and uploaded successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=6057)