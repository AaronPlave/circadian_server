import soundcloud
import db
import datetime
from scraping import modifySoundCloudObject, TIME_DELTA

CLIENT_ID = "a9c272921e809f861f1951ea6ff1f829"
CLIENT_SECRET = "6d4cea605ed5e4c48bec8a48ef545310"
client = soundcloud.Client(client_id=CLIENT_ID)

def validate_new_user(data):
	sc_id = data[0]
	user_id = data[1]
	print "SCID:",sc_id
	sc_user = get_user_by_id(sc_id)
	if not sc_user:
		print "SC: No user found"
		return

	# add user to db
	sourceID = db.add_sc_user_to_db(sc_id,sc_user.fields().get("username"))

	if not db.link_source_and_user(sourceID, user_id):
		return "server"

	sc_user_songs = get_user_songs(sc_user.obj.get("id"))
	if sc_user_songs:
		sc_user_songs = [modifySoundCloudObject(i.obj) for i in sc_user_songs]
		for i in sc_user_songs:
			db.add_song_to_source(i,sourceID)

	# Update last update time in status
	db.set_last_update_time(datetime.datetime.now())
	return "good"

def get_user_by_id(sc_id):
	"""
	Searches SC for user with 'id' == sc_id
	"""
	try:
		res = client.get("/users/"+str(sc_id))
	except:
		print "SC: Unable to find user:",sc_id
		return
	if res.status_code != 200:
		print "SC: Status code != 200 for get_user_by_id for user:",sc_id
		return
	return res

def get_user_songs(sc_id):
	"""
	Gets a user's tracks by sc_id
	"""
	now = datetime.datetime.today()
	today = datetime.datetime(now.year, now.month, now.day)
	time_backwards = today - datetime.timedelta(hours=TIME_DELTA)
	try:
		res = client.get("/users/"+str(sc_id)+"/tracks",created_at={'from':time_backwards})
	except:
		print "SC: Unable to get user:",sc_id,"'s tracks"
		return
	if res.status_code != 200:
		print "SC: Status code != 200 for get_user_songs for user:",sc_id
		return
	return res