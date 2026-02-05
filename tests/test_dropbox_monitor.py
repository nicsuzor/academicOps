import pytest
from pathlib import Path
from unittest.mock import patch

# Add project root to path
import sys
REPO_ROOT = Path(__file__).parents[1].resolve()
sys.path.insert(0, str(REPO_ROOT))

from scripts.lib.incoming_processor import process_incoming_file

@pytest.fixture
def temp_incoming(tmp_path):
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    return incoming

@pytest.fixture
def temp_processed(tmp_path):
    processed = tmp_path / "processed"
    processed.mkdir()
    return processed

@patch("scripts.lib.incoming_processor.Path.home")
@patch("scripts.lib.incoming_processor.notify_user")
def test_process_text_file(mock_notify, mock_home, temp_incoming, temp_processed):
    # Setup mock home to return tmp_path
    mock_home.return_value = temp_processed.parent
    
    # Create a dummy text file
    test_file = temp_incoming / "test.txt"
    test_file.write_text("Hello World")
    
    # Run processor
    process_incoming_file(test_file)
    
    # Verify file moved to notes
    expected_dest = temp_processed.parent / "processed" / "notes" / "test.txt"
    assert expected_dest.exists()
    assert expected_dest.read_text() == "Hello World"
    
    # Verify notification
    mock_notify.assert_called()

@patch("scripts.lib.incoming_processor.Path.home")
@patch("scripts.lib.incoming_processor.notify_user")
def test_process_pdf_file(mock_notify, mock_home, temp_incoming, temp_processed):
    # Setup mock home
    mock_home.return_value = temp_processed.parent
    
    # Create a dummy PDF file (empty is fine for flow check, but pdfminer might choke)
    # We should mock extract_text to avoid needing a real PDF
    with patch("pdfminer.high_level.extract_text") as mock_extract:
        mock_extract.return_value = "Extracted Text Content"
        
        test_file = temp_incoming / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4...")
        
        # Run processor
        process_incoming_file(test_file)
        
        # Verify MD created in docs
        expected_md = temp_processed.parent / "processed" / "docs" / "test.md"
        assert expected_md.exists()
        assert "Extracted Text Content" in expected_md.read_text()

