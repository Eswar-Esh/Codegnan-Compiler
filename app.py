from flask import Flask, request, jsonify, render_template, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
import requests
import time
import asyncio
import aiohttp
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from bson import ObjectId
from flask_cors import CORS


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
CORS(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri="memory://"
)

# MongoDB setup - replace with your connection string
client = MongoClient("mongodb+srv://eswark:Esh123@cluster0.4rbil.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client['mydb']
questions_collection = db['questions']
submissions_collection = db['submissions']
users_collection = db['users_data']

# Judge0 API endpoint
JUDGE0_URL = "http://54.255.191.241:2358/submissions"

# Route to list all questions
@app.route('/')
def home():
    return render_template('base.html')
# Route to add a new question
@app.route('/add_question', methods=['GET', 'POST'])
def add_question():
    if request.method == 'POST':
        question_text = request.form['question']
        language = request.form['language']
        test_cases = [
            {
                "input": input_val,
                "output": output_val,
                "category": category
            }
            for input_val, output_val, category in zip(
                request.form.getlist('testcase_input[]'),
                request.form.getlist('testcase_output[]'),
                request.form.getlist('category[]')
            )
        ]

        # Insert question into MongoDB
        question_id = questions_collection.insert_one({
            "question": question_text,
            "language": language,
            "test_cases": test_cases
        }).inserted_id

        return redirect(url_for('admin'))
    return render_template('add_question.html')



# Route to solve a question (display and submit code)
@app.route('/solve_question/<question_id>', methods=['GET', 'POST'])
def solve_question(question_id):
    if request.method == 'GET':
        # Fetch question data for rendering solve_question.html
        question = questions_collection.find_one({"_id": ObjectId(question_id)})
        if not question:
            return "Question not found", 404
        return render_template('solve_question.html', question=question)

    elif request.method == 'POST':
        data = request.json
        code = data.get("code")
        language_id = data.get("language_id")
        custom_input = data.get("custom_input", None)

        # Retrieve question for executing test cases
        question = questions_collection.find_one({"_id": ObjectId(question_id)})
        if not question:
            return jsonify({"error": "Question not found"}), 404

        # Choose hidden test cases or custom input
        test_cases = [{"input": custom_input}] if custom_input else question["test_cases"]
        results = []

        # Process each test case using Judge0
        for test_case in test_cases:
            submission_data = {
                "source_code": code,
                "language_id": language_id,
                "stdin": test_case["input"]
            }
            response = requests.post(JUDGE0_URL, json=submission_data)
            if response.status_code != 201:
                return jsonify({"error": "Failed to submit code to Judge0"}), 500

            token = response.json().get("token")
            result = check_judge0_result(token)

            # Collect detailed results for each test case
            results.append({
                "input": test_case["input"],
                "expected_output": test_case.get("output"),
                "received_output": result.get("stdout"),
                "status": result.get("status", {}).get("description"),
                "errors": result.get("stderr") or result.get("compile_output", ""),
            })

        # Save the submission result if running with hidden test cases
        if not custom_input:
            submissions_collection.insert_one({
                "question_id": question_id,
                "code": code,
                "results": results,
                "timestamp": int(time.time())
            })

        return jsonify({"results": results})

# Helper function to poll Judge0 for result status
def check_judge0_result(token):
    while True:
        response = requests.get(f"{JUDGE0_URL}/{token}")
        result = response.json()
        if result["status"]["description"] not in ["In Queue", "Processing"]:
            return result
        time.sleep(1)  # Short delay to prevent excessive polling

@app.route('/all_data')
def Alldata():
    questions = questions_collection.find()
    return render_template('index.html', questions=questions)

#signup page
@app.route('/signup',methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        fullname = request.form['fullname']
        username = request.form['username']
        phno = request.form['phno']
        mail = request.form['email']
        password = request.form['password']
        confirm_pwd = request.form['confirm_pwd']
        if password == confirm_pwd:
            data ={'Name':fullname,'Username':username,'ph_number':phno,'email':mail,'password':password,}
            users_collection.insert_one(data)
            return redirect(url_for('login'))
        else:
            return """
                <center>
                <h2 style="font-size:50px;color:#c36;">Invalid Credentials!</h2>
                <h3 style="font-size:30px;"> Password and Confirm_password not matched. Please try again.</h3>
                </center>
                """
    return render_template('signup.html')
#login page
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'POST':
        mail = request.form['email']
        password = request.form['password']
        user = users_collection.find_one({"email": mail})
        if user:
            if user["password"] == password:
                return redirect(url_for('Alldata'))  
        else:
             return """
                <center>
                <h2 style="font-size:50px;color:#c36;">User Not Found.....!</h2>
                <h3 style="font-size:30px;">Give correct username or password. Please try again.</h3>
                </center>
                """        
    return render_template('login.html')
#logout page
@app.route('/logout')
def logout():
    return redirect(url_for('home'))

#Admin Dashboard
@app.route('/User_data')
def User_data():
    users = users_collection.find()
    print(users)
    return render_template('users.html',users=users)
@app.route('/admin_Dashboard')
def admin():
    questions = questions_collection.find()
    return render_template('admin.html',questions=questions)

#admin login
@app.route('/admin',methods=['GET','POST'])
def adminlogin():
    if request.method == 'POST':
        mail = request.form['email']
        password = request.form['password']
        if mail == 'codegnan@codegnan.com' and password == 'Codegnan@2024':
            return redirect(url_for('admin'))  
        else:
             return """
                <center>
                <h2 style="font-size:50px;color:#c36;">Invalid Admin Credentials..!</h2>
                <h3 style="font-size:30px;">Incorrect username or password. Please try again.</h3>
                </center>
                """      
    return render_template('adminlogin.html')

#updates question
@app.route('/edit/<string:record_id>', methods=['GET','POST'])
def edit_quesion(record_id):
    quesion = questions_collection.find_one({"_id": ObjectId(record_id)})
    return render_template('update_question.html',quesion=quesion)

@app.route('/update/<string:record_id>', methods=['GET','POST'])
def update_quesion(record_id):
    if request.method == 'POST':
        # print('-'*40,request.form)
        question = request.form.get("question")
        language = request.form.get("language")
        test_cases = []
        testcase_inputs = request.form.getlist("testcase_input[]")
        testcase_outputs = request.form.getlist("testcase_output[]")
        categories = request.form.getlist("category[]")
        num_cases = min(len(testcase_inputs), len(testcase_outputs), len(categories))
        
        for i in range(num_cases):
            test_cases.append({
                "input": testcase_inputs[i],
                "output": testcase_outputs[i],
                "category": categories[i]
            })
            
        ques = {'question':question,'language':language,'testcases':test_cases}
        questions_collection.update_one({"_id": ObjectId(record_id)},{"$set": {"question": question,"language": language,"testcases": test_cases }})
        return redirect(url_for('admin'))
    return render_template('update_question.html')

#delete Questions
@app.route('/delete/<string:record_id>', methods=['POST'])
def delete_quesion(record_id):
    questions_collection.delete_one({"_id": ObjectId(record_id)})

    return redirect(url_for('admin'))


if __name__ == '__main__':
    app.run(debug=True,use_reloader=True)
