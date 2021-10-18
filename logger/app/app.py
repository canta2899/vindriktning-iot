from flask import Flask
from flask import render_template
from flask import Response
from flask import send_file
from flask import request
from flask import redirect
from flask import url_for
from pygtail import Pygtail
from secrets import token_urlsafe
import signal
import time
import json
import os
import sys

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

def sigint_handler(signal, frame):
    logfile.write("Closing after receiving SIGINT")
    # logfile.close()
    sys.exit(0)

def sigterm_handler(signal, frame):
    logfile.write("Closing after receiving SIGTERM")
    # logfile.close()
    sys.exit(0)

signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGTERM, sigterm_handler)

def update_token_file():
    global alltokens 
    tmp = alltokens.copy()
    with open(TOKENS_FILE, 'w') as f:
        f.write(json.dumps(alltokens))

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

@app.route('/tokens')
def tokens():
    response = []
    for key, value in alltokens.items():
        response.append({
            "chat_id": key,
            "username": value['username'],
            "token": value['token'],
            "done": value['done']
        })
    return Response(
        json.dumps(response), 
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
    return {
        "msg": "Unable to handle request"    
    }, 500

@app.route("/validatetoken", methods=['POST'])
def validatetoken():
    re = request.get_json()
    chat_id = re['chat_id']
    username = re['username']
    token = re['token'] 
    try:
        valid_token = alltokens[str(chat_id)]
        if token == valid_token['token']:
            alltokens[str(chat_id)]['done'] = True
            update_token_file()
            return {
                "msg": "ok"    
            }, 200
    except Exception as e:
        pass
    return {
        "msg": "bad_token"
    }, 401

@app.route("/newtoken", methods=['GET'])
def newtoken():
    try:
        re = request.get_json()
        chat_id = re['chat_id']
        username = re['username']
        new_token = {
            'username': username,
            'token': token_urlsafe(12),
            'done': False
        }
        alltokens[str(chat_id)] = new_token
        update_token_file()
        return {
            "msg": "new_token_made"        
        }, 200
    except Exception as e:
        return {
            "msg": "error"        
        }, 500
    
@app.route("/whitelist")
def whitelist():
    resp = json.dumps(list(alltokens.keys()))
    return Response(resp, mimetype='application/json'), 200

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
