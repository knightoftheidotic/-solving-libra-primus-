import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tools.parse_hashes import extract_hashes_from_text


def test_extract_hashes_basic():
    text = "Here is a hash: 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824 and another: 2CF24DBA5FB0A30E26E83B2AC5B9E29E1B161E5C1FA7425E73043362938B9824"
    hashes = extract_hashes_from_text(text)
    assert len(hashes) == 1
    assert hashes[0] == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_extract_none():
    assert extract_hashes_from_text("") == []
    assert extract_hashes_from_text("no hashes here") == []
