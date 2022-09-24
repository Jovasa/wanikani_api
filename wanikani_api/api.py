from __future__ import annotations

import json
from typing import AnyStr, Union, Iterable, Dict
from datetime import datetime

import urllib3
from pymongo import MongoClient


class UserHandle:
    mongodb_uri = "mongodb://localhost:27017"
    mongo_client = MongoClient(mongodb_uri)
    db = mongo_client["wanikani"]

    def __init__(self, token: AnyStr):
        self._token = token
        self._http = urllib3.PoolManager()
        self._etag_db = self.db["ETag"]
        users_db = self.db["users"]
        user = users_db.find_one({"tokens": {"$in": [token]}})
        if user is not None:
            self._user = user
        else:
            self._user = self.get_user()

    def get_assignments(self, ids: Union[int, Iterable, None] = None, **kwargs):
        pass

    def start_assignment(self, sid: int, started_at: Union[datetime, str, None] = None):
        pass

    def get_level_progressions(self,
                               ids: [int, Iterable, None] = None,
                               updated_after: Union[datetime, str, None] = None):
        pass

    def get_resets(self, ids: [int, Iterable, None] = None, updated_after: Union[datetime, str, None] = None):
        pass

    def get_reviews(self, ids: Union[int, Iterable, None] = None, **kwargs):
        pass

    def create_review(self, aid: Union[int, None] = None, sid: Union[int, None] = None, **kwargs):
        assert aid is not None or sid is not None
        pass

    def get_review_statistics(self, ids: Union[int, Iterable, None] = None, **kwargs):
        pass

    def get_srs_systems(self, ids: Union[int, Iterable, None] = None, updated_after: Union[datetime, str, None] = None):
        pass

    def get_study_materials(self, ids: Union[int, Iterable, None] = None, **kwargs):
        pass

    def create_study_material(self, sid: int, **kwargs):
        pass

    def update_study_material(self, sid: int, **kwargs):
        pass

    def get_subjects(self, ids: Union[int, Iterable, None] = None, **kwargs):
        pass

    def get_summary(self):
        pass

    def get_user(self):
        user_db = self.db["users"]
        url = "https://api.wanikani.com/v2/user"
        headers = {"Authorization": f"Bearer {self._token}"}
        self._get_etag_for_url(url, headers)
        request = self._http.request(
            "GET",
            url,
            headers=headers
        )
        if request.status == 304:
            return user_db.find_one({"tokens": {"$in": [self._token]}})
        user_data = json.loads(request.data.decode("utf-8"))
        self._set_etag(url, request.headers)

        uid = user_data["data"]["id"]
        user = user_db.find_one({"_id": uid})

        # Since one user can have multiple tokens, it is better
        # to keep track of the tokens the user has so that we can
        # cache data based on the user and not the token
        if user is not None:
            if self._token not in user["tokens"]:
                user_db.update_one({"_id": uid}, {"$push": {"tokens": self._token}})
        else:
            user = user_data
            user["_id"] = uid
            user["tokens"] = [self._token]
            user_db.insert_one(user)

        return user

    def update_user(self, **kwargs):
        pass

    def get_voice_actors(self,
                         ids: Union[int, Iterable, None] = None,
                         updated_after: Union[datetime, str, None] = None):
        pass

    def _get_etag_for_url(self, url: str, headers: Dict):
        uid = self._user["_id"]
        if (data := self._etag_db.find_one({"uid": uid, "url": url})) is not None:
            headers["If-Modified-Since"] = data["Last-Modified"]
            headers["If-None-Match"] = data["ETag"]

    def _set_etag(self, url: str, header: Dict):
        uid = self._user["_id"]
        try:
            last_modified = header["Last-Modified"]
            etag = header["ETag"]
            self._etag_db.insert_one({"uid": uid, "url": url, "Last-Modified": last_modified, "ETag": etag})
        except KeyError:
            pass