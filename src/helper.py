# This file contains code from both /https://github.com/buidl-bitcoin/buidl-python/tree/main/buidl/helper.py and 
# https://github.com/LedgerHQ/app-bitcoin-new/tree/develop/bitcoin_client/ledger_bitcoin/common.py
from io import BytesIO
from typing import List, Optional, Literal, Union
from enum import Enum
import hashlib
import hmac
import re

from base64 import b64decode, b64encode
from buidl.pbkdf2 import PBKDF2

try:
    from csiphash import siphash24

    def _siphash(key, value):
        if len(key) != 16:
            raise ValueError("Key should be 16 bytes")
        return little_endian_to_int(siphash24(key, value))

except ModuleNotFoundError:
    from buidl.siphash import SipHash_2_4

    def _siphash(key, value):
        if len(key) != 16:
            raise ValueError("Key should be 16 bytes")
        sip = SipHash_2_4(key)
        sip.update(value)
        return sip.hash()


SIGHASH_DEFAULT = 0
SIGHASH_ALL = 1
SIGHASH_NONE = 2
SIGHASH_SINGLE = 3
SIGHASH_ANYONECANPAY = 0x80
BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
PBKDF2_ROUNDS = 2048
GOLOMB_P = 19
GOLOMB_M = int(round(1.497137 * 2**GOLOMB_P))
TWO_WEEKS = 60 * 60 * 24 * 14
MAX_TARGET = 0xFFFF * 256 ** (0x1D - 3)


HEX_CHARS_RE = re.compile("^[0-9a-f]*$")

UINT64_MAX: int = 18446744073709551615
UINT32_MAX: int = 4294967295
UINT16_MAX: int = 65535


# from bitcoin-core/HWI
class Chain(Enum):
    """
    The blockchain network to use
    """
    MAIN = 0 #: Bitcoin Main network
    TEST = 1 #: Bitcoin Test network
    REGTEST = 2 #: Bitcoin Core Regression Test network
    SIGNET = 3 #: Bitcoin Signet

    def __str__(self) -> str:
        return self.name.lower()

    def __repr__(self) -> str:
        return str(self)

    @staticmethod
    def argparse(s: str) -> Union['Chain', str]:
        try:
            return Chain[s.upper()]
        except KeyError:
            return s

# from bitcoin-core/HWI
class AddressType(Enum):
    """
    The type of address to use
    """
    LEGACY = 1 #: Legacy address type. P2PKH for single sig, P2SH for scripts.
    WIT = 2    #: Native segwit v0 address type. P2WPKH for single sig, P2WPSH for scripts.
    SH_WIT = 3 #: Nested segwit v0 address type. P2SH-P2WPKH for single sig, P2SH-P2WPSH for scripts.
    TAP = 4    #: Segwit v1 Taproot address type. P2TR always.

    def __str__(self) -> str:
        return self.name.lower()

    def __repr__(self) -> str:
        return str(self)

    @staticmethod
    def argparse(s: str) -> Union['AddressType', str]:
        try:
            return AddressType[s.upper()]
        except KeyError:
            return s

def bip32_path_from_string(path: str) -> List[bytes]:
    splitted_path: List[str] = path.split("/")

    if not splitted_path:
        raise Exception(f"BIP32 path format error: '{path}'")

    if "m" in splitted_path and splitted_path[0] == "m":
        splitted_path = splitted_path[1:]

    return [int(p).to_bytes(4, byteorder="big") if "'" not in p
            else (0x80000000 | int(p[:-1])).to_bytes(4, byteorder="big")
            for p in splitted_path]


def write_varint(n: int) -> bytes:
    if n <= 0xFC:
        return n.to_bytes(1, byteorder="little")

    if n <= UINT16_MAX:
        return b"\xFD" + n.to_bytes(2, byteorder="little")

    if n <= UINT32_MAX:
        return b"\xFE" + n.to_bytes(4, byteorder="little")

    if n <= UINT64_MAX:
        return b"\xFF" + n.to_bytes(8, byteorder="little")

    raise ValueError(f"Can't write to varint: '{n}'!")


def read_uint(buf: BytesIO,
              bit_len: int,
              byteorder: Literal['big', 'little'] = 'little') -> int:
    size: int = bit_len // 8
    b: bytes = buf.read(size)

    if len(b) < size:
        raise ValueError(f"Can't read u{bit_len} in buffer!")

    return int.from_bytes(b, byteorder)


def serialize_str(value: str) -> bytes:
    return len(value.encode()).to_bytes(1, byteorder="big") + value.encode()


class ByteStreamParser:
    def __init__(self, input: bytes):
        self.stream = BytesIO(input)

    def assert_empty(self) -> bytes:
        if self.stream.read(1) != b'':
            raise ValueError("Byte stream was expected to be empty")

    def read_bytes(self, n: int) -> bytes:
        result = self.stream.read(n)
        if len(result) < n:
            raise ValueError("Byte stream exhausted")
        return result

    def read_uint(self, n: int, byteorder: Literal['big', 'little'] = "big") -> int:
        return int.from_bytes(self.read_bytes(n), byteorder)

    def read_varint(self) -> int:
        prefix = self.read_uint(1)

        if prefix == 253:
            return self.read_uint(2, 'little')
        elif prefix == 254:
            return self.read_uint(4, 'little')
        elif prefix == 255:
            return self.read_uint(8, 'little')
        else:
            return prefix

def bytes_to_str(b, encoding="ascii"):
    """Returns a string version of the bytes"""
    # use the bytes.decode(encoding) method
    return b.decode(encoding)


def str_to_bytes(s, encoding="ascii"):
    """Returns a bytes version of the string"""
    # use the string.encode(encoding) method
    return s.encode(encoding)


def byte_to_int(b):
    """Returns an integer that corresponds to the byte"""
    return b[0]


def int_to_byte(n):
    """Returns a single byte that corresponds to the integer"""
    if n > 255 or n < 0:
        raise ValueError(
            "integer greater than 255 or lower than 0 cannot be converted into a byte"
        )
    return bytes([n])


def big_endian_to_int(b):
    """little_endian_to_int takes byte sequence as a little-endian number.
    Returns an integer"""
    # use the int.from_bytes(b, <endianness>) method
    return int.from_bytes(b, "big")


def int_to_big_endian(n, length):
    """int_to_little_endian takes an integer and returns the little-endian
    byte sequence of length"""
    # use the int.to_bytes(length, <endianness>) method
    return n.to_bytes(length, "big")


def little_endian_to_int(b):
    """little_endian_to_int takes byte sequence as a little-endian number.
    Returns an integer"""
    # use the int.from_bytes(b, <endianness>) method
    return int.from_bytes(b, "little")


def int_to_little_endian(n, length):
    """int_to_little_endian takes an integer and returns the little-endian
    byte sequence of length"""
    # use the int.to_bytes(length, <endianness>) method
    return n.to_bytes(length, "little")


def hash160(s: bytes) -> bytes:
    return hashlib.new("ripemd160", hashlib.sha256(s).digest()).digest()


def hash256(s: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(s).digest()).digest()


def sha256(s: bytes) -> bytes:
    return hashlib.sha256(s).digest()


def encode_base58(s):
    # determine how many 0 bytes (b'\x00') s starts with
    count = 0
    for c in s:
        if c == 0:
            count += 1
        else:
            break
    # convert from binary to hex, then hex to integer
    num = int(s.hex(), 16)
    result = ""
    prefix = "1" * count
    while num > 0:
        num, mod = divmod(num, 58)
        result = BASE58_ALPHABET[mod] + result
    return prefix + result


def encode_base58_checksum(raw):
    """Takes bytes and turns it into base58 encoding with checksum"""
    # checksum is the first 4 bytes of the hash256
    checksum = hash256(raw)[:4]
    # encode_base58 on the raw and the checksum
    return encode_base58(raw + checksum)


def raw_decode_base58(s):
    num = 0
    # see how many leading 0's we are starting with
    prefix = b""
    for c in s:
        if num == 0 and c == "1":
            prefix += b"\x00"
        else:
            num = 58 * num + BASE58_ALPHABET.index(c)
    # put everything into base64
    byte_array = []
    while num > 0:
        byte_array.insert(0, num & 255)
        num >>= 8
    combined = prefix + bytes(byte_array)
    checksum = combined[-4:]
    if hash256(combined[:-4])[:4] != checksum:
        raise RuntimeError("bad address: {} {}".format(checksum, hash256(combined)[:4]))
    return combined[:-4]


def decode_base58(s):
    return raw_decode_base58(s)[1:]

def read_varint(buf: BytesIO,
                prefix: Optional[bytes] = None) -> int:
    b: bytes = prefix if prefix else buf.read(1)

    if not b:
        raise ValueError(f"Can't read prefix: '{b}'!")

    n: int = {b"\xfd": 2, b"\xfe": 4, b"\xff": 8}.get(b, 1)  # default to 1

    b = buf.read(n) if n > 1 else b

    if len(b) != n:
        raise ValueError("Can't read varint!")

    return int.from_bytes(b, byteorder="little")


def encode_varint(i):
    """encodes an integer as a varint"""
    if i < 0xFD:
        return bytes([i])
    elif i < 0x10000:
        return b"\xfd" + int_to_little_endian(i, 2)
    elif i < 0x100000000:
        return b"\xfe" + int_to_little_endian(i, 4)
    elif i < 0x10000000000000000:
        return b"\xff" + int_to_little_endian(i, 8)
    else:
        raise RuntimeError(f"integer too large: {i}")


def read_varstr(s):
    """reads a variable string from a stream"""
    # remember that s.read(n) will read n bytes from the stream
    # find the length of the string by using read_varint on the string
    item_length = read_varint(s)
    # read that many bytes from the stream
    return s.read(item_length)


def encode_varstr(b):
    """encodes bytes as a varstr"""
    # encode the length of the string using encode_varint
    result = encode_varint(len(b))
    # add the bytes
    result += b
    # return the whole thing
    return result


def merkle_parent(hash1, hash2):
    """Takes the binary hashes and calculates the hash256"""
    # return the hash256 of hash1 + hash2
    return hash256(hash1 + hash2)


def merkle_parent_level(hashes):
    """Takes a list of binary hashes and returns a list that's half
    the length"""
    # if the list has exactly 1 element raise an error
    if len(hashes) == 1:
        raise RuntimeError("Cannot take a parent level with only 1 item")
    # if the list has an odd number of elements, duplicate the last one
    #       and put it at the end so it has an even number of elements
    if len(hashes) % 2 == 1:
        hashes.append(hashes[-1])
    # initialize parent level
    parent_level = []
    # loop over every pair (use: for i in range(0, len(hashes), 2))
    for i in range(0, len(hashes), 2):
        # get the merkle parent of i and i+1 hashes
        parent = merkle_parent(hashes[i], hashes[i + 1])
        # append parent to parent level
        parent_level.append(parent)
    # return parent level
    return parent_level


def merkle_root(hashes):
    """Takes a list of binary hashes and returns the merkle root"""
    # current level starts as hashes
    current_level = hashes
    # loop until there's exactly 1 element
    while len(current_level) > 1:
        # current level becomes the merkle parent level
        current_level = merkle_parent_level(current_level)
    # return the 1st item of current_level
    return current_level[0]


def bit_field_to_bytes(bit_field):
    if len(bit_field) % 8 != 0:
        raise RuntimeError("bit_field does not have a length that is divisible by 8")
    result = bytearray(len(bit_field) // 8)
    for i, bit in enumerate(bit_field):
        byte_index, bit_index = divmod(i, 8)
        if bit:
            result[byte_index] |= 1 << bit_index
    return bytes(result)


def bytes_to_bit_field(some_bytes):
    flag_bits = []
    # iterate over each byte of flags
    for byte in some_bytes:
        # iterate over each bit, right-to-left
        for _ in range(8):
            # add the current bit (byte & 1)
            flag_bits.append(byte & 1)
            # rightshift the byte 1
            byte >>= 1
    return flag_bits


def murmur3(data, seed=0):
    """from http://stackoverflow.com/questions/13305290/is-there-a-pure-python-implementation-of-murmurhash"""
    c1 = 0xCC9E2D51
    c2 = 0x1B873593
    length = len(data)
    h1 = seed
    roundedEnd = length & 0xFFFFFFFC  # round down to 4 byte block
    for i in range(0, roundedEnd, 4):
        # little endian load order
        k1 = (
            (data[i] & 0xFF)
            | ((data[i + 1] & 0xFF) << 8)
            | ((data[i + 2] & 0xFF) << 16)
            | (data[i + 3] << 24)
        )
        k1 *= c1
        k1 = (k1 << 15) | ((k1 & 0xFFFFFFFF) >> 17)  # ROTL32(k1,15)
        k1 *= c2
        h1 ^= k1
        h1 = (h1 << 13) | ((h1 & 0xFFFFFFFF) >> 19)  # ROTL32(h1,13)
        h1 = h1 * 5 + 0xE6546B64
    # tail
    k1 = 0
    val = length & 0x03
    if val == 3:
        k1 = (data[roundedEnd + 2] & 0xFF) << 16
    # fallthrough
    if val in [2, 3]:
        k1 |= (data[roundedEnd + 1] & 0xFF) << 8
    # fallthrough
    if val in [1, 2, 3]:
        k1 |= data[roundedEnd] & 0xFF
        k1 *= c1
        k1 = (k1 << 15) | ((k1 & 0xFFFFFFFF) >> 17)  # ROTL32(k1,15)
        k1 *= c2
        h1 ^= k1
    # finalization
    h1 ^= length
    # fmix(h1)
    h1 ^= (h1 & 0xFFFFFFFF) >> 16
    h1 *= 0x85EBCA6B
    h1 ^= (h1 & 0xFFFFFFFF) >> 13
    h1 *= 0xC2B2AE35
    h1 ^= (h1 & 0xFFFFFFFF) >> 16
    return h1 & 0xFFFFFFFF


def hmac_sha512(key, msg):
    return hmac.HMAC(key=key, msg=msg, digestmod=hashlib.sha512).digest()


def hmac_sha512_kdf(msg, salt):
    return PBKDF2(
        msg,
        salt,
        iterations=PBKDF2_ROUNDS,
        macmodule=hmac,
        digestmodule=hashlib.sha512,
    ).read(64)


def base64_encode(b):
    return b64encode(b).decode("ascii")


def base64_decode(s):
    return b64decode(s)


def serialize_key_value(key, value):
    return encode_varstr(key) + encode_varstr(value)


def child_to_path(child_number):
    if child_number >= 0x80000000:
        hardened = "'"
        index = child_number - 0x80000000
    else:
        hardened = ""
        index = child_number
    return f"/{index}{hardened}"


def path_network(root_path):
    components = root_path.split("/")
    if len(components) < 2:
        return "mainnet"
    elif components[1] in ("44'", "84'", "48'") and components[2] == "1'":
        return "testnet"
    else:
        return "mainnet"


def parse_binary_path(bin_path):
    if len(bin_path) % 4 != 0:
        raise ValueError(f"Not a valid binary path: {bin_path.hex()}")
    path_data = bin_path
    path = "m"
    while len(path_data):
        child_number = little_endian_to_int(path_data[:4])
        path += child_to_path(child_number)
        path_data = path_data[4:]
    return path


def bits_to_target(bits):
    """Turns bits into a target (large 256-bit integer)"""
    # last byte is exponent
    exponent = bits[-1]
    # the first three bytes are the coefficient in little endian
    coefficient = little_endian_to_int(bits[:-1])
    # the formula is:
    # coefficient * 256**(exponent-3)
    return coefficient * 256 ** (exponent - 3)


def target_to_bits(target):
    """Turns a target integer back into bits, which is 4 bytes"""
    raw_bytes = target.to_bytes(32, "big")
    # get rid of leading 0's
    raw_bytes = raw_bytes.lstrip(b"\x00")
    if raw_bytes[0] > 0x7F:
        # if the first bit is 1, we have to start with 00
        exponent = len(raw_bytes) + 1
        coefficient = b"\x00" + raw_bytes[:2]
    else:
        # otherwise, we can show the first 3 bytes
        # exponent is the number of digits in base-256
        exponent = len(raw_bytes)
        # coefficient is the first 3 digits of the base-256 number
        coefficient = raw_bytes[:3]
    # we've truncated the number after the first 3 digits of base-256
    new_bits = coefficient[::-1] + bytes([exponent])
    return new_bits


def calculate_new_bits(previous_bits, time_differential):
    """Calculates the new bits given
    a 2016-block time differential and the previous bits"""
    # if the time differential is greater than 8 weeks, set to 8 weeks
    if time_differential > TWO_WEEKS * 4:
        time_differential = TWO_WEEKS * 4
    # if the time differential is less than half a week, set to half a week
    if time_differential < TWO_WEEKS // 4:
        time_differential = TWO_WEEKS // 4
    # the new target is the previous target * time differential / two weeks
    new_target = bits_to_target(previous_bits) * time_differential // TWO_WEEKS
    # if the new target is bigger than MAX_TARGET, set to MAX_TARGET
    if new_target > MAX_TARGET:
        new_target = MAX_TARGET
    # convert the new target to bits
    return target_to_bits(new_target)


def filter_null(items):
    non_null_items = []
    for item in items:
        if len(item) > 0:
            non_null_items.append(item)
    return non_null_items


def uses_only_hex_chars(string):
    return bool(HEX_CHARS_RE.match(string.lower()))


def is_intable(int_as_string):
    try:
        int(int_as_string)
        return True
    except ValueError:
        return False


def xor_bytes(a, b):
    return bytes(x ^ y for x, y in zip(a, b))
