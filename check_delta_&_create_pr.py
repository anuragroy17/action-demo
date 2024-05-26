import os
import requests
import zipfile
import difflib
import subprocess
from github import Github

# Download the ZIP file from the URL
def download_file(url, local_filename):
    response = requests.get(url)
    if 'Content-Disposition' in response.headers:
        content_disposition = response.headers['Content-Disposition']
        filename = content_disposition.split('filename=')[-1].strip('"')
    else:
        filename = local_filename
    
    with open(filename, 'wb') as f:
        f.write(response.content)
    
    return filename

# Unzip the file
def unzip_file(zip_filename, extract_to):
    with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

# Check for differences
def check_differences(file1, file2):
    with open(file1, 'r') as f1, open(file2, 'r') as f2:
        diff = list(difflib.unified_diff(f1.readlines(), f2.readlines()))
    return diff

# Create a pull request
def create_pull_request(token, repo_name, base_branch, head_branch, title, body):
    g = Github(token)
    repo = g.get_repo(repo_name)
    pr = repo.create_pull(title=title, body=body, base=base_branch, head=head_branch)
    print(f"Pull Request created: {pr.html_url}")

def main():
    url = os.getenv('FILE_URL')
    repo_dir = os.getenv('REPO_DIR')
    github_token = os.getenv('GITHUB_TOKEN')
    repo_name = os.getenv('REPO_NAME')
    base_branch = os.getenv('BASE_BRANCH', 'main')
    head_branch = os.getenv('HEAD_BRANCH', 'update-branch')
    
    # Step 1: Download the ZIP file
    downloaded_zip = download_file(url, 'downloaded_file.zip')
    
    # Step 2: Unzip the file
    extracted_dir = 'extracted_files'
    unzip_file(downloaded_zip, extracted_dir)
    
    # Step 3: Check for differences
    files_with_differences = []
    new_files = []
    for root, _, files in os.walk(extracted_dir):
        for file in files:
            extracted_file_path = os.path.join(root, file)
            repo_file_path = os.path.join(repo_dir, os.path.relpath(extracted_file_path, extracted_dir))
            if os.path.exists(repo_file_path):
                if os.path.basename(extracted_file_path) == os.path.basename(repo_file_path):
                    diff = check_differences(extracted_file_path, repo_file_path)
                    if diff:
                        files_with_differences.append((extracted_file_path, repo_file_path))
                else:
                    new_files.append((extracted_file_path, repo_file_path))
            else:
                new_files.append((extracted_file_path, repo_file_path))
    
    # Step 4: Raise a PR if there are differences or new files
    if files_with_differences or new_files:
        # Create a new branch
        subprocess.run(['git', 'checkout', '-b', head_branch])
        
        # Copy the files with differences and new files to the repo directory
        for extracted_file_path, repo_file_path in files_with_differences + new_files:
            os.makedirs(os.path.dirname(repo_file_path), exist_ok=True)
            subprocess.run(['cp', extracted_file_path, repo_file_path])
        
        # Commit the changes
        subprocess.run(['git', 'add', '.'])
        subprocess.run(['git', 'commit', '-m', 'Update files with differences and add new files'])
        subprocess.run(['git', 'push', 'origin', head_branch])
        
        # Create the pull request
        pr_title = 'Update files with differences and add new files'
        pr_body = 'This PR updates the files with differences and adds new files from the downloaded ZIP file.'
        create_pull_request(github_token, repo_name, base_branch, head_branch, pr_title, pr_body)

if __name__ == "__main__":
    main()
