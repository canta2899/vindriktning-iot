from flask import (
    Flask,
    render_template,
    Response,
    request,
    g, 
    jsonify, 
    redirect,
    url_for
)

from flask_jwt_extended import (
    create_access_token,
    jwt_manager,
    get_jwt, 
    get_jwt_identity, 
    jwt_required,
    JWTManager, 
    set_access_cookies, 
    unset_access_cookies,
    unset_jwt_cookies
)

from flask_jwt_extended.utils import get_current_user, get_jwt_header, set_access_cookies
from werkzeug.utils import redirect

from datetime import datetime, timedelta
from influxdb import InfluxDBClient
from flask_sqlalchemy import SQLAlchemy
from passlib.hash import pbkdf2_sha256
import json
import os
from waitress import serve

from bot import Bot

USE_WSGI = True

APP_NAME = os.environ['AUTH_APPNAME']
APP_SECRET = os.environ['AUTH_APPPASS']
APP_ID = 'engineapp'

# APP_NAME = 'prova'
# APP_SECRET = 'test'

TOKENS_FILE = '/tokens/tokens.json'
INFLUX_DB_DATABASE = 'airquality'

INFLUX_DB_USER = os.environ['INFLUXDB_API_USER'] 
INFLUX_DB_PASSWORD = os.environ['INFLUXDB_API_PASSWORD']
INFLUX_DB_HOST = 'database'         
INFLUX_DB_PORT = 8086
TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN'] 

# INFLUX_DB_USER = 'bridge' 
# INFLUX_DB_PASSWORD = 'bridge'
# INFLUX_DB_HOST = 'localhost'         
# INFLUX_DB_PORT = 8086
# TELEGRAM_BOT_TOKEN = 'past-here-your-token'


LINE = 'select mean("pm25") from "airquality" where time > now() - 10d group by time(2m), "name" fill(none)'
BAR = 'select mean("pm25") from "airquality" where time > now() - 10d group by "name"'

app = Flask(__name__)
jwt = JWTManager(app)

app.config["JWT_COOKIE_SECURE"] = True  # true in production, false in development
app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies"]
app.config["JWT_SECRET_KEY"] = "secret"
app.config['JWT_ACCESS_COOKIE_PATH'] = '/'
app.config['JWT_REFRESH_COOKIE_PATH'] = '/'
app.config['JWT_COOKIE_CSRF_PROTECT'] = True # true in production, false in development
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///appdb.db"
# python3 -c 'import secrets; print(secrets.token_hex())'
app.config['SECRET_KEY'] = '7fb209172a3227ceccd8cb27fbbfd50e00257ac4bf43f0b141fa2ebbc384a0b6'

sensor_list = dict()
influxbot = None

db = SQLAlchemy(app)

# Defining database models

class User(db.Model):
    id = db.Column(db.Integer, db.Sequence('user_id_seq'), primary_key=True)
    name = db.Column(db.Text, unique=True)
    password = db.Column(db.Text)
    is_admin = db.Column(db.Boolean, default=False)

class TelegramUser(db.Model):
    username = db.Column(db.String(50), primary_key=True)
    chat_id = db.Column(db.Integer, nullable=True)


def bind_callback(chat_id, username, params):

    """
        Binds a user by associating its username to its
        chat_id. This is needed in order to send notifications
        to the user
    """

    user = TelegramUser.query.filter_by(username=username).first() 

    if not user:
        return
   
    if not user.chat_id:
        user.chat_id = chat_id
        db.session.commit()
        b.push_notification("Great, you're ready to go!", [chat_id])
        return

    if user.chat_id == chat_id:
        b.push_notification("You're already binded!", [chat_id])
        return

    b.push_notification("There's no binding available, sorry", [chat_id])


def status_callback(chat_id, _, params):

    """
        Responds to the /status command if the user is binded.
        Returns the status about all the sensor or about a single
        sensor if specified
    """

    user = TelegramUser.query.filter_by(chat_id=chat_id).first() 
    if not user:
        return

    tmp_list = sensor_list.copy()

    # If there's no known sensor
    if len(tmp_list) == 0:
        b.push_notification(
            "You have no sensors registered to the network", 
            [chat_id]
        )
        return

    # If it's just /status sends actual status for each known sensor
    if len(params) == 1:
        global_msg = ""
        for sensor in tmp_list.values():
            global_msg += (
                f"Your sensor {sensor['name']} "
                f"is {sensor['status']}\n\n"
            )
        b.push_notification(global_msg, [chat_id])
        return

    # Otherwise, sends actual status for the requested sensor
    for sensor in tmp_list.values():
        if sensor['name'] == params[1]:
            b.push_notification(
                f"The sensor {sensor['name']} "
                f"is {sensor['status']}",
                [chat_id]
            )
            return

    # Otherwise the requested sensor doesn't exist
    b.push_notification("Seems like there's no sensor with that name", [chat_id])
   

def info_callback(chat_id, _, params):

    """
        Responds to the /info command if the user is binded.
        Returns info about the requested sensor.
    """

    users = TelegramUser.query.filter_by(chat_id=chat_id).all()
    chat_ids = [usr.chat_id for usr in users]

    if chat_id not in chat_ids:
        return

    # If no sensor name is specified, requests for one and returns
    if len(params) == 1:
        b.push_notification(
            "Please specify the sensor name. "
            "You can list them with /status", 
            [chat_id]
        )
        return

    # Extracts sensor name
    name = params[1]

    res = get_bot_influx().query('select last("pm25"), "quality" from "airquality" where time > now() - 1m and "name"=$name',
                                 bind_params={'name': name})

    data = list(res.get_points(measurement='airquality'))

    if len(data) == 0:
        b.push_notification("I have no recent updates from that sensor", [chat_id])
        return

    q = data[0]
    
    quality = ""
    if q['quality'] == '2':
        quality = "🔴"
    elif q['quality'] == '1':
        quality = "🟠"
    else:
        quality = "🟢"

    value = q['last'] 

    b.push_notification(
        f"Name: {name}\n\n"
        f"Quality: {quality}\n\n"
        f"Value: {value}", 
        [chat_id]
    )


def start_callback(chat_id, _1, _2):
    b.push_notification(
        (
            "Hi! I'm your VINDRIKTNING bot and I'm ready to help you! 💪🏻 "
            "Make sure to get yourself listed by an admin user and to run "
            "/bind in order to receive notifications 😉"
        ),
        [chat_id]
    )


# Starts telegram bot definind callbacks endpoints

b = Bot(TELEGRAM_BOT_TOKEN)
b.on('/status', status_callback)
b.on('/info', info_callback)
b.on('/bind', bind_callback)
b.on('/start', start_callback)
b.run()


def get_influx():

    """
        Returns influxDB connection instance for the app
        execution context.
    """

    influx = getattr(g, '_influx', None)
    if not influx:
        try:
            influx = InfluxDBClient(
                    INFLUX_DB_HOST, 
                    INFLUX_DB_PORT, 
                    INFLUX_DB_USER, 
                    INFLUX_DB_PASSWORD, 
                    INFLUX_DB_DATABASE
            )

            influx.switch_database(INFLUX_DB_DATABASE)
        except Exception as e:
            pass
    return influx


def get_bot_influx():

    """
        Returns influxDB connection instance for TelegramBot
        exceution context in order to query last sensor value
    """

    global influxbot
    if not influxbot:
        try:
            influxbot = InfluxDBClient(
                    INFLUX_DB_HOST, 
                    INFLUX_DB_PORT, 
                    INFLUX_DB_USER, 
                    INFLUX_DB_PASSWORD, 
                    INFLUX_DB_DATABASE
            )

            influxbot.switch_database(INFLUX_DB_DATABASE)
        except Exception as e:
            pass
    return influxbot


def defaultconverter(o):
    
    """
        Defines a datetime converter for json serialization
    """
    
    if isinstance(o, datetime):
        return o.__str__()

        
# Allows to handle the automatic token refresh if desired

# @app.after_request
# def refresh_expiring_jwts(response):
#     try:
#         exp_timestamp = get_jwt()['exp']
#         now = datetime.now()
#         target_timestamp = datetime.timestamp(now + timedelta(minutes=30))
#         if target_timestamp > exp_timestamp:
#             access_token = create_access_token(identity=get_jwt_identity())
#             # cookie

#         return response
#     except (RuntimeError, KeyError):
#         return response

def is_from_browser(user_agent):
    return user_agent.browser in [
        "camino",
        "chrome",
        "firefox",
        "galeon",
        "kmeleon",
        "konqueror",
        "links",
        "lynx",
        "msie",
        "msn",
        "netscape",
        "opera",
        "safari",
        "seamonkey",
        "webkit",
    ] 
 
@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html', logged=False, params={'admin': False}), 403
 
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', logged=False, params={'admin': False}), 404

@jwt.expired_token_loader
def expired_token(jwt_header, jwt_payload):
    if is_from_browser(request.user_agent):
        return render_template('login.html', logged=False, params={'admin': False})
    return jsonify({'msg': 'Not authorized', 'description': 'Token has expired'}), 401

@app.route('/')
@jwt_required(optional=True)
def entry_point():

    """
        Entry point route. Redirects to login if not logged
        otherwise displays charts
    """

    current_identity = get_jwt_identity()
    
    params = {
        'admin': False
    }
    
    if current_identity:
        user = User.query.filter_by(id=current_identity).first()
        if not user:
            return redirect('/logout')
        if user.is_admin:
            params['admin'] = True
        return render_template('charts.html', logged=True, params=params)
    else:
        return render_template('login.html', logged=False, params=params)


@app.route('/api/data/line')
@jwt_required()
def data():

    """
        Returns data in order to produce line chart if
        the requestor is authorized
    """

    res = get_influx().query(LINE)

    if not res:
        return {'status': 'data_unreachable'}, 500
    
    # get_ts = lambda x: datetime.strptime(x, '%Y-%m-%dT%H:%M:%S%z').timestamp()
    
    data = []
    
    for key, value in res.items():
        data.append({
            'name': key[1]['name'],
            'points': [{'x': p['time'], 'y': p['mean']} for p in value]
        })

    return Response(
        json.dumps(data),
        mimetype='application/json'
    )


@app.route('/api/data/bar')
@jwt_required()
def databar():

    """
        Returns data in order to produce bar plot if 
        the requestor is authorized
    """ 

    res = get_influx().query(BAR)
    if not res:
        return {'status': 'data_unreachable'}, 500
    chart_x = [v[1]['name'] for v in res.keys()] 
    chart_y = [v[0]['mean'] for v in res]
    chart_data = [{'name': name, 'median': median} for name, median in zip(chart_x, chart_y)]
    return Response(
        json.dumps(chart_data),
        mimetype='application/json'
    )


@app.route('/api/airquality', methods=['POST'])
@jwt_required()
def airquality():

    """
        Received air quality update from authorized
        applications. Then, performs database logging
    """

    current_identity = get_jwt_identity()

    if is_from_browser(request.user_agent):
        return jsonify({'msg': 'Forbidden'}), 403

    try:
        new_status = request.get_json()
        new_status['time'] = datetime.now()
    except Exception as e:
        return jsonify({'msg': 'Bad request'}), 400

    get_influx().write_points([new_status])
    return jsonify({'msg': 'ok'}), 200


@app.route("/api/telegram", methods=['GET', 'POST', 'DELETE'])
@jwt_required()
def telegram_users_api():

    current_identity = get_jwt_identity()
    
    if not current_identity:
        return redirect('/login')

    requestor = User.query.filter_by(id=current_identity).first()

    if not requestor:
        return redirect('/')

    if not requestor.is_admin:
        return redirect('/')

    if request.method == 'POST':

        """
            Adds a new telegram user to the database
        """

        try:
            jreq = request.get_json()
            username = jreq['username']
        except Exception as e:
            return jsonify({'msg': 'Bad request'}), 400

        previous = TelegramUser.query.filter_by(username=username).all()
        
        for user in previous:
            db.session.delete(user)

        new_user = TelegramUser(username=username)
        db.session.add(new_user)

        db.session.commit()

        return jsonify({'msg': 'User added'}), 200
    
    if request.method == 'DELETE':

        """
            Removes a telegram user from the database
        """ 

        try:
            jreq = request.get_json()
            username = jreq['username']
        except Exception as e:
            return jsonify({'msg': 'Bad request'}), 400

        user = TelegramUser.query.filter_by(username=username).all()

        if len(user) == 0:
            return jsonify({'msg': 'Unknown user'}), 409 

        for usr in user:
            db.session.delete(usr)
        db.session.commit()

        return jsonify({'msg': 'Deleted user'}), 200
    
    if request.method == 'GET':

        """
            Retrieves all telegram users in the database    
        """
        
        all_users = TelegramUser.query.all()
        response = [{'username': user.username, 'chat_id': user.chat_id} for user in all_users]
        return jsonify(response), 200


@app.route("/api/users", methods=['GET', 'POST', 'DELETE', 'PUT'])
@jwt_required()
def users_api():
    
    """
        Allows to create, delete, update users informations
    """

    current_identity = get_jwt_identity()
    if not current_identity:
        return redirect('/login', logged=False, admin=False)

    requestor = User.query.filter_by(id=current_identity).first()

    if not requestor:
        return redirect('/'),

    if not requestor.is_admin:
        return redirect('/'),
        
    if request.method == 'GET':
        users = User.query.all()
        response = [{'username': user.name, 'is_admin': user.is_admin} for user in users if user.name != requestor.name]
        return jsonify(response), 200 

    if request.method == 'POST':
        try:
            jreq = request.get_json()
            username = jreq['username']
            new_password = jreq['newPassword']
            password = jreq['reqPassword']
            is_admin = jreq['newAdmin']
        except Exception as e:
            return jsonify({'msg': 'Bad request'}), 400
        
        if not pbkdf2_sha256.verify(password, requestor.password):
            return jsonify({'msg': 'Wrong password'}), 401
        
        match = User.query.filter_by(name=username).first()
        
        if not match:
            new_user = User(name=username, password=pbkdf2_sha256.hash(new_password), is_admin=is_admin)
            db.session.add(new_user)
            db.session.commit()
            return jsonify({'msg': 'Added user'}), 200
            
        return jsonify({'msg': 'User already exists'}), 409

    if request.method == 'PUT':
        try:
            jreq = request.get_json()
            username = jreq['username']
            password = jreq['reqPassword']
            new_password = jreq.get('newPassword', None)
            new_is_admin = jreq['newAdmin']
        except Exception as e:
            return jsonify({'msg': 'Bad request'}), 400
            
        # TODO check requestor password

        if not pbkdf2_sha256.verify(password, requestor.password):
            return jsonify({'msg': 'Wrong password'}), 401

        match = User.query.filter_by(name=username).first()
        
        if not match:
            return jsonify({'msg': 'User not exists'}), 409
        
        if new_password is not None:
            match.password = pbkdf2_sha256.hash(new_password)
        
        match.is_admin = new_is_admin

        db.session.commit() 

        return jsonify({'msg': 'User updated'}), 200
    
    if request.method == 'DELETE':
        try:
            jreq = request.get_json()
            username = jreq['username']
        except Exception as e:
            return jsonify({'msg': 'Bad request'}), 400
        
        if username == requestor.name:
            return jsonify({'msg': 'Trying to delete current user'}), 409
        
        match = User.query.filter_by(name=username).first()

        if not match:
            return jsonify({'msg': 'User not found'}), 409


        if match.id == current_identity:
            unset_jwt_cookies()
            return jsonify({'msg': 'Cannot delete current user'}), 100
        
        
        db.session.delete(match)
        db.session.commit()
        return jsonify({'msg': 'Deleted user'}), 200


@app.route("/telegram", methods=['GET'])
@jwt_required(optional=True)
def telegram():

    """
        Sends telegram user page table if authenticated.
        Otherwise redirects to the login page
    """

    current_identity = get_jwt_identity()
    if current_identity:
        user = User.query.filter_by(id=current_identity).first()
        if user.is_admin:
            return render_template('telegram.html', logged=True, params={'admin': True})
    return redirect('/')


@app.route("/users", methods=['GET'])
@jwt_required(optional=True)
def users():

    """
        Sends telegram user page table if authenticated.
        Otherwise redirects to the login page
    """

    current_identity = get_jwt_identity()
    params = {
        'admin': False
    }
    if current_identity:
        user = User.query.filter_by(id=current_identity).first()
        if user.is_admin:
            params['admin'] = True
            return render_template('users.html', logged=True, params=params)
    return redirect('/')

@app.route("/me", methods=['GET'])
@jwt_required()
def me():
    
    """
        Sends user's profile page
    """
    
    current_identity = get_jwt_identity()

    params = {
        'admin': False
    }
    
    if current_identity:
        me = User.query.filter_by(id=current_identity).first()
        params['username'] = me.name
        params['admin'] = me.is_admin
        return render_template('profile.html', logged=True, params=params)
    
    return render_template('login.html', logged=False, params=params)


@app.route("/api/me", methods=['PUT'])
@jwt_required()
def api_me():
    
    """
        Updates user's informations
    """
    
    current_identity = get_jwt_identity()
    
    if not current_identity:
        return jsonify({'msg': 'Not authorized'}), 403
    
    user = User.query.filter_by(id=current_identity).first()
    
    if not user:
        return jsonify({'msg': 'User not found'}), 404

    try:
        jreq = request.get_json()
        username = jreq['username']
        req_password = jreq['reqPassword']
        new_password = jreq['newPassword']
    except Exception as e:
        return jsonify({'msg': 'Bad request'}), 400
    
    if pbkdf2_sha256.verify(req_password, user.password):
        if new_password != "" and new_password != None:
            user.password = pbkdf2_sha256.hash(new_password)
        
        if username != "" and username != None and username != user.name:
            user.name = username
        
        db.session.commit()
        return jsonify({'msg': 'Updated'}), 200

    return jsonify({'msg': 'Wrong password'}), 400

@app.route("/api/auth", methods=['POST'])
def auth_api():

    """
        Handles jwt authorization
    """

    if is_from_browser(request.user_agent):
        try:
            jreq = request.get_json()
            username = jreq['username']
            password = jreq['password']
        except Exception as e:
            return jsonify({'msg': 'Bad request'}), 400        
        
        # TODO check if user is valid and produce access token
        user = User.query.filter_by(name=username).first()

        if not user:
            return jsonify({'msg': 'Unknown user'}), 409
        
        if not pbkdf2_sha256.verify(password, user.password):
            return jsonify({'msg': 'Wrong password'}), 401
        
        response = jsonify({"msg": "login successful"})
        access_token = create_access_token(identity=user.id)
        set_access_cookies(response, access_token)
        return response
    else:
        # Gets name and secret from header
        try:
            appname = request.headers.get('appName')
            secret = request.headers.get('secret')
        except Exception as e:
            return jsonify({'msg': 'Bad request'}), 400

        if appname == APP_NAME and secret == APP_SECRET:
            access_token = create_access_token(identity=APP_ID)
            return jsonify({'access_token': access_token}), 200
        
        return jsonify({'msg': 'Not Authorized'}), 401


@app.route("/login", methods=['GET'])
@jwt_required(optional=True)
def login():

    """
        Sends login page template
    """

    current_identity = get_jwt_identity()
    
    if current_identity:
        return redirect('/')
    return render_template('login.html', admin=False, params={'admin': False})


@app.route('/logout', methods=['GET'])
def logout():
    
    """
        Handles user logout by deleting
        the httponly cookie containing the token
    """

    response = redirect('/')
    unset_jwt_cookies(response)
    return response


@app.route("/api/status", methods=['POST'])
@jwt_required()
def status():

    """
        Receives sensor status update from authorized
        source and updates sensor status locally
    """
    
    current_identity = get_jwt_identity()

    if is_from_browser(request.user_agent):
        return jsonify({'msg': 'Forbidden'}), 403

    try:
        jreq = request.get_json()

        uid = jreq['uid']
        status = jreq['status']
        name = jreq['name'] # TODO expects name from the request
    except Exception as e:
        return jsonify({'msg': 'Bad request'}), 400        

    if uid not in sensor_list.keys():
        sensor_list[uid] = {
            'status': status,
            'name': name
        }
    else:
        sensor_list[uid]['status'] = status
    
    return jsonify({'msg': 'ok'}), 200


@app.route("/api/bot/notification", methods=['POST'])
@jwt_required()
def notify_bot():

    """
        Receives a bot notification request from authorized
        source and triggers a bot notification to all the
        binded users
    """
    current_identity = get_jwt_identity()

    if is_from_browser(request.user_agent):
        return jsonify({'msg': 'Forbidden'}), 403

    try:
        jreq = request.get_json()
        msg = jreq['msg']
    except Exception as e:
        return jsonify({'msg': 'Bad request'}), 400        

    users = TelegramUser.query.all() 
    b.push_notification(msg, [user.chat_id for user in users if user.chat_id is not None])
    return jsonify({'msg': 'ok'})


# Run the app
if __name__ == "__main__":
    if USE_WSGI:
        # Production server
        serve(app, host='0.0.0.0', port=8080, url_scheme='https')
    else:
        # Development server
        app.run(debug=True, host='0.0.0.0', port=8080)
