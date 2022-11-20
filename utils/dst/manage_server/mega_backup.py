import os
import json
import hashlib
import shutil

from get_config import CLUSTER_DIR, BACKUP_DIR


SESSION_PATH = 'save/session'
BACK_UP_RECORD_PATH = os.path.join(BACKUP_DIR, 'record.json')

HEX_STR = "0123456789ABCDEF"


def backup():
    if os.path.exists(BACK_UP_RECORD_PATH):
        with open(BACK_UP_RECORD_PATH, 'r') as fp:
            cluster_records = json.load(fp)
    else:
        cluster_records = {}
    levels = ("Master", "Caves")
    m_session = c_session = None
    for level in levels:
        level_dir = os.path.join(CLUSTER_DIR, level)
        if os.path.exists(level_dir):
            pass  # log handle
            session_dir = os.path.join(level_dir, SESSION_PATH)
            if os.path.exists(session_dir):
                for entry in os.scandir(session_dir):
                    if len(entry.name) == 16 and \
                            all(map(lambda x: x in HEX_STR, entry.name)):
                        if level == levels[0]:  # Master
                            m_session = entry.name
                        else:  # Caves
                            c_session = entry.name
                        _backup(entry)                       
    if m_session and c_session:
        cluster_records[m_session] = (c_session, "Master")
        cluster_records[c_session] = (m_session, "Caves")
    elif m_session and c_session is None:
        cluster_records[m_session] = (None, "Master")
    with open(BACK_UP_RECORD_PATH, 'w') as fp:
        json.dump(cluster_records, fp)


def _backup(e):
    """
    :param e: entry obj of 16bit hex session folder
    """
    backup_session_dir = os.path.join(BACKUP_DIR, e.name)
    if not os.path.exists(backup_session_dir):
        os.mkdir(backup_session_dir)
    for entry in os.scandir(e.path):
        if entry.is_dir():
            backup_user_dir = os.path.join(
                backup_session_dir,
                entry.name,
            )
            if not os.path.exists(backup_user_dir):
                os.mkdir(backup_user_dir)
            for user_entry in os.scandir(entry.path):
                dst = os.path.join(backup_user_dir, user_entry.name)
                compare_and_copy(user_entry.path, dst)
        elif entry.is_file():
            dst = os.path.join(backup_session_dir, entry.name)
            copied = compare_and_copy(entry.path, dst)


def compare(f1, f2):
    with open(f1, 'rb') as fp1:
        digest1 = hashlib.sha1(fp1.read()).hexdigest()
    with open(f2, 'rb') as fp2:
        digest2 = hashlib.sha1(fp2.read()).hexdigest()
    return digest1 == digest2


def compare_and_copy(src, dst):
    if os.path.exists(dst):
                same = compare(src, dst)
                if same:
                    return False
    # not exists or not same
    shutil.copy2(src, dst)
    print(f"copy from{src} to {dst}")
    return True


if __name__ == "__main__":
    backup()