from pymongo import MongoClient

client = MongoClient()
db = client.circadian

sources = db.sources

def format_mongo_objs(mongo_objs):
    """
    Formats python datetime into isoformat for each mongo_obj
    if the obj has a time.
    Also strips out object ID
    """
    if not mongo_objs:
        return []
    for mongo_obj in mongo_objs:
        # remove object_id
        try:
            mongo_obj.pop('_id')
        except:
            print "API: mongo_obj has no _id, panic!"

        old_time = mongo_obj.get('time')
        if old_time:
            mongo_obj['time'] = old_time.isoformat()

        #Case for times nested in "data" field, for static json
        data = mongo_obj.get('data')
        if data:
            old_time_2 = data.get('time')
            if old_time_2:
                print mongo_obj['data']['time'][0]
                mongo_obj['data']['time'][0] = old_time_2[0].isoformat()

    return mongo_objs

def get_source_by_url(source_url):
	"""
	Returns the MongoObject with source_url == source_url if one exists.
	"""
	result = sources.find({"source_url": source_url})
	if result.count() != 0:
		return 

def get_source_by_id(source_id):
	"""
	Returns the MongoObject with id == source_id if one exists.
	"""
