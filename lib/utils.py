import hashlib
import bisect


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def get_df_after_given_date(df, date):
    """Slice the df to only contain data after the given date.
    Assume df.index is datetime objects"""
    return df[bisect.bisect_left(df.index, date) :]