from enum import StrEnum


class NotificationStatus(StrEnum):
    UNREAD = "unread"
    READ = "read"


class NotificationType(StrEnum):
    TASK_ASSIGNED = "task_assigned"
    TASK_COMMENTED = "task_commented"
