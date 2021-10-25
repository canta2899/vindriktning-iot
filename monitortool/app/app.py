from flask import (
    Flask,
    render_template,
    Response,
    request,
    g, 
    jsonify, 
    redirect
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

from flask_jwt_extended.utils import set_access_cookies
from werkzeug.utils import redirect

from secrets import token_urlsafe
from datetime import datetime, timedelta
from influxdb import InfluxDBClient
from flask_sqlalchemy import SQLAlchemy
import json
import os

from bot import Bot

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
# TELEGRAM_BOT_TOKEN = '2062157501:AAHNtFKQuYq6wHzdCrwmYtFfwlgGgex7gcc'

LINE = 'select mean("pm25"), "name" from "airquality" where time > now() - 24h group by time(2m) fill(none)'
BAR = 'select mean("pm25") from "airquality" where time > now() - 24h group by "name"'

app = Flask(__name__)
jwt = JWTManager(app)


app.config["JWT_COOKIE_SECURE"] = False  # true in production
app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies"]
app.config["JWT_SECRET_KEY"] = "secret"
app.config['JWT_ACCESS_COOKIE_PATH'] = '/'
app.config['JWT_REFRESH_COOKIE_PATH'] = '/'
app.config['JWT_COOKIE_CSRF_PROTECT'] = False # true in production
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///appdb.db"
app.config['SECRET_KEY'] = 'secret'

sensor_list = dict()
influxbot = None

db = SQLAlchemy(app)

# Defining database models

class User(db.Model):
    name = db.Column(db.String(50), primary_key=True)
    password = db.Column(db.String(80))

class TelegramUser(db.Model):
    id = db.Column(db.Integer, db.Sequence('user_id_seq'), primary_key=True)
    username = db.Column(db.String(50))
    chat_id = db.Column(db.Integer, nullable=True)
    # expiration = db.Column(db.DateTime, default=datetime.utcnow())

class Application(db.Model):
    name = db.Column(db.String(50), primary_key=True)
    secret = db.Column(db.String(32), unique=True)
    description = db.Column(db.String(100))


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
    if q['quality'] == 2:
        quality = "🔴"
    elif q['quality'] == 1:
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



# Starts telegram bot definind callbacks endpoints

b = Bot(TELEGRAM_BOT_TOKEN)
b.on('/status', status_callback)
b.on('/info', info_callback)
b.on('/bind', bind_callback)
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

        
# token refresh?

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
 
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/')
@jwt_required(optional=True)
def entry_point():

    """
        Entry point route. Redirects to login if not logged
        otherwise displays charts
    """

    current_identity = get_jwt_identity()
    if current_identity:
        return render_template('charts.html', logged=True)
    else:
        return render_template('login.html', logged=False)


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
    queried_data = list(res.get_points(measurement='airquality'))
    chart_data = [{'x': q['time'], 'y': q['mean']} for q in queried_data]
    return Response(
        json.dumps(chart_data),
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

    try:
        new_status = request.get_json()
        new_status['time'] = datetime.now()
    except Exception as e:
        return jsonify({'msg': 'Bad request'}), 400

    get_influx().write_points([new_status])
    return jsonify({'msg': 'ok'}), 200


@app.route("/api/addTgUser", methods=['POST'])
@jwt_required()
def newtoken():

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


@app.route("/api/delTgUser", methods=['POST'])
@jwt_required()
def deltoken():

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


@app.route("/api/allTgUsers", methods=['GET'])
@jwt_required()
def alltoken():

    """
        Shows all telegram users in the database    
    """

    all_users = TelegramUser.query.all()
    response = [{'username': user.username, 'chat_id': user.chat_id} for user in all_users]
    return jsonify(response), 200


@app.route("/telegram", methods=['GET'])
@jwt_required(optional=True)
def telegram():

    """
        Renders telegram user page table if authenticated.
        Otherwise redirects to the login page
    """

    current_identity = get_jwt_identity()
    if current_identity:
        return render_template('telegram.html', logged=True)
    else:
        return render_template('login.html', logged=False)


@app.route("/api/auth", methods=['POST'])
def auth_api():

    """
        APPS AUTHORIZATION ENDPOINT
    """

    # Gets name and secret from header
    try:
        appname = request.headers.get('appName')
        secret = request.headers.get('secret')
    except Exception as e:
        return jsonify({'msg': 'Bad request'}), 400

    # searches for a matching app
    req_app = Application.query.filter_by(name=appname, secret=secret).first()

    # Error if not found 
    if not req_app:
        return jsonify({'message': 'Invalid authentication'}), 401
    
    # Otherwise returs a token
    access_token = create_access_token(identity=req_app.name)
    return jsonify({'access_token': access_token}), 200


@app.route("/api/apps", methods=['GET'])
@jwt_required()
def get_apps():

    """
        Returns app list to authorized requestor
    """

    apps = Application.query.all()
    response = [{'name': app.name, 'description': app.description, 'secret': app.secret} for app in apps]
    return jsonify(response), 200


@app.route("/api/newapp", methods=['POST'])
@jwt_required()
def new_app():    

    """
        Creates a new app
    """
    
    try:
        jreq = request.get_json()
        name = jreq['name']
        desc = jreq['description']
    except Exception: 
        return jsonify({'msg': 'Bad request'}), 400

    app = Application.query.filter_by(name=name).first()
    
    if not app:
        secret = token_urlsafe(32)
        a = Application(name=name, description=desc, secret=secret)
        db.session.add(a)
        db.session.commit()
        return jsonify({'name': name, 'description': desc, 'secret': secret}), 200
    
    return jsonify({'msg': 'Resource already exists!'}), 403
    

@app.route("/api/delapp", methods=['POST'])
@jwt_required()
def del_app():

    """
        Deletes an app with the given name
    """    
    
    try:
        jreq = request.get_json()
        name = jreq['name']
    except Exception as e:
        return jsonify({'msg': 'Bad request'}), 400        
        
    app = Application.query.filter_by(name=name).first()
    
    if not app:
        return jsonify({'msg': 'App not found!'}), 409

    db.session.delete(app)
    db.session.commit()
    return jsonify({'msg': 'ok'}), 200


@app.route("/apps")
@jwt_required(optional=True)
def apps():

    """
        Returns app list page if the user is authorized.
        Otherwise redirects to the login endpoint
    """

    current_identity = get_jwt_identity()
    if current_identity:
        return render_template('apps.html', logged=True)
    else:
        return render_template('login.html', logged=False)


@app.route("/auth", methods=['POST'])
def auth():

    """
        Authenticates the user with given credentials. Returns
        token if valid.
    """

    try:
        jreq = request.get_json()

        username = jreq['username']
        password = jreq['password']
    except Exception as e:
        return jsonify({'msg': 'Bad request'}), 400        
    
    user = User.query.filter_by(name=username, password=password).first()

    if not user:
        return jsonify({'message': 'Unknown user'}), 401
    
    response = jsonify({"msg": "login successful"})
    access_token = create_access_token(identity=user.name)
    set_access_cookies(response, access_token)

    return response

@app.route("/login", methods=['GET'])
def login():

    """
        Renders login page template
    """
    
    return render_template('login.html')


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
    
    current_user = get_jwt_identity()

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
    app.run(debug=True, host='0.0.0.0')
