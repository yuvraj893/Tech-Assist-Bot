import re
import requests
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jobsearch.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

openai_api_key = 'sk-proj-rIG7qr4CB1ZF0GR43QCfT3BlbkFJmEuBtJfdhT2PdQ8ZshgO'

class UserQuery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.String(500), nullable=False)
    response = db.Column(db.String(2000), nullable=False)
    feedback = db.Column(db.String(20), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, nullable=True)

def generate_prompt(query):
    resume_keywords = ['resume', 'cv', 'curriculum vitae']
    interview_keywords = ['interview', 'questions', 'prep', 'preparation']
    networking_keywords = ['networking', 'network', 'connections', 'meetup', 'linkedin']

    if any(keyword in query.lower() for keyword in resume_keywords):
        return f"""
        You are a helpful assistant specialized in providing guidance for tech job seekers. Answer the following query with detailed, tech-specific information, tips, and links where applicable.

        **Resume Help:** Provide tips and advice on how to create a strong tech resume. Include details on important sections such as technical skills, projects, and certifications. Provide links to examples and templates where possible.

        Query: {query}

        Response:
        """
    elif any(keyword in query.lower() for keyword in interview_keywords):
        return f"""
        You are a helpful assistant specialized in providing guidance for tech job seekers. Answer the following query with detailed, tech-specific information, tips, and links where applicable.

        **Interview Tips:** Offer advice on how to prepare for technical interviews. Cover common questions, coding challenges, and behavioral interview tips. Provide links to resources for practicing coding problems and mock interviews.

        Query: {query}

        Response:
        """
    elif any(keyword in query.lower() for keyword in networking_keywords):
        return f"""
        You are a helpful assistant specialized in providing guidance for tech job seekers. Answer the following query with detailed, tech-specific information, tips, and links where applicable.

        **Networking Strategies:** Give guidance on how to build and expand a professional network in the tech industry. Suggest strategies for using LinkedIn, attending meetups, and participating in online communities. Provide links to relevant articles and resources.

        Query: {query}

        Response:
        """
    else:
        return f"""
        You are a helpful assistant specialized in providing guidance for tech job seekers. Answer the following query with detailed, tech-specific information, tips, and links where applicable.

        Query: {query}

        Response:
        """

def analyze_query(text):
    try:
        prompt = generate_prompt(text)
        headers = {
            'Authorization': f'Bearer {openai_api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            'model': 'gpt-3.5-turbo',
            'messages': [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            'temperature': 0.7
        }
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data
        )
        response_json = response.json()
        print(f"Full API response: {response_json}")  # Log the full response

        if response.status_code != 200:
            return f"Error: {response_json.get('error', 'Unknown error')}"

        generated_text = response_json['choices'][0]['message']['content'].strip()
        
        # Properly format response with HTML for new lines and lists
        formatted_response = generated_text.replace('\n', '<br>')
        
        # Add formatting for numbered lists
        formatted_response = re.sub(r'(\d+)\.', r'<br>\1.', formatted_response)
        
        return formatted_response
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return "Sorry, there was a network error. Please try again later."
    except Exception as e:
        print(f"Error analyzing query: {e}")
        return "Sorry, I couldn't process your request at the moment."

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get', methods=['POST'])
def get_bot_response():
    user_input = request.form['user_input']
    print(f"User input: {user_input}")  # Log user input
    
    greeting_keywords = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]
    if any(keyword in user_input.lower() for keyword in greeting_keywords):
        response = "Hello! How can I assist you today?"
    else:
        response = analyze_query(user_input)
    
    print(f"Response: {response}")  # Log response
    new_query = UserQuery(query=user_input, response=response)
    db.session.add(new_query)
    db.session.commit()
    return jsonify(response)

@app.route('/suggest', methods=['POST'])
def suggest():
    query = request.form['query']
    suggestions = ["How to make a resume?", "Tips for job interviews", "Networking strategies"]
    filtered_suggestions = [s for s in suggestions if query.lower() in s.lower()]
    return jsonify({"suggestions": filtered_suggestions})

@app.route('/feedback', methods=['POST'])
def feedback():
    try:
        feedback_type = request.form['feedback']
        user_input = request.form['user_input']
        print(f"Received feedback: {feedback_type} for input: {user_input}")
        
        user_query = db.session.query(UserQuery).filter(UserQuery.query == user_input).order_by(UserQuery.id.desc()).first()
        if user_query:
            user_query.feedback = feedback_type
            db.session.commit()
            return jsonify({'message': 'Thank you for your feedback'}), 200
        else:
            return jsonify({'message': 'Query not found'}), 404
    except Exception as e:
        print(f"Error processing feedback: {e}")
        return jsonify({'message': 'Failed to process feedback'}), 500

@app.route('/analytics')
def analytics():
    frequent_queries = db.session.execute("""
        SELECT query, COUNT(*) as query_count
        FROM user_query
        GROUP BY query
        ORDER BY query_count DESC
        LIMIT 10
    """).fetchall()
    return render_template('analytics.html', frequent_queries=frequent_queries)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
