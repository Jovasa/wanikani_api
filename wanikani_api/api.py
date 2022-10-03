from __future__ import annotations

import json
import pprint
from typing import AnyStr, Union, Iterable, Dict, List
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
        self._subject_cache = self.db["subjects"]
        users_db = self.db["users"]
        user = users_db.find_one({"tokens": {"$in": [token]}})
        if user is not None:
            self._user = user
        else:
            self._user = self.get_user()
        self._personal_cache = self.db[self._user["_id"]]

    def get_assignments(self,
                        *,
                        ids: Union[int, Iterable, None] = None,
                        available_after: Union[datetime, str, None] = None,
                        available_before: Union[datetime, str, None] = None,
                        burned: Union[bool, None] = None,
                        hidden: Union[bool, None] = None,
                        immediately_available_for_lessons: Union[bool, None] = None,
                        immediately_available_for_review: Union[bool, None] = None,
                        in_review: Union[bool, None] = None,
                        levels: Union[List[int], None] = None,
                        srs_stages: Union[List[int], None] = None,
                        started: Union[bool, None] = None,
                        subject_ids: Union[List[int], None] = None,
                        subject_types: Union[List[str], None] = None,
                        unlocked: Union[bool, None] = None,
                        updated_after: Union[datetime, str, None] = None):
        local_args = locals()
        return self._complex_request("assignment", **{k: local_args[k] for k in self.get_assignments.__kwdefaults__})

    def start_assignment(self, sid: int, started_at: Union[datetime, str, None] = None):
        pass

    def get_level_progressions(self,
                               ids: [int, Iterable, None] = None,
                               updated_after: Union[datetime, str, None] = None):
        request_type = "level_progression"
        return self._ids_updated_after_request(ids, updated_after, request_type)

    def get_resets(self, ids: [int, Iterable, None] = None, updated_after: Union[datetime, str, None] = None):
        return self._ids_updated_after_request(ids, updated_after, "reset")

    def get_reviews(self,
                    *,
                    ids: Union[int, Iterable, None] = None,
                    assignment_ids: Union[List[int], None] = None,
                    subject_ids: Union[List[int], None] = None,
                    updated_after: Union[datetime, str, None] = None):
        local_args = locals()
        return self._complex_request("review", **{k: local_args[k] for k in self.get_assignments.__kwdefaults__})

    def create_review(self, aid: Union[int, None] = None, sid: Union[int, None] = None, **kwargs):
        assert aid is not None or sid is not None
        pass

    def get_review_statistics(self,
                              *,
                              ids: Union[int, Iterable, None] = None,
                              hidden: Union[bool, None] = None,
                              percentages_greater_than: Union[int, None] = None,
                              percentages_less_than: Union[int, None] = None,
                              subject_ids: Union[List[int], None] = None,
                              subject_types: Union[List[str], None] = None,
                              updated_after: Union[datetime, str, None] = None):
        local_args = locals()
        return self._complex_request("review_statistic",
                                     **{k: local_args[k] for k in self.get_assignments.__kwdefaults__})

    def get_srs_systems(self, ids: Union[int, Iterable, None] = None, updated_after: Union[datetime, str, None] = None):
        return self._ids_updated_after_request(ids, updated_after, "spaced_repetition_system")

    def get_study_materials(self,
                            *,
                            ids: Union[int, Iterable, None] = None,
                            hidden: Union[bool, None] = None,
                            subject_ids: Union[List[int], None] = None,
                            subject_types: Union[List[str], None] = None,
                            updated_after: Union[datetime, str, None] = None):
        local_args = locals()
        return self._complex_request("study_material",
                                     **{k: local_args[k] for k in self.get_assignments.__kwdefaults__})

    def create_study_material(self,
                              sid: int,
                              *,
                              meaning_note: Union[str, None] = None,
                              reading_note: Union[str, None] = None,
                              meaning_synonyms: Union[List[str], None] = None
                              ):
        data = {
            "subject_id": sid
        }
        for k in self.create_study_material.__kwdefaults__:
            if (val := locals()[k]) is not None:
                data[k] = val

        request = self._http.request(
            "POST",
            "https://api.wanikani.com/v2/study_materials/",
            body=json.dumps(data).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._token}",
                'Content-Type': 'application/json; charset=utf-8'
            }
        )
        d = json.loads(request.data.decode("utf-8"))
        if request.status >= 400:
            print(d)
            raise ValueError

        print(d)
        self._personal_cache.insert_one(d)
        return d

    def update_study_material(self, sid: int,
                              *,
                              meaning_note: Union[str, None] = None,
                              reading_note: Union[str, None] = None,
                              meaning_synonyms: Union[List[str], None] = None):
        data = {}
        for k in self.create_study_material.__kwdefaults__:
            if (val := locals()[k]) is not None:
                data[k] = val

        request = self._http.request(
            "PUT",
            f"https://api.wanikani.com/v2/study_materials/{sid}",
            body=json.dumps(data).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._token}",
                'Content-Type': 'application/json; charset=utf-8'
            }
        )
        d = json.loads(request.data.decode("utf-8"))
        if request.status >= 400:
            print(d)
            raise ValueError

        print(d)
        self._personal_cache.update_one({"id": sid,
                                         "object": "study_material"}, {"$set": d})
        return d

    def get_subjects(self,
                     *,
                     ids: Union[int, Iterable, None] = None,
                     types: Union[List[str], None] = None,
                     slugs: Union[List[str], None] = None,
                     levels: Union[List[int], None] = None,
                     hidden: Union[bool, None] = None,
                     updated_after: Union[datetime, str, None] = None):
        url_params = []
        filter_args = {
            "object": {"$in": ["kanji", "vocabulary", "radical"] if types is None else types}
        }
        if types is not None:
            url_params.append(f"types={','.join(types)}")
        if levels is not None:
            url_params.append(f"levels={','.join([str(x) for x in levels])}")
            filter_args["data.level"] = {"$in": levels}
        if ids is not None:
            temp = ids
            if type(ids) is int:
                temp = [ids]
            url_params.append(f"ids={','.join([str(x) for x in temp])}")
            filter_args["id"] = {"$in": temp}
        if slugs is not None:
            url_params.append(f"slugs={','.join(slugs)}")
            filter_args["data.slug"] = {"$in": slugs}
        if hidden is not None:
            url_params.append(f"hidden={str(hidden).lower()}")
            filter_args["data.hidden_at"] = None if not hidden else {"$ne": None}
        if updated_after is not None:
            if type(updated_after) is str:
                updated_after = datetime.fromisoformat(updated_after)
            url_params.append(f"updated_after={quote(updated_after.isoformat())}")
            filter_args["data_updated_at"] = {"$gte": updated_after}

        is_singular = type(ids) is int and len(url_params) == 1
        if not is_singular:
            params_string = '&'.join(url_params)
            url = f"https://api.wanikani.com/v2/subjects{'?' if url_params else ''}{params_string}"
            cached = self._subject_cache.find(filter_args)
        else:
            url = f"https://api.wanikani.com/v2/subjects/{ids}"
            cached = self._subject_cache.find_one(filter_args)

        data_out = []
        while url:
            headers = {"Authorization": f"Bearer {self._token}"}
            if (etags := self._etag_db.find_one({"url": url})) is not None:
                headers["If-Modified-Since"] = etags["Last-Modified"]
                headers["If-None-Match"] = etags["ETag"]

            request = self._http.request(
                "GET",
                url,
                headers=headers
            )

            # Technically this could cause issues if the first url would not have 304
            # but the second does have, but I don't think that is a feasible case in
            # real world. Like the API should return 200 for all the data.
            if request.status == 304:
                return cached

            data = json.loads(request.data.decode("utf-8"))
            pprint.pprint(request.headers)

            try:
                last_modified = request.headers["Last-Modified"]
                etag = request.headers["ETag"]
                self._etag_db.update_one(
                    {"url": url},
                    {"$set": {"url": url, "Last-Modified": last_modified, "ETag": etag}},
                    upsert=True
                )
            except KeyError:
                pass

            if "pages" in data:
                data_out.extend(data["data"])
                url = data["pages"]["next_url"]
            else:
                self._convert_dates(data)
                self._subject_cache.update_one({"object": data["object"], "id": data["id"]},
                                               {"$set": data},
                                               upsert=True)
                return data
        for item in data_out:
            self._convert_dates(item)
            self._subject_cache.update_one({"object": item["object"], "id": item["id"]},
                                           {"$set": item},
                                           upsert=True)
        return data_out

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
                url_params.append(f"ids={','.join(str(x) for x in ids)}")
                filter_args["id"] = {"$in", ids}
            if updated_after is not None:
                if type(updated_after) is str:
                    updated_after = datetime.fromisoformat(updated_after)

                url_params.append(f"updated_after={quote(updated_after.isoformat())}")
                filter_args["data_updated_at"] = {"$gte": updated_after}

            params_string = '&'.join(url_params)
            url = f"https://api.wanikani.com/v2/{request_type}s{'?' if url_params else ''}{params_string}"

            cached = self._personal_cache.find(filter_args)

        return self._do_requests(cached, request_type, url)

    def _complex_request(self, request_type, **kwargs):
        url_params = []
        filter_args = {"object": request_type}
        local_args = locals()
        self._parse_query_parameters(url_params,
                                     filter_args,
                                     request_type == "assignment",
                                     **kwargs)

        is_singular = "ids" in kwargs and type(kwargs["ids"]) is int and len(url_params) == 1
        if not is_singular:
            params_string = '&'.join(url_params)
            url = f"https://api.wanikani.com/v2/{request_type}s{'?' if url_params else ''}{params_string}"
        else:
            url = f"https://api.wanikani.com/v2/{request_type}s/{kwargs['ids']}"

        cached = None
        can_use_cache = ("levels" not in kwargs or kwargs["levels"] is None) and \
                        ("immediately_available_for_lessons" not in kwargs or kwargs[
                            "immediately_available_for_lessons"] is None) and \
                        ("immediately_available_for_review" not in kwargs or kwargs[
                            "immediately_available_for_review"] is None) and \
                        ("in_review" not in kwargs or kwargs["in_review"] is None)
        if can_use_cache:
            if is_singular:
                cached = self._personal_cache.find_one(filter_args)
            else:
                cached = self._personal_cache.find(filter_args)

        return self._do_requests(cached, request_type, url, can_use_cache)

    def _do_requests(self, cached, request_type, url, can_use_cache=True):
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
            if can_use_cache:
                self._set_etag(url, request.headers)

            if "pages" in data:
                data_out.extend(data["data"])
                url = data["pages"]["next_url"]
            else:
                self._convert_dates(data)
                self._personal_cache.update_one({"object": request_type, "id": data["id"]},
                                                {"$set": data},
                                                upsert=True)
                return data
        for item in data_out:
            self._convert_dates(item)
            self._personal_cache.update_one({"object": request_type, "id": item["id"]},
                                            {"$set": item},
                                            upsert=True)
        return data_out

    @staticmethod
    def _parse_query_parameters(url_params: list, filter_params: dict, is_assignment, **kwargs):
        filter_params["data"] = {}
        for param, value in kwargs.items():
            if value is None:
                continue
            if param == "immediately_available_for_lessons":
                url_params.append(param)
                filter_params["data.unlocked_at"] = {"$lte": datetime.now()}
                filter_params["data.started_at"] = None
            elif param == "immediately_available_for_review":
                url_params.append(param)
                filter_params["data.available_at"] = {"$lte": datetime.now()}
            elif param == "in_review":
                url_params.append(param)
                filter_params["data.available_at"] = {"$ne": None}
            else:
                if "before" in param or "after" in param:
                    if type(value) is str:
                        value = datetime.fromisoformat(value)
                    url_params.append(f"{param}={quote(value.isoformat())}")

                    if param == "updated_after":
                        filter_params["data_updated_at"] = {"$gte": value}
                    elif all([x in kwargs for x in ["available_before", "updated_after"]]):
                        after = kwargs["available_after"]
                        before = kwargs["available_before"]
                        filter_params["data.available_at"] = {
                            "$gte": datetime.fromisoformat(after) if type(after) is str else after,
                            "$lte": datetime.fromisoformat(before) if type(before) is str else before,
                        }
                    elif param == "available_after":
                        filter_params["data.available_at"] = {"$gte": value}
                    elif param == "available_before":
                        filter_params["data.available_at"] = {"$lte": value}
                    continue

                if "percentage" in param:
                    if "percentages_greater_than" in kwargs and "percentages_less_than" in kwargs:
                        upper = kwargs["percentages_less_than"]
                        lower = kwargs["percentages_greater_than"]
                        filter_params["data.percentage_correct"] = {
                            "$gt": lower,
                            "$lt": upper,
                        }
                    elif param == "percentages_less_than":
                        filter_params["data.percentage_correct"] = {"$lt": kwargs["percentages_less_than"], }

                    elif param == "percentages_greater_than":
                        filter_params["data.percentage_correct"] = {"$gt": kwargs["percentages_greater_than"], }
                    continue

                if type(value) in [str, int]:
                    value = [value]

                if type(value) is bool:
                    url_params.append(f"{param}={str(value).lower()}")
                    if is_assignment:
                        filter_params[f"data.{param}_at"] = {"$ne": None} if value else None
                    else:
                        filter_params[f"data.{param}"] = value
                else:
                    url_params.append(f"{param}={','.join(str(x) for x in value)}")
                    if param == "ids":
                        filter_params["id"] = {"$in": value}
                    elif param != "levels":
                        filter_params[f"data.{param[0:-1]}"] = {"$in": value}

    @staticmethod
    def _convert_dates(obj: dict):
        obj["data_updated_at"] = datetime.fromisoformat(obj["data_updated_at"].replace("Z", "+00:00"))
        for key, value in obj["data"].items():
            if key.endswith("_at") and value is not None:
                obj["data"][key] = datetime.fromisoformat(obj["data"][key].replace("Z", "+00:00"))
