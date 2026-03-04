from http import HTTPStatus
from json import loads

from flask.testing import FlaskClient
from pyquery import PyQuery

from core.util.types import NameValueDict


def response_text(response):
    text = response.text
    if "<h1>" in text:
        doc = PyQuery(text)
        return f"{doc('h1').text()}\n\t{doc('p.error').text()}"
    return text


def assert_ok(response) -> None:
    assert response.status_code == HTTPStatus.OK, (
        f"{response.status_code=}, {response_text(response)}"
    )


def assert_not_ok(response) -> None:
    assert response.status_code != HTTPStatus.OK, (
        f"{response.status_code=}, {response_text(response)}"
    )


def assert_expected(response, expect_fail: bool) -> None:
    if expect_fail:
        assert_not_ok(response)
    else:
        assert_ok(response)


def get(
    client: FlaskClient,
    url: str,
    data=None,
    follow_redirects=True,
    expect_fail: bool = False,
):
    response = client.get(url, data=data, follow_redirects=follow_redirects)
    assert_expected(response, expect_fail)
    return response


def post(client: FlaskClient, url: str, data=None, expect_fail: bool = False):
    response = client.post(url, data=data, follow_redirects=True)
    assert_expected(response, expect_fail)
    return response


def get_json(client: FlaskClient, url: str, json: NameValueDict, expect_fail: bool = False):
    response = client.get(url, json=json, content_type="application/json")
    assert_expected(response, expect_fail)
    json_data = loads(response.data)
    return json_data


def post_json(client: FlaskClient, url: str, json: NameValueDict, expect_fail: bool = False):
    response = client.post(url, json=json, content_type="application/json")
    assert_expected(response, expect_fail)
    json_data = loads(response.data)
    return json_data


def set_session(client: FlaskClient, key, value):
    with client.session_transaction() as session:
        session[key] = value


def login(client: FlaskClient, email: str, password: str):
    data = dict(email=email, password=password, remember_me=True)
    post(client, "/account/login", data)


def logout(client: FlaskClient):
    get(client, "/account/logout")


def assert_form_fields(form_data: NameValueDict, **kw) -> None:
    for key, value in kw.items():
        assert form_data.get(key) == value, f"{key}:\t|{form_data.get(key)}| != |{value}|"
