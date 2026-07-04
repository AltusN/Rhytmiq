"""
    Test cases for the Group router.
    - Post a new group
    - Get all groups with a filter by optional club_id query parameter
    - Get a group by ID
    - Update a group by ID
    - Delete a group by ID
"""
from fastapi import status

from test.conftest import make_club, make_group


##-- Post a new group
def test_create_group(client, db_session):
    club = make_club(db_session)
    response = client.post("/groups/", json={"club_id": club.id, "name": "Group A"})
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["club_id"] == club.id
    assert data["name"] == "Group A"

def test_create_group_duplicate_name(client, db_session):
    club = make_club(db_session)
    make_group(db_session, club, name="Group A")
    response = client.post("/groups/", json={"club_id": club.id, "name": "Group A"})
    assert response.status_code == status.HTTP_409_CONFLICT

def test_create_group_invalid_club_id(client):
    response = client.post("/groups/", json={"club_id": 9999, "name": "Group A"})
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_create_group_with_whitespace_name(client, db_session):
    club = make_club(db_session)
    response = client.post("/groups/", json={"club_id": club.id, "name": "  Group B  "})
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Group B"  # Ensure whitespace is stripped

##-- Get all groups with a filter by optional club_id query parameter
def test_list_groups(client, db_session):
    club1 = make_club(db_session)
    club2 = make_club(db_session)
    make_group(db_session, club1, name="Group 1")
    make_group(db_session, club1, name="Group 2")
    make_group(db_session, club2, name="Group 3")

    response = client.get("/groups/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 3

    response = client.get(f"/groups/?club_id={club1.id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2

def test_get_group_by_id(client, db_session):
    club = make_club(db_session)
    group = make_group(db_session, club, name="Group A")
    response = client.get(f"/groups/{group.id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == group.id
    assert data["name"] == "Group A"

def test_list_all_groups(client, db_session):
    club = make_club(db_session)
    club2 = make_club(db_session, name="Another Club")
    make_group(db_session, club, name="Group 1")
    make_group(db_session, club, name="Group 2")
    make_group(db_session, club2, name="Group 3")
    response = client.get("/groups/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 3

def test_list_all_groups_empty(client):
    response = client.get("/groups/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data == []

##-- Update a group by ID
def test_update_group(client, db_session):
    club = make_club(db_session)
    group = make_group(db_session, club, name="Group A")
    response = client.patch(f"/groups/{group.id}", json={"name": "Updated Group A"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Updated Group A"

def test_update_group_duplicate_name(client, db_session):
    club = make_club(db_session)
    make_group(db_session, club, name="Group A")
    group2 = make_group(db_session, club, name="Group B")
    response = client.patch(f"/groups/{group2.id}", json={"name": "Group A"})
    assert response.status_code == status.HTTP_409_CONFLICT

def test_update_group_not_found(client):
    response = client.patch("/groups/9999", json={"name": "Updated Group"})
    assert response.status_code == status.HTTP_404_NOT_FOUND

##-- Delete a group by ID
def test_delete_group(client, db_session):
    club = make_club(db_session)
    group = make_group(db_session, club, name="Group B")
    response = client.delete(f"/groups/{group.id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

def test_delete_group_has_members(client, db_session):
    club = make_club(db_session)
    group = make_group(db_session, club, name="Group C")
    # Assuming you have a function to add a gymnast to the group
    from test.conftest import make_gymnast
    make_gymnast(db_session, club=club, group=group, first_name="John", last_name="Doe")

    response = client.delete(f"/groups/{group.id}")
    assert response.status_code == status.HTTP_409_CONFLICT

def test_delete_group_not_found(client):
    response = client.delete("/groups/9999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
