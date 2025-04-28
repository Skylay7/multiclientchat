import uuid
from enum import Enum


class UserStatus(Enum):
    RegularUser = 1
    Administrator = 2
    Owner = 3


class User:

    def __init__(self, name, address):
        self.name = name
        self.address = address
        self.id = str(uuid.uuid4())  # unique id for identification
        self.message_queue = []
        self.status = UserStatus.RegularUser
        self.is_sharing_screen = False
        self.watchers = []
        self.watching = None

    def __repr__(self):
        return f"User({self.name}, {self.address}, {self.id})"

    def set_user_share_screen(self):
        if self.is_sharing_screen:
            return None
        self.is_sharing_screen = True
        self.watchers = []
        return "User is set"

    def is_user_watching_stream(self, user):
        if type(user) is not User:
            raise ValueError("param must be User.")
        return user in self.watchers

    def add_user_to_watchers_list(self, user):
        if type(user) is not User:
            raise ValueError("param must be User.")
        self.watchers.append(user)

    def remove_user_from_watchers_list(self, user):
        if type(user) is not User:
            raise ValueError("param must be User.")
        self.watchers.remove(user)

