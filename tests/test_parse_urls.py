import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tools.parse_urls import extract_urls_from_text


def test_extract_urls_basic():
    text = "Visit http://example.com and also check www.test.com/path and https://sub.example.org." 
    urls = extract_urls_from_text(text)
    assert "http://example.com" in urls
    assert "www.test.com/path" in urls
    assert any(u.startswith("https://sub.example.org") for u in urls)


def test_extract_none():
    assert extract_urls_from_text("") == []
    assert extract_urls_from_text("no links here") == []
