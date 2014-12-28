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
@app.route('/test3')
def test3():
    songs = format_songs(sources.test3())
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
    songs = db.get_user_songs(userID)
    return json.dumps(format_songs(songs))

# list all sources (sourceURL, sourceID, #songs, )
@app.route('/get/status', methods=['GET'])
def get_status():
    return json.dumps(db.get_last_update_time())

# recommendations
@app.route('/get/recommendations/<userID>', methods=['GET'])
def get_recommendations(userID):
    raw_recs = sources.get_user_recommendations(userID)
    results = {"recommendations":[]}
    print raw_recs
    for i in raw_recs:
        results["recommendations"].append(sources.format_source_result(i))
    print results,"RESS"
    return json.dumps(results)

@app.route('/startscraping', methods=['GET'])
def startscraping():
    sources.refresh_handler()
    return "scraping"

if __name__ == '__main__':
    app.run(debug=True)

