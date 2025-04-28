import socket
import select
import protocol
import msvcrt
import threading
import queue
import cv2
from screensharemanager import ScreenShareManager

input_queue = queue.Queue()
console_lock = threading.Lock()
print_queue = queue.Queue()  # Store messages while user is typing
is_typing = False  # Track typing state

available_commands = ["SEND_MESSAGE", "CHANGE_NAME", "CHANGE_STATUS", "KICK_USER", "SEND_PRIVATE_MESSAGE",
                      "START_SHARE_SCREEN", "END_SHARE_SCREEN", "JOIN_SHARE_SCREEN", "LEAVE_SHARE_SCREEN", "QUIT"]
MESSAGE_TYPES = {"Text": "0", "Binary": "1", "System": "2"}
pending_for_start = False  # Tracks START_SHARE_SCREEN
pending_for_join = False  # Tracks JOIN_SHARE_SCREEN
sharing_screen = False
watching_stream = False


def safe_print(message) -> None:
    """Print messages safely and use a queue when the user is typing."""
    global is_typing
    if is_typing:
        # Store messages in the queue while typing
        print_queue.put(message)
    else:
        # Print immediately if not typing
        with console_lock:
            print(message)


def flush_print_queue() -> None:
    """Flush and print all messages from the queue."""
    while not print_queue.empty():
        with console_lock:
            print(print_queue.get())


def get_input_thread() -> None:
    while True:
        if msvcrt.kbhit():
            user_input = get_input_from_client()
            input_queue.put(user_input)


def handle_requests(client_socket, uuid) -> None:
    global pending_for_start, pending_for_join, sharing_screen, watching_stream
    threading.Thread(target=get_input_thread, daemon=True).start()  # Start input thread

    while True:
        # Check for data from server
        rlist, _, _ = select.select([client_socket], [], [], 0.2)
        if rlist:
            try:
                response = protocol.get_analyzed_data(client_socket)
                if response == b"":
                    safe_print("Server closed.")
                    break
                handle_response(response)
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                client_socket.close()
                safe_print("Error : Connection Shutdown.")
                break
            except Exception as e:
                safe_print(f"Unexpected error: {e}")
                break

        if sharing_screen:
            encoded_frame = ScreenShareManager.capture_frame()
            message = protocol.create_message(f"{uuid}|{MESSAGE_TYPES['Binary']}|".encode() + encoded_frame)
            try:
                client_socket.send(message)
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                client_socket.close()
                safe_print("Error : Connection Shutdown.")
                break
            except Exception as e:
                safe_print(f"Unexpected error: {e}")
                break

        # Check for user input
        if not input_queue.empty():
            client_input = input_queue.get()
            if client_input == "" or client_input == 'QUIT':
                # Quit command
                message = protocol.create_message(f"{uuid}|{MESSAGE_TYPES['Text']}|QUIT|")
                client_socket.send(message)
                break

            # Extract command and message content
            command, content = parse_command(client_input)
            if command:
                if command == "START_SHARE_SCREEN":
                    pending_for_start = True
                if command == "JOIN_SHARE_SCREEN":
                    pending_for_join = True
                message = protocol.create_message(f"{uuid}|{MESSAGE_TYPES['Text']}|{command}|{content}")
                try:
                    client_socket.send(message)
                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                    client_socket.close()
                    safe_print("Error : Connection Shutdown.")
                    break
                except Exception as e:
                    safe_print(f"Unexpected error: {e}")
                    break

    safe_print("Connection closed")


def parse_command(client_input) -> tuple[None, None] | tuple[str, str]:
    input_split = client_input.split(" ")
    if input_split[0] in available_commands:
        return input_split[0], " ".join(input_split[1:])
    safe_print("Invalid input. Command does not exist.")
    return None, None


def get_input_from_client() -> str:
    global is_typing
    is_typing = True  # Set typing state to True
    print("Type command and content (press Enter to finish): ")
    result = []  # client input list that updates

    while True:
        if msvcrt.kbhit():
            char = msvcrt.getch()
            if char == b'\r':  # Enter key
                print()
                break
            elif char == b'\x08':  # Backspace
                if result:
                    result.pop()
                    print("\b \b", end="", flush=True)
                continue
            try:
                result.append(char.decode('utf-8'))
                print(char.decode('utf-8'), end="", flush=True)
            except Exception as e:
                print(f"Error: {e}")
    is_typing = False  # Reset typing state
    flush_print_queue()
    return "".join(result)


def analyze_response(response) -> tuple[str, bytes]:
    delimiter_index = response.find(b"|")
    message_type = response[:delimiter_index].decode()
    content = response[delimiter_index + 1:]
    return message_type, content


def handle_response(response) -> None:
    global pending_for_start, pending_for_join, sharing_screen, watching_stream
    message_type, content = analyze_response(response)
    if message_type == MESSAGE_TYPES["Binary"] and watching_stream:
        ScreenShareManager.watch_share_screen(content)  # Display the received frame
    elif message_type == MESSAGE_TYPES["Text"]:
        safe_print(content.decode())
    elif message_type == MESSAGE_TYPES["System"]:
        if content == b"CONFIRM_START":
            pending_for_start = False
            sharing_screen = True
            safe_print("Screen sharing started.")

        elif content == b"DENIED_START":
            pending_for_start = False
            safe_print("Screen sharing was Denied.")

        elif content == b"CONFIRM_JOIN":
            pending_for_join = False
            watching_stream = True
            cv2.namedWindow('Screen_Capture_Window', cv2.WINDOW_NORMAL)
            safe_print("Joined screen sharing session.")

        elif content == b"DENIED_JOIN":
            pending_for_join = False
            safe_print("Joining share was Denied.")

        elif content == b"DISCONNECT":
            watching_stream = False
            cv2.destroyAllWindows()


def main() -> None:
    username = input("To join chat, type username (Only alphabetic or numbers): ")
    while not username.isalnum():
        username = input("To join chat, type username (Only alphabetic or numbers): ")

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    client_socket.connect((protocol.SERVER_IP, protocol.SERVER_PORT))
    print(f"Connected to {protocol.SERVER_IP} on port {protocol.SERVER_PORT}...")

    # Send username to server for initial registration
    initial_message = protocol.create_message(username)
    client_socket.send(initial_message)
    uuid = protocol.get_analyzed_data(client_socket).decode()
    print(f"Your assigned UUID: {uuid}")
    print("Commands:\n"
          "     SEND_MESSAGE - Send message (e.g., SEND_MESSAGE Hello)\n"
          "     CHANGE_NAME - Change name (e.g., CHANGE_NAME NewName)\n"
          "     CHANGE_STATUS - Change status of user to (RegularUser - 1, Administrator - 2) "
          "(Only if admin or owner) (e.g., CHANGE_STATUS 2RegularUserName)\n"
          "     KICK_USER - Kick user (Only if admin or owner) (e.g., KICK_USER UserName)\n"
          "     SEND_PRIVATE_MESSAGE - Send private message (e.g., SEND_PRIVATE_MESSAGE RecipientName|Hello)\n"
          "     START_SHARE_SCREEN - Starts share-screen that people can join to watch (e.g., START_SHARE_SCREEN)\n"
          "     END_SHARE_SCREEN - Ends share-screen (e.g., END_SHARE_SCREEN)\n"
          "     JOIN_SHARE_SCREEN - Joins a share-screen of user (e.g., JOIN_SHARE_SCREEN ScreenSharerUserName)\n"
          "     LEAVE_SHARE_SCREEN - Leaves a share-screen user currently watch (e.g., LEAVE_SHARE_SCREEN)\n"
          "     QUIT - Quit (QUIT or press Enter)\n")
    # Enter the main request-handling loop
    handle_requests(client_socket, uuid)


if __name__ == '__main__':
    main()
