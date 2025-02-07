import requests


class ApiException(Exception):
    def __init__(self, response: requests.Response) -> None:
        super().__init__(f"status code {response.status_code}: {response.text or 'no content'}")
        self.status_code = response.status_code
        self.text = response.text
