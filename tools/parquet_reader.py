"""
Zero-dependency Apache Parquet reader.

Purpose-built for the LILA BLACK telemetry files, which are written by
parquet-go: UNCOMPRESSED column chunks using PLAIN / RLE_DICTIONARY /
PLAIN encodings. Only the subset of the Parquet spec needed for these
files is implemented, but it is implemented correctly for that subset.

No third-party packages are required (Python 3.8+ standard library only),
which is why this same reader doubles as the repo's preprocessing engine:
evaluators can regenerate the dataset with `python tools/build_dataset.py`
without installing pyarrow/pandas or having any network access.

Implements:
  * Thrift Compact Protocol decoder (the encoding Parquet metadata uses)
  * Parquet FileMetaData / SchemaElement / RowGroup / ColumnChunk parsing
  * Page header parsing (dictionary page + data page v1 and v2)
  * Decoders: PLAIN, RLE/bit-packed hybrid (levels), RLE_DICTIONARY,
    PLAIN_DICTIONARY
  * Definition levels -> nulls for OPTIONAL columns
  * snappy/gzip decompression IF present (these files are uncompressed,
    but the hooks are here so the reader is robust)
"""

import struct
import gzip
import zlib
from typing import List, Dict, Any, Optional

# ----------------------------------------------------------------------------
# Thrift Compact Protocol
# ----------------------------------------------------------------------------

CT_STOP = 0x00
CT_BOOLEAN_TRUE = 0x01
CT_BOOLEAN_FALSE = 0x02
CT_BYTE = 0x03
CT_I16 = 0x04
CT_I32 = 0x05
CT_I64 = 0x06
CT_DOUBLE = 0x07
CT_BINARY = 0x08
CT_LIST = 0x09
CT_SET = 0x0A
CT_MAP = 0x0B
CT_STRUCT = 0x0C


class CompactProtocolReader:
    """Minimal Thrift compact protocol reader."""

    def __init__(self, data: bytes, pos: int = 0):
        self.data = data
        self.pos = pos
        # stack of last field ids for delta encoding within a struct
        self._field_stack: List[int] = []
        self._last_fid = 0

    def read_byte(self) -> int:
        b = self.data[self.pos]
        self.pos += 1
        return b

    def read_varint(self) -> int:
        result = 0
        shift = 0
        while True:
            b = self.data[self.pos]
            self.pos += 1
            result |= (b & 0x7F) << shift
            if not (b & 0x80):
                break
            shift += 7
        return result

    def read_zigzag(self) -> int:
        n = self.read_varint()
        return (n >> 1) ^ -(n & 1)

    def read_binary(self) -> bytes:
        length = self.read_varint()
        val = self.data[self.pos:self.pos + length]
        self.pos += length
        return val

    def read_double(self) -> float:
        val = struct.unpack_from("<d", self.data, self.pos)[0]
        self.pos += 8
        return val

    def read_field_begin(self):
        """Returns (type, field_id) or (CT_STOP, 0)."""
        b = self.read_byte()
        if b == CT_STOP:
            return CT_STOP, 0
        delta = (b & 0xF0) >> 4
        ctype = b & 0x0F
        if delta == 0:
            fid = self.read_zigzag()
        else:
            fid = self._last_fid + delta
        self._last_fid = fid
        return ctype, fid

    def push(self):
        self._field_stack.append(self._last_fid)
        self._last_fid = 0

    def pop(self):
        self._last_fid = self._field_stack.pop()

    def read_collection_begin(self):
        """List/set header -> (elem_type, size)."""
        size_type = self.read_byte()
        size = (size_type & 0xF0) >> 4
        etype = size_type & 0x0F
        if size == 0x0F:
            size = self.read_varint()
        return etype, size

    def skip(self, ctype: int):
        if ctype == CT_BOOLEAN_TRUE or ctype == CT_BOOLEAN_FALSE:
            return
        if ctype == CT_BYTE:
            self.read_byte()
        elif ctype in (CT_I16, CT_I32, CT_I64):
            self.read_zigzag()
        elif ctype == CT_DOUBLE:
            self.read_double()
        elif ctype == CT_BINARY:
            self.read_binary()
        elif ctype == CT_LIST or ctype == CT_SET:
            etype, size = self.read_collection_begin()
            for _ in range(size):
                self.skip(etype)
        elif ctype == CT_MAP:
            size = self.read_varint()
            if size != 0:
                kv = self.read_byte()
                ktype = (kv & 0xF0) >> 4
                vtype = kv & 0x0F
                for _ in range(size):
                    self.skip(ktype)
                    self.skip(vtype)
        elif ctype == CT_STRUCT:
            self.push()
            while True:
                ft, _ = self.read_field_begin()
                if ft == CT_STOP:
                    break
                self.skip(ft)
            self.pop()


# ----------------------------------------------------------------------------
# Parquet metadata structures (parsed from thrift)
# ----------------------------------------------------------------------------

# parquet Type enum
T_BOOLEAN = 0
T_INT32 = 1
T_INT64 = 2
T_INT96 = 3
T_FLOAT = 4
T_DOUBLE = 5
T_BYTE_ARRAY = 6
T_FIXED_LEN_BYTE_ARRAY = 7

# Encoding enum
E_PLAIN = 0
E_PLAIN_DICTIONARY = 2
E_RLE = 3
E_BIT_PACKED = 4
E_RLE_DICTIONARY = 8

# PageType enum
PT_DATA_PAGE = 0
PT_INDEX_PAGE = 1
PT_DICTIONARY_PAGE = 2
PT_DATA_PAGE_V2 = 3

# CompressionCodec
C_UNCOMPRESSED = 0
C_SNAPPY = 1
C_GZIP = 2
C_ZSTD = 6


class SchemaElement:
    def __init__(self):
        self.type: Optional[int] = None
        self.repetition_type: Optional[int] = None  # 0=REQUIRED,1=OPTIONAL,2=REPEATED
        self.name: str = ""
        self.num_children: int = 0
        self.converted_type: Optional[int] = None


def read_schema_element(r: CompactProtocolReader) -> SchemaElement:
    se = SchemaElement()
    r.push()
    while True:
        ft, fid = r.read_field_begin()
        if ft == CT_STOP:
            break
        if fid == 1:      # type
            se.type = r.read_zigzag()
        elif fid == 2:    # type_length
            r.read_zigzag()
        elif fid == 3:    # repetition_type
            se.repetition_type = r.read_zigzag()
        elif fid == 4:    # name
            se.name = r.read_binary().decode("utf-8")
        elif fid == 5:    # num_children
            se.num_children = r.read_zigzag()
        elif fid == 6:    # converted_type
            se.converted_type = r.read_zigzag()
        else:
            r.skip(ft)
    r.pop()
    return se


class ColumnMetaData:
    def __init__(self):
        self.type: Optional[int] = None
        self.encodings: List[int] = []
        self.path_in_schema: List[str] = []
        self.codec: int = 0
        self.num_values: int = 0
        self.total_uncompressed_size: int = 0
        self.total_compressed_size: int = 0
        self.data_page_offset: int = 0
        self.dictionary_page_offset: Optional[int] = None


def read_column_metadata(r: CompactProtocolReader) -> ColumnMetaData:
    cmd = ColumnMetaData()
    r.push()
    while True:
        ft, fid = r.read_field_begin()
        if ft == CT_STOP:
            break
        if fid == 1:
            cmd.type = r.read_zigzag()
        elif fid == 2:    # encodings list
            etype, size = r.read_collection_begin()
            cmd.encodings = [r.read_zigzag() for _ in range(size)]
        elif fid == 3:    # path_in_schema
            etype, size = r.read_collection_begin()
            cmd.path_in_schema = [r.read_binary().decode("utf-8") for _ in range(size)]
        elif fid == 4:    # codec
            cmd.codec = r.read_zigzag()
        elif fid == 5:
            cmd.num_values = r.read_zigzag()
        elif fid == 6:
            cmd.total_uncompressed_size = r.read_zigzag()
        elif fid == 7:
            cmd.total_compressed_size = r.read_zigzag()
        elif fid == 9:
            cmd.data_page_offset = r.read_zigzag()
        elif fid == 11:
            cmd.dictionary_page_offset = r.read_zigzag()
        else:
            r.skip(ft)
    r.pop()
    return cmd


class ColumnChunk:
    def __init__(self):
        self.file_offset: int = 0
        self.meta_data: Optional[ColumnMetaData] = None


def read_column_chunk(r: CompactProtocolReader) -> ColumnChunk:
    cc = ColumnChunk()
    r.push()
    while True:
        ft, fid = r.read_field_begin()
        if ft == CT_STOP:
            break
        if fid == 1:
            cc.file_offset = r.read_zigzag()
        elif fid == 3:
            cc.meta_data = read_column_metadata(r)
        else:
            r.skip(ft)
    r.pop()
    return cc


class RowGroup:
    def __init__(self):
        self.columns: List[ColumnChunk] = []
        self.num_rows: int = 0


def read_row_group(r: CompactProtocolReader) -> RowGroup:
    rg = RowGroup()
    r.push()
    while True:
        ft, fid = r.read_field_begin()
        if ft == CT_STOP:
            break
        if fid == 1:      # columns
            etype, size = r.read_collection_begin()
            for _ in range(size):
                rg.columns.append(read_column_chunk(r))
        elif fid == 3:    # num_rows
            rg.num_rows = r.read_zigzag()
        else:
            r.skip(ft)
    r.pop()
    return rg


class FileMetaData:
    def __init__(self):
        self.schema: List[SchemaElement] = []
        self.num_rows: int = 0
        self.row_groups: List[RowGroup] = []


def read_file_metadata(data: bytes) -> FileMetaData:
    r = CompactProtocolReader(data)
    fmd = FileMetaData()
    r.push()
    while True:
        ft, fid = r.read_field_begin()
        if ft == CT_STOP:
            break
        if fid == 1:      # version
            r.read_zigzag()
        elif fid == 2:    # schema list
            etype, size = r.read_collection_begin()
            for _ in range(size):
                fmd.schema.append(read_schema_element(r))
        elif fid == 3:    # num_rows
            fmd.num_rows = r.read_zigzag()
        elif fid == 4:    # row_groups
            etype, size = r.read_collection_begin()
            for _ in range(size):
                fmd.row_groups.append(read_row_group(r))
        else:
            r.skip(ft)
    r.pop()
    return fmd


# ----------------------------------------------------------------------------
# Page headers
# ----------------------------------------------------------------------------

class PageHeader:
    def __init__(self):
        self.type: int = 0
        self.uncompressed_page_size: int = 0
        self.compressed_page_size: int = 0
        # data page v1
        self.num_values: int = 0
        self.encoding: int = 0
        self.def_level_encoding: int = 0
        self.rep_level_encoding: int = 0
        # dictionary page
        self.dict_num_values: int = 0
        self.dict_encoding: int = 0
        # data page v2
        self.v2_num_values: int = 0
        self.v2_num_nulls: int = 0
        self.v2_num_rows: int = 0
        self.v2_encoding: int = 0
        self.v2_def_levels_byte_length: int = 0
        self.v2_rep_levels_byte_length: int = 0
        self.v2_is_compressed: int = 1


def read_data_page_header(r: CompactProtocolReader, ph: PageHeader):
    r.push()
    while True:
        ft, fid = r.read_field_begin()
        if ft == CT_STOP:
            break
        if fid == 1:
            ph.num_values = r.read_zigzag()
        elif fid == 2:
            ph.encoding = r.read_zigzag()
        elif fid == 3:
            ph.def_level_encoding = r.read_zigzag()
        elif fid == 4:
            ph.rep_level_encoding = r.read_zigzag()
        else:
            r.skip(ft)
    r.pop()


def read_dict_page_header(r: CompactProtocolReader, ph: PageHeader):
    r.push()
    while True:
        ft, fid = r.read_field_begin()
        if ft == CT_STOP:
            break
        if fid == 1:
            ph.dict_num_values = r.read_zigzag()
        elif fid == 2:
            ph.dict_encoding = r.read_zigzag()
        else:
            r.skip(ft)
    r.pop()


def read_data_page_v2_header(r: CompactProtocolReader, ph: PageHeader):
    r.push()
    while True:
        ft, fid = r.read_field_begin()
        if ft == CT_STOP:
            break
        if fid == 1:
            ph.v2_num_values = r.read_zigzag()
        elif fid == 2:
            ph.v2_num_nulls = r.read_zigzag()
        elif fid == 3:
            ph.v2_num_rows = r.read_zigzag()
        elif fid == 4:
            ph.v2_encoding = r.read_zigzag()
        elif fid == 5:
            ph.v2_def_levels_byte_length = r.read_zigzag()
        elif fid == 6:
            ph.v2_rep_levels_byte_length = r.read_zigzag()
        elif fid == 7:
            ph.v2_is_compressed = 0 if r.read_byte() == CT_BOOLEAN_FALSE else 1
        else:
            r.skip(ft)
    r.pop()


def read_page_header(r: CompactProtocolReader) -> PageHeader:
    ph = PageHeader()
    r.push()
    while True:
        ft, fid = r.read_field_begin()
        if ft == CT_STOP:
            break
        if fid == 1:
            ph.type = r.read_zigzag()
        elif fid == 2:
            ph.uncompressed_page_size = r.read_zigzag()
        elif fid == 3:
            ph.compressed_page_size = r.read_zigzag()
        elif fid == 5:
            read_data_page_header(r, ph)
        elif fid == 7:
            read_dict_page_header(r, ph)
        elif fid == 8:
            read_data_page_v2_header(r, ph)
        else:
            r.skip(ft)
    r.pop()
    return ph


# ----------------------------------------------------------------------------
# Value decoders
# ----------------------------------------------------------------------------

def decompress(codec: int, data: bytes, uncompressed_size: int) -> bytes:
    if codec == C_UNCOMPRESSED:
        return data
    if codec == C_GZIP:
        return gzip.decompress(data)
    if codec == C_SNAPPY:
        return _snappy_decompress(data)
    if codec == C_ZSTD:
        try:
            import zstandard  # optional
            return zstandard.ZstdDecompressor().decompress(data, max_output_size=uncompressed_size)
        except Exception as e:
            raise RuntimeError("ZSTD codec requires the 'zstandard' package") from e
    raise RuntimeError(f"Unsupported codec {codec}")


def _snappy_decompress(data: bytes) -> bytes:
    """Pure-python Snappy raw block decompressor (no framing)."""
    pos = 0
    length, shift = 0, 0
    while True:
        b = data[pos]; pos += 1
        length |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    out = bytearray()
    while pos < len(data):
        tag = data[pos]; pos += 1
        t = tag & 0x03
        if t == 0:  # literal
            ln = tag >> 2
            if ln < 60:
                ln += 1
            else:
                nbytes = ln - 59
                ln = int.from_bytes(data[pos:pos + nbytes], "little") + 1
                pos += nbytes
            out += data[pos:pos + ln]; pos += ln
        else:
            if t == 1:
                ln = ((tag >> 2) & 0x07) + 4
                off = ((tag >> 5) << 8) | data[pos]; pos += 1
            elif t == 2:
                ln = (tag >> 2) + 1
                off = int.from_bytes(data[pos:pos + 2], "little"); pos += 2
            else:
                ln = (tag >> 2) + 1
                off = int.from_bytes(data[pos:pos + 4], "little"); pos += 4
            start = len(out) - off
            for i in range(ln):
                out.append(out[start + i])
    return bytes(out)


def _bit_width(max_val: int) -> int:
    w = 0
    while max_val:
        w += 1
        max_val >>= 1
    return w


def decode_rle_bitpacked_hybrid(buf: bytes, bit_width: int, count: int) -> List[int]:
    """Decode a RLE/bit-packed hybrid run into `count` ints."""
    out: List[int] = []
    pos = 0
    n = len(buf)
    byte_width = (bit_width + 7) // 8
    while len(out) < count and pos < n:
        # read varint header
        header = 0; shift = 0
        while True:
            b = buf[pos]; pos += 1
            header |= (b & 0x7F) << shift
            if not (b & 0x80):
                break
            shift += 7
        if header & 1:
            # bit-packed run: (header >> 1) groups of 8 values
            num_groups = header >> 1
            num_vals = num_groups * 8
            total_bytes = num_groups * bit_width
            chunk = buf[pos:pos + total_bytes]; pos += total_bytes
            bitbuf = 0; bits = 0
            for byte in chunk:
                bitbuf |= byte << bits
                bits += 8
                while bits >= bit_width and len(out) < count + num_vals:
                    out.append(bitbuf & ((1 << bit_width) - 1))
                    bitbuf >>= bit_width
                    bits -= bit_width
        else:
            # RLE run: header>>1 repeats of one value
            run_len = header >> 1
            val = int.from_bytes(buf[pos:pos + byte_width], "little") if byte_width else 0
            pos += byte_width
            out.extend([val] * run_len)
    return out[:count]


def decode_plain(buf: bytes, ptype: int, count: int) -> List[Any]:
    out: List[Any] = []
    pos = 0
    if ptype == T_INT32:
        for _ in range(count):
            out.append(struct.unpack_from("<i", buf, pos)[0]); pos += 4
    elif ptype == T_INT64:
        for _ in range(count):
            out.append(struct.unpack_from("<q", buf, pos)[0]); pos += 8
    elif ptype == T_FLOAT:
        for _ in range(count):
            out.append(struct.unpack_from("<f", buf, pos)[0]); pos += 4
    elif ptype == T_DOUBLE:
        for _ in range(count):
            out.append(struct.unpack_from("<d", buf, pos)[0]); pos += 8
    elif ptype == T_BOOLEAN:
        bitpos = 0
        for _ in range(count):
            byte = buf[bitpos // 8]
            out.append(bool(byte & (1 << (bitpos % 8))))
            bitpos += 1
    elif ptype == T_BYTE_ARRAY:
        for _ in range(count):
            ln = struct.unpack_from("<I", buf, pos)[0]; pos += 4
            out.append(buf[pos:pos + ln]); pos += ln
    elif ptype == T_INT96:
        for _ in range(count):
            out.append(buf[pos:pos + 12]); pos += 12
    else:
        raise RuntimeError(f"PLAIN decode unsupported type {ptype}")
    return out


# ----------------------------------------------------------------------------
# Column chunk reader
# ----------------------------------------------------------------------------

def _read_column(data: bytes, cc: ColumnChunk, max_def_level: int) -> List[Any]:
    cmd = cc.meta_data
    # determine where the chunk's pages start
    start = cmd.data_page_offset
    if cmd.dictionary_page_offset is not None and cmd.dictionary_page_offset < start:
        start = cmd.dictionary_page_offset
    end = start + cmd.total_compressed_size
    pos = start

    dictionary: Optional[List[Any]] = None
    values: List[Any] = []

    while pos < end and len(values) < cmd.num_values:
        r = CompactProtocolReader(data, pos)
        ph = read_page_header(r)
        page_start = r.pos
        comp = data[page_start:page_start + ph.compressed_page_size]
        pos = page_start + ph.compressed_page_size

        if ph.type == PT_DICTIONARY_PAGE:
            raw = decompress(cmd.codec, comp, ph.uncompressed_page_size)
            dictionary = decode_plain(raw, cmd.type, ph.dict_num_values)
            continue

        if ph.type == PT_DATA_PAGE:
            raw = decompress(cmd.codec, comp, ph.uncompressed_page_size)
            num = ph.num_values
            p = 0
            def_levels = None
            if max_def_level > 0:
                # def levels: RLE, length-prefixed (4 bytes) for v1
                ln = struct.unpack_from("<I", raw, p)[0]; p += 4
                lvl_buf = raw[p:p + ln]; p += ln
                bw = _bit_width(max_def_level)
                def_levels = decode_rle_bitpacked_hybrid(lvl_buf, bw, num)
            data_buf = raw[p:]
            _decode_data_values(data_buf, ph.encoding, cmd.type, num,
                                 def_levels, max_def_level, dictionary, values)
            continue

        if ph.type == PT_DATA_PAGE_V2:
            num = ph.v2_num_values
            # rep + def levels are NOT compressed in v2; data may be
            rep_len = ph.v2_rep_levels_byte_length
            def_len = ph.v2_def_levels_byte_length
            levels_total = rep_len + def_len
            levels_buf = comp[:levels_total]
            data_part = comp[levels_total:]
            if ph.v2_is_compressed:
                data_part = decompress(cmd.codec, data_part,
                                       ph.uncompressed_page_size - levels_total)
            def_levels = None
            if max_def_level > 0 and def_len > 0:
                bw = _bit_width(max_def_level)
                def_levels = decode_rle_bitpacked_hybrid(
                    levels_buf[rep_len:rep_len + def_len], bw, num)
            _decode_data_values(data_part, ph.v2_encoding, cmd.type, num,
                                def_levels, max_def_level, dictionary, values)
            continue

        # index page or unknown: skip
    return values


def _decode_data_values(data_buf, encoding, ptype, num, def_levels,
                        max_def_level, dictionary, out: List[Any]):
    # number of non-null values present
    if def_levels is not None:
        non_null = sum(1 for d in def_levels if d == max_def_level)
    else:
        non_null = num

    if encoding in (E_PLAIN_DICTIONARY, E_RLE_DICTIONARY):
        # first byte = bit width, then RLE/bitpacked indices
        bw = data_buf[0]
        idx = decode_rle_bitpacked_hybrid(data_buf[1:], bw, non_null)
        decoded = [dictionary[i] for i in idx]
    elif encoding == E_PLAIN:
        decoded = decode_plain(data_buf, ptype, non_null)
    elif encoding == E_RLE:
        bw = _bit_width(1)
        decoded = decode_rle_bitpacked_hybrid(data_buf, bw, non_null)
    else:
        raise RuntimeError(f"Unsupported data encoding {encoding}")

    if def_levels is not None:
        it = iter(decoded)
        for d in def_levels:
            out.append(next(it) if d == max_def_level else None)
    else:
        out.extend(decoded)


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------

def read_parquet(path: str) -> Dict[str, List[Any]]:
    """Read a parquet file into a dict of column_name -> list of values."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"PAR1" or data[-4:] != b"PAR1":
        raise RuntimeError(f"Not a parquet file: {path}")
    footer_len = struct.unpack_from("<I", data, len(data) - 8)[0]
    meta_start = len(data) - 8 - footer_len
    fmd = read_file_metadata(data[meta_start:len(data) - 8])

    # Build leaf columns + their max definition levels.
    # schema[0] is the root; leaves are elements with no children.
    leaves = []
    for se in fmd.schema[1:]:
        if se.num_children == 0:
            max_def = 1 if se.repetition_type == 1 else 0  # OPTIONAL -> 1
            leaves.append((se.name, max_def))

    result: Dict[str, List[Any]] = {name: [] for name, _ in leaves}
    for rg in fmd.row_groups:
        for col_idx, cc in enumerate(rg.columns):
            name, max_def = leaves[col_idx]
            vals = _read_column(data, cc, max_def)
            result[name].extend(vals)
    return result


if __name__ == "__main__":
    import sys
    cols = read_parquet(sys.argv[1])
    n = len(next(iter(cols.values())))
    print("columns:", list(cols.keys()), "rows:", n)
    for i in range(min(5, n)):
        print({k: (v[i].decode() if isinstance(v[i], bytes) else v[i]) for k, v in cols.items()})
