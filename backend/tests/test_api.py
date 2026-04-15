import pytest
import sys
import os
from unittest.mock import MagicMock, patch

# Dodaj parent directory do sys.path aby zaimportować app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def client():
    """Fixture tworzący test client Flask"""
    from app import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_hello_endpoint(client):
    """Test endpointa /api/hello - sprawdza czy API odpowiada poprawnie"""
    response = client.get('/api/hello')
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'Hello World from Backend!'
    assert data['status'] == 'success'


def test_add_user_validation(client):
    """Test walidacji - dodawanie usera bez wymaganych pól powinno zwrócić błąd 400"""
    # Próba dodania usera bez surname
    response = client.post('/api/db/users', json={'name': 'Jan'})
    
    assert response.status_code == 400
    data = response.get_json()
    assert data['status'] == 'error'
    assert 'required' in data['error'].lower()


@patch('app.get_db_connection')
def test_get_users_with_mock_db(mock_db, client):
    """Test pobierania użytkowników z zamockowaną bazą danych"""
    # Przygotowanie mocka bazy danych
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    # Symulacja danych z bazy
    mock_cursor.fetchall.return_value = [
        (1, 'Jan', 'Kowalski', '2024-01-01 12:00:00'),
        (2, 'Anna', 'Nowak', '2024-01-02 13:00:00')
    ]
    
    response = client.get('/api/db/users')
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert len(data['users']) == 2
    assert data['users'][0]['name'] == 'Jan'
    assert data['users'][1]['name'] == 'Anna'
    