import sys
import os
import tempfile

# Add current directory to path
sys.path.append(os.getcwd())

from parser import parse_voters
from database import init_db, get_connection

def test_parser():
    sample_lines = [
        "ABC1234560",
        "Name : John Doe",
        "Father's Name : Richard Doe",
        "House No : 123/A",
        "Age : 45 Gender : Male",
        "Photo is Available",
        "XYZ987654O",
        "Name : Jane Smith",
        "Husband's Name : John Smith",
        "House Number : 456-B",
        "Age : 42 Gender : Female",
        "Photo is Available"
    ]
    
    voters = parse_voters(sample_lines)
    print(f"Parsed {len(voters)} voters")
    for v in voters:
        print(v)
    
    assert len(voters) == 2
    assert voters[0]["voter_id"] == "ABC1234560"
    assert voters[0]["name"] == "John Doe"
    assert voters[1]["voter_id"] == "XYZ9876540" # Should replace O with 0
    assert voters[1]["gender"] == "Female"

def test_multiline_parser():
    sample_lines = [
        "DET1234567",
        "Name",
        "Robert Brown",
        "Father's Name",
        "William Brown",
        "House No : 789",
        "Age : 30 Gender : Male"
    ]
    voters = parse_voters(sample_lines)
    print(f"Parsed {len(voters)} voters (multiline)")
    assert len(voters) == 1
    assert voters[0]["name"] == "Robert Brown"
    assert voters[0]["fathers_name"] == "William Brown"
    print("Multiline parser test passed")

def test_database():
    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ["DATABASE_URL"] = os.path.join(temp_dir, "test_voters.db")
        init_db()
        conn = get_connection()
        cursor = conn.cursor()

        sample_voter = {
            "voter_id": "TEST123456",
            "name": "Test User",
            "fathers_name": "Test Father",
            "house_number": "101",
            "age": 30,
            "gender": "Male",
            "photo_status": "Available"
        }

        cursor.execute("""
            INSERT OR REPLACE INTO voters
            (voter_id, name, fathers_name, house_number, age, gender, photo_status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            sample_voter["voter_id"],
            sample_voter["name"],
            sample_voter["fathers_name"],
            sample_voter["house_number"],
            sample_voter["age"],
            sample_voter["gender"],
            sample_voter["photo_status"]
        ))

        conn.commit()

        cursor.execute("SELECT name FROM voters WHERE voter_id='TEST123456'")
        row = cursor.fetchone()
        assert row[0] == "Test User"
        print("Database test passed")
        conn.close()

if __name__ == "__main__":
    try:
        test_parser()
        test_multiline_parser()
        test_database()
        print("All tests passed successfully!")
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)
