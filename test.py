import base64
import struct

def extract_chat_id(inline_message_id: str) -> int:
    # Decode the inline_message_id
    decoded_id = base64.urlsafe_b64decode(inline_message_id + "=" * (4 - len(inline_message_id) % 4))
    
    # Unpack the decoded_id to retrieve the chat_id
    dc_id, message_id, chat_id, query_id = struct.unpack("<iiiq", decoded_id)
    
    # Convert the chat_id to ensure it starts with -100
    if chat_id < 0:
        chat_id = int(f"-100{abs(chat_id)}")
    
    return chat_id

