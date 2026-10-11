"""The page is served. That is all this test can tell you.

It passes on the kit's page, which has planted usability and accessibility problems, and it
passes on a fixed page too. A green run says nothing about whether a keyboard can reach the
Reserve button, whether a screen reader hears the result, or whether Maya taps twice.
Those need the manual procedures in checklist.md.
"""


def test_the_page_is_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "AfterHours" in res.text
