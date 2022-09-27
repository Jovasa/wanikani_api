from __future__ import annotations

import json
from typing import AnyStr, Union, Iterable, Dict
from datetime import datetime
from urllib.parse import quote

import urllib3
from pymongo import MongoClient
from urllib3.exceptions import HTTPError


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
        self._personal_cache = self.db[self._user["_id"]]

    def get_assignments(self, ids: Union[int, Iterable, None] = None, **kwargs):
        pass

    def start_assignment(self, sid: int, started_at: Union[datetime, str, None] = None):
        pass

    def get_level_progressions(self,
                               ids: [int, Iterable, None] = None,
                               updated_after: Union[datetime, str, None] = None):
        request_type = "level_progression"
        return self._ids_updated_after_request(ids, updated_after, request_type)

    def get_resets(self, ids: [int, Iterable, None] = None, updated_after: Union[datetime, str, None] = None):
        return self._ids_updated_after_request(ids, updated_after, "reset")

    def get_reviews(self, ids: Union[int, Iterable, None] = None, **kwargs):
        pass

    def create_review(self, aid: Union[int, None] = None, sid: Union[int, None] = None, **kwargs):
        assert aid is not None or sid is not None
        pass

    def get_review_statistics(self, ids: Union[int, Iterable, None] = None, **kwargs):
        pass

    def get_srs_systems(self, ids: Union[int, Iterable, None] = None, updated_after: Union[datetime, str, None] = None):
        return self._ids_updated_after_request(ids, updated_after, "spaced_repetition_system")

    def get_study_materials(self, ids: Union[int, Iterable, None] = None, **kwargs):
        pass

    def create_study_material(self, sid: int, **kwargs):
        pass

    def update_study_material(self, sid: int, **kwargs):
        pass

    def get_subjects(self, ids: Union[int, Iterable, None] = None, **kwargs):
        pass

    def get_summary(self):
        url = "https://api.wanikani.com/v2/summary"
        headers = self._get_header(url)
        try:
            request = self._http.request(
                "GET",
                url,
                headers=headers
            )
        except HTTPError:
            # TODO: parameter for whether it is acceptable for the user
            # to use cached data in case the request failed
            report = self._personal_cache.find_one({"object": "report"})
            if report:
                return report
            # TODO: This should be custom error
            raise

        if request.status == 304:
            return self._personal_cache.find_one({"object": "report"})

        data = json.loads(request.data.decode("utf-8"))
        self._set_etag(url, request.headers)

        self._personal_cache.update_one({"object": "report"}, {"$set": data}, upsert=True)
        return data

    def get_user(self):
        user_db = self.db["users"]
        url = "https://api.wanikani.com/v2/user"
        headers = self._get_header(url)
        try:
            request = self._http.request(
                "GET",
                url,
                headers=headers
            )
        except HTTPError:
            # TODO: parameter for whether it is acceptable for the user
            # to use cached data in case the request failed
            user = user_db.find_one({"tokens": {"$in": [self._token]}})
            if user:
                return user
            # TODO: This should be custom error
            raise

        if request.status == 304:
            return user_db.find_one({"tokens": {"$in": [self._token]}})
        user_data = json.loads(request.data.decode("utf-8"))
        self._set_etag(url, request.headers, user_data["data"]["id"])

        uid = user_data["data"]["id"]
        user = user_db.find_one({"_id": uid})

        # Since one user can have multiple tokens, it is better
        # to keep track of the tokens the user has so that we can
        # cache data based on the user and not the token
        if user is not None:
            if self._token not in user["tokens"]:
                user_db.update_one({"_id": uid}, {"$push": {"tokens": self._token}})
            else:
                # The data was updated
                user_data["tokens"] = user["tokens"]
                user_data["_id"] = uid
                user_db.replace_one({"_id": uid}, user_data)
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
        return self._ids_updated_after_request(ids, updated_after, "voice_actor")

    def _get_etag_for_url(self, url: str, headers: Dict):
        if not hasattr(self, "_user"):
            return
        uid = self._user["_id"]
        if (data := self._etag_db.find_one({"uid": uid, "url": url})) is not None:
            headers["If-Modified-Since"] = data["Last-Modified"]
            headers["If-None-Match"] = data["ETag"]

    def _set_etag(self, url: str, header: Dict, uid=None):
        uid = uid or self._user["_id"]
        try:
            last_modified = header["Last-Modified"]
            etag = header["ETag"]
            self._etag_db.update_one(
                {"uid": uid, "url": url},
                {"$set": {"uid": uid, "url": url, "Last-Modified": last_modified, "ETag": etag}},
                upsert=True
            )
        except KeyError:
            pass

    def _get_header(self, url):
        headers = {"Authorization": f"Bearer {self._token}"}
        self._get_etag_for_url(url, headers)
        return headers

    def _ids_updated_after_request(self,
                                   ids: Union[int, Iterable, None],
                                   updated_after: Union[datetime, str, None],
                                   request_type: str):
        if type(ids) is int and updated_after is None:
            url = f"https://api.wanikani.com/v2/{request_type}s/{ids}"
            cached = self._personal_cache.find_one({"object": request_type, "id": ids})
        else:
            url_params = []
            filter_args = {"object": request_type}
            if ids is not None:
                if type(ids) is int:
                    ids = [int]
                url_params.append(f"ids={','.join(ids)}")
                filter_args["id"] = {"$in", ids}
            if updated_after is not None:
                if type(updated_after) is str:
                    updated_after = datetime.fromisoformat(updated_after)

                url_params.append(updated_after.isoformat())
                filter_args["data_updated_at"] = {"$gte": updated_after}

            params_string = '&'.join(quote(x) for x in url_params)
            url = f"https://api.wanikani.com/v2/{request_type}s{'?' if url_params else ''}{params_string}"

            cached = self._personal_cache.find(filter_args)

        data_out = []
        while url:
            headers = self._get_header(url)

            request = self._http.request(
                "GET",
                url,
                headers=headers
            )

            # Technically this could cause issues if the first url would not have 304
            # but the second does have, but I don't think that is a feasible case in
            # real world. Like the API should return 200 for all the data.
            if request.status == 304:
                print("Was cached")
                return cached

            data = json.loads(request.data.decode("utf-8"))
            self._set_etag(url, request.headers)

            if "pages" in data:
                data_out.extend(data["data"])
                url = data["pages"]["next_url"]
            else:
                data["data_updated_at"] = datetime.fromisoformat(data["data_updated_at"].replace("Z", "+00:00"))
                return data

        for item in data_out:
            item["data_updated_at"] = datetime.fromisoformat(item["data_updated_at"].replace("Z", "+00:00"))
            self._personal_cache.update_one({"object": request_type, "id": item["id"]},
                                            {"$set": item},
                                            upsert=True)
        return data_out
