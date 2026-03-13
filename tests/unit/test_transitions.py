"""Tests for transition guard functions."""

from src.orchestration.transitions import (
    GUARD_REGISTRY,
    always,
    review_approved,
    review_revision_needed,
    tests_failed as guard_tests_failed,
    tests_passed as guard_tests_passed,
)


class TestAlways:
    def test_returns_true_for_any_input(self) -> None:
        assert always("") is True
        assert always("anything") is True
        assert always("APPROVED REVISE TESTS FAILED") is True


class TestTestsPassed:
    def test_matches_all_tests_passed(self) -> None:
        assert guard_tests_passed("ALL TESTS PASSED") is True

    def test_case_insensitive(self) -> None:
        assert guard_tests_passed("all tests passed") is True
        assert guard_tests_passed("All Tests Passed") is True

    def test_embedded_in_text(self) -> None:
        assert guard_tests_passed("Result: ALL TESTS PASSED. Moving on.") is True

    def test_no_match(self) -> None:
        assert guard_tests_passed("Some tests passed") is False
        assert guard_tests_passed("TESTS FAILED") is False


class TestTestsFailed:
    def test_matches_tests_failed(self) -> None:
        assert guard_tests_failed("TESTS FAILED") is True

    def test_matches_test_failed_singular(self) -> None:
        assert guard_tests_failed("TEST FAILED") is True

    def test_case_insensitive(self) -> None:
        assert guard_tests_failed("tests failed") is True

    def test_no_match(self) -> None:
        assert guard_tests_failed("ALL TESTS PASSED") is False
        assert guard_tests_failed("no failures") is False


class TestReviewApproved:
    def test_matches_approved(self) -> None:
        assert review_approved("APPROVED") is True

    def test_embedded_in_text(self) -> None:
        assert review_approved("Code looks great. APPROVED.") is True

    def test_rejects_when_revise_also_present(self) -> None:
        assert review_approved("APPROVED but maybe REVISE later") is False

    def test_no_match(self) -> None:
        assert review_approved("Needs more work") is False


class TestReviewRevisionNeeded:
    def test_matches_revise(self) -> None:
        assert review_revision_needed("REVISE") is True

    def test_embedded_in_text(self) -> None:
        assert review_revision_needed("Please REVISE the error handling") is True

    def test_case_insensitive(self) -> None:
        assert review_revision_needed("revise") is True

    def test_no_match(self) -> None:
        assert review_revision_needed("APPROVED") is False


class TestGuardRegistry:
    def test_all_guards_registered(self) -> None:
        expected = {"always", "tests_passed", "tests_failed", "review_approved", "review_revision_needed"}
        assert set(GUARD_REGISTRY.keys()) == expected

    def test_registry_values_are_callable(self) -> None:
        for name, func in GUARD_REGISTRY.items():
            assert callable(func), f"{name} is not callable"
