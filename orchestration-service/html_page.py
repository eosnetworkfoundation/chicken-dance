"""modules for assembling HTML pages from files"""

class HtmlPage:
    """class for assembling HTML pages from files"""
    def __init__(self, html_dir):
        self.html_dir = html_dir
        if not self.html_dir.endswith('/'):
            self.html_dir = self.html_dir + '/'

    def contents(self, file_name="progress.html"):
        """Return contents of html files"""

        if file_name == '/progress':
            file_name = 'progress.html'
        elif file_name == '/grid':
            file_name = 'grid.html'
        elif file_name == '/control':
            file_name = 'control.html'

        file_path = self.html_dir + file_name
        with open(file_path, 'r', encoding='utf-8') as file:
            # Read the file's contents into a string
            file_contents = file.read()
        return file_contents

    def profile_top_bar_html(self, login, avatar_url):
        """return top bar with profile"""
        return f'''    <div class="topbar">
    <a href="/logout">
        <span class="material-symbols-outlined">
           <img src="{avatar_url}">
        </span>
    </a>
    <p>{login}</p>
    </div>'''

    def default_top_bar_html(self, oauth_url):
        """return top bar with no profile"""
        return f'''    <div class="topbar"> <a href="{oauth_url}">
        <span class="material-symbols-outlined">account_circle</span>
    </a> </div>'''

    def not_authorized(self, message="Not Autorized: Please Log In"):
        """return not autorized page contents"""
        return f'''    <div class="maincontent">
        <h2>{message}</h2>
    </div>'''
