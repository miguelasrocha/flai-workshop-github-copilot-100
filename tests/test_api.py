"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        name: {**activity, "participants": activity["participants"].copy()}
        for name, activity in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, activity in original_activities.items():
        activities[name]["participants"] = activity["participants"].copy()


def test_root_redirect(client):
    """Test that root path redirects to static index.html"""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities(client):
    """Test retrieving all activities"""
    response = client.get("/activities")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, dict)
    assert "Chess Club" in data
    assert "Programming Class" in data
    
    # Verify structure of an activity
    chess_club = data["Chess Club"]
    assert "description" in chess_club
    assert "schedule" in chess_club
    assert "max_participants" in chess_club
    assert "participants" in chess_club
    assert isinstance(chess_club["participants"], list)


def test_signup_success(client):
    """Test successful signup for an activity"""
    response = client.post(
        "/activities/Chess Club/signup?email=newstudent@mergington.edu"
    )
    assert response.status_code == 200
    
    data = response.json()
    assert "message" in data
    assert "newstudent@mergington.edu" in data["message"]
    assert "Chess Club" in data["message"]
    
    # Verify the participant was added
    activities_response = client.get("/activities")
    activities_data = activities_response.json()
    assert "newstudent@mergington.edu" in activities_data["Chess Club"]["participants"]


def test_signup_duplicate(client):
    """Test that signing up twice for the same activity fails"""
    email = "duplicate@mergington.edu"
    activity = "Chess Club"
    
    # First signup should succeed
    response1 = client.post(f"/activities/{activity}/signup?email={email}")
    assert response1.status_code == 200
    
    # Second signup should fail
    response2 = client.post(f"/activities/{activity}/signup?email={email}")
    assert response2.status_code == 400
    assert "already signed up" in response2.json()["detail"].lower()


def test_signup_nonexistent_activity(client):
    """Test signup for non-existent activity"""
    response = client.post(
        "/activities/Nonexistent Club/signup?email=test@mergington.edu"
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_unregister_success(client):
    """Test successful unregistration from an activity"""
    # First, sign up a student
    email = "test@mergington.edu"
    activity = "Chess Club"
    client.post(f"/activities/{activity}/signup?email={email}")
    
    # Then unregister
    response = client.delete(f"/activities/{activity}/unregister?email={email}")
    assert response.status_code == 200
    
    data = response.json()
    assert "message" in data
    assert email in data["message"]
    assert activity in data["message"]
    
    # Verify the participant was removed
    activities_response = client.get("/activities")
    activities_data = activities_response.json()
    assert email not in activities_data[activity]["participants"]


def test_unregister_not_registered(client):
    """Test unregistering a student who is not registered"""
    response = client.delete(
        "/activities/Chess Club/unregister?email=notregistered@mergington.edu"
    )
    assert response.status_code == 400
    assert "not registered" in response.json()["detail"].lower()


def test_unregister_nonexistent_activity(client):
    """Test unregister from non-existent activity"""
    response = client.delete(
        "/activities/Nonexistent Club/unregister?email=test@mergington.edu"
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_activity_capacity(client):
    """Test that activity tracks participants correctly"""
    response = client.get("/activities")
    data = response.json()
    
    for activity_name, activity_details in data.items():
        assert len(activity_details["participants"]) <= activity_details["max_participants"]


def test_multiple_signups_different_activities(client):
    """Test that a student can sign up for multiple activities"""
    email = "multitask@mergington.edu"
    
    # Sign up for multiple activities
    response1 = client.post(f"/activities/Chess Club/signup?email={email}")
    response2 = client.post(f"/activities/Programming Class/signup?email={email}")
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    # Verify enrollment in both
    activities_response = client.get("/activities")
    activities_data = activities_response.json()
    assert email in activities_data["Chess Club"]["participants"]
    assert email in activities_data["Programming Class"]["participants"]


def test_url_encoding_in_activity_names(client):
    """Test that activity names with spaces are properly URL encoded"""
    response = client.post(
        "/activities/Chess%20Club/signup?email=urltest@mergington.edu"
    )
    assert response.status_code == 200


def test_url_encoding_in_emails(client):
    """Test that emails are properly URL encoded"""
    from urllib.parse import quote
    
    email = "test+tag@mergington.edu"
    encoded_email = quote(email, safe='')
    response = client.post(
        f"/activities/Chess Club/signup?email={encoded_email}"
    )
    assert response.status_code == 200
    
    # Verify the email was added correctly
    activities_response = client.get("/activities")
    activities_data = activities_response.json()
    assert email in activities_data["Chess Club"]["participants"]
