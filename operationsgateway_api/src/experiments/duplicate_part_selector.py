from enum import IntEnum
import logging

from operationsgateway_api.src.exceptions import ExperimentDetailsError

log = logging.getLogger()


class PartStatus(IntEnum):
    """
    Enum to represent the preference of which part status should be selected when a
    duplicate parts exist
    """

    DELIVERED = 1
    PUBLISHED = 2
    REPUBLISHED = 3
    CHANGED = 4

    # Where a part has this status, we should ignore/remove it from being selected
    PUBLISHREQUESTED = 5
    REPUBLISHREQUESTED = 6
    TENTATIVE = 7
    POSTPONED = 8
    CANCELLED = 9


class DuplicatePartSelector:
    """
    A class that selects which experiment part to choose (from a number of parts that
    have the same part number) based on the part's status

    These checks are performed based on the advice of ISIS Business Applications (who
    maintain the Scheduler) who gave us a list of possible part statuses and advised us
    that delivered, published, republished statuses are preferred over any others. I've
    noticed that the 'Changed' status is present in the test data (for Gemini) on the
    Scheduler, so I've not ignored that status
    """

    def __init__(self, part_number: int, parts: list) -> None:
        self.part_number = part_number
        self.parts = parts

    def select_part(self):
        """
        Select which experiment part should be used based on a number of checks.
        """

        self._remove_parts()
        if len(self.parts) == 1:
            return self.parts[0]
        elif len(self.parts) == 0:
            raise ExperimentDetailsError(
                "No experiment parts to choose, likely that duplicate parts are all"
                " cancelled",
            )

        self._order_parts_by_status()
        log.debug(
            "Number of duplicate parts for part number '%s' after checks: %d",
            self.part_number,
            len(self.parts),
        )
        return self.parts[0]

    def _remove_parts(self) -> None:
        for part in self.parts:
            if self._get_status_precedence(part) > 4:
                self.parts.remove(part)

    def _order_parts_by_status(self) -> None:
        self.parts.sort(key=self._get_status_precedence)

    def _get_status_precedence(self, part) -> PartStatus:
        """
        Get the precedence of the part status. This function is given to `sort()` as a
        key to sort the list
        """
        return getattr(PartStatus, part.status.upper())
