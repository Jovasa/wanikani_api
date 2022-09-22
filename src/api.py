from __future__ import annotations
from typing import AnyStr, Union, Iterable
from datetime import datetime


class UserHandle:
    mongodb_uri = "mongodb://localhost:27017"

    def __init__(self, token: AnyStr):
        pass

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
        pass

    def update_user(self, **kwargs):
        pass

    def get_voice_actors(self,
                         ids: Union[int, Iterable, None] = None,
                         updated_after: Union[datetime, str, None] = None):
        pass
