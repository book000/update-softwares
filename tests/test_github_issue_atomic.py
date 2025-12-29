import unittest
from unittest.mock import patch, MagicMock, call
import requests
from src import GitHubIssue

class TestGitHubIssueAtomic(unittest.TestCase):
  def setUp(self):
    self.repo_name = "test/repo"
    self.issue_number = "123"
    self.github_token = "test_token"
        
  @patch('src.requests.get')
  def test_github_issue_initialization(self, mock_get):
    """Test GitHubIssue initialization with atomic update support."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
      "body": "| ⏳ | Computer1 | Linux | apt | 0 | 0 | <!-- update-softwares#Computer1#apt -->\n"
                                      "| ✅ | Computer2 | Windows | scoop | 5 | 0 | <!-- update-softwares#Computer2#scoop -->"
    }
    mock_get.return_value = mock_response
        
    github_issue = GitHubIssue(self.repo_name, self.issue_number, self.github_token)
        
    self.assertEqual(github_issue.repo_name, self.repo_name)
    self.assertEqual(github_issue.issue_number, self.issue_number)
    self.assertEqual(github_issue.github_token, self.github_token)
    self.assertIsNotNone(github_issue.pending_updates)
    self.assertIsNotNone(github_issue.initial_body_state)
    self.assertEqual(len(github_issue.software_updates), 2)

  @patch('src.requests.patch')
  @patch('src.requests.get')
  def test_atomic_update_with_retry_success(self, mock_get, mock_patch):
    """Test successful atomic update without retry."""
    # Setup initial issue body
    initial_body = "| ⏳ | Computer1 | Linux | apt | 0 | 0 | <!-- update-softwares#Computer1#apt -->"
        
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {"body": initial_body}
    mock_get.return_value = mock_get_response
        
    # Setup successful patch response
    mock_patch_response = MagicMock()
    mock_patch_response.status_code = 200
    mock_patch.return_value = mock_patch_response
        
    github_issue = GitHubIssue(self.repo_name, self.issue_number, self.github_token)
        
    # Test atomic update
    result = github_issue.atomic_update_with_retry(
      computer_name="Computer1",
      package_manager="apt", 
      status="success",
      upgraded="5",
      failed="0"
    )
        
    self.assertTrue(result)
    mock_patch.assert_called_once()
        
    # Verify the patch call contains the expected updated body
    patch_call_args = mock_patch.call_args
    updated_body = patch_call_args[1]['json']['body']
    self.assertIn("✅", updated_body)  # Success checkmark
    self.assertIn("5", updated_body)   # Upgraded count
    self.assertIn("0", updated_body)   # Failed count

  @patch('src.requests.patch')
  @patch('src.requests.get')
  def test_atomic_update_with_retry_on_failure(self, mock_get, mock_patch):
    """Test atomic update with retry on API failure."""
    # Setup initial issue body
    initial_body = "| ⏳ | Computer1 | Linux | apt | 0 | 0 | <!-- update-softwares#Computer1#apt -->"
        
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {"body": initial_body}
    mock_get.return_value = mock_get_response
        
    # Setup patch responses: fail first, succeed second
    mock_patch_response_fail = MagicMock()
    mock_patch_response_fail.status_code = 409  # Conflict
    mock_patch_response_fail.text = "Conflict"
        
    mock_patch_response_success = MagicMock()
    mock_patch_response_success.status_code = 200
        
    mock_patch.side_effect = [mock_patch_response_fail, mock_patch_response_success]
        
    github_issue = GitHubIssue(self.repo_name, self.issue_number, self.github_token)
        
    # Mock time.sleep to speed up test
    with patch('time.sleep'):
      result = github_issue.atomic_update_with_retry(
        computer_name="Computer1",
        package_manager="apt",
        status="failed", 
        upgraded="3",
        failed="2"
      )
        
    self.assertTrue(result)
    self.assertEqual(mock_patch.call_count, 2)  # Should retry once

  @patch('src.requests.patch')
  @patch('src.requests.get')
  def test_atomic_update_max_retries_exceeded(self, mock_get, mock_patch):
    """Test atomic update when max retries are exceeded."""
    # Setup initial issue body
    initial_body = "| ⏳ | Computer1 | Linux | apt | 0 | 0 | <!-- update-softwares#Computer1#apt -->"
        
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {"body": initial_body}
    mock_get.return_value = mock_get_response
        
    # Setup patch to always fail
    mock_patch_response = MagicMock()
    mock_patch_response.status_code = 500
    mock_patch_response.text = "Internal Server Error"
    mock_patch.return_value = mock_patch_response
        
    github_issue = GitHubIssue(self.repo_name, self.issue_number, self.github_token)
        
    # Mock time.sleep to speed up test
    with patch('time.sleep'):
      with self.assertRaises(Exception) as context:
        github_issue.atomic_update_with_retry(
          computer_name="Computer1",
          package_manager="apt",
          status="failed",
          upgraded="0", 
          failed="1",
          max_retries=2
        )
        
    self.assertIn("Failed to update issue body", str(context.exception))
    self.assertEqual(mock_patch.call_count, 2)  # Should retry max_retries times

  @patch('src.requests.get')
  def test_get_software_update_rows_from_body(self, mock_get):
    """Test parsing software update rows from body content."""
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {"body": "test"}
    mock_get.return_value = mock_get_response
        
    github_issue = GitHubIssue(self.repo_name, self.issue_number, self.github_token)
        
    test_body = (
      "| ⏳ | Computer1 | Linux | apt | 0 | 0 | <!-- update-softwares#Computer1#apt -->\n"
      "| ✅ | Computer2 | Windows | scoop | 5 | 0 | <!-- update-softwares#Computer2#scoop -->"
    )
        
    software_updates = github_issue._get_software_update_rows_from_body(test_body)
        
    self.assertEqual(len(software_updates), 2)
        
    # Check first entry
    self.assertEqual(software_updates[0]["computer_name"], "Computer1")
    self.assertEqual(software_updates[0]["package_manager"], "apt")
    self.assertEqual(software_updates[0]["markdown"]["checkmark"], "⏳")
    self.assertEqual(software_updates[0]["markdown"]["computer_name"], "Computer1")
    self.assertEqual(software_updates[0]["markdown"]["operation_system"], "Linux")
        
    # Check second entry  
    self.assertEqual(software_updates[1]["computer_name"], "Computer2")
    self.assertEqual(software_updates[1]["package_manager"], "scoop")
    self.assertEqual(software_updates[1]["markdown"]["checkmark"], "✅")
    self.assertEqual(software_updates[1]["markdown"]["upgraded"], "5")

  @patch('src.requests.get')
  def test_build_updated_body(self, mock_get):
    """Test building updated issue body with modified software updates."""
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {"body": "test"}
    mock_get.return_value = mock_get_response
        
    github_issue = GitHubIssue(self.repo_name, self.issue_number, self.github_token)
        
    original_body = (
      "# Update Status\n"
      "| ⏳ | Computer1 | Linux | apt | 0 | 0 | <!-- update-softwares#Computer1#apt -->\n"
      "| ✅ | Computer2 | Windows | scoop | 5 | 0 | <!-- update-softwares#Computer2#scoop -->\n"
      "End of document"
    )
        
    # Parse and modify software updates
    software_updates = github_issue._get_software_update_rows_from_body(original_body)
    software_updates[0]["markdown"]["checkmark"] = "✅"
    software_updates[0]["markdown"]["upgraded"] = "3"
    software_updates[0]["markdown"]["failed"] = "1"
    software_updates[0]["markdown"]["raw"] = "| ✅ | Computer1 | Linux | apt | 3 | 1 |"
        
    updated_body = github_issue._build_updated_body(original_body, software_updates)
        
    # Verify the updated body contains the new values
    self.assertIn("| ✅ | Computer1 | Linux | apt | 3 | 1 | <!-- update-softwares#Computer1#apt -->", updated_body)
    self.assertIn("| ✅ | Computer2 | Windows | scoop | 5 | 0 | <!-- update-softwares#Computer2#scoop -->", updated_body)
    self.assertIn("# Update Status", updated_body)
    self.assertIn("End of document", updated_body)
    
  @patch('src.requests.get')
  def test_parse_body_with_os_eol_column(self, mock_get):
    """Test parsing issue body with OS EOL column."""
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {"body": "test"}
    mock_get.return_value = mock_get_response
        
    github_issue = GitHubIssue(self.repo_name, self.issue_number, self.github_token)
        
    # 新フォーマット (OS EOL 列あり)
    body_with_eol = (
      "| ⏳ | Computer1 | Linux | apt | 0 | 0 | 2027/04/30 (500 日後) | <!-- update-softwares#Computer1#apt -->\n"
      "| 🔴 | Computer2 | Windows | scoop | 5 | 0 | **2025/10/14 (50 日後)** | <!-- update-softwares#Computer2#scoop -->"
    )
        
    software_updates = github_issue._get_software_update_rows_from_body(body_with_eol)
        
    self.assertEqual(len(software_updates), 2)
        
    # 1つ目のエントリ (OS EOL あり)
    self.assertEqual(software_updates[0]["computer_name"], "Computer1")
    self.assertEqual(software_updates[0]["package_manager"], "apt")
    self.assertEqual(software_updates[0]["markdown"]["os_eol"], "2027/04/30 (500 日後)")
        
    # 2つ目のエントリ (OS EOL あり、クリティカル)
    self.assertEqual(software_updates[1]["computer_name"], "Computer2")
    self.assertEqual(software_updates[1]["package_manager"], "scoop")
    self.assertEqual(software_updates[1]["markdown"]["os_eol"], "**2025/10/14 (50 日後)**")
    
  @patch('src.requests.patch')
  @patch('src.requests.get')
  def test_atomic_update_with_os_eol(self, mock_get, mock_patch):
    """Test atomic update with OS EOL information."""
    # Setup initial issue body with OS EOL column
    initial_body = "| ⏳ | Computer1 | Linux | apt | 0 | 0 | 不明 | <!-- update-softwares#Computer1#apt -->"
        
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {"body": initial_body}
    mock_get.return_value = mock_get_response
        
    # Setup successful patch response
    mock_patch_response = MagicMock()
    mock_patch_response.status_code = 200
    mock_patch.return_value = mock_patch_response
        
    github_issue = GitHubIssue(self.repo_name, self.issue_number, self.github_token)
        
    # Test atomic update with OS EOL
    result = github_issue.atomic_update_with_retry(
      computer_name="Computer1",
      package_manager="apt",
      status="success",
      upgraded="5",
      failed="0",
      os_eol="2027/04/30 (800 日後)",
      os_eol_critical=False
    )
        
    self.assertTrue(result)
    mock_patch.assert_called_once()
        
    # Verify the patch call contains the expected updated body with OS EOL
    patch_call_args = mock_patch.call_args
    updated_body = patch_call_args[1]['json']['body']
    self.assertIn("✅", updated_body)  # Success checkmark
    self.assertIn("5", updated_body)   # Upgraded count
    self.assertIn("0", updated_body)   # Failed count
    self.assertIn("2027/04/30 (800 日後)", updated_body)  # OS EOL info
    
  @patch('src.requests.patch')
  @patch('src.requests.get')
  def test_atomic_update_with_critical_os_eol(self, mock_get, mock_patch):
    """Test atomic update with critical OS EOL (less than 90 days)."""
    # Setup initial issue body with OS EOL column
    initial_body = "| ⏳ | Computer1 | Windows | scoop | 0 | 0 | 不明 | <!-- update-softwares#Computer1#scoop -->"
        
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {"body": initial_body}
    mock_get.return_value = mock_get_response
        
    # Setup successful patch response
    mock_patch_response = MagicMock()
    mock_patch_response.status_code = 200
    mock_patch.return_value = mock_patch_response
        
    github_issue = GitHubIssue(self.repo_name, self.issue_number, self.github_token)
        
    # Test atomic update with critical OS EOL (checkmark should be 🔴)
    result = github_issue.atomic_update_with_retry(
      computer_name="Computer1",
      package_manager="scoop",
      status="success",
      upgraded="13",
      failed="0",
      os_eol="**2025/12/31 (20 日後)**",
      os_eol_critical=True
    )
        
    self.assertTrue(result)
    mock_patch.assert_called_once()
        
    # Verify the patch call contains 🔴 checkmark for critical EOL
    patch_call_args = mock_patch.call_args
    updated_body = patch_call_args[1]['json']['body']
    self.assertIn("🔴", updated_body)  # Critical checkmark
    self.assertIn("13", updated_body)  # Upgraded count
    self.assertIn("0", updated_body)   # Failed count
    self.assertIn("**2025/12/31 (20 日後)**", updated_body)  # Critical OS EOL info

if __name__ == "__main__":
  unittest.main()
