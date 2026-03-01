"""
Unit tests for appointment state machine (_check_transition + _VALID_TRANSITIONS).
Pure Python, no DB required — imports the private names directly for exhaustive testing.
"""

# Third-party
import pytest

# Internal
from app.services.appointment_service import _check_transition, _VALID_TRANSITIONS
from app.core.exceptions import ValidationException
from app.constants.messages import INVALID_STATUS_TRANSITION


class TestValidTransitions:
    """All transitions listed in _VALID_TRANSITIONS should succeed."""

    def test_pending_to_waiting(self):
        _check_transition("pending", "waiting", INVALID_STATUS_TRANSITION)  # no raise

    def test_pending_to_cancelled(self):
        _check_transition("pending", "cancelled", INVALID_STATUS_TRANSITION)

    def test_waiting_to_completed(self):
        _check_transition("waiting", "completed", INVALID_STATUS_TRANSITION)

    def test_waiting_to_cancelled(self):
        _check_transition("waiting", "cancelled", INVALID_STATUS_TRANSITION)

    def test_waiting_to_no_show(self):
        _check_transition("waiting", "no_show", INVALID_STATUS_TRANSITION)

    # Note: reschedule (pending/waiting → pending) is handled directly
    # by the appointment service, NOT via _check_transition, so it is
    # not listed in _VALID_TRANSITIONS and should not be tested here.


class TestInvalidTransitions:
    """All transitions from terminal states must raise ValidationException."""

    def test_completed_to_any_raises(self):
        for target in ("pending", "waiting", "cancelled", "no_show"):
            with pytest.raises(ValidationException) as exc:
                _check_transition("completed", target, INVALID_STATUS_TRANSITION)
            assert exc.value.code == INVALID_STATUS_TRANSITION

    def test_cancelled_to_any_raises(self):
        for target in ("pending", "waiting", "completed", "no_show"):
            with pytest.raises(ValidationException) as exc:
                _check_transition("cancelled", target, INVALID_STATUS_TRANSITION)
            assert exc.value.code == INVALID_STATUS_TRANSITION

    def test_no_show_to_any_raises(self):
        for target in ("pending", "waiting", "completed", "cancelled"):
            with pytest.raises(ValidationException) as exc:
                _check_transition("no_show", target, INVALID_STATUS_TRANSITION)
            assert exc.value.code == INVALID_STATUS_TRANSITION

    def test_pending_to_completed_raises(self):
        """pending → completed must go through waiting first."""
        with pytest.raises(ValidationException):
            _check_transition("pending", "completed", INVALID_STATUS_TRANSITION)

    def test_pending_to_no_show_raises(self):
        with pytest.raises(ValidationException):
            _check_transition("pending", "no_show", INVALID_STATUS_TRANSITION)

    def test_waiting_to_waiting_raises(self):
        """Re-confirming a waiting appointment is invalid."""
        with pytest.raises(ValidationException):
            _check_transition("waiting", "waiting", INVALID_STATUS_TRANSITION)


class TestTransitionMapCoverage:
    """Meta tests: verify the transition map covers all known statuses."""

    KNOWN_STATUSES = {"pending", "waiting", "completed", "cancelled", "no_show"}

    def test_all_statuses_defined_in_map(self):
        defined = set(_VALID_TRANSITIONS.keys())
        assert defined == self.KNOWN_STATUSES

    def test_terminal_states_have_empty_transitions(self):
        for terminal in ("completed", "cancelled", "no_show"):
            assert _VALID_TRANSITIONS[terminal] == set(), (
                f"Terminal state '{terminal}' should have no allowed transitions"
            )
