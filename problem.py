# -*- coding: utf-8 -*-

from swat import CAS
import sasoptpy as so
from data import get_team_info
from data import get_player_db
from data import get_player_info
import os.path
import pandas as pd


def solve_optimal_transfer_problem(team_name, options=None):

    print('\n *** Solving problem for ', team_name, '\n')

    if options is None:
        options = {'age_limit': 33}

    team_info = get_team_info(team_name)
    
    if os.path.isfile('playerdb.pickle'):
        player_db = pd.read_pickle('playerdb.pickle')
    else:
        player_db = get_player_db()

    player_db['player_id'] = player_db.index
    player_db = player_db.set_index(['link'])
    # Remove duplicate rows
    player_db = player_db[~player_db.index.duplicated(keep='last')]

    if options and 'budget_limit' in options:
        budget = options['budget_limit']
    else:
        budget = team_info['budget']

    eligible = []
    for i, pos in enumerate(team_info['positions']):
        print('Filtering eligible candidates for', pos)
        if pos in ('RCB', 'LCB'):
            filter_pos = 'CB'
        elif pos in ('RCM', 'LCM'):
            filter_pos = 'CM'
        elif pos in ('LS', 'RS'):
            filter_pos = 'ST'
        elif pos in ('LDM', 'RDM'):
            filter_pos = 'DM'
        else:
            filter_pos = pos
        # Can play for position
        filtered = player_db[player_db['pos'].str.contains(filter_pos)]
        # Has no missing value
        filtered = filtered[filtered['value'] > 0]
        # Under budget
        filtered = filtered[filtered['value'] < budget]
        # Better than current squad member
        filtered = filtered[filtered['overall'] > team_info['ratings'][i]]
        if options and 'age_limit' in options:
            # Age limit
            filtered = filtered[filtered['age'] <= options['age_limit']]

        for id in filtered['player_id'].tolist():
            eligible.append([id, i, pos])
    
    eligible = pd.DataFrame(eligible, columns=['player_id', 'position', 'pos_str'])
    print('Total number of eligible transfers:', len(eligible))

    squad = []
    for i in range(11):
        try:
            current_member = player_db.loc[team_info['players'][i]]
        except:
            # If user is not in db, fetch player page
            print('Found a player who is not in DB!')
            current_member = get_player_info(team_info['players'][i])
            current_member['player_id'] = len(player_db['name'])
            player_db.loc[team_info['players'][i]] = [
                current_member['name'],
                None,  # img
                None,  # age
                [],  # pos
                0,  # value
                current_member['overall'],
                current_member['potential'],  # potential
                player_db['player_id'].max()+1
            ]

        print('Current squad member for ', team_info['positions'][i], ':',
              current_member['name'], ', rating', current_member['overall'])
        squad.append([i, current_member['player_id'], team_info['positions'][i], current_member['overall']])

    squad = pd.DataFrame(squad, columns=['position', 'player_id', 'pos_str', 'overall'])
    player_db = player_db[player_db['player_id'].isin(eligible['player_id'].tolist() + squad['player_id'].tolist())]
    
    # Modeling
    so.reset_globals()
    m = so.Model(name='optimal_squad_1', session=session)

    PLAYERS, (name, age, value, overall, potential) = m.read_table(
        player_db, key=['player_id'],
        columns=['name', 'age', 'value', 'overall', 'potential'], 
        col_types={'name': 'str'},
        upload=False, casout='player_list')

    ELIG, _ = m.read_table(eligible, key=['player_id', 'position'],
                            upload=False, casout='eligible_list')

    POSITIONS, (member, pos_str, c_overall) = m.read_table(
        squad, key=['position'], columns=['player_id', 'pos_str', 'overall'],
        col_types={'pos_str': 'str'},
        upload=False, casout='squad_list')

    rating = m.add_variables(POSITIONS, name='rating')
    transfer = m.add_variables(ELIG, name='transfer', vartype=so.BIN)

    m.set_objective(
        so.quick_sum(rating[j] for j in POSITIONS), name='total_rating', sense=so.MAX)

    m.add_constraint(so.quick_sum(
        transfer[i, j] * value[i] for (i, j) in ELIG) <= budget, name='budget_con')

    m.add_constraints((
       rating[j] == overall[member[j]] + so.quick_sum(
           transfer[i, j] * (overall[i] - overall[member[j]]) for (i, j2) in ELIG if j==j2) for j in POSITIONS), name='transfer_con')

    # Potential rating alternative

    # m.add_constraints(
    #     (rating[j] == potential[member[j]] + so.quick_sum(
    #          transfer[i, j] * (potential[i] - potential[member[j]]) for (i, j2) in ELIG if j==j2) for j in POSITIONS), name='potential_con')

    m.add_constraints((
        so.quick_sum(transfer[i, j] for (i2, j) in ELIG if i==i2) <= 1 for i in PLAYERS), name='only_one_position')

    m.add_constraints((
        so.quick_sum(transfer[i, j] for (i, j2) in ELIG if j==j2) <= 1 for j in POSITIONS), name='only_one_transfer')

    for j in POSITIONS:
        print(j, pos_str[j], len([1 for (i, j2) in ELIG if j==j2]))

    if team_name is None:
        m.add_constraints((
            so.quick_sum(transfer[i, j] for (i, j2) in ELIG if j==j2) == 1 for j in POSITIONS), name='transfer_one')

    m.solve()
    
    old_rating = sum(c_overall)
    print('Original squad rating:', old_rating)
    new_rating = rating.sum('*').get_value()
    print('New squad rating:', new_rating)
    new_players = []
    final_team = []
    for i, pos in enumerate(POSITIONS):
        for player in PLAYERS:
            if (player, pos) not in ELIG:
                continue
            if transfer[player, pos].get_value() > 0.5:
                print('{}: {} ({}, pot:{}), previous: {} ({}), paid: {}'.format(
                    pos_str[pos], name[player], overall[player], potential[player], name[member[pos]], c_overall[pos], value[player]
                    ))
                new_players.append(name[player])
                final_team.append([pos_str[pos], name[member[pos]],
                                  c_overall[pos], potential[member[pos]], name[player],
                                  overall[player],
                                  potential[player],
                                  value[player]])
                break
        else:
            print('{}: {} ({})'.format(pos_str[pos], name[member[pos]], c_overall[pos]))
            final_team.append([pos_str[pos], name[member[pos]], c_overall[pos], potential[member[pos]], name[member[pos]], c_overall[pos], potential[member[pos]], 0])

    final_team = pd.DataFrame(final_team, columns=['Pos', 'Old', 'Old.R', 'Old.Pot', 'New', 'New.R', 'New.Pot', 'Paid'])
    final_team = final_team.append(final_team.sum(numeric_only=True), ignore_index=True)

    money_spent = so.quick_sum(value[i] * transfer[i, j] for (i, j) in ELIG).get_value()
    efficiency = (new_rating - old_rating) / (money_spent / 1e6) if money_spent > 0 else 0
    print('Rating increase per million euro:', efficiency)
    transfer_list = ', '.join(new_players)
    return (team_name, options['age_limit'],
            old_rating, round(old_rating/11.0, 3),
            round(new_rating), round(new_rating/11.0, 3),
            budget, money_spent, efficiency,
            transfer_list, final_team)
    

if __name__ == '__main__':
    print('Connecting to CAS Server')
    global session
    session = CAS(your_cas_server, your_cas_port)
    teams = ['Manchester City',
             'Liverpool',
             'Chelsea',
             'Tottenham Hotspur',
             'Arsenal',
             'Manchester United'
             ]

    # Case 1: Solve for all teams
    options = {'age_limit': 33}
    results = [solve_optimal_transfer_problem(team, options) for team in teams]

    # Case 2: Budget limitations
    # teams = ['Liverpool']
    # results = []
    # for team in teams:
    #     for budget in [1e+7*i for i in range(21)]:
    #         options = {'age_limit': 33, 'budget_limit': budget}
    #         results.append(solve_optimal_transfer_problem(team, options))

    # Case 3: Empty Team
    # options = {'age_limit': 23, 'budget_limit': 150*1e+6}
    # results = [solve_optimal_transfer_problem(None, options)]

    pd.set_option('display.max_colwidth', 200)

    for r in results:
        print(r[-1].to_string())
        r[-1].to_csv('squads/{}_{}_{}.csv'.format(r[0], r[1], r[6]))

    df = pd.DataFrame(
        [r[:-1] for r in results], columns=[
            'Team', 'Age_Limit', 'Old Rating', 'Avg.Old', 'New Rating', 'Avg.New',
            'Budget', 'Money Spent', 'Efficiency',
            'Transfers'])

    print(df.to_string())



