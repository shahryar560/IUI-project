from flask import Flask, request, render_template, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import csv
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///deskfit.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY') or 'you-will-never-guess'

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    sex = db.Column(db.String(10), nullable=True)
    weight = db.Column(db.Float, nullable=True)
    height = db.Column(db.Float, nullable=True)
    age = db.Column(db.Integer, nullable=True)
    goal = db.Column(db.String(50), nullable=True)
    theme = db.Column(db.String(20), nullable=False, default="light")  # New field for theme
    font_size = db.Column(db.String(20), nullable=False, default="medium")  # New field for font size
    accent_color = db.Column(db.String(20), nullable=False, default="#007bff")  # New field for accent color


class Meal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(100))
    calories = db.Column(db.Float)
    grams = db.Column(db.Float)
    timestamp = db.Column(db.Date, default=datetime.utcnow)

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    duration_minutes = db.Column(db.Float)
    calories_burned = db.Column(db.Float)
    timestamp = db.Column(db.Date, default=datetime.utcnow)

class WaterLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    amount_ml = db.Column(db.Float)
    timestamp = db.Column(db.Date, default=datetime.utcnow)

class Food(db.Model):  # Database for storing food items
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    calories_per_gram = db.Column(db.Float)

# Load food database from CSV file
def load_food_database():
    with open('calories.csv', newline='', encoding='ISO-8859-1') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                food_name = row['FoodItem']
                calories_per_100g = float(row['Cals_per100grams'].replace(' cal', '')) / 100
                if not Food.query.filter_by(name=food_name).first():
                    db.session.add(Food(name=food_name, calories_per_gram=calories_per_100g))
            except KeyError as e:
                print(f"Column {e} is missing from CSV. Please check column names.")
                break
            except ValueError as e:
                print(f"Error converting calories for {row['FoodItem']}: {e}")
                continue  # Skip this row if there's an error
    db.session.commit()

with app.app_context():
    db.create_all()
    load_food_database()

# Routes
@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_user():
    data = request.form
    user = User.query.filter_by(username=data['username'], password=data['password']).first()

    if user:
        session['user_id'] = user.id
        return redirect(url_for('dashboard'))
    else:
        # Pass an error message to the template
        return render_template('login.html', error="Incorrect username or password.")

@app.route('/signup', methods=['POST'])
def signup_user():
    data = request.form
    new_user = User(username=data['username'], password=data['password'])
    db.session.add(new_user)
    db.session.commit()
    session['user_id'] = new_user.id
    return redirect(url_for('onboarding'))

@app.route('/onboarding')
def onboarding():
    return render_template('onboarding.html')

@app.route('/save_onboarding', methods=['POST'])
def save_onboarding():
    data = request.form
    user = db.session.get(User, session['user_id'])
    user.sex = data['sex']
    user.weight = float(data['weight'])
    user.height = float(data['height']) / 100
    user.age = int(data['age'])
    user.goal = data['goal']
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    user = db.session.get(User, session['user_id'])
    return render_template('dashboard.html', user=user)

# Suggest foods and return calorie data
@app.route('/food_suggestions', methods=['GET'])
def food_suggestions():
    query = request.args.get('query', '')
    if query:
        suggestions = Food.query.filter(Food.name.ilike(f"%{query}%")).all()
        return jsonify([
            {"name": food.name, "calories_per_gram": food.calories_per_gram}
            for food in suggestions
        ])
    return jsonify([])

# Log a meal and add new foods to the database if needed
@app.route('/log_meal', methods=['POST'])
def log_meal():
    food_name = request.form['food_name']
    grams = float(request.form['grams'])
    food = Food.query.filter_by(name=food_name).first()

    if food:
        calories = food.calories_per_gram * grams
    else:
        if 'calories_per_gram' in request.form and request.form['calories_per_gram']:
            calories_per_gram = float(request.form['calories_per_gram'])
            calories = calories_per_gram * grams
            new_food = Food(name=food_name, calories_per_gram=calories_per_gram)
            db.session.add(new_food)
        else:
            return redirect(url_for('dashboard'))

    meal = Meal(user_id=session['user_id'], name=food_name, calories=calories, grams=grams, timestamp=datetime.utcnow().date())
    db.session.add(meal)
    db.session.commit()
    return redirect(url_for('dashboard'))

# Log daily water intake
@app.route('/log_water', methods=['POST'])
def log_water():
    amount_ml = float(request.form['amount_ml'])
    water_log = WaterLog(user_id=session['user_id'], amount_ml=amount_ml, timestamp=datetime.utcnow().date())
    db.session.add(water_log)
    db.session.commit()
    return redirect(url_for('dashboard'))

# Log walking activity
@app.route('/log_activity', methods=['POST'])
def log_activity():
    duration_minutes = float(request.form['duration_minutes'])
    user = User.query.get(session['user_id'])
    calories_burned = duration_minutes * user.weight * 0.035
    activity = Activity(user_id=user.id, duration_minutes=duration_minutes, calories_burned=calories_burned, timestamp=datetime.utcnow().date())
    db.session.add(activity)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/update_preferences', methods=['POST'])
def update_preferences():
    user = User.query.get(session['user_id'])
    data = request.form
    user.theme = data.get("theme", "light")
    user.font_size = data.get("font_size", "medium")
    user.accent_color = data.get("accent_color", "#007bff")
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/settings')
def settings():
    user = User.query.get(session['user_id'])
    return render_template('settings.html', user=user)

@app.route('/get_health_status')
def get_health_status():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)

    # Retrieve user data
    total_calories = db.session.query(db.func.sum(Meal.calories)).filter_by(user_id=user_id).scalar() or 0
    total_water = db.session.query(db.func.sum(WaterLog.amount_ml)).filter_by(user_id=user_id).scalar() or 0
    total_walk = db.session.query(db.func.sum(Activity.duration_minutes)).filter_by(user_id=user_id).scalar() or 0

    # Format data for the prompt
    prompt = (
        f"Given this user's recent health data:\n"
        f"- Total Calories Consumed: {total_calories} kcal\n"
        f"- Total Water Intake: {total_water} ml\n"
        f"- Total Walking Duration: {total_walk} minutes\n\n"
        "Please provide a short, encouraging health status summary that includes a brief evaluation "
        "of the user's calorie intake, hydration, and physical activity."
    )

    # Send data to OpenAI's GPT model for a summary using ChatCompletion
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a health advisor."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=60,
            temperature=0.7
        )
        status = response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print("OpenAI API Error:", e)
        status = "Error retrieving status. Please try again later."

    return jsonify({"status": status})


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))

# Retrieve daily summaries for chart display
@app.route('/get_summary_data', methods=['GET'])
def get_summary_data():
    user_id = session['user_id']

    # Aggregate data by date for calorie intake, calories burned, and water intake
    calorie_data = db.session.query(Meal.timestamp, db.func.sum(Meal.calories)) \
        .filter(Meal.user_id == user_id) \
        .group_by(Meal.timestamp).all()
    
    activity_data = db.session.query(Activity.timestamp, db.func.sum(Activity.calories_burned)) \
        .filter(Activity.user_id == user_id) \
        .group_by(Activity.timestamp).all()
    
    water_data = db.session.query(WaterLog.timestamp, db.func.sum(WaterLog.amount_ml)) \
        .filter(WaterLog.user_id == user_id) \
        .group_by(WaterLog.timestamp).all()

    dates = sorted(set(date for date, _ in calorie_data + activity_data + water_data))
    calorie_intake = {date: 0 for date in dates}
    calories_burned = {date: 0 for date in dates}
    water_intake = {date: 0 for date in dates}

    for date, cal in calorie_data:
        calorie_intake[date] = cal
    for date, burn in activity_data:
        calories_burned[date] = burn
    for date, water in water_data:
        water_intake[date] = water

    return jsonify({
        "dates": [date.strftime("%Y-%m-%d") for date in dates],
        "calorie_intake": [calorie_intake[date] for date in dates],
        "calories_burned": [calories_burned[date] for date in dates],
        "water_intake": [water_intake[date] for date in dates]
    })

if __name__ == '__main__':
    app.run(debug=True)
