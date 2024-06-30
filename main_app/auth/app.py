from flask import Flask, request, jsonify, make_response
from werkzeug.utils import secure_filename
from elastic_search import data_to_elasticSearch, elastic_search, data_to_feedback
from sqlalchemy import desc
from modules import *
from flask_login import login_required
from flask_migrate import Migrate, upgrade
from flask_login import LoginManager
from flask_mail import Mail, Message
from functools import wraps
from auth import auth
from auth import bcrypt, db, app
from datetime import datetime
from auth.models import User ,create_table_if_not_exists ,ScrappedDates, BlacklistToken, conversationHistory
import json
import urllib.parse


app.register_blueprint(auth, url_prefix='/auth')
Migrate(app, db)
# upgrade(app, db)
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'liam@outscore.com '
app.config['MAIL_PASSWORD'] = 'dlpzfdtbscivemrg'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
posta = Mail(app)


@app.route('/')
def hello():
    response = """<!DOCTYPE html>
                    <html>
                    <head>
                        <title>Agronomy Chatbot</title>
                        <style>
                            body {
                                display: flex;
                                justify-content: center;
                                align-items: center;
                                height: 100vh;
                                margin: 0;
                            }
                        </style>
                    </head>
                    <body>
                        <h1>AGNOROMY CHATBOT </h1>
                    </body>
                    </html>"""
    return response



@app.route('/api/data-to-es', methods = ['GET', 'POST'])
def data_to_es():
    """
    start_date = str m/d/Y
    end_date = str m/d/Y
    page = int 1,2,3,4
        1 --> Machine Talk
        2 --> Drone Talk
        3 --> Crop Talk
        4 --> Precision Talk
    """
     # get the auth token
    auth_header = request.headers.get('Authorization')
    if auth_header:
        try:
            auth_token = auth_header.split(" ")[1]
        except IndexError:
            responseObject = {
                'status': 'fail',
                'message': 'Bearer token malformed.'
            }
            return make_response(jsonify(responseObject)), 401
    else:
        auth_token = ''
    if auth_token:
        resp = User.decode_auth_token(auth_token)
        if not isinstance(resp, str):
            # user = User.query.filter_by(id=resp).first()
            start_date = request.form['start_date']
            end_date = request.form['end_date']
            page = request.form['page']
            try:
                run_scraper(start_date, end_date, page)
            except (json.JSONDecodeError, IOError):
                raise Exception
            pages = {1: "machine talk", 2: "drone talk", 3: "crop talk", 4: "precision talk"}
            page_name = pages.get(int(page))
            lastDateData = ScrappedDates.query.filter_by(page_name=page_name).first()
            if lastDateData:
                lastDateData.date = end_date
                db.session.commit()
            else:
                last_date = ScrappedDates(
                    date = end_date,
                    page_name = page_name
                )
                db.session.add(last_date)
                db.session.commit()
            responseObject = {
                'status': 'success',
                'responce': f'Data till {end_date} is successfully scrapped from {page_name} and added to Elasticsearch successfully'
            }
            return make_response(jsonify(responseObject)), 200
        responseObject = {
            'status': 'fail',
            'message': resp
        }
        return make_response(jsonify(responseObject)), 401
    else:
        responseObject = {
            'status': 'fail',
            'message': 'Provide a valid auth token.'
        }
        return make_response(jsonify(responseObject)), 401



@app.route('/api/agronomyBot', methods = ['POST'])
def agronomyBot():
    """
    This is a POST api
    Input: question/query from user
    Response: response from the chatbot
    elastic_search: run the search query on the es_index and find the most relenvant index
            and then send that data to chatgpt api and get response from there.
    """
    # get the auth token
    auth_header = request.headers.get('Authorization')
    if auth_header:
        try:
            auth_token = auth_header.split(" ")[1]
        except IndexError:
            responseObject = {
                'status': 'fail',
                'message': 'Bearer token malformed.'
            }
            return make_response(jsonify(responseObject)), 401
    else:
        auth_token = ''
    if auth_token:
        resp = User.decode_auth_token(auth_token)
        if not isinstance(resp, str):
            user = User.query.filter_by(id=resp).first()
            city = user.city
            state = user.state
            country = user.country
            question = request.form['question']
            previous_respone = previous_response = (
                        db.session.query(conversationHistory)
                        .filter_by(user_id=str(resp))
                        .order_by(desc(conversationHistory.id)) 
                        .limit(5)
                        .all()
                    )
            response = elastic_search(question, city, state, country, previous_respone)
            _resp_ = conversationHistory(
                user_id= user.id,
                question = question,
                response = response
            )
            db.session.add(_resp_)
            db.session.commit()
            responseObject = {
                'status': 'success',
                'responce': response
            }
            return make_response(jsonify(responseObject)), 200
        responseObject = {
            'status': 'fail',
            'message': resp
        }
        return make_response(jsonify(responseObject)), 401
    else:
        responseObject = {
            'status': 'fail',
            'message': 'Provide a valid auth token.'
        }
        return make_response(jsonify(responseObject)), 401



@app.route('/api/feedback', methods=['POST'])
def feedback():
    """
    Feedback = True/ False (True = Good, Flase = Bad)
    Suggestion = Text that contains the suggestion from the user
    question = Question/query 
    Response =  Chatbot's response generated for which the feedback is.
    """
    # get the auth token
    auth_header = request.headers.get('Authorization')
    if auth_header:
        try:
            auth_token = auth_header.split(" ")[1]
        except IndexError:
            responseObject = {
                'status': 'fail',
                'message': 'Bearer token malformed.'
            }
            return make_response(jsonify(responseObject)), 401
    else:
        auth_token = ''
    if auth_token:
        resp = User.decode_auth_token(auth_token)
        if not isinstance(resp, str):
            data = request.get_json()
            feedback = data.get('feedback')
            suggestion = data.get('suggestion')
            question = data.get('question')
            response = data.get('response')

            data_to_feedback(question, feedback, response, suggestion)
            responseObject = {
                'status': 'success',
                'responce': 'Feedback stored successfully'
            }
            return make_response(jsonify(responseObject)), 200
        responseObject = {
            'status': 'fail',
            'message': resp
        }
        return make_response(jsonify(responseObject)), 401
    else:
        responseObject = {
            'status': 'fail',
            'message': 'Provide a valid auth token.'
        }
        return make_response(jsonify(responseObject)), 401



@app.route('/api/signup', methods=['POST', 'GET'])
def signup():
    # get the post data
    post_data = request.get_json()
    # check if user already exists
    user = User.query.filter_by(email=post_data.get('email')).first()
    if not user:
        try:
            user = User(
                email=post_data.get('email'),
                password=post_data.get('password'),
                city=post_data.get('city'),
                state=post_data.get('state'),
                country=post_data.get('country') 
            )
            # insert the user
            db.session.add(user)
            db.session.commit()
            print(db.session)
            # generate the auth token
            # auth_token = User.encode_auth_token(user.id)
            # responseObject = {
            #     'status': 'success',
            #     'message': 'Successfully registered.',
            #     'auth_token': auth_token.decode()
            # }
            return make_response(jsonify({"Status": "User registered successfully"})), 201
        except Exception as e:
            responseObject = {
                'status': 'fail',
                'message': 'Some error occurred. Please try again.'
            }
            return make_response(jsonify(responseObject)), 301
    else:
        responseObject = {
            'status': 'fail',
            'message': 'User already exists. Please Log in.',
        }
        return make_response(jsonify(responseObject)), 202



@app.route('/api/login', methods=['GET', 'POST'])
def login():
    # get the post data
    post_data = request.get_json()
    try:
        # fetch the user data
        user = User.query.filter_by(
            email=post_data.get('email')
        ).first()
        if user and bcrypt.check_password_hash(
            user.password, post_data.get('password')
        ):
            auth_token = user.encode_auth_token(user.id)
            if auth_token:
                user.last_login = datetime.utcnow()
                db.session.commit()
                responseObject = {
                    'status': 'success',
                    'message': 'Successfully logged in.',
                    'auth_token': auth_token
                }
                return make_response(jsonify(responseObject)), 200
        else:
            responseObject = {
                'status': 'fail',
                'message': 'User does not exist.'
            }
            return make_response(jsonify(responseObject)), 404
    except Exception as e:
        responseObject = {
            'status': 'fail',
            'message': 'Try again'
        }
        return make_response(jsonify(responseObject)), 500



@app.route('/api/forget-password', methods=['POST', 'GET'])
def forget_password():
    mail = request.get_json().get('mail')
    check = User.query.filter_by(email=mail).first()
    print(check)
    if check:
        db.session.commit()
        msg = Message('Confirm Password Change', sender = 'liam@outscore.com', recipients = [mail])
        url_part = urllib.parse.quote(check.password, safe='')
        message = f"""
                Dear LIAM user,
                We've received a request to reset your password. If you want to reset your password, click the link below and enter your new password.
                https://www.outscore.com/reset-password/{url_part}
                Thanks,
                LIAM Support
                """
        msg.body = message
        posta.send(msg)
        responseObj = {
            "Message": msg.body,
            "Status" : "Email sent"
        }
        return make_response(jsonify(responseObj))
    else:
        return make_response(jsonify({"status": "FAILED"}))



@app.route('/api/reset-password', methods=['GET', 'POST'])
def reset_password():
    code = request.args.get('authentication_token')
    data = request.get_json()
    code = urllib.parse.unquote(code)
    check = User.query.filter_by(password=code).first()
    if check:
        _pass = data.get('password')
        confirm_pass = data.get('confirmPassword')
        if _pass == confirm_pass:
            user = User(
                email=check.email,
                password=_pass,
                city=check.city,
                state=check.state,
                country=check.country 
            )
            db.session.delete(check)
            db.session.commit()
            db.session.add(user)
            db.session.commit()
            responseObj = {
                "Status": "Successful",
                "Message": "Password updated successfully. You can login now."
            }
            return make_response(jsonify(responseObj))
        else: 
            responseObj = {
                "Message": "Please enter the same password",
                "status": "Fail"
            }
            return make_response(jsonify(responseObj))
    else:
        responseObj = {
            "Message": "The user is not found.",
            "Status": "FAILED"
        }
        return make_response(jsonify(responseObj))



@app.route('/api/scraper-last-date', methods=['GET', 'POST'])
def last_date():
    auth_header = request.headers.get('Authorization')
    if auth_header:
        try:
            auth_token = auth_header.split(" ")[1]
        except IndexError:
            responseObject = {
                'status': 'fail',
                'message': 'Bearer token malformed.'
            }
            return make_response(jsonify(responseObject)), 401
    else:
        auth_token = ''
    if auth_token:
        resp = User.decode_auth_token(auth_token)
        if not isinstance(resp, str):
            try:
                page = request.get_json().get('pageName')
                lastDate = ScrappedDates.query.filter_by(page_name = page).first()
                if lastDate:
                    responseObj = {
                        "last Date": lastDate.date,
                        "Page Name": lastDate.page_name
                    }
                    return make_response(jsonify(responseObj))
                else:
                    return make_response(jsonify({"Message": "Date not entered yet, PLease run the scraper to get the latest date.."}))
            except Exception as e:
                return make_response(jsonify({"ERROR": e}))
        responseObject = {
            'status': 'fail',
            'message': resp
        }
        return make_response(jsonify(responseObject)), 401
    else:
        responseObject = {
            'status': 'fail',
            'message': 'Provide a valid auth token.'
        }
        return make_response(jsonify(responseObject)), 401



@app.route('/api/get-user', methods = ['GET', 'POST'])
def get_user():
    auth_header = request.headers.get('Authorization')
    if auth_header:
        try:
            auth_token = auth_header.split(" ")[1]
        except IndexError:
            responseObject = {
                'status': 'fail',
                'message': 'Bearer token malformed.'
            }
            return make_response(jsonify(responseObject)), 401
    else:
        auth_token = ''
    if auth_token:
        resp = User.decode_auth_token(auth_token)
        if not isinstance(resp, str):
            user = User.query.filter_by(id = resp).first()
            if user:
                responseObj = {
                    "email" : user.email,
                    "city" : user.city,
                    "state" : user.state,
                    "country": user.country
                }
                return make_response(jsonify(responseObj))
            else:
                responseObj = {
                    "Message": "User doesn't exit or updated",
                    "Status" : "fail"
                }
                return make_response(jsonify(responseObj))
        responseObject = {
            'status': 'fail',
            'message': resp
        }
        return make_response(jsonify(responseObject)), 401
    else:
        responseObject = {
            'status': 'fail',
            'message': 'Provide a valid auth token.'
        }
        return make_response(jsonify(responseObject)), 401



@app.route('/api/update-user', methods = ['GET', 'POST'])
def update_user():
    auth_header = request.headers.get('Authorization')
    if auth_header:
        try:
            auth_token = auth_header.split(" ")[1]
        except IndexError:
            responseObject = {
                'status': 'fail',
                'message': 'Bearer token malformed.'
            }
            return make_response(jsonify(responseObject)), 401
    else:
        auth_token = ''
    if auth_token:
        resp = User.decode_auth_token(auth_token)
        if not isinstance(resp, str):
            user = User.query.filter_by(id = resp).first()
            if user:
                data = request.get_json()
                user.city = data.get('city')
                user.state = data.get('state')
                user.country = data.get('country')
                db.session.commit()
                responseObj = {
                    "Message": "User Data updated successfully.",
                    "Status" : "SUCCESS"
                }
                return make_response(jsonify(responseObj))
            else:
                responseObj = {
                    "Message": "User doesn't exist.",
                    "status" : "FAIL"
                }
                return make_response(jsonify(responseObj))
        responseObject = {
            'status': 'fail',
            'message': resp
        }
        return make_response(jsonify(responseObject)), 401
    else:
        responseObject = {
            'status': 'fail',
            'message': 'Provide a valid auth token.'
        }
        return make_response(jsonify(responseObject)), 401



@app.route('/api/logout', methods=['GET', 'POST'])
def logout():
    auth_header = request.headers.get('Authorization')
    if auth_header:
        auth_token = auth_header.split(" ")[1]
    else:
        auth_token = ''
    if auth_token:
        resp = User.decode_auth_token(auth_token)
        if not isinstance(resp, str):
            # mark the token as blacklisted
            blacklist_token = BlacklistToken(token=auth_token)
            try:
                # insert the token
                db.session.add(blacklist_token)
                db.session.commit()
                responseObject = {
                    'status': 'success',
                    'message': 'Successfully logged out.'
                }
                return make_response(jsonify(responseObject)), 200
            except Exception as e:
                responseObject = {
                    'status': 'fail',
                    'message': e
                }
                return make_response(jsonify(responseObject)), 200
        else:
            responseObject = {
                'status': 'fail',
                'message': resp
            }
            return make_response(jsonify(responseObject)), 401
    else:
        responseObject = {
            'status': 'fail',
            'message': 'Provide a valid auth token.'
        }
        return make_response(jsonify(responseObject)), 403



@app.route('/api/get-all-users', methods = ['POST'])
def get_all_users():
    users = User.query.all()
    
    user_list = []
    for user in users:
        user_data = {
            'email': user.email,
            'last_login': user.last_login.isoformat() if user.last_login else None
        }
        user_list.append(user_data)
    
    return make_response(jsonify(users=user_list))

@app.errorhandler(500)
def handel_500(e):
        return jsonify({'Error' : 'Something went wrong!'}), 500

@app.errorhandler(404)
def handel_404(e):
        return jsonify({'Error' : 'NOT FOUND!'}), 404


if __name__ == '__main__':
     create_table_if_not_exists()
     app.run(debug = True)


