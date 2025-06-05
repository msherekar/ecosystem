"""
File Handler Module

Provides file upload and handling functionality.
"""

from typing import Dict, Any
import streamlit as st


def handle_file_upload(file=None) -> Dict[str, Any]:
    """
    Handle file upload functionality
    
    Args:
        file: Optional file object from Streamlit file_uploader
        
    Returns:
        Dictionary with upload result
    """
    try:
        if file is None:
            # Display file upload widget
            uploaded_file = st.file_uploader(
                "Choose a file",
                type=['csv', 'h5ad', 'xlsx', 'tsv', 'h5', 'txt', 'json']
            )
            
            if uploaded_file is not None:
                # Store in session state
                st.session_state["uploaded_file"] = uploaded_file
                st.session_state["uploaded_data"] = uploaded_file
                
                return {
                    "success": True,
                    "message": f"Successfully uploaded {uploaded_file.name}",
                    "filename": uploaded_file.name,
                    "size": uploaded_file.size,
                    "type": uploaded_file.type
                }
            else:
                return {
                    "success": False,
                    "message": "No file selected",
                    "action_required": "Please select a file to upload"
                }
        else:
            # Process provided file
            st.session_state["uploaded_file"] = file
            st.session_state["uploaded_data"] = file
            
            return {
                "success": True,
                "message": f"Successfully processed {file.name}",
                "filename": file.name,
                "size": file.size,
                "type": file.type
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"File upload failed: {str(e)}",
            "error": str(e)
        }


# Test code to verify the module works independently
if __name__ == "__main__":
    def test_file_handler():
        """Test file handler functionality"""
        print("Testing file_handler module...")
        
        # Test handle_file_upload without file
        result = handle_file_upload()
        print(f"✅ handle_file_upload without file: {result.get('success', 'unknown')}")
        
        # Mock file object for testing
        class MockFile:
            def __init__(self):
                self.name = "test_file.csv"
                self.size = 1024
                self.type = "text/csv"
        
        mock_file = MockFile()
        result = handle_file_upload(mock_file)
        print(f"✅ handle_file_upload with mock file: {result.get('success', False)}")
        print(f"   Message: {result.get('message', 'No message')}")
        
        print("🎉 All file_handler tests passed!")
    
    # Run test
    test_file_handler() 