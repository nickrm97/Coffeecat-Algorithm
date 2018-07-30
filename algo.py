from .models import Event, Profile
from .notifications import send_twist_notifications, coffee_success_post
from django.contrib.auth.models import User
from django.utils import timezone

from datetime import datetime
import random, operator

# The inner arrays must be displayed in alphabetical order to work, A-Z
unfavourable_matchups = sorted([
    ['hugh', 'nathan'], ['dre', 'rhys'], ['bohdan', 'rhys'], ['dre', 'nathan'], ['dre', 'hugh'],
    ['hugh', 'noam'], ['carley', 'shannon'], ['dre', 'matt'], ['dre', 'nick'],
])


class Matchup:
    """
    Matchup object, used to represent a potential matchup between two people
    """
    ranking = 0
    def __init__(self, person1, person2):
        self.persons = [person1, person2]
        self.ranking = calc_rank(person1, person2)

    def __str__(self):
        return (str(self.persons[0]) + str(self.persons[1]))


def count_matches(person1, person2):
    """
    Counts the previous meetings between two people
    """
    events = Event.objects.all()
    count = 0
    for event in events:
        if person1 in event.profiles.all() and person2 in event.profiles.all():
            count += 1
    return count


def recent_match(person1, person2):
    """
    Returns how long since the pair have had coffee (in months)
    """
    events = Event.objects.all()
    catchups = []
    for event in events:
        if person1 in event.profiles.all() and person2 in event.profiles.all():
            catchups.append(event)

    # Sorting the recent catchups based on date/time
    catchups.sort(key=lambda r: r.event.created_at)

    # If they have previously caught up, return the time since they last did
    if(len(catchups)):
        most_recent = catchups.pop()

        d1 = most_recent.date
        d2 = timezone.now()

        # Calculate and return the months since they last caught up
        difference = (d2 - d1)
        return(difference.days // 30)

    # Otherwise, lets put their rank up very high, as they haven't met before.
    else:
        return 12


def calc_rank(person1, person2):
    """
    Calculates the rank of a matchup. A matchup rank represents the importance
    of the pair getting coffee; a higher rank means greater priortiy.

    Rank is influenced by how many times a pair have caught up before, when the pair
    most recently caught up, and if it's an unfavourable matchup (eg. Hugh and Nathan)
    """
    rank = 0
    rank -= count_matches(person1, person2) * 0.75
    rank += recent_match(person1, person2)
    # If this matchup is considered 'unfavouable', decrease its rank
    if sorted([person1.user.first_name, person2.user.first_name]) in unfavourable_matchups:
        rank -= 3
    return rank


def does_matchup_exist(person1, person2, potential_matches):
    """
    Checks if a potential matchup already exists between two people
    """
    for match in potential_matches:
        if person1 in match.persons and person2 in match.persons:
            return True
    return False


def find_infrequent_rand(taken):
    """
    Used when matching up the odd person, looks at the bottom 25 percent of
    'coffee getters' in terms of frequency. Randomly assigns one of them a
    second coffee!
    """
    # Sorting by how many times the person has had coffee (with anyone)
    taken.sort(key=lambda r: Event.objects.filter(profiles=r).count())

    # Finding the bottom 25%, picking one of them at random
    rand_num = random.randint(0, len(taken) // 4)

    # print("(" + str(taken[rand_num]) + " x2)")
    return taken[rand_num]


def create_matchups():
    """
    Creates the coffee matchups for a given month. This is the main function.
    """
    potential_matches = []
    confirmed_matchups = []
    taken = []
    profiles = Profile.objects.all()

    for profile in profiles:
        for match in profiles:
            # Create a potential matchup, providing the matchup doesn't exist and we aren't matching the person with themself
            if not does_matchup_exist(profile, match, potential_matches) and profile is not match:
                x = Matchup(profile, match)
                potential_matches.append(x)

    # Sort the potential matches based on ranking, with highest being matched first
    potential_matches.sort(key=lambda r: r.ranking, reverse=True)
    for matchup in potential_matches:
        # If the matchup safely exists with two people, and they're not yet assigned, match them up
        if len(matchup.persons) is 2:
            if matchup.persons[0] not in taken and matchup.persons[1] not in taken:
                taken.append(matchup.persons[0])
                taken.append(matchup.persons[1])
                confirmed_matchups.append(matchup)

    # If we have an odd amount of people, somebody gets to have coffee twice :D
    if len(profiles) % 2 is not 0:
        last_person = [unmatched for unmatched in profiles if unmatched not in taken].pop()
        # Matching this person with somebody who hasn't had coffee much (ie. new staff)
        last_matchup = Matchup(last_person, find_infrequent_rand(taken))
        taken.append(last_person)
        confirmed_matchups.append(last_matchup)
    # Returns an array of matchup objects, to be turned into events
    return confirmed_matchups


def create_events():
    """
    A basic function to read the matchups and create the events
    """
    matchups = create_matchups()

    for matchup in matchups:
        # Create the event
        event = Event.objects.create(date=timezone.now())
        # Add the two matched people to the event
        for person in matchup.persons:
            event.profiles.add(person)
    # Send the reports in twist
    send_twist_notifications(matchups)
