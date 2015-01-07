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

@app.route('/add/group', methods=['POST'])
def add_group():
    if not request.json:
        return json.dumps({"error":"server"})
        
    name = request.json["name"]
    users = request.json["users"]
    error = ""
    if not db.add_group(name,users):
        error = "server"
    return json.dumps({"error":error})

@app.route('/add/groupuser', methods=['GET'])
def add_user_to_group():
    error = ""
    groupID = request.args.get("groupID")
    userID = request.args.get("userID")
    result = db.add_user_to_group(userID,groupID)
    if not result:
        error = "server"
    return json.dumps({"error":error})

@app.route('/add/groupsong', methods=['GET'])
def add_song_to_group():
    error = ""
    groupID = request.args.get("groupID")
    userID = request.args.get("userID")
    songID = request.args.get("songID")
    sourceID = request.args.get("sourceID")
    try:
        result = db.add_song_to_group(songID,sourceID,groupID,userID)
        sent = sources.group_notification(userID,groupID)
        if not result or not sent:
            error = "server"
    except Exception,e:
        print "EXCEPTION ADDING GROUPSONG:",e
        error = "server"
    return json.dumps({"error":error})

@app.route('/add/user', methods=['GET'])
def add_user(userID):
    userID = request.args.get("userID")
    picURL = request.args.get("profilePictureURL")
    name = request.args.get("name")
    deviceToken = request.args.get("deviceToken")
    s = False
    if db.add_user(user_id=userID,picURL=picURL,name=name,deviceToken=deviceToken):
        s = True
    return json.dumps({"ADD":s})

# add blog source
@app.route('/add/source/blog', methods=['GET'])
def add_blog_source():
    sourceURL = request.args.get("sourceURL")
    userID = request.args.get("userID")
    result = sources.add_blog_source(sourceURL,userID)
    return json.dumps(result)

# add soundcloud source
@app.route('/add/source/sc', methods=['GET'])
def add_sc_source():
    scID = request.args.get("scID")
    userID = request.args.get("userID")
    result = sources.add_sc_source(scID,userID)
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
    raw_recs = db.get_user_recommendations(userID)
    results = {"recommendations":[]}
    for i in raw_recs:
        results["recommendations"].append(sources.format_source_result(i))
    return json.dumps(results)

@app.route('/get/groups/<userID>', methods=['GET'])
def get_group(userID):
    groups = db.get_groups_by_user_id(userID)
    return json.dumps({"groups":groups})


@app.route('/startscraping', methods=['GET'])
def startscraping():
    sources.refresh_handler()
    return "scraping"

@app.route('/cleardb', methods=['GET'])
def cleardb():
    db.remove_all()
    return "True"


if __name__ == '__main__':
    app.run(debug=True)

