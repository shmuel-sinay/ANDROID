#!/usr/bin/env python3
"""Read Android Verified Boot (AVB) metadata without external tools.

Usage: avb_info.py IMAGE [IMAGE...]  -> prints JSON

Handles standalone vbmeta images and images that carry an AVB footer
("AVBf" in the last 64 bytes). All AVB structures are big-endian.
"""
import hashlib
import json
import struct
import sys

ALGORITHMS = {0: "NONE", 1: "SHA256_RSA2048", 2: "SHA256_RSA4096", 3: "SHA256_RSA8192",
              4: "SHA512_RSA2048", 5: "SHA512_RSA4096", 6: "SHA512_RSA8192"}
HEADER_FLAGS = {1: "HASHTREE_DISABLED", 2: "VERIFICATION_DISABLED"}


def cstr(b):
    return b.split(b"\0")[0].decode(errors="replace")


def parse_descriptors(data):
    out, pos = [], 0
    while pos + 16 <= len(data):
        tag, n = struct.unpack_from(">QQ", data, pos)
        body = data[pos + 16: pos + 16 + n]
        pos += 16 + n
        if tag == 0:  # property
            klen, vlen = struct.unpack_from(">QQ", body, 0)
            key = body[16:16 + klen].decode(errors="replace")
            val = body[16 + klen + 1:16 + klen + 1 + vlen]
            out.append({"type": "property", "key": key,
                        "value": val.decode(errors="replace")})
        elif tag == 1:  # hashtree (dm-verity)
            (ver, img_size, tree_off, tree_size, dbs, hbs, fec_roots, fec_off,
             fec_size) = struct.unpack_from(">IQQQIIIQQ", body, 0)
            alg = cstr(body[56:88])
            name_len, salt_len, dig_len, flags = struct.unpack_from(">IIII", body, 88)
            p = 88 + 16 + 60
            name = body[p:p + name_len].decode()
            p += name_len
            salt = body[p:p + salt_len].hex()
            p += salt_len
            out.append({"type": "hashtree", "partition": name, "dm_verity_version": ver,
                        "image_size": img_size, "tree_offset": tree_off,
                        "tree_size": tree_size, "data_block_size": dbs,
                        "hash_block_size": hbs, "fec_num_roots": fec_roots,
                        "fec_offset": fec_off, "fec_size": fec_size,
                        "hash_algorithm": alg, "salt": salt,
                        "root_digest": body[p:p + dig_len].hex(), "flags": flags})
        elif tag == 2:  # hash
            img_size = struct.unpack_from(">Q", body, 0)[0]
            alg = cstr(body[8:40])
            name_len, salt_len, dig_len, flags = struct.unpack_from(">IIII", body, 40)
            p = 40 + 16 + 60
            name = body[p:p + name_len].decode()
            p += name_len
            salt = body[p:p + salt_len].hex()
            p += salt_len
            out.append({"type": "hash", "partition": name, "image_size": img_size,
                        "hash_algorithm": alg, "salt": salt,
                        "digest": body[p:p + dig_len].hex(), "flags": flags})
        elif tag == 3:  # kernel cmdline
            flags, ln = struct.unpack_from(">II", body, 0)
            out.append({"type": "kernel_cmdline", "flags": flags,
                        "cmdline": body[8:8 + ln].decode(errors="replace")})
        elif tag == 4:  # chain partition
            rloc, name_len, pk_len = struct.unpack_from(">III", body, 0)
            p = 12 + 4 + 60
            name = body[p:p + name_len].decode()
            pk = body[p + name_len:p + name_len + pk_len]
            out.append({"type": "chain_partition", "partition": name,
                        "rollback_index_location": rloc,
                        "public_key_sha1": hashlib.sha1(pk).hexdigest()})
        else:
            out.append({"type": f"unknown_{tag}", "size": n})
    return out


def parse_vbmeta(blob):
    if blob[:4] != b"AVB0":
        return None
    (major, minor, auth_size, aux_size, alg, _ho, _hs, _so, sig_size, pk_off, pk_size,
     _pmo, _pms, desc_off, desc_size, rollback, flags, rloc) = struct.unpack_from(
        ">IIQQIQQQQQQQQQQQII", blob, 4)
    release = cstr(blob[128:176])
    aux = blob[256 + auth_size: 256 + auth_size + aux_size]
    pk = aux[pk_off:pk_off + pk_size]
    return {
        "libavb_version": f"{major}.{minor}",
        "algorithm": ALGORITHMS.get(alg, alg),
        "signed": alg != 0 and sig_size > 0,
        "public_key_sha1": hashlib.sha1(pk).hexdigest() if pk else None,
        "rollback_index": rollback,
        "rollback_index_location": rloc,
        "flags": flags,
        "flags_decoded": [v for k, v in HEADER_FLAGS.items() if flags & k],
        "release_string": release,
        "descriptors": parse_descriptors(aux[desc_off:desc_off + desc_size]),
    }


def inspect(path):
    with open(path, "rb") as f:
        head = f.read(64 * 1024)
        info = {"file": path}
        meta = parse_vbmeta(head)
        if meta:
            info["kind"] = "vbmeta"
            info.update(meta)
            return info
        f.seek(-64, 2)
        foot = f.read(64)
        if foot[:4] == b"AVBf":
            _maj, _min, orig_size, vb_off, vb_size = struct.unpack_from(">IIQQQ", foot, 4)
            f.seek(vb_off)
            info["kind"] = "footer"
            info["original_image_size"] = orig_size
            info.update(parse_vbmeta(f.read(vb_size)) or {})
            return info
    info["kind"] = "none"
    return info


if __name__ == "__main__":
    print(json.dumps([inspect(p) for p in sys.argv[1:]], indent=2, ensure_ascii=False))
