import socket
import select
import logging
from typing import List, Tuple, Optional, Any
import protocol
from user import UserStatus
from user import User
from usermanager import UserManager
import message

MAX_QUEUE_SIZE = 500
user_manager = UserManager()

message_types = message.Message.MESSAGE_TYPES
available_commands = ["SEND_MESSAGE", "CHANGE_NAME", "CHANGE_STATUS", "KICK_USER", "SEND_PRIVATE_MESSAGE",
                      "START_SHARE_SCREEN", "END_SHARE_SCREEN", "JOIN_SHARE_SCREEN", "LEAVE_SHARE_SCREEN", "QUIT"]
open_client_sockets = []
errors_to_send = []


def handle_clients(server_socket) -> None:
    while True:
        try:
            rlist, wlist, _ = select.select([server_socket] + open_client_sockets, open_client_sockets, [])
        except ValueError:
            logging.error("Error in select: Cleaning up stale sockets.")
            clean_closed_sockets()
            continue
        if rlist:
            handle_requests(rlist, server_socket)
        if wlist:
            handle_responses_errors(wlist)
            handle_chat_responses(wlist)


def handle_requests(rlist, server_socket) -> None:
    for current_socket in rlist:
        if current_socket is server_socket:
            try:
                handle_new_connection(server_socket)
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                logging.error(f"Client crashed: {current_socket.getpeername()}")
                handle_client_quiting(current_socket, None)
            except Exception as e:
                logging.error(f"Error accepting new connection: {e}")
        else:
            try:
                data = protocol.get_analyzed_data(current_socket)
                if data == b"":
                    logging.info("Connection Closed")
                    handle_client_quiting(current_socket, None)
                elif data is None:
                    continue
                    # print("Error while receiving")
                else:
                    handle_command_request(current_socket, data)
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                logging.error(f"Client crashed: {current_socket.getpeername()}")
                handle_client_quiting(current_socket, None)
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                handle_client_quiting(current_socket, None)


def handle_new_connection(server_socket) -> None:
    connection, client_address = server_socket.accept()
    logging.info(f"New client {client_address} joined!")

    username = protocol.get_analyzed_data(connection).decode()
    user_manager.create_user(username, connection, client_address)
    new_user = user_manager.get_user_by_socket(connection)

    if len(open_client_sockets) == 0:
        new_user.status = UserStatus.Owner

    # Update user dictionary and open sockets list
    open_client_sockets.append(connection)

    new_user_list = user_manager.get_list_of_users_without_users([new_user])
    send_text_system_message(f"{new_user.name} joined the chat.", new_user_list)

    # Send UUID to the client
    connection.send(protocol.create_message(new_user.id))
    logging.info(f"Assigned UUID {new_user.id} to {new_user.name}")


def handle_command_request(current_socket, data) -> None:
    try:
        uuid, message_type, command, content, user = analyze_command(current_socket, data)
    except Exception as e:
        user = user_manager.get_user_by_socket(current_socket)
        send_text_system_message("Error: Mistake in Message format", [user])
        logging.error(f"Error : {e}")
        return

    if message_type == message_types["Binary"]:
        send_frame(content, user.watchers)

    elif message_type == message_types["Text"]:
        if command == "SEND_MESSAGE":  # Send message
            send_message(content, user)
        elif command == "CHANGE_NAME":  # Update username
            handle_change_name(content, user)
        elif command == "QUIT":  # Quit
            handle_client_quiting(current_socket, user)
        elif command == "CHANGE_STATUS":
            handle_status_change(user, content)
        elif command == "KICK_USER":
            handle_kick_user(user, content)
        elif command == "SEND_PRIVATE_MESSAGE":
            handle_private_messages(user, content)
        elif command == "START_SHARE_SCREEN":
            handle_start_share_screen(user)
        elif command == "JOIN_SHARE_SCREEN":
            handle_join_share_screen(user, content)
        elif command == "LEAVE_SHARE_SCREEN":
            handle_leave_share_screen(user)
        elif command == "END_SHARE_SCREEN":
            handle_end_share_screen(user)


def analyze_command(current_socket, data) -> None | tuple[str, str, Optional[str], bytes, Optional[User]]:
    # Define the delimiter as bytes
    delimiter = protocol.DELIMITER.encode()

    # Find the first three delimiters to separate the header

    uuid_end = data.find(delimiter)
    type_end = data.find(delimiter, uuid_end + 1)

    # Extract uuid, message_type, and command
    uuid = data[:uuid_end].decode()
    message_type = data[uuid_end + 1:type_end].decode()
    content = data[type_end + 1:]

    # Validate user
    user = user_manager.get_user_by_socket(current_socket)
    if not user or user.id != uuid:
        send_text_system_message("Error: Invalid UUID", [user])
        return "", "", None, b"", None

    # Validate message type
    if message_type not in message_types.values():
        send_text_system_message("Error: Invalid type", [user])
        return "", "", None, b"", None
    if message_type == message_types["Binary"]:
        return uuid, message_type, None, content, user

    command_end = data.find(delimiter, type_end + 1)
    command = data[type_end + 1:command_end].decode()
    # Extract content
    content = data[command_end + 1:]  # Everything after the last delimiter
    if message_type == message_types["Text"]:
        # Decode content if it's text
        content = content.decode()
        if command not in available_commands:
            send_text_system_message("Error: Command does not exist", [user])
            return "", "", None, b"", None
    # Return the parsed components
    return uuid, message_type, command, content, user


def send_message(content, sender_user) -> None:
    message_obj = message.ChatMessage(content, message_types["Text"], sender_user.name)
    for user in user_manager.get_users():
        if sender_user != user:
            if len(user.message_queue) < MAX_QUEUE_SIZE:
                user.message_queue.append(message_obj)
            else:
                logging.info(f"Message queue for {user.name} is full. Dropping message.")


def send_system_message(user, content) -> None:
    message_obj = message.SystemMessage(content, message_types["System"])
    if len(user.message_queue) < MAX_QUEUE_SIZE:
        user.message_queue.append(message_obj)
    else:
        logging.info(f"Message queue for {user.name} is full. Dropping message.")


def handle_change_name(content, user) -> None:
    logging.info(f"User {user.name} changed name to {content}")
    user.name = content


def handle_client_quiting(current_socket, user) -> None:
    if user is None:
        user = user_manager.get_user_by_socket(current_socket)
    handle_leave_share_screen(user)
    list_of_users = user_manager.get_list_of_users_without_users([user])
    send_text_system_message(f"{user.name} left the chat.", list_of_users)
    remove_user(current_socket)


def send_text_system_message(content, list_of_users) -> None:
    message_obj = message.TextSystemMessage(content, message_types["Text"])
    for user in list_of_users:
        if len(user.message_queue) < MAX_QUEUE_SIZE:
            user.message_queue.append(message_obj)
        else:
            logging.info(f"Message queue for {user.name} is full. Dropping message.")


def send_private_message(content, sender_user, recipient_user) -> None:
    message_obj = message.PrivateMessage(content, message_types["Text"], sender_user.name)
    if len(recipient_user.message_queue) < MAX_QUEUE_SIZE:
        recipient_user.message_queue.append(message_obj)
    else:
        logging.info(f"Message queue for {recipient_user.name} is full. Dropping message.")


def handle_private_messages(sender, content) -> None:
    data_parts = content.split(protocol.DELIMITER)
    if len(data_parts) < 2:
        send_text_system_message("Error: params length.", [sender])
        return

    recipient_name = data_parts[0]
    recipient = user_manager.get_user_by_name(recipient_name)
    if not recipient:
        send_text_system_message("Error: Recipient not found.", [sender])
        return
    recipient = recipient[0]

    content = f"{protocol.DELIMITER}".join(data_parts[1:])
    send_private_message(content, sender, recipient)


def handle_status_change(sender, content) -> None:
    if sender.status != UserStatus.Administrator and sender.status != UserStatus.Owner:
        send_text_system_message("Error: Not enough permissions.", [sender])
        return

    status_to_change_to = content[0]
    if not status_to_change_to.isdigit() or status_to_change_to not in ['1', '2']:
        send_text_system_message("Error: Cant promote to unknown status.", [sender])
        return
    status_to_change_to = int(status_to_change_to)

    recipient_name = content[1:]
    recipient = user_manager.get_user_by_name(recipient_name)
    if not recipient:
        send_text_system_message("Error: Recipient not found.", [sender])
        return
    recipient = recipient[0]

    if recipient.status == UserStatus.Owner:
        send_text_system_message("Error: Cannot change status to owner.", [sender])
        return
    recipient.status = UserStatus(status_to_change_to)
    send_text_system_message(f"{recipient.name} status changed to {recipient.status}.", user_manager.get_users())


def handle_kick_user(sender, recipient_name) -> None:
    if not (sender.status == UserStatus.Administrator or sender.status == UserStatus.Owner):
        send_text_system_message("Error: Not enough permissions.", [sender])
        return

    recipient = user_manager.get_user_by_name(recipient_name)
    if not recipient:
        send_text_system_message("Error: Recipient not found.", [sender])
        return
    recipient = recipient[0]

    if recipient.status == UserStatus.Owner:
        send_text_system_message("Error: Cannot kick owner.", [sender])
        return

    recipient_sock = user_manager.get_socket_by_user(recipient)
    handle_client_quiting(recipient_sock, recipient)
    send_text_system_message(f"{recipient_name} was kicked by {sender.name}", user_manager.get_users())


def handle_start_share_screen(user) -> None:
    if type(user) is not User:
        logging.error("Was not given user")
        send_system_message(user, "DENIED_START")
        return
    result = user.set_user_share_screen()
    if result is None:
        logging.error(f"{user.name} Was already sharing screen")
        send_text_system_message("Error: Already Sharing Screen.", [user])
        send_system_message(user, "DENIED_START")
        return
    send_system_message(user, "CONFIRM_START")
    logging.info(f"{user.name} Started ShareScreen")


def handle_end_share_screen(user) -> None:
    if type(user) is not User:
        logging.error("Was not given user")
        return
    if not user.is_sharing_screen:
        send_text_system_message(f"Share-screen is not activated.", user.watchers)
        return
    send_text_system_message(f"{user.name} ended stream.", user.watchers)
    for watcher in user.watchers:
        handle_leave_share_screen(watcher)
    user.is_sharing_screen = False


def handle_join_share_screen(user, content) -> None:
    screen_sharer_name = content
    screen_sharer = user_manager.get_user_by_name(screen_sharer_name)
    if not screen_sharer:
        send_text_system_message("Error: Screen-sharer not found.", [user])
        send_system_message(user, "DENIED_JOIN")
        return
    screen_sharer = screen_sharer[0]

    if not screen_sharer.is_sharing_screen:
        send_text_system_message("Error: User is not Sharing screen.", [user])
        send_system_message(user, "DENIED_JOIN")
        return

    if user.watching is not None:
        send_text_system_message("Error: Already watching stream.", [user])
        send_system_message(user, "DENIED_JOIN")
        return

    if screen_sharer.is_user_watching_stream(user):
        send_text_system_message("Error: Already watching stream.", [user])
        send_system_message(user, "DENIED_JOIN")
        return

    send_system_message(user, "CONFIRM_JOIN")
    send_text_system_message(f"{user.name} joined stream.", [user, screen_sharer])
    screen_sharer.add_user_to_watchers_list(user)
    user.watching = screen_sharer
    logging.info(f"{user.name} Joined {screen_sharer_name} Stream")


def handle_leave_share_screen(user) -> None:
    if user.watching is None:
        send_text_system_message("Error: User does not watch stream.", [user])
        return

    user.watching.remove_user_from_watchers_list(user)
    send_system_message(user, "DISCONNECT")
    send_text_system_message(f"{user.name} left stream.", [user, user.watching])
    logging.info(f"{user.name} Joined {user.watching.name} Stream")
    user.watching = None


def send_frame(content, list_of_users) -> None:
    message_obj = message.Frame(content, message_types["Binary"])
    for user in list_of_users:
        if len(user.message_queue) < MAX_QUEUE_SIZE:
            user.message_queue.append(message_obj)
        else:
            logging.info(f"Message queue for {user.name} is full. Dropping message.")


def handle_responses_errors(wlist) -> None:
    for error in errors_to_send:
        current_socket, data = error
        if current_socket in wlist:
            try:
                current_socket.send(data)
                errors_to_send.remove(error)
            except (BlockingIOError, ConnectionResetError):
                logging.error(f"Failed to send error message to {current_socket}")
                handle_client_quiting(current_socket, None)


def handle_chat_responses(wlist) -> None:
    for sock in wlist:
        user = user_manager.get_user_by_socket(sock)
        if not user or len(user.message_queue) == 0:
            continue

        while len(user.message_queue) > 0:
            message_obj = user.message_queue.pop(0)
            try:
                sock.send(protocol.create_message(message_obj.create_message()))
                # logging.info(f"Sent message to {user.name}: {message_obj.content}")
            except BlockingIOError:
                user.message_queue.insert(0, message_obj)
                break
            except ConnectionResetError:
                logging.error(f"Connection reset during send to {user.name}")
                handle_client_quiting(sock, user)
                break


def remove_user(sock) -> None:
    user = user_manager.remove_user(sock)
    if user:
        open_client_sockets.remove(sock)
        sock.close()
        logging.info(f"User {user.name} disconnected.")
        if open_client_sockets and user.status == UserStatus.Owner:
            new_owner = user_manager.get_user_by_socket(open_client_sockets[0])
            new_owner.status = UserStatus.Owner
            send_text_system_message(f"Owner {user.name} has left and {new_owner.name} has been promoted to Owner.",
                                     user_manager.get_users())


def clean_closed_sockets() -> None:
    for sock in open_client_sockets:
        if sock.fileno() == -1:
            open_client_sockets.remove(sock)
            user_manager.remove_user(sock)


def main() -> None:
    """
    Start the server and handle client connections.
    """
    print("Setting up server...")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server_socket.bind((protocol.SERVER_IP, protocol.SERVER_PORT))
    server_socket.listen()
    print("Listening for clients...")

    # setup log file and configuration
    logging.basicConfig(filename='log.log', level=logging.INFO, filemode='w',
                        format=f'%(asctime)s -%(levelname)s - %(message)s')

    try:
        handle_clients(server_socket)
    except KeyboardInterrupt:
        logging.info("Shutting down server gracefully...")
    finally:
        user_manager.clear_user_manager()
        for sock in open_client_sockets:
            sock.close()
        server_socket.close()


if __name__ == '__main__':
    main()
