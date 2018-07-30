from django.utils import timezone
from .models import Location, Event

import requests
import calendar

TWIST_WEBHOOK = "" # censored
COFFEE_LINK = ""

def send_twist_notifications(matchups):
    """
    Prepares and sends the twist message
    """
    date = timezone.now().strftime('%B %Y').upper()
    message = ""
    message += prev_month_report_twist()
    message += month_catchup_report(matchups)
    message += suggest_location()
    message += "To record your coffee catchup, click here: " + COFFEE_LINK
    # print(message)
    requests.post(TWIST_WEBHOOK, json={ 'content': message})


def prev_month_report_twist():
    """
    Produces a report of the previous month's coffee catchups
    """
    # Look for the month before the current month
    now = timezone.now()
    prev_month = now.month-1 if now.month > 1 else 12
    prev_month_year = now.year if now.month > prev_month else now.year - 1

    # Formatting month and year for previous month
    formatted_month = calendar.month_name[prev_month].upper()
    message = "\n🐱  **COFFEE CATCHUP REPORT for " + formatted_month + " " + str(prev_month_year) + "** 🐱  \n"

    # Filter for all events in the previous month
    prev_month_events = Event.objects.filter(date__month=prev_month, date__year=prev_month_year)

    for event in prev_month_events:
        profile1 = event.profiles.all()[0].user.first_name
        profile2 = event.profiles.all()[1].user.first_name
        # For the events, if a submission was given, the event was complete. Otherwise, it was not
        if event.submission_set.count():
            message +=("✅ " + str(profile1).title() + " and " + str(profile2).title() + "\n")
        else:
            message +=("❌ " + str(profile1).title() + " and " + str(profile2).title() + "\n")
    # Handles if no events were found for the previous month (ie. count = 0)
    if not prev_month_events.count():
        message += "Looks like there were no coffee catchups last month...\n"
    return message


def month_catchup_report(matchups):
    """
    Produces a list of all of the current month's coffee catchups
    """
    # Formatting the date nicely
    date = timezone.now().strftime('%B %Y').upper()
    message = "\n☕ **COFFEE CATCHUPS for " + date + "** ☕ \n"

    for matchup in matchups:
        person1 = matchup.persons[0].user.first_name
        person2 = matchup.persons[1].user.first_name
        message+= "😺  " + str(person1).title() + " and " + str(person2).title() + "\n"
    return message

def suggest_location():
    """
    Suggests a random location to visit this month
    """
    # Get a random location. An incredible algorithm, I know...
    location = Location.objects.order_by('?').first()
    message = ""
    if location:
        message += "\n🌲🌲 Coffee Cat suggests: Visit " + str(location) + "🌲🌲\n"
    return message

def coffee_success_post(event):
    """
    Posts a message after a successful event. To be called when a submission is made.
    """
    message = "😺 **COFFEE CATCHUP ALERT** 😺\n"
    profile1 = event.profiles.all()[0].user.first_name
    profile2 = event.profiles.all()[1].user.first_name

    message += "Success! **" + profile1 + "** and **" + profile2 + "** had coffee!\n"

    if event.venue is not None:
        message += " They had coffee at **" + str(event.venue.title) + "**!\n"

    # Including the photo URl so it loads within Twist
    message += "http://media.gettyimages.com/photos/two-people-in-cafe-enjoying-the-meeting-picture-id178025732?s=170667a&w=1007"
    requests.post(TWIST_WEBHOOK, json={ 'content': message })
