import json
from flask import Flask,request
from server import sources, db
app = Flask(__name__)

def format_songs(songs):
    return {'songs':songs}

@app.route('/')
def hello():
    return "ALIVE"

####$$$$$$ TEST ####$$$$$$$
@app.route('/test2')
def test2():
    songs = format_songs(sources.test())
    return json.dumps(songs)
##################

@app.route('/add/user/<userID>', methods=['GET'])
def add_user(userID):
    s = False
    if db.add_user(userID):
        s = True
    return json.dumps({"ADD":s})

# add source
@app.route('/add/source', methods=['GET'])
def add_source():
    sourceURL = request.args.get("sourceURL")
    userID = request.args.get("userID")
    result = sources.add_source(sourceURL,userID)
    return json.dumps(result)

# get songs from user_id
@app.route('/get/songs/<userID>', methods=['GET'])
def get_songs(userID):
    songs = db.get_user_songs("1")
    return json.dumps(format_songs(songs))

# list all sources (sourceURL, sourceID, #songs, )
@app.route('/get/status', methods=['GET'])
def get_status():
    print db.get_last_update_time()
    return json.dumps(db.get_last_update_time())

@app.route('/startscraping', methods=['GET'])
def startscraping():
    sources.refresh_handler()
    return "scraping"

if __name__ == '__main__':
    app.run(debug=True)

