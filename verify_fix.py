
import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from lib.overwhelm.dashboard import clean_activity_text

def test_clean_activity_text():
    # Test docstring
    assert "max 120 characters" in clean_activity_text.__doc__
    print("Docstring verification passed.")

    # Test functionality
    long_text = "a" * 150
    cleaned = clean_activity_text(long_text)
    
    # It should be 120 chars long (117 chars + "...")
    assert len(cleaned) == 120
    assert cleaned.endswith("...")
    assert cleaned.startswith("a" * 117)
    print("Functionality verification passed.")

if __name__ == "__main__":
    test_clean_activity_text()
