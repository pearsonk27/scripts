"""Get the first Saturday of every quarter"""
import datetime


def get_first_saturday_of_quarter(year, quarter):
    """Returns the first Saturday of the given quarter."""

    # Get the first day of the quarter.
    first_day_of_quarter = datetime.date(year, (quarter - 1) * 3 + 1, 1)

    # Get the weekday of the first day of the quarter.
    weekday_of_first_day = first_day_of_quarter.weekday()

    # If the first day of the quarter is not a Saturday, add days until we reach a Saturday.
    days_to_add = 6 - weekday_of_first_day
    first_saturday_of_quarter = first_day_of_quarter + datetime.timedelta(
        days=days_to_add
    )

    return first_saturday_of_quarter

def get_all_wanted_first_saturdays_of_quarters(beggining_year, beggining_quarter, quarters_wanted):
    """Get all wanted first Saturdays of quarters"""
    while quarters_wanted > 0:
        first_saturday_of_quarter = get_first_saturday_of_quarter(beggining_year, beggining_quarter)
        print(first_saturday_of_quarter)
        quarters_wanted -= 1
        if beggining_quarter in [1, 2, 3]:
            beggining_quarter += 1
        else:
            beggining_quarter = 1
            beggining_year += 1

get_all_wanted_first_saturdays_of_quarters(2024, 3, 16)
