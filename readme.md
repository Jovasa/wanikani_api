# Python wrapper for the Wanikani API

Currently, implements all endpoints and caching using mongodb.
Not tested for all endpoints but *should* be working.
However, will only work properly when proper data is given and otherwise will fail.

## MongoDB
MongoDB is required for usage, and mongo_db uri can be set using environmental variable `WANIKANI_API_MONGODB_URI`, defaults to `mongodb://localhost:27017` if nothing is set.

## WIP
* Directly accessing the cache instead of forcing to make a 304 request to access the cache