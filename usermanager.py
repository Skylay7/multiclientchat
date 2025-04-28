from user import User
import logging


class UserManager:

    def __init__(self):
        self._socket_to_user = {}

    def create_user(self, username, socket, address):
        new_user = User(username, address)
        self._socket_to_user[socket] = new_user

    def remove_user(self, socket):
        if socket not in self._socket_to_user:
            logging.warning(f"Attempt to remove non-existent socket: {socket}")
            return False  # Return False to indicate failure

        return self._socket_to_user.pop(socket, None)

    def get_users(self):
        return self._socket_to_user.values()

    def get_user_by_socket(self, socket):
        if socket not in self._socket_to_user:
            logging.warning(f"Attempt to get non-existent socket: {socket}")
            return None  # Return None to indicate failure

        return self._socket_to_user[socket]

    def get_user_by_name(self, username):
        """Returns user by username if exists. if not returns None"""
        return list(filter(lambda user: user.name == username, self._socket_to_user.values()))

    def get_list_of_users_without_users(self, user_list):
        if type(user_list) is not list:
            raise ValueError("user_list must be a list.")

        new_user_list = list(self._socket_to_user.values())
        for user in user_list:
            new_user_list.remove(user)
        return new_user_list

    def get_socket_by_user(self, user):
        if user and type(user) is User:
            return list(filter(lambda x: self._socket_to_user[x] == user, self._socket_to_user))[0]
        return None

    def clear_user_manager(self):
        self._socket_to_user.clear()
