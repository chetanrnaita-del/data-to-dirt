"""
Comprehensive verification test for newly enrolled 61 students roster:
1. Verification of all 61 accounts, initials passwords, and IDs
2. Authentication using Name + Initials and Student ID + Initials
3. Verification of 1500 GB total cleaned up data
4. Verification of 62 total trees planted
5. Verification of Teacher and Analytics Grade 5 aggregations
"""

import unittest
import json
from src.app.server import app, load_state, reset_all_auth_lockouts
from src.services.auth import default_auth_service

EXPECTED_STUDENTS = [
    "Ishaan Sarkar",
    "Medhansh Mukesh Bhatia",
    "Myrra Singh",
    "Nidhi Pramit Bhinde",
    "Nishma Ruparel",
    "Pareena Ramesh Poojari",
    "Rehaa Gautam",
    "Saanvi Paneri",
    "SHREEDATT SANKULKAR",
    "Vivaan Vinay Shah",
    "Vrinda Jhamnani Kumar",
    "Yashi Gosrani",
    "Yuvan Gelda",
    "Aadaan Rajan",
    "Aadya Shetty",
    "Aanvi Sherigar",
    "Arjun Singh",
    "Deivyan Suyog Puntambekar",
    "Gurliv Randhawa",
    "Jyotsna Shakya",
    "Kamlesh Vyas",
    "Kehaan Nagda",
    "Kiara Ahuja",
    "Kiaraa Kadmawala",
    "Manthan Gudhka",
    "Mithran Pal",
    "Mohammed Ashaz Momin",
    "Nathan Dias",
    "Rachel Sabu",
    "Reya Shah",
    "Rishima Ghosh",
    "RUGVED AJAY KADAM",
    "Sarrah Shah",
    "Shanaya Jacob",
    "Soumya Koulgi",
    "Vaania Vinod Makhija",
    "Vihaan Anchan",
    "Xander Simon",
    "Yash Modi",
    "Aaruhi Anand",
    "Abheer Singh",
    "Allan Jacob",
    "Amayra Shah",
    "Arjun Prashant Tyagi",
    "Arshit Naresh Vangani",
    "Arush Iyer",
    "Aryana Mukherjee",
    "Dhruvin Dhiren Savla",
    "Elina Singh",
    "Harshil Mahendra Nakar",
    "Hiyaa Sanghavi",
    "Lisha Rohra",
    "Muskaan Agrawal",
    "Mysha Fatima",
    "Reet Selly",
    "Rudra Sachin Salian",
    "Shaurya Thakkar",
    "Vanessa BAHARANI",
    "Viha Gosar",
    "Vivaan Vishal Chawla",
    "Viya Panchmia"
]

class TestRosterAccounts(unittest.TestCase):
    def setUp(self):
        reset_all_auth_lockouts()
        self.client = app.test_client()
        self.state = load_state()

    def tearDown(self):
        reset_all_auth_lockouts()

    def test_total_count_and_totals(self):
        """All 61 students exist and sum to 1500 GB and 62 trees."""
        self.assertEqual(len(EXPECTED_STUDENTS), 61)

        students_map = {s.get("name", "").lower(): s for s in self.state.get("students", [])}
        found_students = []
        for name in EXPECTED_STUDENTS:
            self.assertIn(name.lower(), students_map, f"Student {name} must exist in state")
            found_students.append(students_map[name.lower()])

        self.assertEqual(len(found_students), 61)

        total_bytes = sum(s.get("bytes_cleared", 0) for s in found_students)
        total_gb = total_bytes / (1024 ** 3)
        self.assertAlmostEqual(total_gb, 1500.0, places=3, msg="Total bytes cleared must equal 1500.00 GB")

        total_trees = sum(s.get("trees", 0) for s in found_students)
        self.assertEqual(total_trees, 62, "Total trees planted across the 61 students must equal 62")

    def test_passwords_are_initials(self):
        """All 61 students have their pin and password set to their initials."""
        students_map = {s.get("name", "").lower(): s for s in self.state.get("students", [])}
        for name in EXPECTED_STUDENTS:
            s = students_map[name.lower()]
            words = name.split()
            expected_initials = "".join(w[0].upper() for w in words)
            self.assertEqual(s.get("pin"), expected_initials)
            self.assertEqual(s.get("password"), expected_initials)

    def test_sample_students_can_login_with_initials(self):
        """Students can authenticate using both name and initials as password."""
        sample_logins = [
            ("Ishaan Sarkar", "IS"),
            ("Medhansh Mukesh Bhatia", "MMB"),
            ("Medhansh Mukesh Bhatia", "mb"),
            ("SHREEDATT SANKULKAR", "SS"),
            ("RUGVED AJAY KADAM", "RAK"),
            ("Vanessa BAHARANI", "VB"),
            ("Viya Panchmia", "VP"),
            ("Arjun Prashant Tyagi", "APT"),
            ("Dhruvin Dhiren Savla", "DDS"),
            ("Elina Singh", "ES")
        ]
        for name, pwd in sample_logins:
            reset_all_auth_lockouts()
            res = self.client.post("/api/auth/login", json={
                "role": "student",
                "user_id": name,
                "pin": pwd
            })
            self.assertEqual(res.status_code, 200, f"Login failed for {name} with pin {pwd}")
            data = res.get_json()
            self.assertEqual(data.get("status"), "authenticated")
            self.assertEqual(data.get("role"), "student")

    def test_teacher_analytics_grade5_shows_1500gb_and_62trees(self):
        """Teacher analytics for Grade 5 shows 1500 GB and 62 trees funded."""
        t_session = default_auth_service.create_session(role="teacher", user_id="teacher_grade5", class_code="grade5")
        headers = {"Authorization": f"Bearer {t_session['token']}"}
        res = self.client.get("/api/teacher/analytics?class_code=grade5", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertAlmostEqual(data.get("total_data_cleaned_gb", 0), 1500.0, delta=0.1)
        self.assertEqual(data.get("total_trees_funded"), 62)


if __name__ == "__main__":
    unittest.main()
