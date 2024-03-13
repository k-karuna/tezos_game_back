import codecs
import uuid
from datetime import datetime


def get_hex_payload(plain_text_payload):
    bytes_hex = codecs.encode(plain_text_payload.encode('utf-8'), 'hex').decode()
    bytes_length = hex(len(bytes_hex) // 2)[2:]
    add_padding = "00000000" + bytes_length
    padded_bytes_length = add_padding[-8:]
    start_prefix = "0501"
    payload_bytes = start_prefix + padded_bytes_length + bytes_hex
    return payload_bytes


def get_payload_for_sign():
    return f"Tezos Signed Message: {datetime.now().isoformat()} {get_uuid_hash()}"


def get_uuid_hash():
    return uuid.uuid4().hex


def get_shortened_address(address):
    return address[:4] + "···" + address[-6:]
