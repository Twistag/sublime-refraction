import sublime
import sublime_plugin
import urllib.request
import json
import select
import time


BASE_URL = "https://www.refraction.dev"


# Sublime Services
def get_selected_text(self):
    result = ""
    for region in self.view.sel():
        result += self.view.substr(region)
    return result

def get_code_and_lang(self):
    code = get_selected_text(self)
    lang = "Python"
    data = {
        'code': code,
        'language': lang
    }
    return data


# Extension Functionality
def authenticate(data, callback):
    response = call_backend('/api/vscode/authenticate', data)
    if not is_2xx(response):
        sublime.error_message("User is not authenticated")
    else:
        callback()


def get_generated_data(utility, request_body, callback):
    with call_backend('/api/generate/' + utility, request_body) as response:
        callback("\n\n", 0)
        offset = len("\n\n")
        while not response.closed:
            ready_to_read, _, _ = select.select([response], [], [], 0.1)

            if response in ready_to_read:
                line = response.readline().decode()
                if not line:
                    break

                time.sleep(0.005)
                callback(line, offset)
                offset += len(line)


def generate_async(self, utility):
    auth_credentials = get_auth_credentials()
    request_body = get_code_and_lang(self)
    if is_empty_string(auth_credentials['userId']):
        sublime.error_message('Please set your Refraction User ID. Use method "Refraction: Enter User Credentials"')
    elif is_empty_string(request_body['code']):
        sublime.error_message("No code selected")
    elif is_empty_string(request_body['language']):
        sublime.error_message("Language not set")
    elif len(request_body['code']) > 3000:
        sublime.error_message("Sorry, but the code you've selected is too long (" + str(len(request_body['code'])) + " tokens). Please reduce the length of your code to 3000 tokens or less.")
    else:
        handle_response = lambda response_data, offset: print_response_data(self, response_data, offset)
        call_generate = lambda: get_generated_data(utility, request_body, handle_response)
        call_auth = lambda: authenticate(auth_credentials, call_generate)
        send_request_async(call_auth)

def print_response_data(self, response_data, offset):
    print(response_data)
    self.view.run_command("insert_after_selection", {"text": response_data, 'offset': offset})


# Http Client
def send_request_async(callback):
    def async_request():
        callback()

    sublime.set_timeout_async(async_request, 0)


def call_backend(path, request_body):
    url = BASE_URL + path
    auth_data = get_auth_credentials()
    data_bytes = json.dumps(request_body).encode('utf-8')
    request = urllib.request.Request(url, data=data_bytes, method='POST')

    request.add_header("Content-Type", "application/json")
    request.add_header("X-Refraction-Source", "sublime")
    request.add_header("X-Refraction-User", auth_data["userId"])
    request.add_header("X-Refraction-Team", auth_data["teamId"])

    response = urllib.request.urlopen(request)
    return response


def is_2xx(http_response):
    return 200 >= http_response.status and http_response.status < 300


# Auth Properties
def get_auth_credentials():
    settings = sublime.load_settings("Refraction.sublime-settings")

    userId = settings.get("userId")
    teamId = settings.get("teamId")
    if userId is None:
        userId = ""
    if teamId is None:
        teamId = ""
    data = {
        'userId': userId,
        'teamId': teamId
    }
    return data


def update_auth_credentials(auth_credentials):
    settings = sublime.load_settings("Refraction.sublime-settings")
    settings.set("userId", auth_credentials["userId"])
    settings.set("teamId", auth_credentials["teamId"])


# Utils
def is_empty_string(text):
    return text is None or len(text) == 0


# Commands
class RefractionBugsCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        sublime.status_message("This is a warning message!")
        generate_async(self, 'bugs')


class RefractionDebugCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        generate_async(self, 'debug')


class RefractionDocumentationCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        generate_async(self, 'documentation')


class RefractionLiteralsCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        generate_async(self, 'literals')


class RefractionRefactorCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        generate_async(self, 'refactor')


class RefractionStyleCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        generate_async(self, 'style')


class RefractionTypesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        generate_async(self, 'types')


class RefractionUnitTestsCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.insert(edit, 0, "unit-tests")


class InsertAfterSelectionCommand(sublime_plugin.TextCommand):
    def run(self, edit, text, offset):
        for region in self.view.sel():
            self.view.insert(edit, region.end() + offset, text)


class RefractionInputUserCredentialsCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        def on_done(input_values):
            userId = input_values[0]
            teamId = input_values[1]
            auth_credentials = {
                'userId': userId,
                'teamId': teamId
            }
            update_auth_credentials(auth_credentials)

        auth_credentials = get_auth_credentials()

        self.view.window().show_input_panel(
            "Enter user id:",
            auth_credentials['userId'],
            lambda userId: self.on_field1_done(userId, on_done, auth_credentials),
            None,
            None
        )

    def on_field1_done(self, userId, on_done, auth_credentials):
        self.view.window().show_input_panel(
            "Enter team id:",
            auth_credentials["teamId"],
            lambda teamId: on_done([userId, teamId]),
            None,
            None
        )
