"""
Unit tests for RBAC — permission checks, owner vs staff permission sets.
Pure Python, no DB required.
"""

# Internal
from app.rbac.permissions import (
    ANALYTICS_READ,
    APPOINTMENT_CANCEL,
    APPOINTMENT_READ,
    APPOINTMENT_WRITE,
    CONSULTATION_SUBMIT,
    CONSULTATION_WRITE,
    OWNER_ONLY_PERMISSIONS,
    PATIENT_READ,
    PATIENT_WRITE,
    RECOMMENDED_ASSISTANT_PERMISSIONS,
    RECOMMENDED_RECEPTIONIST_PERMISSIONS,
)


class TestOwnerOnlyPermissions:
    def test_consultation_write_is_owner_only(self):
        assert CONSULTATION_WRITE in OWNER_ONLY_PERMISSIONS

    def test_consultation_submit_is_owner_only(self):
        assert CONSULTATION_SUBMIT in OWNER_ONLY_PERMISSIONS

    def test_analytics_read_is_owner_only(self):
        assert ANALYTICS_READ in OWNER_ONLY_PERMISSIONS

    def test_patient_read_is_not_owner_only(self):
        assert PATIENT_READ not in OWNER_ONLY_PERMISSIONS

    def test_appointment_write_is_not_owner_only(self):
        assert APPOINTMENT_WRITE not in OWNER_ONLY_PERMISSIONS


class TestRecommendedPermissionSets:
    def test_assistant_has_appointment_permissions(self):
        assert APPOINTMENT_READ in RECOMMENDED_ASSISTANT_PERMISSIONS
        assert APPOINTMENT_WRITE in RECOMMENDED_ASSISTANT_PERMISSIONS

    def test_assistant_has_patient_read(self):
        assert PATIENT_READ in RECOMMENDED_ASSISTANT_PERMISSIONS

    def test_receptionist_has_appointment_read(self):
        assert APPOINTMENT_READ in RECOMMENDED_RECEPTIONIST_PERMISSIONS

    def test_receptionist_has_patient_read(self):
        assert PATIENT_READ in RECOMMENDED_RECEPTIONIST_PERMISSIONS

    def test_no_recommended_set_contains_owner_only_perms(self):
        """Assistant and receptionist should never receive owner-only perms."""
        all_staff_perms = (
            set(RECOMMENDED_ASSISTANT_PERMISSIONS) | set(RECOMMENDED_RECEPTIONIST_PERMISSIONS)
        )
        overlap = all_staff_perms & set(OWNER_ONLY_PERMISSIONS)
        assert overlap == set(), f"Owner-only perms found in staff sets: {overlap}"
