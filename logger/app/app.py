from typing import DefaultDict
from flask import Flask
from flask import render_template
from flask import Response
from flask import send_file
from flask import request
from flask import redirect
from flask import url_for
from datetime import datetime, timedelta
from influxdb import InfluxDBClient
import time
import json
import os
import sys

LOG_FILE = '/log/logfile.log'
CRASH_REPORT_FILE = '/log/crashreport.log'
TOKENS_FILE = '/tokens/tokens.json'

INFLUX_DB_DATABASE = 'airquality'

# INFLUX_DB_USER = os.environ['INFLUXDB_MQTT_USER'] 
# INFLUX_DB_PASSWORD = os.environ['INFLUXDB_MQTT_PASSWORD']
# INFLUX_DB_HOST = 'database'         

INFLUX_DB_USER = 'bridge'
INFLUX_DB_PASSWORD = 'bridge'
INFLUX_DB_HOST = 'localhost'         

INFLUX_DB_PORT = 8086

QUERY = 'select mean("pm25") from "airquality" where time > now() - 24h group by time(10s) fill(none)'


dbready = False

try:
    dbclient = InfluxDBClient(
            INFLUX_DB_HOST, 
            INFLUX_DB_PORT, 
            INFLUX_DB_USER, 
            INFLUX_DB_PASSWORD, 
            INFLUX_DB_DATABASE
    )

    dbclient.switch_database(INFLUX_DB_DATABASE)
    dbready = True
except Exception as e:
    print("Unable to perform InfluxDB connection")
    sys.exit(1)



app = Flask(__name__)

app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

alltokens = dict()

if os.path.exists(TOKENS_FILE):
    with open(TOKENS_FILE, 'r') as f:
        alltokens = json.loads(f.read())

def defaultconverter(o):
    if isinstance(o, datetime):
        return o.__str__()

def update_token_file():
    global alltokens 
    tmp = alltokens.copy()
    with open(TOKENS_FILE, 'w') as f:
        f.write(json.dumps(tmp, default=defaultconverter))


@app.route('/')
def entry_point():
	return render_template('index.html')


@app.route('/api/data')
def data():
    if dbready:
        res = dbclient.query(QUERY)
        queried_data = list(res.get_points(measurement='airquality'))
        # chart_data = [{'x': time.mktime(datetime.fromisoformat(q['time'][:-1]).timetuple()), 'y': q['mean']} for q in queried_data]
        chart_data = [{'x': q['time'], 'y': q['mean']} for q in queried_data]
        print(chart_data[0])
        return Response(
            json.dumps(chart_data),
            mimetype='application/json'
        )
    else:
        return {'msg': 'data_unreachable'}, 500


@app.route('/api/tokens')
def tokens():
    response = [token for token in alltokens.values()]
    return Response(
        json.dumps(response, default=defaultconverter), 
        mimetype='application/json'
    )


@app.route('/api/download/<reqfile>', methods=['GET'])
def download(reqfile):
    if reqfile == 'log':
        requested_file = LOG_FILE
    elif reqfile == 'crashreport':
        requested_file = CRASH_REPORT_FILE
    else:
        return {'msg': 'Unknown resource'}, 404
    return send_file(
        requested_file, 
        mimetype='text/plain', 
        attachment_filename='logfile.log', 
        as_attachment=True
    )

@app.route("/api/validate", methods=['GET'])
def validatetoken():
    re = request.get_json()
    chat_id = re['chat_id']
    username = re['username']
    if username in alltokens:
        if datetime.now() > alltokens[username]['expires']:
            return {
                "msg": "token_expired"
            }, 401

        if alltokens[username]['chat_id'] == '':
            alltokens[username]['chat_id'] = chat_id
            update_token_file()

        return {
            "msg": "ok"
        }, 200
    else:
        return {
            "msg": "not_authorized"
        }, 401


@app.route("/api/newtoken", methods=['POST'])
def newtoken():
    re = request.get_json()
    username = re['username']
    duration = re['duration']

    new_token = {
        'chat_id': '',
        'username': username,
        'expires': datetime.now() + timedelta(days=int(duration))
    }

    alltokens[username] = new_token
    update_token_file()

    response = {
        'status': 'ok',
        'tokens': alltokens
    }

    return Response(
        json.dumps(response, default=defaultconverter), 
        mimetype='application/json'
    ), 200


@app.route("/api/deltoken", methods=['POST'])
def deltoken():
    re = request.get_json()
    username = re['username']

    removed = alltokens.pop(username, None)

    if not removed:
        return {
            'status': 'not_found'        
        }, 404 

    update_token_file()

    return {
        'status': 'ok'
    }, 200


@app.route("/api/whitelist")
def whitelist():
    wl = [val['chat_id'] for val in alltokens.values() if val['chat_id'] != '']
    return Response(
        json.dumps(wl, default=defaultconverter), 
        mimetype='application/json'
    ), 200



if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
