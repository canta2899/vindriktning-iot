from typing import DefaultDict
from flask import Flask
from flask import render_template
from flask import Response
from flask import send_file
from flask import request
from flask import redirect
from flask import url_for
from pygtail import Pygtail
from datetime import datetime, timedelta
import time
import json
import os

LOG_FILE = '/log/logfile.log'
LOG_OFFSET_FILE = '/log/logfile.log.offset'
CRASH_REPORT_FILE = '/log/crashreport.log'
TOKENS_FILE = '/log/tokens.json'

app = Flask(__name__)

app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

alltokens = dict()

if os.path.exists(TOKENS_FILE):
    with open(TOKENS_FILE, 'r') as f:
        alltokens = json.loads(f.read())

if os.path.exists(LOG_FILE):
    os.rename(LOG_FILE, CRASH_REPORT_FILE)
    with open(LOG_FILE, 'a') as f:
        f.write("INITIALIZING LOG FILE\n\n")

if os.path.exists(LOG_OFFSET_FILE):
    os.remove(LOG_OFFSET_FILE)

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

@app.route('/log')
def progress_log():
	def generate():
		for line in Pygtail(LOG_FILE, read_from_end=True,every_n=1):
			yield "data:" + str(line) + "\n\n"
			time.sleep(0.2)
	return Response(
        generate(), 
        mimetype='text/event-stream'
    )

@app.route('/api/tokens')
def tokens():
    response = [token for token in alltokens.values()]
    return Response(
        json.dumps(response, default=defaultconverter), 
        mimetype='application/json'
    )

@app.route('/download')
def download():
    return send_file(
        LOG_FILE, 
        mimetype='text/plain', 
        attachment_filename='logfile.log', 
        as_attachment=True
    )

@app.route('/logging', methods = ['POST'])
def logging():
    req_data = request.get_json()
    with open(LOG_FILE, 'a') as f:
        f.write(req_data['msg'] + "\n\n")
        return {"msg": "ok"}, 200

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



if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
