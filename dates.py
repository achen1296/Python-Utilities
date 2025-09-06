from datetime import date, datetime, timedelta


def last_day_of_week(w: int, d: date | datetime | None = None):
    if not (0 <= w < 7):
        raise ValueError
    if not d:
        d = date.today()
    return d - timedelta(days=(d.weekday() - w) % 7)


def next_day_of_week(w: int, d: date | datetime | None = None):
    if not (0 <= w < 7):
        raise ValueError
    if not d:
        d = date.today()
    return d + timedelta(days=(w - d.weekday()) % 7)
