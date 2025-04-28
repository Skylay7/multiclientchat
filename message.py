import datetime
from abc import ABC, abstractmethod


class Message(ABC):
    MESSAGE_TYPES = {"Text": "0",
                     "Binary": "1",
                     "System": "2"}

    def __init__(self, content, message_type):
        self.content = content
        self.message_type = message_type

    @abstractmethod
    def create_message(self):
        return f"{self.message_type}|{self.content}"


class TextMessage(Message):

    def __init__(self, content, message_type):
        self.time_of_upload = datetime.datetime.now().strftime("%H:%M")
        super().__init__(content, message_type)

    def create_message(self):
        message_build = f"{self.message_type}|{self.time_of_upload} {self.content}"
        return message_build


class ChatMessage(TextMessage):

    def __init__(self, content, message_type, sender):
        super().__init__(content, message_type)
        self.sender_name = sender

    def create_message(self):
        message_build = f"{self.message_type}|{self.time_of_upload} {self.sender_name} : {self.content}"
        return message_build


class PrivateMessage(ChatMessage):

    def create_message(self):
        message_build = f"{self.message_type}|{self.time_of_upload} Private Message From {self.sender_name} : {self.content}"
        return message_build


class TextSystemMessage(TextMessage):
    pass


class SystemMessage(Message):
    def create_message(self):
        return super().create_message()


class Frame(Message):

    def create_message(self):
        return f"{self.message_type}|".encode() + self.content
