import itertools
import random
import re
import time
import traceback
from collections import Counter, defaultdict

from secrets import EMAIL, PASS
from selenium import webdriver

URL = r'http://fltsnk.football.cbssports.com/office-pool/standings/live'
MESSAGE_URL = r'http://fltsnk.football.cbssports.com/messages/feed/post'
NOT_SUBMITED = 'This player did not submit picks for this week'


def init_selenium(implicitly_wait=20, page_load_timeout=10):
    """
    Creates a selenium driver
    """
    try:
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--start-maximized")
        driver = webdriver.Remote(
            command_executor=r"http://selenium-server:4444/wd/hub",
            desired_capabilities=chrome_options.to_capabilities()
        )
        driver.maximize_window()
        driver.set_window_size(1920, 1080)
        # Move the window to position x/y
        driver.set_window_position(0, 0)
        driver.implicitly_wait(implicitly_wait)
        return driver
    except:
        raise Exception("Error starting selenium: traceback: {0}".format(
            traceback.format_exc())
        )


def main():
    driver = init_selenium()

    driver.get(URL)
    time.sleep(random.uniform(3, 4))

    # Login
    user_input = driver.find_element_by_id('userid')
    pass_input = driver.find_element_by_id('password')
    user_input.send_keys(EMAIL)
    pass_input.send_keys(PASS)
    driver.find_element_by_class_name('formButton').click()

    # Parse week
    driver.get(URL)
    time.sleep(random.uniform(3, 4))
    week = driver.find_element_by_class_name('selected_arrow').text
    player_row_body = driver.find_element_by_id('nflplayerRows')
    player_trs = player_row_body.find_elements_by_tag_name('tr')

    points_regex = re.compile('(.*)\n\((.*)\)')

    # Parse picks
    remaining_bets = defaultdict(list)
    all_week_pts = Counter()
    all_ytd_pts = Counter()
    all_tie_breakers = {}
    # remaining teams is the list in order of the games remaining,
    # each team will be the top players picks
    remaining_teams = []
    fill_remaining_teams = True
    for player_tr in player_trs:
        player_tds = player_tr.find_elements_by_tag_name('td')
        if player_tds[1].text == NOT_SUBMITED:
            continue
        player_name = player_tds[0].text
        tie_breaker = int(player_tds[-3].text)
        week_pts = int(player_tds[-2].text)
        ytd_pts = int(player_tds[-1].text)

        for player_td in player_tds[1:-3]:
            played = True
            bet = re.search(points_regex, player_td.text)
            team = bet.group(1)
            points = int(bet.group(2))

            # class can be 'incorrect inprogress'
            correct = player_td.get_attribute("class").lower()
            correct_split = correct.split(' ')
            correct = correct_split[0]
            in_progress = ''
            if len(correct_split) == 2:
                in_progress = correct_split[1]

            if in_progress == 'inprogress':
                played = False
                # if game is in progress "correct" picks count toward score
                # Subtract them here
                if correct:
                    correct = ''
                    week_pts -= points
                    ytd_pts -= points
            elif in_progress != '':
                print(in_progress)
                raise Exception('Failed to parse correct class name')

            if correct == '':
                played = False
                correct = None
            elif correct == 'correct':
                correct = True
            elif correct == 'incorrect':
                correct = False
            else:
                print(correct)
                raise Exception('Failed to parse correct class name')

            all_week_pts[player_name] = week_pts
            all_ytd_pts[player_name] = ytd_pts
            all_tie_breakers[player_name] = tie_breaker

            if not played:
                if fill_remaining_teams:
                    remaining_teams.append(team)
                remaining_bets[player_name].append((team, points))
        fill_remaining_teams = False

    print('~'*50)
    subject = f'Week {week} possibilities'
    print(subject)
    print('~'*50)

    # Calculate all possibilities
    perms = list(itertools.product([False, True], repeat=len(remaining_teams)))
    results = ['Here are all the possible winners this week.\n', '-'*50]
    for perm in perms:
        perm_results = []
        perm_week_pts = all_week_pts.copy()
        for player, player_picks in remaining_bets.items():
            for game_index, player_pick in enumerate(player_picks):
                player_outcome = remaining_teams[game_index] == player_pick[0]
                if player_outcome == perm[game_index]:
                    perm_week_pts[player] += player_pick[1]

        game_results = []
        for game_index, team in enumerate(remaining_teams):
            if perm[game_index]:
                game_results.append(f'{team} wins')
            else:
                game_results.append(f'{team} lose')
        game_results = 'If ' + ', and '.join(game_results) + ':'
        perm_results.append(game_results)
        top_week_pts = perm_week_pts.most_common()
        winners = list(
            itertools.takewhile(
                lambda x: x[1] >= top_week_pts[0][1], top_week_pts)
            )
        for winner in winners:
            winner_name = winner[0]
            tie_breaker = all_tie_breakers[winner_name]
            winner_points = winner[1]
            winner_msg = f'{winner_name} wins with {winner_points} points'
            if len(winners) != 1:
                winner_msg += f' and {tie_breaker} as their tie breaker'
            winner_msg += '.'
            perm_results.append(winner_msg)
        perm_results.append('-'*50)
        results += perm_results

    # Print results
    print('!'*50)
    print(subject)
    print('!'*50)
    body = '\n'.join(results)
    print(body)

    # Send email
    driver.get(MESSAGE_URL)
    time.sleep(random.uniform(3, 4))

    subject_input = driver.find_element_by_id('subject')
    body_input = driver.find_element_by_id('body')
    subject_input.send_keys(subject)
    body_input.send_keys(body)
    driver.find_element_by_id('submitButton').click()


if __name__ == '__main__':
    main()
